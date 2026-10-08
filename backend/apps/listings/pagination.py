"""Keyset ("cursor") paging for the feed.

A cursor holds the sort values of the last listing on a page (e.g. its price and id), and the
next page starts strictly after them. Unlike offset paging, a listing posted or removed between
two requests doesn't shift later pages, so there are no duplicates or gaps. Every sort ends
with id, so ties on the other values still have a single order.
"""

import base64
import binascii
import json
from datetime import UTC, datetime

from django.db.models import Q, QuerySet
from rest_framework import serializers

PAGE_SIZE = 24
MAX_CURSOR_LENGTH = 200
INVALID = {"cursor": ["This cursor isn't valid. Start again from the first page."]}


def _int(value) -> int:
    # bool is an int in Python; a cursor never holds one.
    if not isinstance(value, int) or isinstance(value, bool) or not -(2**63) < value < 2**63:
        raise ValueError
    return value


def _datetime(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError
    return moment.astimezone(UTC)  # OverflowError past year 9999


# Model fields a sort can use, with how their values go into and out of a cursor. Decoding
# checks types strictly: a cursor comes back from the client and may have been edited.
CURSOR_FIELDS = {
    "created_at": (datetime.isoformat, _datetime),
    "price_cents": (int, _int),
    "id": (int, _int),
}


def encode_cursor(listing, sort: str, ordering: tuple[str, ...]) -> str:
    values = [CURSOR_FIELDS[f.lstrip("-")][0](getattr(listing, f.lstrip("-"))) for f in ordering]
    payload = json.dumps({"sort": sort, "after": values})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str, sort: str, ordering: tuple[str, ...]) -> list:
    """The sort values in a cursor made for this sort. A 400 if it's not one: edited, made
    for another sort, or not a cursor at all."""
    try:
        if len(cursor) > MAX_CURSOR_LENGTH:
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        values = payload["after"]
        if payload["sort"] != sort or not isinstance(values, list):
            raise ValueError
        if len(values) != len(ordering):
            raise ValueError
        return [CURSOR_FIELDS[f.lstrip("-")][1](v) for f, v in zip(ordering, values, strict=True)]
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
        binascii.Error,
        UnicodeDecodeError,
    ) as exc:
        raise serializers.ValidationError(INVALID) from exc


def after(values: list, ordering: tuple[str, ...]) -> Q:
    """Rows that sort after `values` in `ordering`: (a > x) or (a = x and b > y) or ...,
    with < for descending fields."""
    condition = Q()
    equal = Q()
    for field, value in zip(ordering, values, strict=True):
        name = field.lstrip("-")
        lookup = "lt" if field.startswith("-") else "gt"
        condition |= equal & Q(**{f"{name}__{lookup}": value})
        equal &= Q(**{name: value})
    return condition


def page(queryset: QuerySet, sort: str, ordering: tuple[str, ...], cursor: str | None):
    """One page (PAGE_SIZE rows) of the queryset sorted by `sort` (whose model ordering is
    `ordering`), starting after `cursor`. Returns the rows and the cursor for the next page
    (None on the last page)."""
    size = PAGE_SIZE
    queryset = queryset.order_by(*ordering)
    if cursor:
        queryset = queryset.filter(after(decode_cursor(cursor, sort, ordering), ordering))
    rows = list(queryset[: size + 1])  # one extra, to tell whether there's a next page
    if len(rows) <= size:
        return rows, None
    return rows[:size], encode_cursor(rows[size - 1], sort, ordering)
