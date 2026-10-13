"""Reports, blocks, and moderation actions.

Reports never punish anyone by themselves. They gather evidence into a case; a moderator
reviews it and decides. The one automatic step is hiding a listing that several students
report as a weapon or drugs, until a moderator looks at it.

Every staff action needs a reason and writes a permanent ModerationAction.
"""

from datetime import datetime, timedelta
from pathlib import PurePosixPath
from statistics import median

from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.listings import services as listing_services
from apps.listings.models import Listing
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.notifications import services as notification_services
from apps.reviews.models import Review
from apps.schools.services import school_for_email

from . import checks
from .models import (
    Appeal,
    BannedEmail,
    Block,
    EvidenceAccess,
    EvidenceFile,
    EvidenceSnapshot,
    InfoRequest,
    ModerationAction,
    ModerationCase,
    ModeratorScope,
    Report,
    UserRestriction,
)

REPORTS_PER_DAY = 20
MAX_EVIDENCE_MESSAGES = 20
# Distinct students reporting a listing as one of these hides it until a moderator reviews it.
AUTO_HIDE_REPORTERS = 3
AUTO_HIDE_CATEGORIES = {Report.ProhibitedCategory.WEAPON, Report.ProhibitedCategory.DRUGS}

MODERATOR = "Moderator"
SENIOR_MODERATOR = "Senior moderator"
SCHOOL_ADMIN = "School administrator"

OPEN_CASE_STATUSES = [
    ModerationCase.Status.OPEN,
    ModerationCase.Status.INVESTIGATING,
    ModerationCase.Status.APPEALED,
]
Kind = UserRestriction.Kind
Reason = Report.Reason


# --- Blocking ---


@transaction.atomic
def block_user(*, blocker: User, blocked: User) -> Block:
    """Block another student. Open requests and deals between the two are canceled; from now
    on neither can message, deal, or trade with the other."""
    if blocker.pk == blocked.pk:
        raise ValidationError("You can't block yourself.")
    block, _ = Block.objects.get_or_create(blocker=blocker, blocked=blocked)
    deal_services.cancel_deals_between(
        blocker, blocked, reason="One student blocked the other.", announce=False
    )
    return block


def unblock_user(*, blocker: User, blocked: User) -> None:
    Block.objects.filter(blocker=blocker, blocked=blocked).delete()


# --- Reporting ---


def _priority(reason: str, category: str) -> int:
    if reason == Reason.UNSAFE_MEETUP or (
        reason == Reason.PROHIBITED_ITEM and category in AUTO_HIDE_CATEGORIES
    ):
        return ModerationCase.Priority.URGENT
    if reason in {Reason.PROHIBITED_ITEM, Reason.HARASSMENT, Reason.SCAM, Reason.COUNTERFEIT}:
        return ModerationCase.Priority.HIGH
    return ModerationCase.Priority.NORMAL


def _other_participant(conversation: Conversation, user: User) -> User:
    other = conversation.participants.exclude(pk=user.pk).first()
    if other is None:
        raise ValidationError("There's no one else in this conversation.")
    return other


def _resolve_target(reporter: User, target_type: str, target_id: int, message_ids) -> dict:
    """What's being reported, who it's about, and which messages count as evidence. Students
    can only report things they can see: their own conversations and deals, public profiles,
    listings, and reviews."""
    T = Report.TargetType
    mine = ConversationParticipant.objects.filter(user=reporter).values("conversation_id")
    try:
        if target_type == T.LISTING:
            listing = Listing.objects.select_related("seller", "school").get(
                pk=target_id,
                status__in=[Listing.Status.AVAILABLE, Listing.Status.PENDING, Listing.Status.SOLD],
            )
            return {"listing": listing, "reported_user": listing.seller, "school": listing.school}
        if target_type == T.USER:
            user = User.objects.select_related("school").get(pk=target_id, is_active=True)
            return {"reported_user": user, "school": user.school}
        if target_type == T.MESSAGE:
            message = Message.objects.select_related("sender__school").get(
                pk=target_id, conversation_id__in=mine
            )
            return {
                "message": message,
                "conversation": message.conversation,
                "reported_user": message.sender,
                "school": message.sender.school,
                "evidence": [message],
            }
        if target_type == T.CONVERSATION:
            conversation = Conversation.objects.get(pk=target_id, id__in=mine)
            other = _other_participant(conversation, reporter)
            ids = list(dict.fromkeys(message_ids))
            if not ids:
                raise ValidationError(
                    {"message_ids": "Choose the messages that show what happened."}
                )
            if len(ids) > MAX_EVIDENCE_MESSAGES:
                raise ValidationError(
                    {"message_ids": f"Choose up to {MAX_EVIDENCE_MESSAGES} messages."}
                )
            evidence = list(conversation.messages.filter(pk__in=ids).order_by("created_at"))
            if len(evidence) != len(ids):
                raise ValidationError({"message_ids": "Choose messages from this conversation."})
            return {
                "conversation": conversation,
                "reported_user": other,
                "school": other.school,
                "evidence": evidence,
            }
        if target_type == T.DEAL:
            deal = Deal.objects.select_related("buyer__school", "seller__school", "listing").get(
                Q(buyer=reporter) | Q(seller=reporter), pk=target_id
            )
            other = deal.seller if deal.buyer_id == reporter.pk else deal.buyer
            return {"deal": deal, "reported_user": other, "school": deal.listing.school}
        if target_type == T.REVIEW:
            review = Review.objects.select_related("author__school").get(pk=target_id)
            return {
                "review": review,
                "reported_user": review.author,
                "school": review.author.school,
            }
    except (
        Listing.DoesNotExist,
        User.DoesNotExist,
        Message.DoesNotExist,
        Conversation.DoesNotExist,
        Deal.DoesNotExist,
        Review.DoesNotExist,
    ) as exc:
        raise ValidationError("We couldn't find what you're reporting.") from exc
    raise ValidationError({"target_type": "Choose what you're reporting."})


_TARGET_FIELDS = ("listing", "message", "conversation", "deal", "review")


def _target_filter(target_type: str, target: dict) -> dict:
    """The fields that identify the reported thing, for spotting duplicate reports."""
    if target_type == Report.TargetType.USER:
        return {
            "reported_user": target["reported_user"],
            "listing": None,
            "message": None,
            "conversation": None,
            "deal": None,
            "review": None,
        }
    field = {
        Report.TargetType.LISTING: "listing",
        Report.TargetType.MESSAGE: "message",
        Report.TargetType.CONVERSATION: "conversation",
        Report.TargetType.DEAL: "deal",
        Report.TargetType.REVIEW: "review",
    }[target_type]
    return {field: target[field]}


def _case_for(*, reported_user: User, listing: Listing | None, school, priority: int):
    """The open case this report joins: the listing's, or else the reported user's."""
    cases = ModerationCase.objects.select_for_update().filter(status__in=OPEN_CASE_STATUSES)
    case = (
        cases.filter(listing=listing).first()
        if listing is not None
        else cases.filter(subject_user=reported_user, listing__isnull=True).first()
    )
    if case is None:
        case = ModerationCase.objects.create(
            subject_user=reported_user, listing=listing, school=school, priority=priority
        )
    elif priority < case.priority:
        case.priority = priority
        case.save(update_fields=["priority", "updated_at"])
    else:
        return case
    if priority == ModerationCase.Priority.URGENT:
        _alert_moderators(case, f"Urgent case #{case.pk}", "A report needs review soon.")
    return case


@transaction.atomic
def create_report(
    *,
    reporter: User,
    target_type: str,
    target_id: int,
    reason: str,
    details: str = "",
    prohibited_category: str = "",
    message_ids=(),
    block: bool = False,
) -> Report:
    """A student reports a listing, profile, message, conversation, deal, or review. Evidence
    is copied at once, so later edits or deletions don't erase it."""
    if reason not in Reason.values:
        raise ValidationError({"reason": "Choose a reason."})
    if prohibited_category and reason != Reason.PROHIBITED_ITEM:
        raise ValidationError({"prohibited_category": "Only for prohibited items."})
    if prohibited_category and prohibited_category not in Report.ProhibitedCategory.values:
        raise ValidationError({"prohibited_category": "Choose what kind of prohibited item."})
    details = details.strip()
    if len(details) > 1000:
        raise ValidationError({"details": "Keep details under 1,000 characters."})
    since = timezone.now() - timedelta(days=1)
    if Report.objects.filter(reporter=reporter, created_at__gte=since).count() >= REPORTS_PER_DAY:
        raise ValidationError("You've sent a lot of reports today. Try again tomorrow.")

    target = _resolve_target(reporter, target_type, target_id, message_ids)
    reported_user = target["reported_user"]
    if reported_user.pk == reporter.pk:
        raise ValidationError("You can't report yourself.")
    if Report.objects.filter(
        reporter=reporter,
        target_type=target_type,
        status=Report.Status.OPEN,
        **_target_filter(target_type, target),
    ).exists():
        raise ValidationError("You've already reported this. Our team will review it.")

    listing = target.get("listing")
    case = _case_for(
        reported_user=reported_user,
        listing=listing,
        school=target["school"],
        priority=_priority(reason, prohibited_category),
    )
    report = Report.objects.create(
        case=case,
        reporter=reporter,
        reported_user=reported_user,
        school=target["school"],
        target_type=target_type,
        reason=reason,
        prohibited_category=prohibited_category,
        details=details,
        **{field: target.get(field) for field in _TARGET_FIELDS},
    )
    evidence = target.get("evidence", [])
    report.evidence_messages.set(evidence)
    _snapshot(report, target, evidence)

    if listing is not None:
        _maybe_auto_hide(listing, case)
    if block:
        block_user(blocker=reporter, blocked=reported_user)
    return report


# --- Evidence ---


def _snapshot(report: Report, target: dict, evidence: list[Message]) -> None:
    if listing := target.get("listing"):
        details = getattr(listing, "item_details", None)
        snapshot = EvidenceSnapshot.objects.create(
            report=report,
            kind="listing",
            source_id=listing.pk,
            data={
                "title": listing.title,
                "description": listing.description,
                "price_cents": listing.price_cents,
                "status": listing.status,
                "category": str(listing.category),
                "seller": listing.seller.username,
                "condition": getattr(details, "condition", ""),
                "brand": getattr(details, "brand", ""),
            },
        )
        for photo in listing.photos.all():
            _copy_file(snapshot, photo.image)
    for message in evidence:
        EvidenceSnapshot.objects.create(
            report=report,
            kind="message",
            source_id=message.pk,
            data={
                "sender": message.sender.username,
                "body": message.body,
                "sent_at": message.created_at.isoformat(),
                "conversation_id": message.conversation_id,
            },
        )
    if target["reported_user"] and report.target_type == Report.TargetType.USER:
        user = target["reported_user"]
        EvidenceSnapshot.objects.create(
            report=report,
            kind="profile",
            source_id=user.pk,
            data={
                "username": user.username,
                "first_name": user.first_name,
                "profile_description": user.profile_description,
                "instagram_handle": user.instagram_handle,
            },
        )
    if deal := target.get("deal"):
        EvidenceSnapshot.objects.create(
            report=report,
            kind="deal",
            source_id=deal.pk,
            data={
                "listing": deal.listing.title,
                "kind": deal.kind,
                "status": deal.status,
                "agreed_amount_cents": deal.agreed_amount_cents,
                "events": [
                    {
                        "type": event.event_type,
                        "actor_id": event.actor_id,
                        "data": event.data,
                        "at": event.created_at.isoformat(),
                    }
                    for event in deal.events.all()
                ],
                "meetups": [
                    {
                        "spot": proposal.meeting_spot.name,
                        "starts_at": proposal.starts_at.isoformat(),
                        "status": proposal.status,
                        "proposed_by_id": proposal.proposed_by_id,
                    }
                    for proposal in deal.meetup_proposals.select_related("meeting_spot")
                ],
            },
        )
    if review := target.get("review"):
        EvidenceSnapshot.objects.create(
            report=report,
            kind="review",
            source_id=review.pk,
            data={
                "author": review.author.username,
                "subject_id": review.subject_id,
                "rating": review.rating,
                "comment": review.comment,
                "deal_id": review.deal_id,
            },
        )


def _copy_file(snapshot: EvidenceSnapshot, source) -> None:
    """Copy a stored file into the evidence store. A missing original is skipped; the rest of
    the snapshot still stands."""
    try:
        with source.open("rb") as handle:
            content = handle.read()
    except (FileNotFoundError, ValueError):
        return
    evidence = EvidenceFile(snapshot=snapshot, original_name=source.name)
    evidence.file.save(PurePosixPath(source.name).name, ContentFile(content), save=True)


def record_evidence_access(*, staff: User, case: ModerationCase, viewed: str, reason: str = ""):
    """Log that a staff member looked at evidence. Viewing more than the reported messages
    needs a reason."""
    _require_staff(staff, case)
    return EvidenceAccess.objects.create(staff=staff, case=case, viewed=viewed, reason=reason)


def _maybe_auto_hide(listing: Listing, case: ModerationCase) -> None:
    listing.refresh_from_db(fields=["status"])
    if listing.status == Listing.Status.REMOVED:
        return
    reporters = (
        Report.objects.filter(
            listing=listing,
            reason=Reason.PROHIBITED_ITEM,
            prohibited_category__in=AUTO_HIDE_CATEGORIES,
            status=Report.Status.OPEN,
        )
        .values("reporter")
        .distinct()
        .count()
    )
    if reporters < AUTO_HIDE_REPORTERS:
        return
    reason = (
        f"Hidden automatically after {reporters} students reported it as a weapon or drugs. "
        "Restore it if the review finds nothing wrong."
    )
    _take_down(listing, reason)
    ModerationAction.objects.create(
        case=case,
        kind=ModerationAction.Kind.AUTO_HIDE_LISTING,
        reason=reason,
        target_user=listing.seller,
        listing=listing,
    )
    if case.priority != ModerationCase.Priority.URGENT:
        case.priority = ModerationCase.Priority.URGENT
        case.save(update_fields=["priority", "updated_at"])


def _take_down(listing: Listing, reason: str) -> None:
    """Cancel every open deal that holds the listing, then remove it."""
    deal_services.cancel_deals_for_listing(listing, reason=reason)
    listing.refresh_from_db(fields=["status"])
    if listing.status != Listing.Status.REMOVED:
        listing_services.remove_by_moderation(listing)


# --- Staff roles, school scope, and conflicts of interest ---


def _groups(user: User) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


def is_moderator(user: User) -> bool:
    if not (user.is_authenticated and user.is_active and user.is_staff):
        return False
    return user.is_superuser or bool(_groups(user) & {MODERATOR, SENIOR_MODERATOR})


def is_senior_moderator(user: User) -> bool:
    return is_moderator(user) and (user.is_superuser or SENIOR_MODERATOR in _groups(user))


def moderated_school_ids(user: User) -> set[int] | None:
    """The schools a staff member moderates, or None for every school."""
    if user.is_superuser:
        return None
    scope = ModeratorScope.objects.filter(user=user).first()
    if scope is None:
        return None
    ids = set(scope.schools.values_list("id", flat=True))
    return ids or None


def visible_cases(staff: User):
    """The cases a moderator can see: within their schools, and never cases about themselves."""
    if not is_moderator(staff):
        return ModerationCase.objects.none()
    cases = ModerationCase.objects.exclude(subject_user=staff)
    schools = moderated_school_ids(staff)
    return cases if schools is None else cases.filter(school_id__in=schools)


def conflict_of_interest(staff: User, case: ModerationCase) -> tuple[str, bool] | None:
    """Why `staff` shouldn't act on this case, and whether a senior moderator can override it.
    Being the subject or a reporter can never be overridden."""
    if staff.pk == case.subject_user_id:
        return "it's about you", False
    if case.reports.filter(reporter=staff).exists():
        return "you reported it", False
    subject = case.subject_user_id
    if Deal.objects.filter(
        Q(buyer=staff, seller_id=subject) | Q(buyer_id=subject, seller=staff)
    ).exists():
        return "you've had a deal with this student", True
    shared = ConversationParticipant.objects.filter(user=staff).values("conversation_id")
    if ConversationParticipant.objects.filter(user_id=subject, conversation_id__in=shared).exists():
        return "you've messaged this student", True
    return None


def _require_staff(
    staff: User, case: ModerationCase | None, *, senior: bool = False, override_reason: str = ""
) -> None:
    if not is_moderator(staff):
        raise PermissionDenied("Only moderators can do this.")
    if senior and not is_senior_moderator(staff):
        raise PermissionDenied("Only a senior moderator can do this.")
    if case is None:
        return
    schools = moderated_school_ids(staff)
    if schools is not None and case.school_id not in schools:
        raise PermissionDenied("This case is outside the schools you moderate.")
    conflict = conflict_of_interest(staff, case)
    if conflict is None:
        return
    why, overridable = conflict
    if not (overridable and override_reason.strip() and is_senior_moderator(staff)):
        raise PermissionDenied(
            f"You can't act on this case because {why}. Pass it to another moderator."
        )
    _record(staff, case, ModerationAction.Kind.CONFLICT_OVERRIDE, override_reason, conflict=why)


def _record(staff, case, kind, reason, *, target_user=None, listing=None, user_message="", **data):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Give a reason for this action."})
    action = ModerationAction.objects.create(
        case=case,
        actor=staff,
        kind=kind,
        reason=reason,
        user_message=user_message,
        target_user=target_user,
        listing=listing,
        data=data,
    )
    if case is not None:
        ModerationCase.objects.filter(pk=case.pk).update(updated_at=timezone.now())
    return action


def _require_involved(case: ModerationCase, user: User) -> None:
    """Consequences go to the case's subject, or to a reporter (e.g. for false reports)."""
    if user.pk != case.subject_user_id and not case.reports.filter(reporter=user).exists():
        raise ValidationError("That student isn't part of this case.")


# --- Notices and alerts ---

APPEAL_WINDOW = timedelta(days=14)
STANDING_LINK = "/profile/standing"
# Consequences a student is told about, and can appeal.
NOTICE_KINDS = {
    ModerationAction.Kind.WARN,
    ModerationAction.Kind.RESTRICT,
    ModerationAction.Kind.REMOVE_LISTING,
    ModerationAction.Kind.SUSPEND,
    ModerationAction.Kind.BAN,
}
# Outcomes that count as "we took action" for a reporter.
ENFORCEMENT_KINDS = NOTICE_KINDS | {ModerationAction.Kind.AUTO_HIDE_LISTING}
PAUSED = {
    Kind.SELLING: "Selling",
    Kind.MESSAGING: "Messaging",
    Kind.DEALS: "Buying and making deals",
}


def _case_reasons(case: ModerationCase) -> str:
    reasons = case.reports.values_list("reason", flat=True).distinct()
    labels = sorted({Reason(reason).label.lower() for reason in reasons})
    return ", ".join(labels) or "your account"


def _until(moment: datetime | None) -> str:
    if moment is None:
        return ""
    return f" until {timezone.localtime(moment):%b %-d, %-I:%M %p}"


def _default_message(kind: str, case: ModerationCase, **context) -> str:
    about = f"After reviewing reports about {_case_reasons(case)}"
    if kind == ModerationAction.Kind.WARN:
        return (
            f"{about}, a Tanu moderator is giving your account a warning. Please make sure what "
            "you post and send follows Tanu's community guidelines. Further problems can lead "
            "to restrictions."
        )
    if kind == ModerationAction.Kind.RESTRICT:
        paused = PAUSED[context["restriction"]]
        return (
            f"{about}, {paused.lower()} is paused on your account{_until(context['until'])}. "
            "Anything already in progress, like a Pending handoff, can still be finished."
        )
    if kind == ModerationAction.Kind.SUSPEND:
        return (
            f"{about}, your Tanu account is suspended{_until(context['until'])}. Your open "
            "deals were canceled and your listings are hidden until then."
        )
    if kind == ModerationAction.Kind.BAN:
        return f"{about}, your Tanu account has been permanently closed."
    if kind == ModerationAction.Kind.REMOVE_LISTING:
        title = context["listing"].title
        return (
            f"Your listing “{title}” was removed because it doesn't follow Tanu's community "
            f"guidelines (reported for {_case_reasons(case)})."
        )
    return ""


def _send_notice(action: ModerationAction, title: str) -> None:
    """Tell the affected student what happened and how to appeal. Suspended and banned students
    can't sign in, so they're emailed."""
    signed_out = action.kind in {ModerationAction.Kind.SUSPEND, ModerationAction.Kind.BAN}
    appeal = (
        "If you think this is a mistake, reply to this email to ask for a review."
        if signed_out
        else f"If you think this is a mistake, you can appeal within {APPEAL_WINDOW.days} days "
        "from your Account status page."
    )
    notification_services.notify(
        action.target_user,
        kind=notification_services.Kind.MODERATION_NOTICE,
        title=title,
        body=f"{action.user_message}\n\n{appeal}",
        link=STANDING_LINK,
        email=signed_out,
    )


def _alert_moderators(
    case: ModerationCase, title: str, body: str = "", *, seniors_only=False, exclude=()
) -> None:
    """Tell moderators who could take the case: in its school, without a conflict."""
    for moderator in moderators():
        if moderator.pk in exclude or (seniors_only and not is_senior_moderator(moderator)):
            continue
        schools = moderated_school_ids(moderator)
        if schools is not None and case.school_id not in schools:
            continue
        if conflict_of_interest(moderator, case) is not None:
            continue
        notification_services.notify(
            moderator,
            kind=notification_services.Kind.STAFF_ALERT,
            title=title,
            body=body,
            link=f"/moderation/cases/{case.pk}",
        )


# --- Case handling ---


@transaction.atomic
def add_note(
    *, staff: User, case: ModerationCase, note: str, override_reason: str = ""
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    return _record(staff, case, ModerationAction.Kind.NOTE, note)


@transaction.atomic
def assign_case(
    *,
    staff: User,
    case: ModerationCase,
    assignee: User,
    reason: str = "Assigned",
    override_reason: str = "",
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    if not is_moderator(assignee):
        raise ValidationError("Assign the case to a moderator.")
    conflict = conflict_of_interest(assignee, case)
    if conflict is not None:
        raise ValidationError(f"@{assignee.username} can't take this case because {conflict[0]}.")
    case.assigned_to = assignee
    if case.status == ModerationCase.Status.OPEN:
        case.status = ModerationCase.Status.INVESTIGATING
    case.save(update_fields=["assigned_to", "status", "updated_at"])
    action = _record(staff, case, ModerationAction.Kind.ASSIGN, reason, assignee_id=assignee.pk)
    if assignee.pk != staff.pk:
        notification_services.notify(
            assignee,
            kind=notification_services.Kind.STAFF_ALERT,
            title=f"Case #{case.pk} was assigned to you",
            body=f"@{staff.username}: {action.reason}",
            link=f"/moderation/cases/{case.pk}",
        )
    return action


@transaction.atomic
def escalate_case(
    *, staff: User, case: ModerationCase, reason: str, override_reason: str = ""
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    case.escalated = True
    case.save(update_fields=["escalated", "updated_at"])
    action = _record(staff, case, ModerationAction.Kind.ESCALATE, reason)
    _alert_moderators(
        case, f"Case #{case.pk} was escalated", action.reason, seniors_only=True, exclude={staff.pk}
    )
    return action


def _close(staff, case, kind, reason) -> ModerationAction:
    action = _record(staff, case, kind, reason, target_user=case.subject_user)
    reporters = User.objects.filter(
        reports_made__case=case, reports_made__status=Report.Status.OPEN
    ).distinct()
    acted = case.actions.filter(kind__in=ENFORCEMENT_KINDS).exists()
    for reporter in reporters:
        notification_services.notify(
            reporter,
            kind=notification_services.Kind.REPORT_UPDATE,
            title="Update on your report",
            body=(
                "We reviewed your report and took action. Thanks for helping keep Tanu safe."
                if acted
                else "We reviewed your report and didn't find a violation of Tanu's "
                "community guidelines. Thanks for letting us know."
            ),
        )
    case.status = ModerationCase.Status.RESOLVED
    case.resolved_at = timezone.now()
    case.save(update_fields=["status", "resolved_at", "updated_at"])
    case.reports.update(status=Report.Status.RESOLVED)
    return action


@transaction.atomic
def dismiss_case(
    *, staff: User, case: ModerationCase, reason: str, override_reason: str = ""
) -> ModerationAction:
    """No violation found."""
    _require_staff(staff, case, override_reason=override_reason)
    return _close(staff, case, ModerationAction.Kind.DISMISS, reason)


@transaction.atomic
def resolve_case(
    *, staff: User, case: ModerationCase, reason: str, override_reason: str = ""
) -> ModerationAction:
    """Close a case after acting on it."""
    _require_staff(staff, case, override_reason=override_reason)
    return _close(staff, case, ModerationAction.Kind.RESOLVE, reason)


@transaction.atomic
def request_info(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    question: str,
    override_reason: str = "",
) -> InfoRequest:
    """Ask someone in the case (the reported student or a reporter) a follow-up question."""
    _require_staff(staff, case, override_reason=override_reason)
    _require_involved(case, user)
    action = _record(staff, case, ModerationAction.Kind.REQUEST_INFO, question, target_user=user)
    info_request = InfoRequest.objects.create(
        case=case, recipient=user, asked_by=staff, question=action.reason
    )
    notification_services.notify(
        user,
        kind=notification_services.Kind.INFO_REQUEST,
        title="A Tanu moderator has a question for you",
        body=f"{action.reason}\n\nAnswer it from your Account status page.",
        link=STANDING_LINK,
    )
    return info_request


@transaction.atomic
def answer_info_request(*, user: User, info_request_id: int, answer: str) -> InfoRequest:
    info_request = (
        InfoRequest.objects.select_for_update(of=("self",))
        .filter(pk=info_request_id, recipient=user)
        .select_related("case")
        .first()
    )
    if info_request is None:
        raise ValidationError("We couldn't find that question.")
    if info_request.answered_at is not None:
        raise ValidationError("You've already answered this question.")
    answer = answer.strip()
    if not answer:
        raise ValidationError({"answer": "Write an answer."})
    if len(answer) > 2000:
        raise ValidationError({"answer": "Keep your answer under 2,000 characters."})
    info_request.answer = answer
    info_request.answered_at = timezone.now()
    info_request.save(update_fields=["answer", "answered_at"])
    case = info_request.case
    ModerationAction.objects.create(
        case=case,
        actor=user,
        kind=ModerationAction.Kind.INFO_RECEIVED,
        reason=answer,
        target_user=user,
        data={"info_request_id": info_request.pk},
    )
    notification_services.notify(
        case.assigned_to or info_request.asked_by,
        kind=notification_services.Kind.STAFF_ALERT,
        title=f"@{user.username} answered your question on case #{case.pk}",
        body=answer,
        link=f"/moderation/cases/{case.pk}",
    )
    return info_request


# --- Listings ---


@transaction.atomic
def remove_listing(
    *,
    staff: User,
    case: ModerationCase,
    listing: Listing,
    reason: str,
    user_message: str = "",
    override_reason: str = "",
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    message = user_message.strip() or _default_message(
        ModerationAction.Kind.REMOVE_LISTING, case, listing=listing
    )
    action = _record(
        staff,
        case,
        ModerationAction.Kind.REMOVE_LISTING,
        reason,
        target_user=listing.seller,
        listing=listing,
        user_message=message,
    )
    _take_down(listing, reason)
    _send_notice(action, "A listing of yours was removed")
    return action


@transaction.atomic
def restore_listing(
    *, staff: User, case: ModerationCase, listing: Listing, reason: str, override_reason: str = ""
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    action = _record(
        staff,
        case,
        ModerationAction.Kind.RESTORE_LISTING,
        reason,
        target_user=listing.seller,
        listing=listing,
    )
    listing_services.restore_by_moderation(listing)
    notification_services.notify(
        listing.seller,
        kind=notification_services.Kind.MODERATION_NOTICE,
        title="Your listing is back",
        body=f"After a review, “{listing.title}” is available again.",
        link=f"/listings/{listing.pk}",
    )
    return action


# --- Account consequences: warning -> restriction -> suspension -> ban ---


@transaction.atomic
def warn_user(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    reason: str,
    user_message: str = "",
    override_reason: str = "",
) -> ModerationAction:
    _require_staff(staff, case, override_reason=override_reason)
    _require_involved(case, user)
    message = user_message.strip() or _default_message(ModerationAction.Kind.WARN, case)
    action = _record(
        staff, case, ModerationAction.Kind.WARN, reason, target_user=user, user_message=message
    )
    _send_notice(action, "A warning from Tanu's moderators")
    return action


def _restriction(staff, case, user, kind, reason, expires_at, user_message) -> UserRestriction:
    if expires_at is not None and expires_at <= timezone.now():
        raise ValidationError({"expires_at": "Choose a time in the future."})
    action_kind = {
        Kind.SUSPENSION: ModerationAction.Kind.SUSPEND,
        Kind.BAN: ModerationAction.Kind.BAN,
    }.get(kind, ModerationAction.Kind.RESTRICT)
    message = user_message.strip() or _default_message(
        action_kind, case, restriction=kind, until=expires_at
    )
    action = _record(
        staff,
        case,
        action_kind,
        reason,
        target_user=user,
        user_message=message,
        restriction=kind,
        expires_at=expires_at.isoformat() if expires_at else None,
    )
    restriction = UserRestriction.objects.create(
        user=user, kind=kind, reason=action.reason, action=action, expires_at=expires_at
    )
    titles = {
        ModerationAction.Kind.SUSPEND: f"Your Tanu account is suspended{_until(expires_at)}",
        ModerationAction.Kind.BAN: "Your Tanu account has been closed",
    }
    _send_notice(
        action, titles.get(action_kind, f"{PAUSED.get(kind, kind)} paused{_until(expires_at)}")
    )
    return restriction


@transaction.atomic
def restrict_user(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    kind: str,
    reason: str,
    expires_at: datetime | None = None,
    user_message: str = "",
    override_reason: str = "",
) -> UserRestriction:
    """Take away one feature (selling, messaging, or deals). Pending deals can still finish."""
    _require_staff(staff, case, override_reason=override_reason)
    _require_involved(case, user)
    if kind not in {Kind.SELLING, Kind.MESSAGING, Kind.DEALS}:
        raise ValidationError({"kind": "Choose selling, messaging, or deals."})
    return _restriction(staff, case, user, kind, reason, expires_at, user_message)


@transaction.atomic
def suspend_user(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    reason: str,
    until: datetime,
    user_message: str = "",
    override_reason: str = "",
) -> UserRestriction:
    """Switch the account off until `until`. Their open deals, including Pending ones, are
    canceled so nobody meets a suspended student; their listings are hidden meanwhile."""
    _require_staff(staff, case, senior=True, override_reason=override_reason)
    _require_involved(case, user)
    if until is None:
        raise ValidationError({"until": "Choose when the suspension ends."})
    restriction = _restriction(staff, case, user, Kind.SUSPENSION, reason, until, user_message)
    account_services.set_account_active(user, False)
    deal_services.cancel_deals_for_user(user, reason="A student in this deal was suspended.")
    from .tasks import end_suspension

    end_suspension.configure(schedule_at=until).defer(restriction_id=restriction.pk)
    return restriction


@transaction.atomic
def ban_user(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    reason: str,
    user_message: str = "",
    override_reason: str = "",
) -> UserRestriction:
    """Permanently switch the account off, cancel its deals, remove its listings, and refuse
    signup for its emails (and the same name at the school's other domains)."""
    _require_staff(staff, case, senior=True, override_reason=override_reason)
    _require_involved(case, user)
    restriction = _restriction(staff, case, user, Kind.BAN, reason, None, user_message)
    account_services.set_account_active(user, False)
    deal_services.cancel_deals_for_user(user, reason="A student in this deal was banned.")
    for listing in Listing.objects.filter(
        seller=user, status__in=[Listing.Status.AVAILABLE, Listing.Status.PENDING]
    ):
        _take_down(listing, reason="The seller was banned.")
    emails = {address.email for address in EmailAddress.objects.filter(user=user)} | {user.email}
    for email in emails:
        school = school_for_email(email) or user.school
        if school is None:
            continue
        BannedEmail.objects.get_or_create(
            school=school,
            local_part=email.rsplit("@", 1)[0].lower(),
            defaults={"email": email, "action": restriction.action},
        )
    return restriction


def _reactivate_if_clear(user: User) -> None:
    still_off = checks.active_restrictions(user).filter(kind__in=[Kind.SUSPENSION, Kind.BAN])
    if not still_off.exists():
        account_services.set_account_active(user, True)


def _lift(restriction: UserRestriction, staff: User) -> None:
    restriction.lifted_at = timezone.now()
    restriction.lifted_by = staff
    restriction.save(update_fields=["lifted_at", "lifted_by"])
    if restriction.kind == Kind.BAN:
        BannedEmail.objects.filter(action=restriction.action).delete()
    if restriction.kind in {Kind.SUSPENSION, Kind.BAN}:
        _reactivate_if_clear(restriction.user)


@transaction.atomic
def lift_restriction(
    *, staff: User, restriction: UserRestriction, reason: str, case: ModerationCase | None = None
) -> UserRestriction:
    """End a restriction early. Lifting a suspension or ban needs a senior moderator."""
    senior = restriction.kind in {Kind.SUSPENSION, Kind.BAN}
    _require_staff(staff, case, senior=senior)
    if restriction.lifted_at is not None:
        raise ValidationError("This restriction was already lifted.")
    _record(
        staff,
        case,
        ModerationAction.Kind.LIFT_RESTRICTION,
        reason,
        target_user=restriction.user,
        restriction_id=restriction.pk,
    )
    _lift(restriction, staff)
    notification_services.notify(
        restriction.user,
        kind=notification_services.Kind.MODERATION_NOTICE,
        title=f"{restriction.get_kind_display()} restriction lifted",
        body="A moderator lifted a restriction on your account.",
        link=STANDING_LINK,
        email=senior,
    )
    return restriction


@transaction.atomic
def end_expired_suspension(*, restriction_id: int) -> None:
    """Background job: switch the account back on once a suspension runs out, unless another
    suspension or a ban still applies."""
    restriction = UserRestriction.objects.select_for_update().filter(pk=restriction_id).first()
    if restriction is None or restriction.lifted_at is not None:
        return
    if restriction.expires_at is None or restriction.expires_at > timezone.now():
        return
    _reactivate_if_clear(restriction.user)
    ModerationAction.objects.create(
        case=restriction.action.case if restriction.action else None,
        kind=ModerationAction.Kind.LIFT_RESTRICTION,
        reason="The suspension ended.",
        target_user=restriction.user,
        data={"restriction_id": restriction.pk},
    )


# --- Appeals ---


def appeal_deadline(action: ModerationAction) -> datetime:
    return action.created_at + APPEAL_WINDOW


def can_appeal(action: ModerationAction) -> bool:
    return (
        action.kind in NOTICE_KINDS
        and timezone.now() <= appeal_deadline(action)
        and not Appeal.objects.filter(action=action).exists()
    )


@transaction.atomic
def file_appeal(*, user: User, action_id: int, message: str) -> Appeal:
    """A student asks for a decision about them to be reviewed again, within 14 days."""
    action = (
        ModerationAction.objects.select_for_update(of=("self",))
        .filter(pk=action_id, target_user=user, kind__in=NOTICE_KINDS)
        .select_related("case", "actor")
        .first()
    )
    if action is None:
        raise ValidationError("We couldn't find that decision.")
    if Appeal.objects.filter(action=action).exists():
        raise ValidationError("You've already appealed this decision.")
    if timezone.now() > appeal_deadline(action):
        raise ValidationError(f"The {APPEAL_WINDOW.days}-day appeal window has closed.")
    message = message.strip()
    if not message:
        raise ValidationError({"message": "Tell us why the decision should change."})
    if len(message) > 2000:
        raise ValidationError({"message": "Keep your appeal under 2,000 characters."})
    appeal = Appeal.objects.create(action=action, user=user, message=message)
    case = action.case
    ModerationAction.objects.create(
        case=case,
        actor=user,
        kind=ModerationAction.Kind.APPEAL_FILED,
        reason=message,
        target_user=user,
        data={"appeal_id": appeal.pk},
    )
    if case is not None:
        case.status = ModerationCase.Status.APPEALED
        case.resolved_at = None
        case.save(update_fields=["status", "resolved_at", "updated_at"])
        _alert_moderators(
            case,
            f"Appeal on case #{case.pk}",
            message,
            seniors_only=action.kind in {ModerationAction.Kind.SUSPEND, ModerationAction.Kind.BAN},
            exclude={action.actor_id},
        )
    return appeal


def _undo(action: ModerationAction) -> None:
    """Reverse a consequence after a successful appeal."""
    staff = action.actor
    restriction = UserRestriction.objects.filter(action=action, lifted_at__isnull=True).first()
    if restriction is not None:
        _lift(restriction, staff)
    if action.kind == ModerationAction.Kind.REMOVE_LISTING and action.listing is not None:
        listing = action.listing
        listing.refresh_from_db()
        if (
            listing.status == Listing.Status.REMOVED
            and listing.removed_by == Listing.RemovedBy.MODERATION
        ):
            listing_services.restore_by_moderation(listing)


@transaction.atomic
def decide_appeal(
    *,
    staff: User,
    appeal: Appeal,
    uphold: bool,
    reason: str,
    override_reason: str = "",
) -> Appeal:
    """A different moderator reviews the appeal. Overturning it reverses the decision."""
    action = appeal.action
    case = action.case
    senior = action.kind in {ModerationAction.Kind.SUSPEND, ModerationAction.Kind.BAN}
    _require_staff(staff, case, senior=senior, override_reason=override_reason)
    if appeal.status != Appeal.Status.PENDING:
        raise ValidationError("This appeal was already decided.")
    if action.actor_id == staff.pk:
        raise PermissionDenied("A different moderator must review this appeal.")
    _record(
        staff,
        case,
        ModerationAction.Kind.APPEAL_DECIDED,
        reason,
        target_user=appeal.user,
        appeal_id=appeal.pk,
        decision="upheld" if uphold else "overturned",
    )
    if not uphold:
        _undo(action)
    appeal.status = Appeal.Status.UPHELD if uphold else Appeal.Status.OVERTURNED
    appeal.decided_by = staff
    appeal.decision_reason = reason.strip()
    appeal.decided_at = timezone.now()
    appeal.save(update_fields=["status", "decided_by", "decision_reason", "decided_at"])
    still_pending = Appeal.objects.filter(action__case=case, status=Appeal.Status.PENDING)
    if case is not None and not still_pending.exists():
        case.status = ModerationCase.Status.RESOLVED
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolved_at", "updated_at"])
    notification_services.notify(
        appeal.user,
        kind=notification_services.Kind.APPEAL_UPDATE,
        title="Your appeal was accepted" if not uphold else "Your appeal was reviewed",
        body=(
            "After a second review, we reversed the decision. Thanks for your patience."
            if not uphold
            else "After a second review by a different moderator, the original decision stands."
        ),
        link=STANDING_LINK,
        email=senior,
    )
    return appeal


# --- A student's own record ---


def my_standing(user: User) -> dict:
    """What a student sees about their own account: active restrictions, decisions about
    them (with appeal status), and questions from moderators. Never internal reasons."""
    notices = (
        ModerationAction.objects.filter(target_user=user, kind__in=NOTICE_KINDS)
        .select_related("listing")
        .order_by("-created_at")
    )
    appeals = {appeal.action_id: appeal for appeal in Appeal.objects.filter(user=user)}
    return {
        "restrictions": checks.active_restrictions(user).order_by("expires_at"),
        "notices": [
            {
                "action": action,
                "appeal": appeals.get(action.pk),
                "can_appeal": action.pk not in appeals and can_appeal(action),
                "appeal_deadline": appeal_deadline(action),
            }
            for action in notices
        ],
        "info_requests": InfoRequest.objects.filter(recipient=user),
    }


# --- Reading cases (the moderation portal) ---


def moderation_queue(
    staff: User,
    *,
    status: str = "active",
    priority: int | None = None,
    school: str = "",
    reason: str = "",
    target_type: str = "",
    assigned: str = "",
    repeat: bool = False,
):
    """The cases a moderator can see, filtered, most urgent and oldest first."""
    cases = visible_cases(staff).select_related("subject_user", "assigned_to", "listing", "school")
    if status == "active":
        cases = cases.filter(status__in=OPEN_CASE_STATUSES)
    elif status:
        cases = cases.filter(status=status)
    if priority:
        cases = cases.filter(priority=priority)
    if school:
        cases = cases.filter(school__slug=school)
    if reason:
        cases = cases.filter(reports__reason=reason)
    if target_type:
        cases = cases.filter(reports__target_type=target_type)
    if assigned == "me":
        cases = cases.filter(assigned_to=staff)
    elif assigned == "none":
        cases = cases.filter(assigned_to__isnull=True)
    cases = cases.annotate(
        report_count=Count("reports", distinct=True),
        reporter_count=Count("reports__reporter", distinct=True),
        latest_report_at=Max("reports__created_at"),
        prior_case_count=Count("subject_user__moderation_cases", distinct=True) - 1,
        recent_consequences=Count(
            "subject_user__moderation_actions_received",
            filter=Q(
                subject_user__moderation_actions_received__kind__in=NOTICE_KINDS,
                subject_user__moderation_actions_received__created_at__gte=timezone.now()
                - PATTERN_WINDOW,
            ),
            distinct=True,
        ),
    )
    if repeat:
        cases = cases.filter(prior_case_count__gte=1)
    return cases.prefetch_related("reports").order_by("priority", "created_at", "id")


def queue_summary(staff: User) -> dict:
    active = visible_cases(staff).filter(status__in=OPEN_CASE_STATUSES)
    return {
        "open": active.count(),
        "urgent": active.filter(priority=ModerationCase.Priority.URGENT).count(),
        "assigned_to_me": active.filter(assigned_to=staff).count(),
        "escalated": active.filter(escalated=True).count(),
    }


def moderators():
    return (
        User.objects.filter(is_active=True, is_staff=True)
        .filter(Q(is_superuser=True) | Q(groups__name__in=[MODERATOR, SENIOR_MODERATOR]))
        .distinct()
    )


def case_detail(staff: User, case: ModerationCase) -> dict:
    """Everything a moderator needs to decide a case. Opening it is logged as evidence
    access."""
    if not visible_cases(staff).filter(pk=case.pk).exists():
        raise PermissionDenied("This case isn't available to you.")
    EvidenceAccess.objects.create(staff=staff, case=case, viewed="case detail")
    row = moderation_queue(staff, status="").get(pk=case.pk)
    subject = case.subject_user
    reports = case.reports.select_related("reporter").prefetch_related("evidence__files")
    conflict = conflict_of_interest(staff, case)
    reporters = User.objects.filter(reports_made__case=case).distinct()
    return {
        "case": row,
        "legal_hold": case.legal_hold,
        "reports": reports,
        "actions": case.actions.select_related("actor", "target_user"),
        "appeals": Appeal.objects.filter(action__case=case).select_related(
            "user", "decided_by", "action__actor", "action__target_user"
        ),
        "info_requests": case.info_requests.select_related("recipient", "asked_by"),
        "subject": {
            "user": subject,
            "email": subject.email,
            "is_active": subject.is_active,
            "date_joined": subject.date_joined,
            "school_name": subject.school.short_name if subject.school else "",
            "active_restrictions": checks.active_restrictions(subject),
            "past_actions": ModerationAction.objects.filter(target_user=subject)
            .exclude(case=case)
            .select_related("actor", "target_user")
            .order_by("-created_at")[:20],
            "other_cases": moderation_queue(staff, status="")
            .filter(subject_user=subject)
            .exclude(pk=case.pk)[:10],
            "reports_received": Report.objects.filter(reported_user=subject).count(),
            "reports_made": Report.objects.filter(reporter=subject).count(),
            "recent_consequences": recent_consequences(subject),
            "repeat_offender": recent_consequences(subject) >= REPEAT_OFFENDER_ACTIONS,
        },
        "reporter_records": [
            {"user": reporter, **reporter_record(reporter)} for reporter in reporters
        ],
        "involved_users": [subject, *reporters],
        "eligible_assignees": [
            user for user in moderators() if conflict_of_interest(user, case) is None
        ],
        "viewer": {
            "can_act": conflict is None,
            "is_senior": is_senior_moderator(staff),
            "conflict": conflict[0] if conflict else None,
            "conflict_overridable": bool(conflict and conflict[1]),
        },
    }


# --- Patterns and stats ---

PATTERN_WINDOW = timedelta(days=90)
# Consequences in the last 90 days that make someone a repeat offender.
REPEAT_OFFENDER_ACTIONS = 2
# A reporter with at least this many reviewed reports, almost all dismissed.
FALSE_REPORT_MIN = 3
FALSE_REPORT_UPHELD_RATE = 0.25


def _report_outcomes():
    """Reviewed reports, each marked with whether its case led to a consequence."""
    enforced = ModerationAction.objects.filter(case=OuterRef("case"), kind__in=ENFORCEMENT_KINDS)
    return Report.objects.filter(status=Report.Status.RESOLVED).annotate(enforced=Exists(enforced))


def reporter_record(user: User) -> dict:
    """How often this student's reviewed reports led to action. Few upheld out of many is a
    sign of careless or bad-faith reporting, for a moderator to judge."""
    rows = _report_outcomes().filter(reporter=user)
    total = rows.count()
    upheld = rows.filter(enforced=True).count()
    return {
        "reviewed": total,
        "upheld": upheld,
        "possible_false_reporter": total >= FALSE_REPORT_MIN
        and upheld / total <= FALSE_REPORT_UPHELD_RATE,
    }


def recent_consequences(user: User) -> int:
    since = timezone.now() - PATTERN_WINDOW
    return ModerationAction.objects.filter(
        target_user=user, kind__in=NOTICE_KINDS, created_at__gte=since
    ).count()


def moderation_stats(staff: User, *, days: int = 30, school: str = "") -> dict:
    """Numbers for the moderation stats page, limited to the schools `staff` moderates."""
    if not is_moderator(staff):
        raise PermissionDenied("Only moderators can see moderation stats.")
    now = timezone.now()
    since = now - timedelta(days=days)
    cases = visible_cases(staff)
    if school:
        cases = cases.filter(school__slug=school)
    case_ids = cases.values("id")
    reports = Report.objects.filter(case_id__in=case_ids, created_at__gte=since)
    actions = ModerationAction.objects.filter(case_id__in=case_ids, created_at__gte=since)
    opened = cases.filter(created_at__gte=since)

    first_responses, resolutions = [], []
    for case in opened.prefetch_related("actions"):
        staff_actions = [
            action.created_at
            for action in case.actions.all()
            if action.actor_id is not None
            and action.kind
            not in {ModerationAction.Kind.INFO_RECEIVED, ModerationAction.Kind.APPEAL_FILED}
        ]
        if staff_actions:
            first_responses.append((min(staff_actions) - case.created_at).total_seconds() / 3600)
        if case.resolved_at:
            resolutions.append((case.resolved_at - case.created_at).total_seconds() / 3600)

    appeals = Appeal.objects.filter(action__case_id__in=case_ids, created_at__gte=since)

    def counts(queryset, field, labels=None):
        rows = queryset.values(field).annotate(count=Count("id")).order_by("-count")
        return [
            {
                "key": str(row[field] or ""),
                "label": (labels or {}).get(row[field], str(row[field] or "Unknown")),
                "count": row["count"],
            }
            for row in rows
        ]

    pattern_since = now - PATTERN_WINDOW
    offenders = (
        ModerationAction.objects.filter(
            case_id__in=case_ids, kind__in=NOTICE_KINDS, created_at__gte=pattern_since
        )
        .values("target_user")
        .annotate(consequences=Count("id"))
        .filter(consequences__gte=REPEAT_OFFENDER_ACTIONS)
        .order_by("-consequences")[:10]
    )
    offender_users = User.objects.in_bulk([row["target_user"] for row in offenders])
    reporters = (
        _report_outcomes()
        .filter(case_id__in=case_ids)
        .values("reporter")
        .annotate(reviewed=Count("id"), upheld=Count("id", filter=Q(enforced=True)))
        .filter(reviewed__gte=FALSE_REPORT_MIN)
        .order_by("-reviewed")
    )
    flagged = [
        row for row in reporters if row["upheld"] / row["reviewed"] <= FALSE_REPORT_UPHELD_RATE
    ]
    reporter_users = User.objects.in_bulk([row["reporter"] for row in flagged])

    return {
        "days": days,
        "cases_opened": opened.count(),
        "cases_resolved": cases.filter(resolved_at__gte=since).count(),
        "open_now": cases.filter(status__in=OPEN_CASE_STATUSES).count(),
        "urgent_open": cases.filter(
            status__in=OPEN_CASE_STATUSES, priority=ModerationCase.Priority.URGENT
        ).count(),
        "median_hours_to_first_action": round(median(first_responses), 1)
        if first_responses
        else None,
        "median_hours_to_resolve": round(median(resolutions), 1) if resolutions else None,
        "reports": reports.count(),
        "reports_by_reason": counts(reports, "reason", dict(Reason.choices)),
        "reports_by_school": counts(reports, "school__short_name"),
        "outcomes": counts(
            actions.filter(kind__in=ENFORCEMENT_KINDS | {ModerationAction.Kind.DISMISS}),
            "kind",
            dict(ModerationAction.Kind.choices),
        ),
        "appeals_filed": appeals.count(),
        "appeals_overturned": appeals.filter(status=Appeal.Status.OVERTURNED).count(),
        "appeals_upheld": appeals.filter(status=Appeal.Status.UPHELD).count(),
        "appeals_pending": appeals.filter(status=Appeal.Status.PENDING).count(),
        "repeat_offenders": [
            {"user": offender_users[row["target_user"]], "count": row["consequences"]}
            for row in offenders
            if row["target_user"] in offender_users
        ],
        "possible_false_reporters": [
            {
                "user": reporter_users[row["reporter"]],
                "reviewed": row["reviewed"],
                "upheld": row["upheld"],
            }
            for row in flagged
            if row["reporter"] in reporter_users
        ],
    }
