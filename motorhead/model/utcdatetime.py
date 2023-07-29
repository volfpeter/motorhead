from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


def _ensure_utc(value: datetime) -> datetime:
    """
    Makes sure the given datetime is in UTC.

    If `value` has no timezone info, the method sets UTC.

    Raises:
        ValueError: If `value` has timezone info but it's not UTC.
    """
    tzinfo = value.tzinfo
    if tzinfo is None:  # No timezone info, assume UTC.
        return value.replace(tzinfo=timezone.utc)

    if tzinfo == timezone.utc:  # Timezone is UTC, no-op.
        return value

    # Non-UTC timezone info, raise exception.
    raise ValueError("Non-UTC timezone.")


UTCDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]
"""
Datetime that accepts only naive and UTC datetime objects and replaces
the timezone of naive datetimes with UTC.
"""
