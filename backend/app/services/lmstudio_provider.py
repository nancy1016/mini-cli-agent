"""LM Studio OpenAI-compatible Provider。"""

from __future__ import annotations

import httpx

from backend.app.core.config import (
    LM_STUDIO_API_KEY,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_CHAT_TIMEOUT_SECONDS,
    LM_STUDIO_HEALTH_TIMEOUT_SECONDS,
    MINI_AGENT_MODEL,
)
from backend.app.services.llm_provider import ModelChatResult, ModelHealthResult


class LMStudioProvider:
    """提供模型健康检查和无工具、非流式 Chat 调用。"""

    def __init__(
        self,
        base_url: str = LM_STUDIO_BASE_URL,
        model: str = MINI_AGENT_MODEL,
        api_key: str = LM_STUDIO_API_KEY,
        timeout: float = LM_STUDIO_HEALTH_TIMEOUT_SECONDS,
        chat_timeout: float = LM_STUDIO_CHAT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.chat_timeout = chat_timeout
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

    def _chat_result(
        self,
        *,
        content: str | None = None,
        error: str | None = None,
    ) -> ModelChatResult:
        return {
            "ok": error is None and bool(content),
            "content": content,
            "provider": "LM Studio",
            "model": self.model,
            "error": error,
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
    ) -> ModelChatResult:
        request_url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max(1, min(max_tokens, 300)),
            "stream": False,
        }
        try:
            with httpx.Client(
                timeout=self.chat_timeout,
                transport=self.transport,
                trust_env=False,
            ) as client:
                response = client.post(
                    request_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            return self._chat_result(error="模型调用超时")
        except httpx.HTTPStatusError as exc:
            return self._chat_result(
                error=f"LM Studio /v1/chat/completions 返回 HTTP {exc.response.status_code}"
            )
        except httpx.RequestError:
            return self._chat_result(error="模型服务连接失败")
        except Exception:
            return self._chat_result(error="模型调用失败")

        try:
            body = response.json()
            choices = body.get("choices") if isinstance(body, dict) else None
            if not isinstance(choices, list) or not choices:
                raise ValueError("choices must be a non-empty list")
            choice = choices[0]
            message = choice.get("message") if isinstance(choice, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str):
                raise ValueError("message content must be a string")
        except Exception:
            return self._chat_result(error="模型响应格式异常")

        if not content.strip():
            return self._chat_result(error="模型返回空内容")

        return self._chat_result(content=content.strip())
