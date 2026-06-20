"""Missing information checks for JobHuntLedger records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


MissingResult = dict[str, list[str]]


def is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "待补充"}
    return False


def _empty_result() -> MissingResult:
    return {"required": [], "recommended": []}


def _contains_any(value: object, keywords: Iterable[str]) -> bool:
    if not isinstance(value, str):
        return False
    return any(keyword in value for keyword in keywords)


def check_application_missing_fields(application: Any) -> MissingResult:
    missing = _empty_result()

    if is_missing(application.company):
        missing["required"].append("company")
    if is_missing(application.position):
        missing["required"].append("position")
    if is_missing(application.location):
        missing["recommended"].append("location")
    if is_missing(application.apply_source):
        missing["recommended"].append("apply_source")
    if is_missing(application.apply_link) and _contains_any(
        application.apply_source,
        ("官网", "网申"),
    ):
        missing["recommended"].append("apply_link")

    return missing


def check_interview_missing_fields(interview: Any) -> MissingResult:
    missing = _empty_result()

    if is_missing(interview.company):
        missing["required"].append("company")
    if is_missing(interview.position):
        missing["required"].append("position")
    if is_missing(interview.interview_time):
        missing["required"].append("interview_time")
    if is_missing(interview.meeting_link) and _contains_any(
        interview.interview_method,
        ("腾讯会议", "飞书会议", "线上"),
    ):
        missing["recommended"].append("meeting_link")

    return missing


def check_all_missing_info(
    applications: Iterable[Any],
    interviews: Iterable[Any],
) -> dict[str, list[dict[str, object]]]:
    return {
        "applications": [
            {
                "id": application.id,
                "missing": check_application_missing_fields(application),
            }
            for application in applications
        ],
        "interviews": [
            {
                "id": interview.id,
                "application_id": interview.application_id,
                "missing": check_interview_missing_fields(interview),
            }
            for interview in interviews
        ],
    }
