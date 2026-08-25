"""将冻结的 V1 求职台账能力适配为只读 Web API 数据。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from backend.app.core.config import resolve_database_path
from jobhunt.models import Application, Interview
from jobhunt.repository import list_applications, list_interviews
from jobhunt.service import (
    check_missing_info,
    get_next_thirty_days_interviews,
    get_next_three_days_interviews,
    get_today_interviews,
    get_tomorrow_interviews,
    get_weekly_interviews,
)


DbPath = str | Path
TERMINAL_STATUSES = {"offer", "未通过", "已放弃"}
INTERVIEW_RANGE_HANDLERS = {
    "today": get_today_interviews,
    "tomorrow": get_tomorrow_interviews,
    "next_three_days": get_next_three_days_interviews,
    "this_week": get_weekly_interviews,
    "next_thirty_days": get_next_thirty_days_interviews,
}

FIELD_LABELS = {
    "company": "公司",
    "position": "岗位",
    "location": "工作地点",
    "apply_source": "投递来源",
    "apply_link": "投递链接",
    "interview_time": "面试时间",
    "meeting_link": "会议链接",
}


def _db_path(db_path: DbPath | None) -> Path:
    return resolve_database_path(db_path)


def _application_row(application: Application) -> dict[str, object]:
    return asdict(application)


def _interview_row(interview: Interview) -> dict[str, object]:
    return asdict(interview)


def _missing_fields(item: dict[str, object]) -> list[str]:
    missing = item.get("missing")
    if not isinstance(missing, dict):
        return []
    required = missing.get("required", [])
    recommended = missing.get("recommended", [])
    return [str(field) for field in [*required, *recommended]]


def _suggestion(fields: list[str]) -> str:
    labels = [FIELD_LABELS.get(field, field) for field in fields]
    return f"建议补充：{'、'.join(labels)}" if labels else ""


def list_application_rows(
    status: str | None = None,
    keyword: str | None = None,
    db_path: DbPath | None = None,
) -> list[dict[str, object]]:
    """读取投递记录，并在 API 层执行简单筛选。"""
    normalized_status = status.strip() if status else None
    normalized_keyword = keyword.strip().casefold() if keyword else None

    rows: list[dict[str, object]] = []
    for application in list_applications(db_path=_db_path(db_path)):
        if normalized_status and application.status != normalized_status:
            continue
        if normalized_keyword:
            searchable = " ".join(
                value
                for value in (
                    application.company,
                    application.position,
                    application.location or "",
                )
                if value
            ).casefold()
            if normalized_keyword not in searchable:
                continue
        rows.append(_application_row(application))
    return rows


def list_interview_rows(
    range_name: str = "next_three_days",
    db_path: DbPath | None = None,
) -> list[dict[str, object]]:
    """按 V1 已支持的时间范围读取面试记录。"""
    handler = INTERVIEW_RANGE_HANDLERS.get(range_name)
    if handler is None:
        supported = ", ".join(INTERVIEW_RANGE_HANDLERS)
        raise ValueError(f"unsupported interview range: {range_name}; supported: {supported}")
    interviews = handler(db_path=_db_path(db_path))
    return [_interview_row(interview) for interview in interviews]


def list_missing_info_rows(
    db_path: DbPath | None = None,
) -> list[dict[str, object]]:
    """将 V1 的分组缺失检查结果展开为前端表格行。"""
    path = _db_path(db_path)
    applications = {item.id: item for item in list_applications(db_path=path)}
    interviews = {item.id: item for item in list_interviews(db_path=path)}
    result = check_missing_info(db_path=path)
    rows: list[dict[str, object]] = []

    for item in result.get("applications", []):
        fields = _missing_fields(item)
        application = applications.get(item.get("id"))
        if not fields or application is None:
            continue
        rows.append(
            {
                "company": application.company,
                "position": application.position,
                "missing_fields": fields,
                "suggestion": _suggestion(fields),
            }
        )

    for item in result.get("interviews", []):
        fields = _missing_fields(item)
        interview = interviews.get(item.get("id"))
        if not fields or interview is None:
            continue
        rows.append(
            {
                "company": interview.company,
                "position": interview.position,
                "missing_fields": fields,
                "suggestion": _suggestion(fields),
            }
        )
    return rows


def get_dashboard_summary(db_path: DbPath | None = None) -> dict[str, object]:
    """聚合 Dashboard 所需的 V1 真实数据。"""
    path = _db_path(db_path)
    applications = list_applications(db_path=path)
    next_three_days = get_next_three_days_interviews(db_path=path)
    next_thirty_days = get_next_thirty_days_interviews(db_path=path)
    missing_rows = list_missing_info_rows(db_path=path)

    recent_applications = sorted(
        applications,
        key=lambda item: (item.apply_date, item.id or 0),
        reverse=True,
    )[:5]

    return {
        "total_applications": len(applications),
        "active_applications": sum(
            1 for item in applications if item.status.casefold() not in TERMINAL_STATUSES
        ),
        "offer_count": sum(1 for item in applications if item.status.casefold() == "offer"),
        "next_three_days_interviews": len(next_three_days),
        "next_thirty_days_interviews": len(next_thirty_days),
        "missing_info_count": len(missing_rows),
        "recent_applications": [_application_row(item) for item in recent_applications],
        "upcoming_interviews": [_interview_row(item) for item in next_thirty_days[:5]],
    }
