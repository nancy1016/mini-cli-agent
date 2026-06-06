"""
Agent 工具定义和工具分发器。

第一版只提供安全的只读工具：
- 获取当前时间
- 列出 workspace 文件
- 读取 workspace 文本文件

不提供 shell 执行，不提供写文件。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import WORKSPACE_DIR, MAX_TOOL_RESULT_CHARS
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


TOOL_FUNCTIONS = {
    "get_current_datetime": lambda **kwargs: get_current_datetime(),
    "list_workspace_files": lambda **kwargs: list_workspace_files(),
    "read_text_file": lambda **kwargs: read_text_file(kwargs.get("path", "")),
}


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
