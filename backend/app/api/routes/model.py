"""模型 Provider 健康检查接口。"""

from fastapi import APIRouter, Request

from backend.app.schemas.model import ModelHealthResponse


router = APIRouter(prefix="/model", tags=["model"])


@router.get("/health", response_model=ModelHealthResponse)
def model_health(request: Request) -> dict[str, object]:
    return request.app.state.model_provider.health_check()
