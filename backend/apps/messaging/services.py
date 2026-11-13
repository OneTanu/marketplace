from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import verified_users
from apps.listings.models import Listing
from apps.trust import checks as trust_checks

from .models import MESSAGE_MAX_LENGTH, Conversation, ConversationParticipant, Message

# Spam limits, high enough that normal chatting never meets them.
MAX_MESSAGES_PER_MINUTE = 30
# Conversations a student starts, i.e. sends the first message in. Replying never counts, and
# neither do deal requests or opening an empty chat.
MAX_NEW_PEOPLE_PER_HOUR = 20
TOO_FAST = "You're sending messages too quickly. Wait a moment and try again."
TOO_MANY_NEW_PEOPLE = (
    "You've messaged a lot of new people in the last hour. Try again later, or keep chatting "
    "with students you've already messaged."
)


def _check_send_limits(sender: User, conversation: Conversation) -> None:
    now = timezone.now()
    sent = Message.objects.filter(sender=sender)
    if sent.filter(created_at__gte=now - timedelta(minutes=1)).count() >= MAX_MESSAGES_PER_MINUTE:
        raise ValidationError(TOO_FAST)
    if conversation.messages.exists():
        return  # a reply or a follow-up, not starting a conversation
    first_in_conversation = (
        Message.objects.filter(conversation=OuterRef("conversation")).order_by("id").values("id")
    )
    started = (
        sent.filter(created_at__gte=now - timedelta(hours=1))
        .annotate(first_id=Subquery(first_in_conversation[:1]))
        .filter(pk=F("first_id"))
        .count()
    )
    if started >= MAX_NEW_PEOPLE_PER_HOUR:
        raise ValidationError(TOO_MANY_NEW_PEOPLE)


def direct_key(first: User, second: User) -> str:
    low, high = sorted((first.pk, second.pk))
    return f"{low}:{high}"


@transaction.atomic
def start_direct_conversation(*, sender: User, recipient: User) -> Conversation:
    if sender.pk == recipient.pk:
        raise ValidationError("You cannot message yourself.")
    trust_checks.require_not_blocked(sender, recipient)
    if verified_users().filter(pk__in=[sender.pk, recipient.pk]).count() != 2:
        raise ValidationError("Both students must have active, verified accounts.")
    conversation, created = Conversation.objects.get_or_create(
        direct_key=direct_key(sender, recipient),
        defaults={"created_by": sender},
    )
    if created:
        ConversationParticipant.objects.bulk_create(
            [
                ConversationParticipant(conversation=conversation, user=sender),
                ConversationParticipant(conversation=conversation, user=recipient),
            ]
        )
    return conversation


@transaction.atomic
def send_message(
    *,
    conversation: Conversation,
    sender: User,
    body: str,
    listing: Listing | None = None,
) -> Message:
    """Send a student's message. Deals never writes into chats: requests and their updates
    live on the Deals page and in notifications."""
    body = body.strip()
    if not body:
        raise ValidationError("Message cannot be empty.")
    if len(body) > MESSAGE_MAX_LENGTH:
        raise ValidationError(f"Messages may contain at most {MESSAGE_MAX_LENGTH:,} characters.")
    if not verified_users().filter(pk=sender.pk).exists():
        raise ValidationError("Your account must be active and verified to send messages.")
    membership = ConversationParticipant.objects.filter(
        conversation=conversation, user=sender
    ).first()
    if membership is None:
        raise ValidationError("You are not a participant in this conversation.")
    trust_checks.require_can(sender, trust_checks.Kind.MESSAGING)
    if conversation.participants.exclude(pk=sender.pk).filter(is_active=False).exists():
        # Deactivated, suspended, or banned: the conversation stays as history, read-only.
        raise ValidationError("This account isn't available right now.")
    for other in conversation.participants.exclude(pk=sender.pk):
        trust_checks.require_not_blocked(sender, other)
    _check_send_limits(sender, conversation)
    if listing is not None:
        if listing.status == Listing.Status.REMOVED:
            raise ValidationError("This listing is no longer available.")
        if not conversation.participants.filter(pk=listing.seller_id).exists():
            raise ValidationError("This listing does not belong in this conversation.")
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        listing=listing,
    )
    Conversation.objects.filter(pk=conversation.pk).update(
        last_message_at=message.created_at,
        updated_at=timezone.now(),
    )
    membership.last_read_message = message
    membership.save(update_fields=["last_read_message"])
    _queue_unread_emails(conversation, message)
    return message


def _queue_unread_emails(conversation: Conversation, message: Message) -> None:
    """Email each other participant about this message if it's the first one they haven't
    read (their conversation just went from read to unread)."""
    from apps.notifications.services import queue_unread_message_email

    for other in conversation.participant_records.exclude(user_id=message.sender_id):
        already_unread = (
            conversation.messages.filter(pk__lt=message.pk, pk__gt=other.last_read_message_id or 0)
            .exclude(sender_id=other.user_id)
            .exists()
        )
        if not already_unread:
            queue_unread_message_email(recipient_id=other.user_id, message_id=message.pk)


@transaction.atomic
def mark_conversation_read(
    *, conversation: Conversation, user: User, message: Message | None = None
) -> ConversationParticipant:
    membership = ConversationParticipant.objects.get(conversation=conversation, user=user)
    target = message or conversation.messages.order_by("-id").first()
    if target is None:
        return membership
    if target.conversation_id != conversation.pk:
        raise ValidationError("That message does not belong to this conversation.")
    if membership.last_read_message_id and target.pk <= membership.last_read_message_id:
        return membership
    membership.last_read_message = target
    membership.save(update_fields=["last_read_message"])
    return membership
