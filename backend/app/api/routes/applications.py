"""投递记录只读接口。"""

from fastapi import APIRouter, Query, Request

from backend.app.services.v1_adapter import list_application_rows


router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
def application_list(
    request: Request,
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> list[dict[str, object]]:
    return list_application_rows(
        status=status,
        keyword=keyword,
        db_path=request.app.state.database_path,
    )
