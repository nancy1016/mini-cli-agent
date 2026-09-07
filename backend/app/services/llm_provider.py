"""本地大模型 Provider 的最小公共契约。"""

from typing import Protocol, TypedDict


class ModelHealthResult(TypedDict):
    ok: bool
    provider: str
    base_url: str
    configured_model: str
    loaded_models: list[str]
    server_reachable: bool
    model_available: bool
    error: str | None


class LLMProvider(Protocol):
    def health_check(self) -> ModelHealthResult:
        """返回 Provider 与配置模型的结构化可用状态。"""
        ...
