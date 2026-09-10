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


class ModelChatResult(TypedDict):
    ok: bool
    content: str | None
    provider: str
    model: str
    error: str | None


class LLMProvider(Protocol):
    def health_check(self) -> ModelHealthResult:
        """返回 Provider 与配置模型的结构化可用状态。"""
        ...

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
    ) -> ModelChatResult:
        """返回一次无工具、非流式的模型回答。"""
        ...
