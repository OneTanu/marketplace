"""Notifications: in-app, plus email for things a student needs even when they can't sign in
(e.g. a suspension). Other apps call notify(); nothing else creates Notification rows."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.listings.models import Color, ItemDetails

from .models import Notification, SavedSearch, SavedSearchMatch

Kind = Notification.Kind


def notify(
    user,
    *,
    kind: str,
    title: str,
    body: str = "",
    link: str = "",
    email: bool = False,
    dedupe_key: str = "",
) -> Notification:
    """Record a notification. With `email`, also queue an email, which only goes out if the
    surrounding transaction commits (the job lives in the same database). With `dedupe_key`,
    a second call with the same key returns the first notification and sends nothing."""
    if dedupe_key:
        with transaction.atomic():
            notification, created = Notification.objects.get_or_create(
                user=user,
                dedupe_key=dedupe_key,
                defaults={"kind": kind, "title": title, "body": body, "link": link},
            )
        if not created:
            return notification
    else:
        notification = Notification.objects.create(
            user=user, kind=kind, title=title, body=body, link=link
        )
    if email and user.email:
        from .tasks import send_notification_email

        send_notification_email.defer(notification_id=notification.pk)
    return notification


def unread(user):
    return Notification.objects.filter(user=user, read_at__isnull=True)


def mark_read(user, ids: list[int] | None = None) -> int:
    """Mark some (or, with no ids, all) of a user's notifications read. Returns how many."""
    notifications = unread(user)
    if ids is not None:
        notifications = notifications.filter(pk__in=ids)
    return notifications.update(read_at=timezone.now())


@transaction.atomic
def send_email(*, notification_id: int) -> None:
    notification = Notification.objects.select_related("user").filter(pk=notification_id).first()
    if notification is None:
        return
    link = f"\n\n{settings.WEB_APP_URL}{notification.link}" if notification.link else ""
    send_mail(
        subject=f"Tanu: {notification.title}",
        message=f"{notification.body}{link}\n\n— Tanu",
        from_email=None,
        recipient_list=[notification.user.email],
    )


# --- Saved searches ---
#
# A saved search holds the feed's filters (see SavedSearch). Running it rebuilds the /search
# URL; alerts reuse listings.services.browse_listings, so a match is exactly a listing the
# search would show.

MAX_SAVED_SEARCHES = 25
MAX_NAME_LENGTH = SavedSearch._meta.get_field("name").max_length
FILTER_FIELDS = (
    "query",
    "school",
    "all_schools",
    "category",
    "brand",
    "min_price_cents",
    "max_price_cents",
    "size",
    "condition",
    "color",
)
TOO_MANY_SEARCHES = f"You can save up to {MAX_SAVED_SEARCHES} searches. Delete one to save another."
ALREADY_SAVED = "You've already saved this search."
NOTHING_TO_SAVE = "Add a keyword or a filter before saving this search."


def normalize_filters(
    *,
    query: str = "",
    school=None,
    all_schools: bool = False,
    category=None,
    brand: str = "",
    min_price_cents: int | None = None,
    max_price_cents: int | None = None,
    size: str = "",
    condition: str = "",
    color: str = "",
) -> dict:
    """The saved form of a search's filters: whitespace collapsed, a valid school scope and
    price range, and at least one filter. Raises ValidationError otherwise."""
    filters = {
        "query": " ".join(query.split()),
        "school": school,
        "all_schools": bool(all_schools),
        "category": category,
        "brand": " ".join(brand.split()),
        "min_price_cents": min_price_cents,
        "max_price_cents": max_price_cents,
        "size": size.strip(),
        "condition": condition,
        "color": color,
    }
    if school is not None and all_schools:
        raise ValidationError({"school": "Choose one school, or all schools, not both."})
    if (
        min_price_cents is not None
        and max_price_cents is not None
        and min_price_cents > max_price_cents
    ):
        raise ValidationError({"max_price_cents": "Must be at least the minimum price."})
    if not any(value for key, value in filters.items() if key not in {"school", "all_schools"}):
        raise ValidationError(NOTHING_TO_SAVE)
    return filters


def default_search_name(filters: dict) -> str:
    """A readable name for a search, e.g. '"denim" · Men › Jeans · Levi's · 32x30 · Under $40'."""
    parts = []
    if filters.get("query"):
        parts.append(f"“{filters['query']}”")
    if filters.get("category"):
        parts.append(str(filters["category"]))
    for key in ("brand", "size"):
        if filters.get(key):
            parts.append(filters[key])
    if filters.get("color"):
        parts.append(Color(filters["color"]).label)
    if filters.get("condition"):
        parts.append(ItemDetails.Condition(filters["condition"]).label)
    low, high = filters.get("min_price_cents"), filters.get("max_price_cents")
    if low is not None and high is not None:
        parts.append(f"{_dollars(low)}–{_dollars(high)}")
    elif high is not None:
        parts.append(f"Under {_dollars(high)}")
    elif low is not None:
        parts.append(f"{_dollars(low)}+")
    if filters.get("all_schools"):
        parts.append("All schools")
    elif filters.get("school"):
        parts.append(filters["school"].short_name)
    name = " · ".join(parts) or "Saved search"
    return name if len(name) <= MAX_NAME_LENGTH else f"{name[: MAX_NAME_LENGTH - 1]}…"


def _dollars(cents: int) -> str:
    return f"${cents // 100:,}" if cents % 100 == 0 else f"${cents / 100:,.2f}"


def _clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise ValidationError({"name": "Give this search a name."})
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError({"name": f"Keep the name under {MAX_NAME_LENGTH} characters."})
    return name


def create_saved_search(
    user, *, name: str = "", sort: str = SavedSearch.Sort.NEWEST, alerts_enabled=True, **filters
) -> SavedSearch:
    """Save a search for the user: at most MAX_SAVED_SEARCHES each, and never the same filters
    twice. A blank name gets a generated one."""
    filters = normalize_filters(**filters)
    name = _clean_name(name) if name.strip() else default_search_name(filters)
    with transaction.atomic():
        # Lock the owner so two saves at once can't both pass the limit.
        get_user_model().objects.select_for_update().filter(pk=user.pk).first()
        searches = SavedSearch.objects.filter(user=user)
        if searches.filter(**filters).exists():
            raise ValidationError(ALREADY_SAVED)
        if searches.count() >= MAX_SAVED_SEARCHES:
            raise ValidationError(TOO_MANY_SEARCHES)
        search = SavedSearch(
            user=user, name=name, sort=sort, alerts_enabled=alerts_enabled, **filters
        )
        search.full_clean(validate_constraints=False)
        try:
            with transaction.atomic():
                search.save()
        except IntegrityError as exc:
            raise ValidationError(ALREADY_SAVED) from exc
    return search


def update_saved_search(
    search: SavedSearch, user, *, name: str | None = None, alerts_enabled: bool | None = None
) -> SavedSearch:
    """Rename a saved search or turn its alerts on or off. Its filters don't change: save the
    new search instead."""
    _require_owner(search, user)
    fields = []
    if name is not None:
        search.name = _clean_name(name)
        fields.append("name")
    if alerts_enabled is not None:
        search.alerts_enabled = alerts_enabled
        fields.append("alerts_enabled")
    if fields:
        search.save(update_fields=[*fields, "updated_at"])
    return search


def delete_saved_search(search: SavedSearch, user) -> None:
    _require_owner(search, user)
    search.delete()


def _require_owner(search: SavedSearch, user) -> None:
    if search.user_id != user.pk:
        raise PermissionDenied("This isn't your saved search.")


def feed_filters(search: SavedSearch):
    """The saved search as the feed's filters (listings.services.FeedFilters)."""
    from apps.listings.services import ALL_SCHOOLS, FeedFilters

    if search.all_schools:
        school = ALL_SCHOOLS
    else:
        school = search.school.slug if search.school_id else ""
    return FeedFilters(
        school=school,
        category=search.category,
        min_price=search.min_price_cents,
        max_price=search.max_price_cents,
        conditions=(search.condition,) if search.condition else (),
        colors=(search.color,) if search.color else (),
        size=search.size,
        brand=search.brand,
        query=search.query,
    )


# --- Saved-search alerts ---


def queue_saved_search_alerts(listing) -> None:
    """Queue alert matching for a newly posted listing. Call inside the transaction that
    creates it: the job only exists if the listing is committed."""
    from .tasks import alert_saved_searches

    alert_saved_searches.defer(listing_id=listing.pk)


def alert_saved_searches(*, listing_id: int) -> int:
    """Notify every student with an alerting saved search that matches this new listing, once
    per student. Safe to run again: SavedSearchMatch remembers who was told. Returns how many
    were notified.

    Never the seller, nobody blocked by or blocking the seller, and only for a listing that's
    still Available. A cheap database pass narrows the searches; each candidate is then checked
    with the feed's own query (browse_listings), so every filter, school scope and seller
    restriction applies exactly as when the student runs the search."""
    from apps.listings.models import Listing
    from apps.listings.services import browse_listings
    from apps.trust import checks as trust_checks

    listing = (
        Listing.objects.select_related("category", "school")
        .filter(pk=listing_id, kind="item", status=Listing.Status.AVAILABLE)
        .first()
    )
    if listing is None:
        return 0
    ancestors = []
    category = listing.category
    while category is not None and category.pk not in ancestors:
        ancestors.append(category.pk)
        category = category.parent
    price = listing.price_cents

    candidates = (
        SavedSearch.objects.filter(alerts_enabled=True, user__is_active=True)
        .exclude(user_id=listing.seller_id)
        .exclude(user_id__in=trust_checks.blocked_either_way_ids(listing.seller_id))
        .exclude(user_id__in=SavedSearchMatch.objects.filter(listing=listing).values("user_id"))
        .filter(Q(category__isnull=True) | Q(category_id__in=ancestors))
        .filter(Q(min_price_cents__isnull=True) | Q(min_price_cents__lte=price))
        .filter(Q(max_price_cents__isnull=True) | Q(max_price_cents__gte=price))
        .filter(
            Q(all_schools=True)
            | Q(school_id=listing.school_id)
            | Q(school__isnull=True, user__school_id=listing.school_id)
        )
        .select_related("user", "school", "category")
        .order_by("created_at", "id")
    )
    notified = set()
    for search in candidates:
        if search.user_id in notified:
            continue
        matches = browse_listings(search.user, feed_filters(search)).filter(pk=listing.pk)
        if not matches.exists():
            continue
        with transaction.atomic():
            match, created = SavedSearchMatch.objects.get_or_create(
                user=search.user, listing=listing, defaults={"saved_search": search}
            )
            if not created:
                continue
            match.notification = notify(
                search.user,
                kind=Kind.SAVED_SEARCH,
                title=f"New match for “{search.name}”",
                body=f"{listing.title}, {'Free' if price == 0 else _dollars(price)}",
                link=f"/listings/{listing.pk}",
            )
            match.save(update_fields=["notification"])
        notified.add(search.user_id)
    return len(notified)
