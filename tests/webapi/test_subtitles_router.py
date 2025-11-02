import pytest
from fastapi import HTTPException

from modules.webapi.routers.subtitles import _parse_end_time, _parse_time_offset


def test_parse_end_time_relative_minutes() -> None:
    start_seconds = _parse_time_offset("00:01")
    end_seconds = _parse_end_time("+5", start_seconds)
    assert end_seconds == pytest.approx(start_seconds + 300.0)


def test_parse_end_time_accepts_absolute() -> None:
    start_seconds = _parse_time_offset("00:00")
    end_seconds = _parse_end_time("03:00", start_seconds)
    assert end_seconds == pytest.approx(180.0)


def test_parse_end_time_relative_timecode() -> None:
    start_seconds = _parse_time_offset("00:10")
    end_seconds = _parse_end_time("+01:30", start_seconds)
    assert end_seconds == pytest.approx(start_seconds + 90.0)


def test_parse_end_time_blank_returns_none() -> None:
    assert _parse_end_time("", 0.0) is None
    assert _parse_end_time(None, 0.0) is None


def test_parse_end_time_requires_greater_than_start() -> None:
    with pytest.raises(HTTPException):
        _parse_end_time("00:00", 5.0)


def test_parse_end_time_invalid_relative_raises() -> None:
    with pytest.raises(HTTPException):
        _parse_end_time("+abc", 0.0)
