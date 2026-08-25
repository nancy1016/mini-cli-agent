"""面试记录只读接口。"""

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.services.v1_adapter import list_interview_rows


router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get("")
def interview_list(
    request: Request,
    range_name: str = Query(default="next_three_days", alias="range"),
) -> list[dict[str, object]]:
    try:
        return list_interview_rows(
            range_name=range_name,
            db_path=request.app.state.database_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
