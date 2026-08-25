"""缺失信息只读接口。"""

from fastapi import APIRouter, Request

from backend.app.services.v1_adapter import list_missing_info_rows


router = APIRouter(prefix="/missing-info", tags=["missing-info"])


@router.get("")
def missing_info_list(request: Request) -> list[dict[str, object]]:
    return list_missing_info_rows(db_path=request.app.state.database_path)
