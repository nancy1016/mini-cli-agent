"""
通用工具函数。
"""

from __future__ import annotations

from typing import Any


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    """
    兼容 dict 和 Ollama SDK 返回对象。
    有些版本返回 dict，有些地方可能返回具备属性访问的对象。
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def to_plain_data(obj: Any) -> Any:
    """
    把 Ollama SDK 对象转换成 JSON 可序列化的普通 Python 数据。
    """
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [to_plain_data(x) for x in obj]

    if isinstance(obj, tuple):
        return [to_plain_data(x) for x in obj]

    if isinstance(obj, dict):
        return {str(k): to_plain_data(v) for k, v in obj.items()}

    if hasattr(obj, "model_dump"):
        return to_plain_data(obj.model_dump())

    if hasattr(obj, "dict"):
        return to_plain_data(obj.dict())

    try:
        return dict(obj)
    except Exception:
        return str(obj)


def truncate_text(text: str, max_chars: int) -> str:
    """
    截断过长文本，保留开头和结尾。
    """
    if len(text) <= max_chars:
        return text

    half = max_chars // 2
    return (
        text[:half]
        + "\n\n...[TRUNCATED: 内容过长，已截断]...\n\n"
        + text[-half:]
    )
