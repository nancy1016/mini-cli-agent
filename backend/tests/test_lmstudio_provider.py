"""LM Studio Provider 的无网络单元测试。"""

from collections.abc import Callable
import json

import httpx
import pytest

from backend.app.services.lmstudio_provider import LMStudioProvider


BASE_URL = "http://127.0.0.1:1234/v1"
MODEL = "qwen2.5-7b-instruct"


def make_provider(handler: Callable[[httpx.Request], httpx.Response]) -> LMStudioProvider:
    return LMStudioProvider(
        base_url=BASE_URL,
        model=MODEL,
        api_key="test-key",
        timeout=2,
        chat_timeout=30,
        transport=httpx.MockTransport(handler),
    )


def test_health_check_returns_available_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == f"{BASE_URL}/models"
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"data": [{"id": MODEL}]})

    result = make_provider(handler).health_check()

    assert result == {
        "ok": True,
        "provider": "LM Studio",
        "base_url": BASE_URL,
        "configured_model": MODEL,
        "loaded_models": [MODEL],
        "server_reachable": True,
        "model_available": True,
        "error": None,
    }


def test_health_check_reports_configured_model_not_loaded():
    provider = make_provider(
        lambda _: httpx.Response(200, json={"data": [{"id": "other-model"}]})
    )

    result = provider.health_check()

    assert result["ok"] is False
    assert result["server_reachable"] is True
    assert result["model_available"] is False
    assert result["loaded_models"] == ["other-model"]
    assert result["error"] == "配置模型未加载"


def test_health_check_disables_environment_proxy(monkeypatch):
    captured: dict[str, object] = {}
    real_client = httpx.Client

    def create_client(*args, **kwargs):
        captured["trust_env"] = kwargs.get("trust_env")
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "backend.app.services.lmstudio_provider.httpx.Client",
        create_client,
    )

    result = make_provider(lambda _: httpx.Response(200, json={"data": [{"id": MODEL}]})).health_check()

    assert result["ok"] is True
    assert captured["trust_env"] is False


def test_health_check_handles_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    result = make_provider(handler).health_check()

    assert result["ok"] is False
    assert result["server_reachable"] is False
    assert result["error"] == f"无法连接 LM Studio；请求 URL：{BASE_URL}/models"


def test_health_check_handles_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    result = make_provider(handler).health_check()

    assert result["ok"] is False
    assert result["server_reachable"] is False
    assert result["error"] == f"连接 LM Studio 超时；请求 URL：{BASE_URL}/models"


def test_health_check_handles_http_error():
    result = make_provider(lambda _: httpx.Response(500)).health_check()

    assert result["ok"] is False
    assert result["server_reachable"] is True
    assert result["error"] == (
        f"LM Studio /v1/models 返回 HTTP 500；请求 URL：{BASE_URL}/models"
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"data": "not-a-list"}),
        httpx.Response(200, json={"data": [{"name": MODEL}]}),
    ],
)
def test_health_check_handles_invalid_response(response: httpx.Response):
    result = make_provider(lambda _: response).health_check()

    assert result["ok"] is False
    assert result["server_reachable"] is True
    assert result["model_available"] is False
    assert result["error"] == f"LM Studio 返回格式异常；请求 URL：{BASE_URL}/models"


def test_chat_returns_model_content_without_tools():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == f"{BASE_URL}/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == MODEL
        assert payload["temperature"] == 0.2
        assert payload["max_tokens"] == 300
        assert payload["stream"] is False
        assert "tools" not in payload
        assert "tool_choice" not in payload
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  润色后的回答。  "}}]},
        )

    result = make_provider(handler).chat([{"role": "user", "content": "查询投递"}])

    assert result == {
        "ok": True,
        "content": "润色后的回答。",
        "provider": "LM Studio",
        "model": MODEL,
        "error": None,
    }


def test_health_and_chat_use_separate_timeouts(monkeypatch):
    captured_timeouts = []
    real_client = httpx.Client

    def create_client(*args, **kwargs):
        captured_timeouts.append(kwargs.get("timeout"))
        return real_client(*args, **kwargs)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "回答"}}]})

    monkeypatch.setattr("backend.app.services.lmstudio_provider.httpx.Client", create_client)
    provider = make_provider(handler)

    provider.health_check()
    provider.chat([])

    assert captured_timeouts == [2, 30]


def test_chat_handles_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    result = make_provider(handler).chat([])

    assert result["ok"] is False
    assert result["content"] is None
    assert result["error"] == "模型服务连接失败"


def test_chat_handles_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    result = make_provider(handler).chat([])

    assert result["ok"] is False
    assert result["error"] == "模型调用超时"


def test_chat_handles_http_error():
    result = make_provider(lambda _: httpx.Response(500)).chat([])

    assert result["ok"] is False
    assert result["error"] == "LM Studio /v1/chat/completions 返回 HTTP 500"


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        (httpx.Response(200, content=b"not-json"), "模型响应格式异常"),
        (httpx.Response(200, json={"choices": []}), "模型响应格式异常"),
        (
            httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
            "模型返回空内容",
        ),
    ],
)
def test_chat_handles_invalid_response(response: httpx.Response, expected_error: str):
    result = make_provider(lambda _: response).chat([])

    assert result["ok"] is False
    assert result["content"] is None
    assert result["error"] == expected_error
