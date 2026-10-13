"""Reports, moderation cases, restrictions, blocks, and the audit trail behind them.

Reports never punish anyone by themselves: a moderator reviews the evidence and decides. Every
staff action is a ModerationAction, which can't be edited or deleted once written.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q


class ModerationCase(models.Model):
    """One investigation. Reports about the same listing (or, for everything else, the same
    user) join the open case instead of starting new ones."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        APPEALED = "appealed", "Appealed"

    class Priority(models.IntegerChoices):
        # Lower sorts first in the queue.
        URGENT = 1, "Urgent"
        HIGH = 2, "High"
        NORMAL = 3, "Normal"

    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="moderation_cases"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="moderation_cases",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="moderation_cases",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, default=Priority.NORMAL)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_moderation_cases",
    )
    escalated = models.BooleanField(default=False)
    # Keep every record for this case even if a user asks for their data to be deleted.
    legal_hold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["priority", "created_at", "id"]
        indexes = [
            models.Index(fields=["status", "priority", "created_at"], name="trust_case_queue_idx"),
        ]

    def __str__(self):
        return f"Case {self.pk} about {self.subject_user_id}"


class Report(models.Model):
    class TargetType(models.TextChoices):
        LISTING = "listing", "Listing"
        USER = "user", "Profile"
        MESSAGE = "message", "Message"
        CONVERSATION = "conversation", "Conversation"
        DEAL = "deal", "Deal or meetup"
        REVIEW = "review", "Review"

    class Reason(models.TextChoices):
        PROHIBITED_ITEM = "prohibited_item", "Prohibited item"
        COUNTERFEIT = "counterfeit", "Counterfeit item"
        SCAM = "scam", "Scam or payment concern"
        HARASSMENT = "harassment", "Harassment"
        SPAM = "spam", "Spam"
        UNSAFE_MEETUP = "unsafe_meetup", "Unsafe meetup behavior"
        NO_SHOW = "no_show", "No-show"
        MISLEADING_LISTING = "misleading_listing", "Misleading listing"
        INAPPROPRIATE = "inappropriate", "Inappropriate profile or message"
        OTHER = "other", "Other"

    class ProhibitedCategory(models.TextChoices):
        WEAPON = "weapon", "Weapon"
        DRUGS = "drugs", "Drugs or prescriptions"
        ALCOHOL = "alcohol", "Alcohol"
        TOBACCO = "tobacco", "Tobacco or vapes"
        FOOD = "food", "Food"
        STOLEN = "stolen", "Stolen goods"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    case = models.ForeignKey(ModerationCase, on_delete=models.PROTECT, related_name="reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports_made"
    )
    # Whoever owns the reported content: the seller, message sender, review author, and so on.
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports_received"
    )
    school = models.ForeignKey(
        "schools.School", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    message = models.ForeignKey(
        "messaging.Message", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    deal = models.ForeignKey(
        "deals.Deal", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    review = models.ForeignKey(
        "reviews.Review", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # For a conversation report: only these messages are visible to moderators.
    evidence_messages = models.ManyToManyField(
        "messaging.Message", blank=True, related_name="evidence_in_reports"
    )
    reason = models.CharField(max_length=30, choices=Reason.choices)
    prohibited_category = models.CharField(
        max_length=20, choices=ProhibitedCategory.choices, blank=True
    )
    details = models.CharField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(reporter=models.F("reported_user")), name="trust_report_not_self"
            ),
        ]
        indexes = [
            models.Index(fields=["reporter", "-created_at"], name="trust_report_reporter_idx"),
            models.Index(fields=["reported_user", "-created_at"], name="trust_report_reported_idx"),
        ]

    def __str__(self):
        return f"Report {self.pk}: {self.reason} on {self.target_type}"


class EvidenceSnapshot(models.Model):
    """A copy of reported content as it was when reported, so later edits or deletions
    don't erase the evidence."""

    report = models.ForeignKey(Report, on_delete=models.PROTECT, related_name="evidence")
    kind = models.CharField(max_length=20)
    source_id = models.PositiveBigIntegerField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.kind} {self.source_id} for report {self.report_id}"


class EvidenceFile(models.Model):
    """A copy of a reported photo. Sellers can delete their listing photos; these stay."""

    snapshot = models.ForeignKey(EvidenceSnapshot, on_delete=models.PROTECT, related_name="files")
    file = models.FileField(upload_to="evidence/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.original_name or self.file.name


class ModerationAction(models.Model):
    """Append-only audit trail of everything staff (or the system) did. Can't be changed or
    deleted once saved."""

    class Kind(models.TextChoices):
        NOTE = "note", "Note"
        ASSIGN = "assign", "Assign"
        ESCALATE = "escalate", "Escalate"
        DISMISS = "dismiss", "Dismiss"
        RESOLVE = "resolve", "Resolve"
        REMOVE_LISTING = "remove_listing", "Remove listing"
        AUTO_HIDE_LISTING = "auto_hide_listing", "Hide listing pending review"
        RESTORE_LISTING = "restore_listing", "Restore listing"
        WARN = "warn", "Warning"
        RESTRICT = "restrict", "Restrict"
        SUSPEND = "suspend", "Suspend"
        BAN = "ban", "Ban"
        LIFT_RESTRICTION = "lift_restriction", "Lift restriction"
        CONFLICT_OVERRIDE = "conflict_override", "Conflict of interest override"

    case = models.ForeignKey(
        ModerationCase, on_delete=models.PROTECT, null=True, blank=True, related_name="actions"
    )
    # Null for automatic actions (e.g. hiding a listing after several weapon reports).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="moderation_actions",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    reason = models.TextField()
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="moderation_actions_received",
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(condition=~Q(reason=""), name="trust_action_has_reason"),
        ]

    def __str__(self):
        return f"{self.kind} by {self.actor_id or 'system'}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("Moderation actions are permanent and can't be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Moderation actions are permanent and can't be deleted.")


class UserRestriction(models.Model):
    """A consequence on an account. Active until lifted or, if it has one, until it expires."""

    class Kind(models.TextChoices):
        SELLING = "selling", "Selling"
        MESSAGING = "messaging", "Messaging"
        DEALS = "deals", "Buying and deals"
        SUSPENSION = "suspension", "Temporary suspension"
        BAN = "ban", "Permanent ban"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="restrictions"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    reason = models.TextField()
    action = models.ForeignKey(
        ModerationAction, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "kind"], name="trust_restriction_user_idx")]

    def __str__(self):
        return f"{self.kind} on {self.user_id}"


class Block(models.Model):
    """One student blocking another. Works both ways: neither can message, deal, or trade
    with the other. The blocked student is never told."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="trust_one_block_per_pair"),
            models.CheckConstraint(
                condition=~Q(blocker=models.F("blocked")), name="trust_block_not_self"
            ),
        ]

    def __str__(self):
        return f"{self.blocker_id} blocked {self.blocked_id}"


class EvidenceAccess(models.Model):
    """Who looked at which evidence, when, and why."""

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evidence_accesses"
    )
    case = models.ForeignKey(
        ModerationCase, on_delete=models.PROTECT, related_name="evidence_accesses"
    )
    viewed = models.CharField(max_length=100)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.staff_id} viewed {self.viewed} on case {self.case_id}"


class BannedEmail(models.Model):
    """A banned student's email. Signup is refused for it, and for the same name at any other
    domain of that school (e.g. umd.edu and terpmail.umd.edu)."""

    school = models.ForeignKey("schools.School", on_delete=models.PROTECT, related_name="+")
    local_part = models.CharField(max_length=254)
    email = models.EmailField()
    action = models.ForeignKey(
        ModerationAction, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "local_part"], name="trust_one_ban_per_name"),
        ]

    def __str__(self):
        return self.email


class ModeratorScope(models.Model):
    """Which schools a staff member moderates. No schools means every school."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moderator_scope"
    )
    schools = models.ManyToManyField("schools.School", blank=True, related_name="+")

    def __str__(self):
        return f"Moderation scope for {self.user_id}"
