"""模型健康检查 API 的无网络测试。"""

import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.llm_provider import ModelHealthResult


AVAILABLE: ModelHealthResult = {
    "ok": True,
    "provider": "LM Studio",
    "base_url": "http://127.0.0.1:1234/v1",
    "configured_model": "qwen2.5-7b-instruct",
    "loaded_models": ["qwen2.5-7b-instruct"],
    "server_reachable": True,
    "model_available": True,
    "error": None,
}


class StubProvider:
    def __init__(self, result: ModelHealthResult) -> None:
        self.result = result

    def health_check(self) -> ModelHealthResult:
        return self.result


class FailIfCalledProvider:
    def health_check(self) -> ModelHealthResult:
        raise AssertionError("agent/chat 不应调用模型 Provider")


def test_model_health_api_returns_available_status(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db", model_provider=StubProvider(AVAILABLE)))

    response = client.get("/api/v1/model/health")

    assert response.status_code == 200
    assert response.json() == AVAILABLE
    assert "api_key" not in json.dumps(response.json())


def test_model_health_api_returns_http_200_when_unavailable(tmp_path):
    unavailable: ModelHealthResult = {
        **AVAILABLE,
        "ok": False,
        "loaded_models": [],
        "server_reachable": False,
        "model_available": False,
        "error": "无法连接 LM Studio",
    }
    client = TestClient(
        create_app(tmp_path / "jobhunt.db", model_provider=StubProvider(unavailable))
    )

    response = client.get("/api/v1/model/health")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error"] == "无法连接 LM Studio"


def test_unavailable_model_provider_does_not_affect_agent_chat(tmp_path):
    client = TestClient(
        create_app(tmp_path / "jobhunt.db", model_provider=FailIfCalledProvider())
    )

    response = client.post("/api/v1/agent/chat", json={"text": "我现在投了哪些公司？"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["intent"] == "query_applications"
    assert response.json()["model"]["used"] is False
