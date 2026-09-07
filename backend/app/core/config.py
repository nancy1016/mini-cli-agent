"""Web 应用的轻量配置。"""

import os
from pathlib import Path


PROJECT_NAME = "JobHuntLedger-Agent"
API_PREFIX = "/api/v1"
DATABASE_PATH = "data/jobhunt.db"
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
MINI_AGENT_MODEL = os.getenv("MINI_AGENT_MODEL", "qwen2.5-7b-instruct")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")


def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


LM_STUDIO_HEALTH_TIMEOUT_SECONDS = _positive_float_env(
    "LM_STUDIO_HEALTH_TIMEOUT_SECONDS",
    2.0,
)


def resolve_database_path(db_path: str | Path | None = None) -> Path:
    """将 API 或测试传入的数据库路径归一化为 Path。"""
    return Path(db_path or DATABASE_PATH)
