"""Shared date helpers for the Review Chân Thật blog.

The blog is published for a Vietnamese audience, so *every* publish date must be
decided in the ``Asia/Ho_Chi_Minh`` timezone (GMT+7), never in UTC. GitHub Actions
runners and most containers run in UTC, so ``datetime.utcnow()`` / ``date.today()``
would stamp a post created just after local midnight with *yesterday's* date. That
made new posts sort below older ones on the homepage.

Rules enforced here:
- Publish dates are ISO 8601 *with* an explicit ``+07:00`` offset.
- "Today" is always the calendar day in Hồ Chí Minh time.
- Never fabricate or future-date a post.
- Display format is ``dd-mm-yyyy hh:mm:ss`` for all visible UI.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

# Single source of truth for the blog's timezone.
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DISPLAY_DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"


def now_vietnam() -> datetime:
    """Timezone-aware "now" in Hồ Chí Minh time."""
    return datetime.now(VN_TZ).replace(microsecond=0)


def now_vietnam_iso() -> str:
    """Current instant as ISO 8601 with the +07:00 offset, e.g. ``2026-07-09T09:00:00+07:00``."""
    return now_vietnam().isoformat()


def today_vietnam_date() -> str:
    """Today's calendar date in Hồ Chí Minh time, ``YYYY-MM-DD``."""
    return now_vietnam().date().isoformat()


def vietnam_date_of(value: datetime) -> date:
    """Return the Hồ Chí Minh calendar day for any aware datetime.

    A naive datetime is treated as already being in VN time.
    """
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(VN_TZ).date()


def publish_datetime_iso(hour: int = 9, minute: int = 0) -> str:
    """ISO 8601 publish timestamp for *today* in VN time at the given wall-clock time.

    Useful for generators that want a stable time-of-day but the real current day.
    """
    now = now_vietnam()
    stamped = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return stamped.isoformat()


def format_vietnam_datetime(value: datetime | str) -> str:
    """Format datetime for display: dd-mm-yyyy hh:mm:ss.

    Args:
        value: datetime object or ISO string (with or without timezone).

    Returns:
        Display string in Vietnam timezone, e.g. "09-07-2026 14:35:20"
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=VN_TZ)

    return value.astimezone(VN_TZ).strftime(DISPLAY_DATETIME_FORMAT)
