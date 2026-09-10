"""V2-01B-1 规则 Agent HTTP API 测试。"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import create_application, create_interview, list_applications, list_interviews


class ApiModelProvider:
    def health_check(self):
        return {
            "ok": True,
            "provider": "LM Studio",
            "base_url": "http://127.0.0.1:1234/v1",
            "configured_model": "qwen2.5-7b-instruct",
            "loaded_models": ["qwen2.5-7b-instruct"],
            "server_reachable": True,
            "model_available": True,
            "error": None,
        }

    def chat(self, messages, *, temperature=0.2, max_tokens=300):
        return {
            "ok": True,
            "content": "你目前有 1 条投递记录。",
            "provider": "LM Studio",
            "model": "qwen2.5-7b-instruct",
            "error": None,
        }


def test_agent_chat_queries_applications(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="查询公司", position="测试开发", db_path=db_path)
    client = TestClient(create_app(db_path))

    response = client.post("/api/v1/agent/chat", json={"text": "我现在投了哪些公司？"})

    assert response.status_code == 200
    assert response.json()["data"]["applications"][0]["company"] == "查询公司"


def test_agent_chat_queries_interviews(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    application = create_application(company="今天面试公司", position="测试", db_path=db_path)
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time=f"{date.today().isoformat()} 15:00",
        db_path=db_path,
    )
    client = TestClient(create_app(db_path))

    response = client.post("/api/v1/agent/chat", json={"text": "今天有哪些面试？"})

    assert response.status_code == 200
    assert len(response.json()["data"]["interviews"]) == 1


def test_agent_chat_queries_missing_info(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="缺失公司", position="测试", db_path=db_path)
    client = TestClient(create_app(db_path))

    response = client.post("/api/v1/agent/chat", json={"text": "哪些信息没填完整？"})

    assert response.status_code == 200
    assert response.json()["intent"] == "query_missing_info"
    assert len(response.json()["data"]["items"]) == 1


def test_agent_application_preview_and_confirm(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    client = TestClient(create_app(db_path))
    chat = client.post(
        "/api/v1/agent/chat",
        json={"text": "今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。"},
    )

    assert chat.status_code == 200
    preview_id = chat.json()["preview"]["preview_id"]
    assert list_applications(db_path=db_path) == []

    confirm = client.post("/api/v1/agent/confirm", json={"preview_id": preview_id})

    assert confirm.status_code == 200
    assert confirm.json()["intent"] == "confirm_application"
    assert len(list_applications(db_path=db_path)) == 1


def test_agent_interview_preview_and_confirm(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)
    client = TestClient(create_app(db_path))
    tomorrow = date.today() + timedelta(days=1)
    chat = client.post(
        "/api/v1/agent/chat",
        json={"text": "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。"},
    )

    assert chat.status_code == 200
    assert chat.json()["preview"]["fields"]["interview_time"] == f"{tomorrow.isoformat()} 15:00"
    assert list_interviews(db_path=db_path) == []

    confirm = client.post(
        "/api/v1/agent/confirm",
        json={"preview_id": chat.json()["preview"]["preview_id"]},
    )

    assert confirm.status_code == 200
    assert len(list_interviews(db_path=db_path)) == 1


def test_agent_status_preview_and_confirm(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)
    client = TestClient(create_app(db_path))
    chat = client.post(
        "/api/v1/agent/chat", json={"text": "西安吉利科技公司一面通过了。"}
    )

    assert chat.status_code == 200
    assert list_applications(db_path=db_path)[0].status == "已投递"

    confirm = client.post(
        "/api/v1/agent/confirm",
        json={"preview_id": chat.json()["preview"]["preview_id"]},
    )

    assert confirm.status_code == 200
    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_agent_unknown_returns_ok_false(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db"))

    response = client.post("/api/v1/agent/chat", json={"text": "帮我写一首诗"})

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["intent"] == "unknown"


def test_agent_confirm_unknown_preview_returns_404(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db"))

    response = client.post("/api/v1/agent/confirm", json={"preview_id": "missing"})

    assert response.status_code == 404


def test_agent_confirm_same_preview_twice_returns_409(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    client = TestClient(create_app(db_path))
    chat = client.post(
        "/api/v1/agent/chat",
        json={"text": "今天在官网投递了重复API公司公司的测试岗，地点西安。"},
    )
    preview_id = chat.json()["preview"]["preview_id"]

    first = client.post("/api/v1/agent/confirm", json={"preview_id": preview_id})
    second = client.post("/api/v1/agent/confirm", json={"preview_id": preview_id})

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(list_applications(db_path=db_path)) == 1


def test_agent_request_validation_returns_422(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db"))

    assert client.post("/api/v1/agent/chat", json={}).status_code == 422
    assert client.post("/api/v1/agent/confirm", json={}).status_code == 422


def test_agent_chat_api_exposes_model_usage_without_changing_data(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="API 润色公司", position="测试开发", db_path=db_path)
    client = TestClient(create_app(db_path, model_provider=ApiModelProvider()))

    response = client.post("/api/v1/agent/chat", json={"text": "我现在投了哪些公司？"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "你目前有 1 条投递记录。"
    assert body["data"]["applications"][0]["company"] == "API 润色公司"
    assert body["model"] == {
        "used": True,
        "provider": "LM Studio",
        "name": "qwen2.5-7b-instruct",
        "fallback_reason": None,
    }
