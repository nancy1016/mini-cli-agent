"""后端健康检查接口。"""

from fastapi import APIRouter

from backend.app.core.config import PROJECT_NAME


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, object]:
    return {
        "ok": True,
        "service": PROJECT_NAME,
        "version": "v2-01b-3a",
        "message": "backend is running",
    }
