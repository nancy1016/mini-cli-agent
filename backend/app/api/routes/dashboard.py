"""Dashboard 只读接口。"""

from fastapi import APIRouter, Request

from backend.app.services.v1_adapter import get_dashboard_summary


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(request: Request) -> dict[str, object]:
    return get_dashboard_summary(db_path=request.app.state.database_path)
