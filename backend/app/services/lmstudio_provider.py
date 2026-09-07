"""LM Studio OpenAI-compatible Provider。"""

from __future__ import annotations

import httpx

from backend.app.core.config import (
    LM_STUDIO_API_KEY,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_HEALTH_TIMEOUT_SECONDS,
    MINI_AGENT_MODEL,
)
from backend.app.services.llm_provider import ModelHealthResult


class LMStudioProvider:
    """仅提供模型健康检查；本阶段不调用 chat/completions。"""

    def __init__(
        self,
        base_url: str = LM_STUDIO_BASE_URL,
        model: str = MINI_AGENT_MODEL,
        api_key: str = LM_STUDIO_API_KEY,
        timeout: float = LM_STUDIO_HEALTH_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport

    def _result(
        self,
        *,
        loaded_models: list[str] | None = None,
        server_reachable: bool,
        model_available: bool = False,
        error: str | None,
    ) -> ModelHealthResult:
        return {
            "ok": server_reachable and model_available,
            "provider": "LM Studio",
            "base_url": self.base_url,
            "configured_model": self.model,
            "loaded_models": loaded_models or [],
            "server_reachable": server_reachable,
            "model_available": model_available,
            "error": error,
        }

    def health_check(self) -> ModelHealthResult:
        request_url = f"{self.base_url}/models"
        try:
            with httpx.Client(
                timeout=self.timeout,
                transport=self.transport,
                trust_env=False,
            ) as client:
                response = client.get(request_url)
                response.raise_for_status()
        except httpx.TimeoutException:
            return self._result(
                server_reachable=False,
                error=f"连接 LM Studio 超时；请求 URL：{request_url}",
            )
        except httpx.HTTPStatusError as exc:
            return self._result(
                server_reachable=True,
                error=(
                    f"LM Studio /v1/models 返回 HTTP {exc.response.status_code}；"
                    f"请求 URL：{request_url}"
                ),
            )
        except httpx.RequestError:
            return self._result(
                server_reachable=False,
                error=f"无法连接 LM Studio；请求 URL：{request_url}",
            )
        except Exception:
            return self._result(
                server_reachable=False,
                error=f"LM Studio 健康检查失败；请求 URL：{request_url}",
            )

        try:
            payload = response.json()
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise ValueError("data must be a list")
            loaded_models = []
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                    raise ValueError("model id must be a string")
                loaded_models.append(row["id"])
        except Exception:
            return self._result(
                server_reachable=True,
                error=f"LM Studio 返回格式异常；请求 URL：{request_url}",
            )

        model_available = self.model in loaded_models
        return self._result(
            loaded_models=loaded_models,
            server_reachable=True,
            model_available=model_available,
            error=None if model_available else "配置模型未加载",
        )
