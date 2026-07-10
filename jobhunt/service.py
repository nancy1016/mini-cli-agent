"""JobHuntLedger V1 的核心业务流程编排。

本模块负责串联 parser、missing、repository 和 status 等模块，完成
“文本解析预览 -> 用户确认 -> 保存数据库”的闭环；不直接写 SQL，也不接入 CLI 或 Agent 工具。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from jobhunt.database import DEFAULT_DB_PATH
from jobhunt.missing import (
    check_all_missing_info,
    check_application_missing_fields,
    check_interview_missing_fields,
)
from jobhunt.models import Application, Interview
from jobhunt.parser import (
    parse_application_text,
    parse_interview_text,
    parse_status_update_text,
)
from jobhunt.reminders import (
    list_interviews_next_three_days,
    list_interviews_this_week,
    list_interviews_today,
    list_interviews_tomorrow,
)
from jobhunt.repository import (
    create_application,
    create_interview,
    find_applications_by_company,
    list_applications,
    list_interviews,
    update_application_status,
)
from jobhunt.status import normalize_status


DbPath = str | Path

_INTERVIEW_STAGE_STATUS = {
    "一面": "一面待进行",
    "二面": "二面待进行",
    "三面": "三面待进行",
    "HR面": "HR面待进行",
}


def _application_preview_object(parsed: dict[str, object]) -> Application:
    return Application(
        id=None,
        company=str(parsed.get("company") or ""),
        position=str(parsed.get("position") or ""),
        location=_optional_text(parsed.get("location")),
        recruit_type=_optional_text(parsed.get("recruit_type")),
        apply_source=_optional_text(parsed.get("apply_source")),
        apply_link=_optional_text(parsed.get("apply_link")),
        apply_date=str(parsed.get("apply_date") or ""),
        status=str(parsed.get("status") or ""),
        notes=_optional_text(parsed.get("notes")),
    )


def _interview_preview_object(parsed: dict[str, object], application_id: int = 0) -> Interview:
    return Interview(
        id=None,
        application_id=application_id,
        company=str(parsed.get("company") or ""),
        position=str(parsed.get("position") or ""),
        stage=str(parsed.get("stage") or ""),
        interview_time=str(parsed.get("interview_time") or ""),
        interview_method=_optional_text(parsed.get("interview_method")),
        meeting_link=_optional_text(parsed.get("meeting_link")),
        notes=_optional_text(parsed.get("notes")),
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _matched_application_summary(application: Application) -> dict[str, object]:
    return {
        "id": application.id,
        "company": application.company,
        "position": application.position,
        "status": application.status,
    }


def _create_application_from_parsed(
    parsed: dict[str, object],
    db_path: DbPath,
) -> Application:
    return create_application(
        company=str(parsed.get("company") or ""),
        position=str(parsed.get("position") or ""),
        location=_optional_text(parsed.get("location")),
        recruit_type=_optional_text(parsed.get("recruit_type")),
        apply_source=_optional_text(parsed.get("apply_source")),
        apply_link=_optional_text(parsed.get("apply_link")),
        apply_date=_optional_text(parsed.get("apply_date")),
        status=_optional_text(parsed.get("status")),
        notes=_optional_text(parsed.get("notes")),
        db_path=db_path,
    )


def _find_application_by_preview(
    preview: dict[str, object],
    db_path: DbPath,
) -> Application | None:
    matched = preview.get("matched_application")
    parsed = _parsed_dict(preview)
    company = str(parsed.get("company") or "")

    if not isinstance(matched, dict):
        return None

    matched_id = matched.get("id")
    for application in find_applications_by_company(company, db_path=db_path):
        if application.id == matched_id:
            return application
    return None


def _parsed_dict(preview: dict[str, object]) -> dict[str, object]:
    parsed = preview.get("parsed")
    if not isinstance(parsed, dict):
        raise ValueError("preview 中缺少 parsed 字段")
    return parsed


def _status_from_stage(stage: object) -> str | None:
    # 只有 V1 明确定义的面试阶段才会驱动状态更新；未知阶段保持原状态，避免误改台账。
    raw_status = _INTERVIEW_STAGE_STATUS.get(str(stage or "").strip())
    return normalize_status(raw_status) if raw_status else None


def preview_application_from_text(
    text: str,
    base_date: date | None = None,
) -> dict[str, object]:
    """解析投递文本并返回保存前预览。

    Args:
        text: 用户输入的投递描述文本。
        base_date: 相对日期解析基准日；测试或固定场景可显式传入。

    Returns:
        包含解析字段、缺失信息和 will_save=False 的结构化预览。
    """
    parsed = parse_application_text(text, base_date=base_date)
    application = _application_preview_object(parsed)

    # preview 阶段只展示解析结果和缺失信息，绝不写入数据库。
    return {
        "action": "preview_application",
        "parsed": parsed,
        "missing": check_application_missing_fields(application),
        "will_save": False,
    }


def confirm_create_application(
    preview: dict[str, object],
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Application:
    """根据投递预览创建投递记录。

    Args:
        preview: preview_application_from_text 返回的结构化预览。
        db_path: SQLite 数据库路径，测试中可传入 tmp_path 下的临时库。

    Returns:
        repository 创建并返回的 Application 对象。
    """
    parsed = _parsed_dict(preview)

    # confirm 阶段才真正保存，所有持久化能力统一交给 repository。
    return _create_application_from_parsed(parsed, db_path=db_path)


def preview_interview_from_text(
    text: str,
    base_date: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> dict[str, object]:
    """解析面试文本并匹配已有投递记录。

    Args:
        text: 用户输入的面试通知文本。
        base_date: 相对日期解析基准日。
        db_path: 用于查找已有投递记录的 SQLite 数据库路径。

    Returns:
        包含解析字段、匹配投递记录、缺失信息和 will_save=False 的预览。
    """
    parsed = parse_interview_text(text, base_date=base_date)
    interview = _interview_preview_object(parsed)
    applications = find_applications_by_company(str(parsed.get("company") or ""), db_path=db_path)
    matched_application = applications[0] if applications else None

    # 找不到对应投递时，只返回提示信息；是否补建投递必须留给用户确认。
    return {
        "action": "preview_interview",
        "parsed": parsed,
        "matched_application": (
            _matched_application_summary(matched_application)
            if matched_application
            else None
        ),
        "needs_application_creation": matched_application is None,
        "missing": check_interview_missing_fields(interview),
        "will_save": False,
    }


def confirm_create_interview(
    preview: dict[str, object],
    create_application_if_missing: bool = False,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> dict[str, object]:
    """根据面试预览创建面试记录，并按阶段更新投递状态。

    Args:
        preview: preview_interview_from_text 返回的结构化预览。
        create_application_if_missing: 面试无匹配投递时，是否先补建投递记录。
        db_path: SQLite 数据库路径，测试中可传入 tmp_path 下的临时库。

    Returns:
        包含 Application、Interview 和 updated_status 的保存结果。
    """
    parsed = _parsed_dict(preview)
    application = _find_application_by_preview(preview, db_path=db_path)

    if application is None:
        if not create_application_if_missing:
            raise ValueError("面试未匹配到投递记录，请确认是否同时创建投递记录")
        application = create_application(
            company=str(parsed.get("company") or ""),
            position=str(parsed.get("position") or ""),
            db_path=db_path,
        )

    if application.id is None:
        raise ValueError("投递记录缺少 id，无法创建面试记录")

    interview = create_interview(
        application_id=application.id,
        company=str(parsed.get("company") or ""),
        position=str(parsed.get("position") or ""),
        stage=str(parsed.get("stage") or ""),
        interview_time=str(parsed.get("interview_time") or ""),
        interview_method=_optional_text(parsed.get("interview_method")),
        meeting_link=_optional_text(parsed.get("meeting_link")),
        notes=_optional_text(parsed.get("notes")),
        db_path=db_path,
    )

    updated_status = _status_from_stage(parsed.get("stage"))
    if updated_status is not None:
        # 创建面试后再根据 stage 更新 applications.status，保持记录状态与面试进度一致。
        application = update_application_status(
            application_id=application.id,
            status=updated_status,
            db_path=db_path,
        )

    return {
        "application": application,
        "interview": interview,
        "updated_status": updated_status,
    }


def list_all_applications(
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Application]:
    """查询全部投递记录。

    Args:
        db_path: SQLite 数据库路径。

    Returns:
        repository 返回的 Application 列表；展示格式由 CLI 或 Agent 层负责。
    """
    return list_applications(db_path=db_path)


def get_today_interviews(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询今天的面试记录。

    Args:
        today: 查询基准日；未传入时由 reminders 使用系统日期。
        db_path: SQLite 数据库路径。

    Returns:
        今天 00:00 到 23:59 之间的 Interview 列表。
    """
    return list_interviews_today(today=today, db_path=db_path)


def get_tomorrow_interviews(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询明天的面试记录。

    Args:
        today: 查询基准日；未传入时由 reminders 使用系统日期。
        db_path: SQLite 数据库路径。

    Returns:
        明天 00:00 到 23:59 之间的 Interview 列表。
    """
    return list_interviews_tomorrow(today=today, db_path=db_path)


def get_next_three_days_interviews(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询未来三天的面试记录。

    Args:
        today: 查询基准日；未传入时由 reminders 使用系统日期。
        db_path: SQLite 数据库路径。

    Returns:
        未来三天的 Interview 列表，范围包含今天、明天、后天。
    """
    # 未来三天的边界统一由 reminders 维护，service 只表达业务意图。
    return list_interviews_next_three_days(today=today, db_path=db_path)


def get_weekly_interviews(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询本周的面试记录。

    Args:
        today: 查询基准日；未传入时由 reminders 使用系统日期。
        db_path: SQLite 数据库路径。

    Returns:
        ISO 周内的 Interview 列表，范围为周一到周日。
    """
    # 本周范围按 ISO 周计算，即周一到周日。
    return list_interviews_this_week(today=today, db_path=db_path)


def check_missing_info(
    db_path: DbPath = DEFAULT_DB_PATH,
) -> dict[str, list[dict[str, object]]]:
    """汇总检查投递和面试记录的缺失信息。

    Args:
        db_path: SQLite 数据库路径。

    Returns:
        按 applications 和 interviews 分组的缺失信息检查结果。
    """
    # service 负责聚合两类记录，具体缺失规则仍由 missing 模块统一维护。
    return check_all_missing_info(
        applications=list_applications(db_path=db_path),
        interviews=list_interviews(db_path=db_path),
    )


def update_application_status_from_text(
    text: str,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Application:
    """根据自然语言状态文本更新投递状态。

    Args:
        text: 用户输入的状态更新文本，例如“陕西某软件公司一面通过了。”。
        db_path: SQLite 数据库路径。

    Returns:
        更新后的 Application 对象。

    Raises:
        ValueError: 当文本中的公司无法匹配任何投递记录时抛出。
    """
    parsed = parse_status_update_text(text)
    applications = find_applications_by_company(
        str(parsed.get("company") or ""),
        db_path=db_path,
    )
    if not applications:
        raise ValueError("未找到对应公司的投递记录，无法更新状态")

    # V1 简化策略：同一公司有多条投递时先更新第一条；后续版本再按 position 精确匹配。
    target = applications[0]
    if target.id is None:
        raise ValueError("投递记录缺少 id，无法更新状态")

    return update_application_status(
        application_id=target.id,
        status=str(parsed.get("status") or ""),
        db_path=db_path,
    )


def preview_status_update_from_text(
    text: str,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> dict[str, object]:
    """解析状态更新文本并返回保存前预览。

    Args:
        text: 用户输入的状态更新文本，例如“陕西某软件公司一面通过了。”。
        db_path: SQLite 数据库路径。

    Returns:
        包含解析字段、匹配投递记录和 will_save=False 的结构化预览。
    """
    parsed = parse_status_update_text(text)
    applications = find_applications_by_company(
        str(parsed.get("company") or ""),
        db_path=db_path,
    )
    matched_application = applications[0] if applications else None

    # 状态更新同样遵循 preview -> confirm；预览阶段不写数据库。
    return {
        "action": "preview_status_update",
        "parsed": parsed,
        "matched_application": (
            _matched_application_summary(matched_application)
            if matched_application
            else None
        ),
        "needs_application_match": matched_application is None,
        "new_status": parsed.get("status"),
        "will_save": False,
    }


def confirm_update_application_status(
    preview: dict[str, object],
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Application:
    """根据状态更新预览确认写入投递状态。

    Args:
        preview: preview_status_update_from_text 返回的结构化预览。
        db_path: SQLite 数据库路径。

    Returns:
        更新后的 Application 对象。

    Raises:
        ValueError: 当预览没有匹配投递记录时抛出。
    """
    parsed = _parsed_dict(preview)
    matched = preview.get("matched_application")
    if not isinstance(matched, dict) or matched.get("id") is None:
        raise ValueError("状态更新未匹配到投递记录，无法确认保存")

    # V1 简化策略延续 preview 的匹配结果；同公司多投递时后续版本再按岗位精确确认。
    return update_application_status(
        application_id=int(matched["id"]),
        status=str(parsed.get("status") or ""),
        db_path=db_path,
    )
