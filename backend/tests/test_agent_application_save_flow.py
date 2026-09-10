"""V2-01C-0 Agent 新增投递保存主链路测试。"""

from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import list_applications


class NoWriteModelProvider:
    """记录模型调用；新增投递 preview/confirm 均不应触发 chat。"""

    def __init__(self) -> None:
        self.chat_calls = 0

    def chat(self, messages, *, temperature=0.2, max_tokens=300):
        self.chat_calls += 1
        return {
            "ok": False,
            "content": None,
            "provider": "test",
            "model": "must-not-be-called",
            "error": "unexpected model call",
        }

    def health_check(self):
        return {
            "ok": False,
            "provider": "test",
            "base_url": "http://127.0.0.1:1234/v1",
            "configured_model": "must-not-be-called",
            "loaded_models": [],
            "server_reachable": False,
            "model_available": False,
            "error": "not used by this test",
        }


def test_agent_application_preview_confirm_and_list_flow(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    provider = NoWriteModelProvider()
    client = TestClient(create_app(db_path, model_provider=provider))
    text = "今天投了浙江大华公司的大模型开发岗"

    assert client.get("/api/v1/applications").json() == []

    preview_response = client.post("/api/v1/agent/chat", json={"text": text})

    assert preview_response.status_code == 200
    preview_body = preview_response.json()
    assert preview_body["intent"] == "preview_application"
    assert preview_body["requires_confirmation"] is True
    assert preview_body["preview"]["preview_id"]
    assert preview_body["preview"]["type"] == "application"
    fields = preview_body["preview"]["fields"]
    assert fields["company"] == "浙江大华公司"
    assert fields["position"] == "大模型开发"
    assert fields["apply_date"] == date.today().isoformat()
    assert fields["status"] == "已投递"
    assert fields["location"] == "待补充"
    assert fields["apply_source"] == "待补充"
    assert fields["apply_link"] == ""
    assert set(preview_body["preview"]["missing"]["recommended"]) == {
        "location",
        "apply_source",
    }
    assert preview_body["model"]["used"] is False
    assert provider.chat_calls == 0
    assert list_applications(db_path=db_path) == []
    assert client.get("/api/v1/applications", params={"keyword": "浙江大华"}).json() == []

    confirm_response = client.post(
        "/api/v1/agent/confirm",
        json={"preview_id": preview_body["preview"]["preview_id"]},
    )

    assert confirm_response.status_code == 200
    confirm_body = confirm_response.json()
    assert confirm_body["intent"] == "confirm_application"
    assert confirm_body["requires_confirmation"] is False
    assert confirm_body["model"]["used"] is False
    assert provider.chat_calls == 0

    saved = list_applications(db_path=db_path)
    assert len(saved) == 1
    assert saved[0].company == "浙江大华公司"
    assert saved[0].position == "大模型开发"
    assert saved[0].apply_date == date.today().isoformat()
    assert saved[0].status == "已投递"

    rows = client.get("/api/v1/applications", params={"keyword": "浙江大华"}).json()
    assert len(rows) == 1
    assert rows[0]["company"] == "浙江大华公司"
    assert rows[0]["position"] == "大模型开发"
    assert rows[0]["status"] == "已投递"
