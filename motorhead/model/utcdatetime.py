from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import AfterValidator

_no_delta = timedelta()


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

    if value.utcoffset() == _no_delta:
        # Timezone is UTC (at least in offset), replace Pydantic's tzinfo with UTC.
        return value.replace(tzinfo=timezone.utc)

    # Non-UTC timezone info, raise exception.
    raise ValueError("Non-UTC timezone.")


UTCDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]
"""
Pydantic `datetime` that accepts only naive and UTC datetime objects and replaces
the timezone of naive datetimes with UTC.
"""
