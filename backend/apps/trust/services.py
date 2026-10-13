"""Reports, blocks, and moderation actions.

Reports never punish anyone by themselves. They gather evidence into a case; a moderator
reviews it and decides. The one automatic step is hiding a listing that several students
report as a weapon or drugs, until a moderator looks at it.

Every staff action needs a reason and writes a permanent ModerationAction.
"""

from datetime import datetime, timedelta
from pathlib import PurePosixPath

from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.listings import services as listing_services
from apps.listings.models import Listing
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.reviews.models import Review
from apps.schools.services import school_for_email

from . import checks
from .models import (
    BannedEmail,
    Block,
    EvidenceAccess,
    EvidenceFile,
    EvidenceSnapshot,
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
    deal_services.cancel_deals_between(blocker, blocked, reason="One student blocked the other.")
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
        return ModerationCase.objects.create(
            subject_user=reported_user, listing=listing, school=school, priority=priority
        )
    if priority < case.priority:
        case.priority = priority
        case.save(update_fields=["priority", "updated_at"])
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


def _record(staff, case, kind, reason, *, target_user=None, listing=None, **data):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Give a reason for this action."})
    action = ModerationAction.objects.create(
        case=case,
        actor=staff,
        kind=kind,
        reason=reason,
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


# --- Case handling ---


@transaction.atomic
def add_note(*, staff: User, case: ModerationCase, note: str) -> ModerationAction:
    _require_staff(staff, case)
    return _record(staff, case, ModerationAction.Kind.NOTE, note)


@transaction.atomic
def assign_case(*, staff: User, case: ModerationCase, assignee: User, reason: str = "Assigned"):
    _require_staff(staff, case)
    if not is_moderator(assignee):
        raise ValidationError("Assign the case to a moderator.")
    conflict = conflict_of_interest(assignee, case)
    if conflict is not None:
        raise ValidationError(f"@{assignee.username} can't take this case because {conflict[0]}.")
    case.assigned_to = assignee
    if case.status == ModerationCase.Status.OPEN:
        case.status = ModerationCase.Status.INVESTIGATING
    case.save(update_fields=["assigned_to", "status", "updated_at"])
    return _record(staff, case, ModerationAction.Kind.ASSIGN, reason, assignee_id=assignee.pk)


@transaction.atomic
def escalate_case(*, staff: User, case: ModerationCase, reason: str) -> ModerationAction:
    _require_staff(staff, case)
    case.escalated = True
    case.save(update_fields=["escalated", "updated_at"])
    return _record(staff, case, ModerationAction.Kind.ESCALATE, reason)


def _close(staff, case, kind, reason) -> ModerationAction:
    action = _record(staff, case, kind, reason, target_user=case.subject_user)
    case.status = ModerationCase.Status.RESOLVED
    case.resolved_at = timezone.now()
    case.save(update_fields=["status", "resolved_at", "updated_at"])
    case.reports.update(status=Report.Status.RESOLVED)
    return action


@transaction.atomic
def dismiss_case(*, staff: User, case: ModerationCase, reason: str) -> ModerationAction:
    """No violation found."""
    _require_staff(staff, case)
    return _close(staff, case, ModerationAction.Kind.DISMISS, reason)


@transaction.atomic
def resolve_case(*, staff: User, case: ModerationCase, reason: str) -> ModerationAction:
    """Close a case after acting on it."""
    _require_staff(staff, case)
    return _close(staff, case, ModerationAction.Kind.RESOLVE, reason)


# --- Listings ---


@transaction.atomic
def remove_listing(*, staff: User, case: ModerationCase, listing: Listing, reason: str):
    _require_staff(staff, case)
    action = _record(
        staff,
        case,
        ModerationAction.Kind.REMOVE_LISTING,
        reason,
        target_user=listing.seller,
        listing=listing,
    )
    _take_down(listing, reason)
    return action


@transaction.atomic
def restore_listing(*, staff: User, case: ModerationCase, listing: Listing, reason: str):
    _require_staff(staff, case)
    action = _record(
        staff,
        case,
        ModerationAction.Kind.RESTORE_LISTING,
        reason,
        target_user=listing.seller,
        listing=listing,
    )
    listing_services.restore_by_moderation(listing)
    return action


# --- Account consequences: warning -> restriction -> suspension -> ban ---


@transaction.atomic
def warn_user(*, staff: User, case: ModerationCase, user: User, reason: str):
    _require_staff(staff, case)
    _require_involved(case, user)
    return _record(staff, case, ModerationAction.Kind.WARN, reason, target_user=user)


def _restriction(staff, case, user, kind, reason, expires_at) -> UserRestriction:
    if expires_at is not None and expires_at <= timezone.now():
        raise ValidationError({"expires_at": "Choose a time in the future."})
    action_kind = {
        Kind.SUSPENSION: ModerationAction.Kind.SUSPEND,
        Kind.BAN: ModerationAction.Kind.BAN,
    }.get(kind, ModerationAction.Kind.RESTRICT)
    action = _record(
        staff,
        case,
        action_kind,
        reason,
        target_user=user,
        restriction=kind,
        expires_at=expires_at.isoformat() if expires_at else None,
    )
    return UserRestriction.objects.create(
        user=user, kind=kind, reason=action.reason, action=action, expires_at=expires_at
    )


@transaction.atomic
def restrict_user(
    *,
    staff: User,
    case: ModerationCase,
    user: User,
    kind: str,
    reason: str,
    expires_at: datetime | None = None,
) -> UserRestriction:
    """Take away one feature (selling, messaging, or deals). Pending deals can still finish."""
    _require_staff(staff, case)
    _require_involved(case, user)
    if kind not in {Kind.SELLING, Kind.MESSAGING, Kind.DEALS}:
        raise ValidationError({"kind": "Choose selling, messaging, or deals."})
    return _restriction(staff, case, user, kind, reason, expires_at)


@transaction.atomic
def suspend_user(
    *, staff: User, case: ModerationCase, user: User, reason: str, until: datetime
) -> UserRestriction:
    """Switch the account off until `until`. Their open deals, including Pending ones, are
    canceled so nobody meets a suspended student; their listings are hidden meanwhile."""
    _require_staff(staff, case, senior=True)
    _require_involved(case, user)
    if until is None:
        raise ValidationError({"until": "Choose when the suspension ends."})
    restriction = _restriction(staff, case, user, Kind.SUSPENSION, reason, until)
    account_services.set_account_active(user, False)
    deal_services.cancel_deals_for_user(user, reason="A student in this deal was suspended.")
    from .tasks import end_suspension

    end_suspension.configure(schedule_at=until).defer(restriction_id=restriction.pk)
    return restriction


@transaction.atomic
def ban_user(*, staff: User, case: ModerationCase, user: User, reason: str) -> UserRestriction:
    """Permanently switch the account off, cancel its deals, remove its listings, and refuse
    signup for its emails (and the same name at the school's other domains)."""
    _require_staff(staff, case, senior=True)
    _require_involved(case, user)
    restriction = _restriction(staff, case, user, Kind.BAN, reason, None)
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
    restriction.lifted_at = timezone.now()
    restriction.lifted_by = staff
    restriction.save(update_fields=["lifted_at", "lifted_by"])
    if restriction.kind == Kind.BAN:
        BannedEmail.objects.filter(action=restriction.action).delete()
    if senior:
        _reactivate_if_clear(restriction.user)
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
