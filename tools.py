"""
Agent 工具定义和工具分发器。

当前提供两类工具：
- 通用安全工具：获取当前时间、列出 workspace 文件、读取 workspace 文本文件；
- JobHuntLedger 工具：支持求职投递、面试、状态更新、查询和缺失信息检查。

写库类 JobHunt 工具必须经过“预览 -> 用户确认 -> 保存/更新”的流程，
未传入 confirmed=true 时不会写入数据库。
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

from config import WORKSPACE_DIR, MAX_TOOL_RESULT_CHARS
from jobhunt.database import DEFAULT_DB_PATH
from jobhunt.service import (
    check_missing_info,
    confirm_create_application,
    confirm_create_interview,
    confirm_update_application_status,
    get_next_three_days_interviews,
    get_today_interviews,
    get_tomorrow_interviews,
    get_weekly_interviews,
    list_all_applications,
    preview_application_from_text,
    preview_interview_from_text,
    preview_status_update_from_text,
)
from jobhunt.repository import list_interviews
from utils import get_field, truncate_text


def ensure_workspace() -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def safe_resolve_workspace_path(path: str) -> Path:
    """
    安全解析 workspace 内部路径。
    禁止访问 workspace 之外的路径。
    """
    ensure_workspace()

    if not path:
        raise ValueError("路径不能为空")

    # 去掉用户可能输入的前缀，提升易用性：
    # read_text_file("workspace/README.md") -> README.md
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("workspace/"):
        normalized = normalized[len("workspace/"):]

    target = (WORKSPACE_DIR / normalized).resolve()
    workspace_root = WORKSPACE_DIR.resolve()

    try:
        target.relative_to(workspace_root)
    except ValueError:
        raise ValueError("禁止访问 workspace 目录之外的路径")

    return target


def get_current_datetime() -> str:
    """
    获取当前本地日期和时间。
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_workspace_files() -> str:
    """
    列出 workspace 目录下的文件。
    """
    ensure_workspace()

    files = []
    for p in sorted(WORKSPACE_DIR.rglob("*")):
        if p.is_file():
            files.append(str(p.relative_to(WORKSPACE_DIR)))

    if not files:
        return "workspace 目录下没有文件。"

    if len(files) > 200:
        shown = files[:200]
        return "\n".join(shown) + f"\n\n...[TRUNCATED: 共 {len(files)} 个文件，仅显示前 200 个]"

    return "\n".join(files)


def read_text_file(path: str) -> str:
    """
    读取 workspace 目录下的文本文件。
    """
    try:
        target = safe_resolve_workspace_path(path)

        if not target.exists():
            return f"ERROR: 文件不存在: {path}"

        if not target.is_file():
            return f"ERROR: 不是文件: {path}"

        size = target.stat().st_size
        if size > 200_000:
            return f"ERROR: 文件过大：{size} bytes。第一版 Demo 暂不读取超过 200KB 的文件。"

        content = target.read_text(encoding="utf-8", errors="replace")
        return content

    except Exception as e:
        return f"ERROR: {e}"


def _to_jsonable(value: Any) -> Any:
    """将 service 返回对象转换为适合工具返回的 JSON 数据。"""
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    return value


def _json_tool_result(value: Any) -> str:
    return json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2)


def _jobhunt_success(data: Any) -> str:
    return _json_tool_result({"ok": True, "data": data})


def _jobhunt_error(message: str) -> str:
    return _json_tool_result({"ok": False, "error": message})


def _coerce_preview(preview: Any) -> dict[str, object]:
    data = preview
    if isinstance(preview, str):
        data = json.loads(preview)

    if isinstance(data, dict):
        if data.get("ok") is True and isinstance(data.get("data"), dict):
            return data["data"]
        if "action" in data:
            return data

    raise ValueError("preview 必须是预览工具返回的 JSON 对象")


def _parse_tool_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _tool_db_path(db_path: str | None = None, **kwargs: Any) -> str | Path:
    return db_path or kwargs.get("db_path") or DEFAULT_DB_PATH


def jobhunt_preview_application(
    text: str,
    base_date: str | None = None,
    **kwargs: Any,
) -> str:
    return _jobhunt_success(
        preview_application_from_text(
            text=text,
            base_date=_parse_tool_date(base_date),
        )
    )


def jobhunt_save_application(
    preview: Any,
    confirmed: bool = False,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    if confirmed is not True:
        return _jobhunt_error("写入数据库前必须先向用户展示预览，并传入 confirmed=true")

    application = confirm_create_application(
        preview=_coerce_preview(preview),
        db_path=_tool_db_path(db_path, **kwargs),
    )
    return _jobhunt_success({"saved": True, "application": application})


def jobhunt_preview_interview(
    text: str,
    base_date: str | None = None,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    return _jobhunt_success(
        preview_interview_from_text(
            text=text,
            base_date=_parse_tool_date(base_date),
            db_path=_tool_db_path(db_path, **kwargs),
        )
    )


def jobhunt_save_interview(
    preview: Any,
    confirmed: bool = False,
    create_application_if_missing: bool = False,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    if confirmed is not True:
        return _jobhunt_error("写入数据库前必须先向用户展示预览，并传入 confirmed=true")

    result = confirm_create_interview(
        preview=_coerce_preview(preview),
        create_application_if_missing=create_application_if_missing,
        db_path=_tool_db_path(db_path, **kwargs),
    )
    return _jobhunt_success({"saved": True, **result})


def jobhunt_preview_status_update(
    text: str,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    return _jobhunt_success(
        preview_status_update_from_text(
            text=text,
            db_path=_tool_db_path(db_path, **kwargs),
        )
    )


def jobhunt_update_status(
    preview: Any,
    confirmed: bool = False,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    if confirmed is not True:
        return _jobhunt_error("写入数据库前必须先向用户展示预览，并传入 confirmed=true")

    application = confirm_update_application_status(
        preview=_coerce_preview(preview),
        db_path=_tool_db_path(db_path, **kwargs),
    )
    return _jobhunt_success({"updated": True, "application": application})


def jobhunt_list_applications(
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    applications = list_all_applications(db_path=_tool_db_path(db_path, **kwargs))
    return _jobhunt_success({"applications": applications})


def jobhunt_list_interviews(
    range: str = "all",
    today: str | None = None,
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    db = _tool_db_path(db_path, **kwargs)
    current_day = _parse_tool_date(today)
    if range == "all":
        interviews = list_interviews(db_path=db)
    elif range == "today":
        interviews = get_today_interviews(today=current_day, db_path=db)
    elif range == "tomorrow":
        interviews = get_tomorrow_interviews(today=current_day, db_path=db)
    elif range == "next_three_days":
        interviews = get_next_three_days_interviews(today=current_day, db_path=db)
    elif range == "this_week":
        interviews = get_weekly_interviews(today=current_day, db_path=db)
    else:
        return _jobhunt_error(f"不支持的面试查询范围：{range}")
    return _jobhunt_success({"range": range, "interviews": interviews})


def jobhunt_check_missing_info(
    db_path: str | None = None,
    **kwargs: Any,
) -> str:
    missing_info = check_missing_info(db_path=_tool_db_path(db_path, **kwargs))
    return _jobhunt_success({"missing_info": missing_info})


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "获取当前本地日期和时间。当用户询问现在时间、日期、今天几号时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "列出 workspace 目录下的文件。当用户询问工作区有哪些文件，或需要先查看文件列表时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "读取 workspace 目录下的文本文件内容。当用户要求查看、分析、总结某个本地文件时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于 workspace 目录的文件路径，例如 README.md 或 docs/intro.md。",
                    }
                },
                "required": ["path"],
            },
        },
    },
]


JOBHUNT_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "jobhunt_preview_application",
            "description": "预览一段投递文本的解析结果和缺失信息。只预览，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "用户描述投递记录的原始文本。",
                    },
                    "base_date": {
                        "type": "string",
                        "description": "可选，YYYY-MM-DD，用于解析今天/明天等相对日期。",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_save_application",
            "description": "用户明确确认投递预览无误后，保存投递记录。必须先调用 jobhunt_preview_application，并且 confirmed 必须为 true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "preview": {
                        "type": "object",
                        "description": "jobhunt_preview_application 返回的完整 JSON 对象。",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "用户明确确认保存时传 true。",
                    },
                },
                "required": ["preview", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_preview_interview",
            "description": "预览一段面试通知文本的解析结果、匹配投递记录和缺失信息。只预览，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "用户描述面试通知的原始文本。",
                    },
                    "base_date": {
                        "type": "string",
                        "description": "可选，YYYY-MM-DD，用于解析今天/明天/下周等相对日期。",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_save_interview",
            "description": "用户明确确认面试预览无误后，保存面试记录。必须先调用 jobhunt_preview_interview，并且 confirmed 必须为 true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "preview": {
                        "type": "object",
                        "description": "jobhunt_preview_interview 返回的完整 JSON 对象。",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "用户明确确认保存时传 true。",
                    },
                    "create_application_if_missing": {
                        "type": "boolean",
                        "description": "面试未匹配投递时，用户是否确认同时创建投递记录。",
                    },
                },
                "required": ["preview", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_preview_status_update",
            "description": "预览一段状态更新文本的解析结果和匹配投递记录。只预览，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "用户描述状态变化的原始文本，例如“陕西某软件公司一面通过了”。",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_update_status",
            "description": "用户明确确认状态更新预览无误后，更新投递状态。必须先调用 jobhunt_preview_status_update，并且 confirmed 必须为 true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "preview": {
                        "type": "object",
                        "description": "jobhunt_preview_status_update 返回的完整 JSON 对象。",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "用户明确确认更新时传 true。",
                    },
                },
                "required": ["preview", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_list_applications",
            "description": "查询所有求职投递记录。只读，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_list_interviews",
            "description": "按范围查询面试记录。只读，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "range": {
                        "type": "string",
                        "enum": ["all", "today", "tomorrow", "next_three_days", "this_week"],
                        "description": "查询范围：all 全部，today 今天，tomorrow 明天，next_three_days 未来三天，this_week 本周。",
                    },
                    "today": {
                        "type": "string",
                        "description": "可选，YYYY-MM-DD，作为 today/tomorrow/next_three_days/this_week 的查询基准日。",
                    },
                },
                "required": ["range"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jobhunt_check_missing_info",
            "description": "检查所有投递和面试记录的缺失信息。只读，不写入数据库。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

TOOL_SCHEMAS.extend(JOBHUNT_TOOL_SCHEMAS)


TOOL_FUNCTIONS = {
    "get_current_datetime": lambda **kwargs: get_current_datetime(),
    "list_workspace_files": lambda **kwargs: list_workspace_files(),
    "read_text_file": lambda **kwargs: read_text_file(kwargs.get("path", "")),
}

TOOL_FUNCTIONS.update(
    {
        "jobhunt_preview_application": jobhunt_preview_application,
        "jobhunt_save_application": jobhunt_save_application,
        "jobhunt_preview_interview": jobhunt_preview_interview,
        "jobhunt_save_interview": jobhunt_save_interview,
        "jobhunt_preview_status_update": jobhunt_preview_status_update,
        "jobhunt_update_status": jobhunt_update_status,
        "jobhunt_list_applications": jobhunt_list_applications,
        "jobhunt_list_interviews": jobhunt_list_interviews,
        "jobhunt_check_missing_info": jobhunt_check_missing_info,
    }
)


def normalize_tool_call(tool_call: Any) -> dict:
    """
    把 Ollama 返回的 tool_call 统一成 dict。
    """
    function = get_field(tool_call, "function", {})
    name = get_field(function, "name", None)
    arguments = get_field(function, "arguments", {})

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}

    if arguments is None:
        arguments = {}

    return {
        "name": name,
        "arguments": arguments,
    }


def run_tool_call(tool_call: Any) -> dict:
    """
    执行单个工具调用，并返回 role=tool 的 message。
    """
    normalized = normalize_tool_call(tool_call)
    name = normalized["name"]
    arguments = normalized["arguments"]

    if not name:
        result = "ERROR: 工具调用缺少函数名。"

    elif name not in TOOL_FUNCTIONS:
        result = f"ERROR: 未知工具: {name}"

    else:
        try:
            result = TOOL_FUNCTIONS[name](**arguments)
        except Exception as e:
            result = f"ERROR: 工具执行失败: {e}"

    result = truncate_text(str(result), MAX_TOOL_RESULT_CHARS)

    # 保留 tool_name 可以帮助模型知道是哪一个工具返回的结果
    return {
        "role": "tool",
        "tool_name": name or "unknown_tool",
        "content": result,
    }


def tool_names() -> list[str]:
    return [schema["function"]["name"] for schema in TOOL_SCHEMAS]
