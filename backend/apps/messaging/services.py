from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import verified_users
from apps.listings.models import Listing
from apps.trust import checks as trust_checks

from .models import MESSAGE_MAX_LENGTH, Conversation, ConversationParticipant, Message


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
    automated: bool = False,
) -> Message:
    """Send a message. `automated` marks the notes Deals writes for a student ("Made an offer
    of $20"), which still go out when the student can't send their own messages."""
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
    if not automated:
        trust_checks.require_can(sender, trust_checks.Kind.MESSAGING)
    for other in conversation.participants.exclude(pk=sender.pk):
        trust_checks.require_not_blocked(sender, other)
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
    return message


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
