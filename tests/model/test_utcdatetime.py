from datetime import timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from motorhead.model.utcdatetime import UTCDatetime


@pytest.mark.parametrize(
    "value",
    (
        "2024-02-04",
        "2024-02-04 10:00",
        "2024-02-04 11:10:00Z",
        "2024-02-04 12:20:10+00:00",
        "2024-02-04T13:30:20.123456+00:00",
        "2024-02-04T14:40:30.234567Z",
    ),
)
def test_valid_UTCDatetime(value: str) -> None:
    result = TypeAdapter[UTCDatetime](UTCDatetime).validate_python(value)
    assert result.tzinfo is timezone.utc


@pytest.mark.parametrize(
    "value",
    (
        "not-datetime",
        "2024-02-04T12:20:10+02:00",
        "2024-02-04T13:30:20.123456-02:00",
        "2024-02-04T13:30:20.123456+01:00",
    ),
)
def test_UTCDatetime_invalid(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(UTCDatetime).validate_python(value)
