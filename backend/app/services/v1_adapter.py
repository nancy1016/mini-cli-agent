"""将冻结的 V1 求职台账能力适配为只读 Web API 数据。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
import re
from typing import Any

from backend.app.core.config import resolve_database_path
from jobhunt.models import Application, Interview
from jobhunt.repository import (
    find_applications_by_company,
    list_applications,
    list_interviews,
)
from jobhunt.service import (
    check_missing_info,
    confirm_create_application,
    confirm_create_interview,
    confirm_update_application_status,
    get_next_thirty_days_interviews,
    get_next_three_days_interviews,
    get_today_interviews,
    get_tomorrow_interviews,
    get_weekly_interviews,
    preview_application_from_text,
    preview_interview_from_text,
    preview_status_update_from_text,
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
    base_date: date | None = None,
) -> list[dict[str, object]]:
    """按 V1 已支持的时间范围读取面试记录。"""
    handler = INTERVIEW_RANGE_HANDLERS.get(range_name)
    if handler is None:
        supported = ", ".join(INTERVIEW_RANGE_HANDLERS)
        raise ValueError(f"unsupported interview range: {range_name}; supported: {supported}")
    interviews = handler(today=base_date, db_path=_db_path(db_path))
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


def _require_preview_action(preview: dict[str, object], expected: str) -> None:
    if preview.get("action") != expected:
        raise ValueError(f"预览类型不匹配，期望 {expected}")


def _candidate_rows(applications: list[Application]) -> list[dict[str, object]]:
    return [_application_row(application) for application in applications]


def preview_application(
    text: str,
    db_path: DbPath | None = None,
    base_date: date | None = None,
) -> dict[str, object]:
    """调用 V1 生成投递预览；db_path 保留统一的 Web Adapter 签名。"""
    del db_path
    return preview_application_from_text(text=text, base_date=base_date)


def confirm_application(
    preview: dict[str, object],
    db_path: DbPath | None = None,
) -> dict[str, object]:
    _require_preview_action(preview, "preview_application")
    return _application_row(
        confirm_create_application(preview=preview, db_path=_db_path(db_path))
    )


def preview_interview(
    text: str,
    db_path: DbPath | None = None,
    base_date: date | None = None,
) -> dict[str, object]:
    path = _db_path(db_path)
    preview = preview_interview_from_text(text=text, base_date=base_date, db_path=path)
    parsed = preview.get("parsed")
    company = str(parsed.get("company") or "") if isinstance(parsed, dict) else ""
    matches = find_applications_by_company(company, db_path=path) if company else []
    result = dict(preview)
    result["candidates"] = _candidate_rows(matches)
    result["requires_clarification"] = len(matches) > 1
    if len(matches) > 1:
        result["matched_application"] = None
    return result


def confirm_interview(
    preview: dict[str, object],
    db_path: DbPath | None = None,
) -> dict[str, object]:
    _require_preview_action(preview, "preview_interview")
    if preview.get("requires_clarification"):
        raise ValueError("同一公司存在多条投递记录，请先明确岗位")
    if preview.get("needs_application_creation"):
        raise ValueError("面试未匹配到投递记录，请先创建投递或补充公司信息")
    result = confirm_create_interview(
        preview=preview,
        create_application_if_missing=False,
        db_path=_db_path(db_path),
    )
    return {str(key): _to_jsonable(value) for key, value in result.items()}


def preview_status_update(
    text: str,
    db_path: DbPath | None = None,
) -> dict[str, object]:
    path = _db_path(db_path)
    # V1 支持“已放弃”，Web 输入中的常见口语“放弃了”在适配层归一化后再复用 V1。
    normalized_text = text.replace("放弃了", "已放弃")
    preview = preview_status_update_from_text(text=normalized_text, db_path=path)
    parsed = preview.get("parsed")
    company = str(parsed.get("company") or "") if isinstance(parsed, dict) else ""
    matches = find_applications_by_company(company, db_path=path) if company else []
    result = dict(preview)
    result["candidates"] = _candidate_rows(matches)
    result["requires_clarification"] = len(matches) > 1
    if len(matches) > 1:
        result["matched_application"] = None
    return result


def confirm_status_update(
    preview: dict[str, object],
    db_path: DbPath | None = None,
) -> dict[str, object]:
    _require_preview_action(preview, "preview_status_update")
    if preview.get("requires_clarification"):
        raise ValueError("同一公司存在多条投递记录，请先明确岗位")
    return _application_row(
        confirm_update_application_status(preview=preview, db_path=_db_path(db_path))
    )


def query_application_status(
    company_text: str | None,
    db_path: DbPath | None = None,
) -> dict[str, object]:
    raw_text = (company_text or "").strip()
    company_match = re.search(r"([A-Za-z0-9\u4e00-\u9fff]+?公司)", raw_text)
    company = company_match.group(1) if company_match else raw_text
    if not company:
        return {"status": "needs_company", "candidates": []}

    matches = find_applications_by_company(company, db_path=_db_path(db_path))
    if not matches:
        return {"status": "not_found", "company": company, "candidates": []}
    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "company": company,
            "candidates": _candidate_rows(matches),
        }
    return {
        "status": "found",
        "company": company,
        "application": _application_row(matches[0]),
    }


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (Application, Interview)):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value
