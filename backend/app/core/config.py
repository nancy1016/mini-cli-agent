"""V2-01A Web MVP 的轻量配置。"""

from pathlib import Path


PROJECT_NAME = "JobHuntLedger-Agent"
API_PREFIX = "/api/v1"
DATABASE_PATH = "data/jobhunt.db"


def resolve_database_path(db_path: str | Path | None = None) -> Path:
    """将 API 或测试传入的数据库路径归一化为 Path。"""
    return Path(db_path or DATABASE_PATH)
