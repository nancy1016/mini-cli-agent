"""
会话历史保存和加载。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import HISTORY_DIR
from utils import to_plain_data


def ensure_history_dir() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def new_session_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_session(
    session_id: str,
    model: str,
    messages: list[dict],
    active_skill_name: str | None = None,
) -> Path:
    ensure_history_dir()

    data = {
        "session_id": session_id,
        "model": model,
        "active_skill_name": active_skill_name,
        "messages": to_plain_data(messages),
    }

    path = HISTORY_DIR / f"{session_id}.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def list_sessions() -> list[Path]:
    ensure_history_dir()
    return sorted(HISTORY_DIR.glob("*.json"), reverse=True)


def load_session(index: int) -> dict[str, Any]:
    sessions = list_sessions()

    if index < 1 or index > len(sessions):
        raise ValueError(f"历史编号不存在：{index}")

    path = sessions[index - 1]
    return json.loads(path.read_text(encoding="utf-8"))


def format_session_list() -> str:
    sessions = list_sessions()

    if not sessions:
        return "暂无历史会话。"

    lines = []
    for i, path in enumerate(sessions, start=1):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            msg_count = len(data.get("messages", []))
            skill = data.get("active_skill_name") or "-"
            lines.append(f"{i}. {path.stem} | messages={msg_count} | skill={skill}")
        except Exception:
            lines.append(f"{i}. {path.stem} | 无法读取")

    return "\n".join(lines)
