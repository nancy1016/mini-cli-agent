"""将 V1 Web Adapter 能力注册为规则 Agent 工具。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from backend.app.services import v1_adapter


DbPath = str | Path
Tool = Callable[..., object]


def list_applications_tool(*, db_path: DbPath | None = None, **_: object) -> dict[str, object]:
    return {"applications": v1_adapter.list_application_rows(db_path=db_path)}


def list_interviews_tool(
    *,
    range_name: str = "next_three_days",
    db_path: DbPath | None = None,
    base_date: date | None = None,
    **_: object,
) -> dict[str, object]:
    return {
        "range": range_name,
        "interviews": v1_adapter.list_interview_rows(
            range_name=range_name,
            db_path=db_path,
            base_date=base_date,
        ),
    }


def check_missing_info_tool(*, db_path: DbPath | None = None, **_: object) -> dict[str, object]:
    return {"items": v1_adapter.list_missing_info_rows(db_path=db_path)}


def query_application_status_tool(
    *, company: str | None = None, db_path: DbPath | None = None, **_: object
) -> dict[str, object]:
    return v1_adapter.query_application_status(company, db_path=db_path)


def preview_application_tool(
    *, text: str, db_path: DbPath | None = None, base_date: date | None = None, **_: object
) -> dict[str, object]:
    return v1_adapter.preview_application(text, db_path=db_path, base_date=base_date)


def preview_interview_tool(
    *, text: str, db_path: DbPath | None = None, base_date: date | None = None, **_: object
) -> dict[str, object]:
    return v1_adapter.preview_interview(text, db_path=db_path, base_date=base_date)


def preview_status_update_tool(
    *, text: str, db_path: DbPath | None = None, **_: object
) -> dict[str, object]:
    return v1_adapter.preview_status_update(text, db_path=db_path)


def confirm_application_tool(
    *, preview: dict[str, object], db_path: DbPath | None = None
) -> dict[str, object]:
    return {"application": v1_adapter.confirm_application(preview, db_path=db_path)}


def confirm_interview_tool(
    *, preview: dict[str, object], db_path: DbPath | None = None
) -> dict[str, object]:
    return v1_adapter.confirm_interview(preview, db_path=db_path)


def confirm_status_update_tool(
    *, preview: dict[str, object], db_path: DbPath | None = None
) -> dict[str, object]:
    return {"application": v1_adapter.confirm_status_update(preview, db_path=db_path)}


class ToolRegistry:
    """按意图和预览 action 限制可调用的工具集合。"""

    CHAT_TOOLS: dict[str, Tool] = {
        "query_applications": list_applications_tool,
        "query_interviews": list_interviews_tool,
        "query_missing_info": check_missing_info_tool,
        "query_application_status": query_application_status_tool,
        "preview_application": preview_application_tool,
        "preview_interview": preview_interview_tool,
        "preview_status_update": preview_status_update_tool,
    }
    CONFIRM_TOOLS: dict[str, Tool] = {
        "preview_application": confirm_application_tool,
        "preview_interview": confirm_interview_tool,
        "preview_status_update": confirm_status_update_tool,
    }

    def run_chat_tool(
        self,
        intent: str,
        *,
        text: str,
        arguments: dict[str, object],
        db_path: DbPath | None,
        base_date: date | None,
    ) -> object:
        tool = self.CHAT_TOOLS.get(intent)
        if tool is None:
            raise ValueError(f"不支持的 Agent 意图：{intent}")
        return tool(
            text=text,
            db_path=db_path,
            base_date=base_date,
            range_name=arguments.get("range", "next_three_days"),
            company=arguments.get("company"),
        )

    def run_confirm_tool(
        self,
        action: str,
        *,
        preview: dict[str, object],
        db_path: DbPath | None,
    ) -> object:
        tool = self.CONFIRM_TOOLS.get(action)
        if tool is None:
            raise ValueError(f"不支持确认的预览类型：{action}")
        return tool(preview=preview, db_path=db_path)
