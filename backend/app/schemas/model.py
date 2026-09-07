"""模型服务状态的 HTTP 响应模型。"""

from pydantic import BaseModel, Field


class ModelHealthResponse(BaseModel):
    ok: bool
    provider: str
    base_url: str
    configured_model: str
    loaded_models: list[str] = Field(default_factory=list)
    server_reachable: bool
    model_available: bool
    error: str | None = None
