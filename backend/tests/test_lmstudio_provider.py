"""LM Studio Provider 的无网络单元测试。"""

from collections.abc import Callable

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
