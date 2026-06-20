"""Data structures for JobHuntLedger records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


DEFAULT_APPLICATION_STATUS = "已投递"


def today_string() -> str:
    """Return today's date in ISO format for application records."""
    return date.today().isoformat()


@dataclass(frozen=True)
class Application:
    id: int | None
    company: str
    position: str
    location: str | None = None
    recruit_type: str | None = None
    apply_source: str | None = None
    apply_link: str | None = None
    apply_date: str = ""
    status: str = DEFAULT_APPLICATION_STATUS
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.apply_date:
            object.__setattr__(self, "apply_date", today_string())


@dataclass(frozen=True)
class Interview:
    id: int | None
    application_id: int
    company: str
    position: str
    stage: str
    interview_time: str
    interview_method: str | None = None
    meeting_link: str | None = None
    notes: str | None = None
