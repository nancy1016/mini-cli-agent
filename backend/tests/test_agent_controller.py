"""V2-01B-1 AgentController 查询、预览和确认测试。"""

from datetime import date, datetime, timedelta, timezone

import pytest

from backend.app.services.agent_controller import (
    AgentController,
    PreviewConflictError,
    PreviewNotFoundError,
)
from jobhunt.repository import (
    create_application,
    create_interview,
    list_applications,
    list_interviews,
)


BASE_DATE = date(2026, 7, 13)


class RecordingModelProvider:
    def __init__(self, *, ok=True, content="模型润色后的回答", error=None):
        self.calls = []
        self.result = {
            "ok": ok,
            "content": content,
            "provider": "LM Studio",
            "model": "qwen2.5-7b-instruct",
            "error": error,
        }

    def chat(self, messages, *, temperature=0.2, max_tokens=300):
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.result


def test_query_applications_returns_real_data(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)

    result = AgentController().handle_agent_message("我现在投了哪些公司？", db_path=db_path)

    assert result["ok"] is True
    assert result["intent"] == "query_applications"
    assert result["data"]["applications"][0]["company"] == "西安吉利科技公司"


def test_query_interviews_supports_fixed_base_date(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    application = create_application(company="面试查询公司", position="测试开发", db_path=db_path)
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time="2026-07-14 15:00",
        db_path=db_path,
    )

    result = AgentController().handle_agent_message(
        "这周有哪些面试？", db_path=db_path, base_date=BASE_DATE
    )

    assert result["ok"] is True
    assert result["data"]["range"] == "this_week"
    assert len(result["data"]["interviews"]) == 1


def test_query_missing_info_returns_real_data(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="缺失信息公司", position="测试", db_path=db_path)

    result = AgentController().handle_agent_message("哪些信息没填完整？", db_path=db_path)

    assert result["ok"] is True
    assert result["intent"] == "query_missing_info"
    assert len(result["data"]["items"]) == 1


def test_query_single_application_status(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(
        company="西安吉利科技公司", position="测试开发", status="一面待进行", db_path=db_path
    )

    result = AgentController().handle_agent_message(
        "西安吉利科技公司目前是什么状态？", db_path=db_path
    )

    assert result["ok"] is True
    assert result["data"]["application"]["status"] == "一面待进行"


def test_status_update_without_company_requests_clarification(tmp_path):
    db_path = tmp_path / "jobhunt.db"

    result = AgentController().handle_agent_message("这个岗位我放弃了。", db_path=db_path)

    assert result["ok"] is False
    assert result["message"] == "请补充公司名称后再更新状态。"
    assert result["preview"] is None


def test_same_company_multiple_positions_requires_clarification(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="重复公司", position="测试开发", db_path=db_path)
    create_application(company="重复公司", position="后端开发", db_path=db_path)
    controller = AgentController()

    query = controller.handle_agent_message("重复公司目前是什么状态？", db_path=db_path)
    update = controller.handle_agent_message("重复公司一面通过了。", db_path=db_path)

    assert query["ok"] is False
    assert len(query["data"]["candidates"]) == 2
    assert update["ok"] is False
    assert update["preview"] is None
    assert [item.status for item in list_applications(db_path=db_path)] == ["已投递", "已投递"]


def test_application_preview_does_not_write_until_confirm(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    controller = AgentController()

    preview = controller.handle_agent_message(
        "今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。",
        db_path=db_path,
        base_date=BASE_DATE,
    )

    assert preview["ok"] is True
    assert preview["intent"] == "preview_application"
    assert preview["requires_confirmation"] is True
    assert list_applications(db_path=db_path) == []

    confirmed = controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=db_path)

    assert confirmed["ok"] is True
    assert confirmed["intent"] == "confirm_application"
    assert list_applications(db_path=db_path)[0].company == "上海百胜软件公司"


def test_interview_preview_and_confirm_update_linked_application(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)
    controller = AgentController()

    preview = controller.handle_agent_message(
        "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
        db_path=db_path,
        base_date=BASE_DATE,
    )

    assert preview["ok"] is True
    assert list_interviews(db_path=db_path) == []
    assert list_applications(db_path=db_path)[0].status == "已投递"

    confirmed = controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=db_path)

    assert confirmed["intent"] == "confirm_interview"
    assert len(list_interviews(db_path=db_path)) == 1
    assert list_applications(db_path=db_path)[0].status == "一面待进行"


def test_status_preview_does_not_update_until_confirm(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)
    controller = AgentController()

    preview = controller.handle_agent_message("西安吉利科技公司一面通过了。", db_path=db_path)

    assert preview["ok"] is True
    assert preview["preview"]["fields"]["old_status"] == "已投递"
    assert preview["preview"]["fields"]["new_status"] == "一面通过"
    assert list_applications(db_path=db_path)[0].status == "已投递"

    controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=db_path)

    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_unknown_preview_id_does_not_write(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    controller = AgentController()

    with pytest.raises(PreviewNotFoundError):
        controller.confirm_agent_preview("does-not-exist", db_path=db_path)
    assert list_applications(db_path=db_path) == []


def test_expired_preview_does_not_write(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    now = [datetime(2026, 7, 13, tzinfo=timezone.utc)]
    controller = AgentController(clock=lambda: now[0])
    preview = controller.handle_agent_message(
        "今天在官网投递了过期测试公司的测试开发岗，地点西安。",
        db_path=db_path,
        base_date=BASE_DATE,
    )
    now[0] += timedelta(minutes=16)

    with pytest.raises(PreviewConflictError, match="过期"):
        controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=db_path)
    assert list_applications(db_path=db_path) == []


def test_consumed_preview_cannot_be_confirmed_twice(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    controller = AgentController()
    preview = controller.handle_agent_message(
        "今天在官网投递了重复确认公司的测试开发岗，地点西安。",
        db_path=db_path,
        base_date=BASE_DATE,
    )
    preview_id = preview["preview"]["preview_id"]

    controller.confirm_agent_preview(preview_id, db_path=db_path)
    with pytest.raises(PreviewConflictError, match="已经确认"):
        controller.confirm_agent_preview(preview_id, db_path=db_path)

    assert len(list_applications(db_path=db_path)) == 1


def test_preview_cannot_be_confirmed_against_another_database(tmp_path):
    source_db = tmp_path / "source.db"
    other_db = tmp_path / "other.db"
    controller = AgentController()
    preview = controller.handle_agent_message(
        "今天在官网投递了跨库保护公司的测试开发岗，地点西安。",
        db_path=source_db,
        base_date=BASE_DATE,
    )

    with pytest.raises(PreviewConflictError, match="数据库不匹配"):
        controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=other_db)

    assert list_applications(db_path=source_db) == []
    assert list_applications(db_path=other_db) == []


def test_interview_without_application_is_not_saved(tmp_path):
    db_path = tmp_path / "jobhunt.db"

    result = AgentController().handle_agent_message(
        "明天下午三点，没有投递记录公司测试开发岗一面，电话通知的。",
        db_path=db_path,
        base_date=BASE_DATE,
    )

    assert result["ok"] is False
    assert result["preview"] is None
    assert list_applications(db_path=db_path) == []
    assert list_interviews(db_path=db_path) == []


def test_unknown_input_never_writes(tmp_path):
    db_path = tmp_path / "jobhunt.db"

    result = AgentController().handle_agent_message("帮我写一封邮件", db_path=db_path)

    assert result["ok"] is False
    assert result["intent"] == "unknown"
    assert list_applications(db_path=db_path) == []


def test_successful_query_uses_model_without_changing_tool_data(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="润色查询公司", position="测试开发", db_path=db_path)
    provider = RecordingModelProvider(content="你目前有 1 条投递记录。")

    result = AgentController(model_provider=provider).handle_agent_message(
        "我现在投了哪些公司？", db_path=db_path
    )

    assert result["message"] == "你目前有 1 条投递记录。"
    assert result["data"]["applications"][0]["company"] == "润色查询公司"
    assert result["model"] == {
        "used": True,
        "provider": "LM Studio",
        "name": "qwen2.5-7b-instruct",
        "fallback_reason": None,
    }
    assert len(provider.calls) == 1


def test_query_falls_back_to_rule_message_when_model_fails(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="回退公司", position="测试开发", db_path=db_path)
    provider = RecordingModelProvider(ok=False, content=None, error="模型调用超时")

    result = AgentController(model_provider=provider).handle_agent_message(
        "我现在投了哪些公司？", db_path=db_path
    )

    assert result["message"] == "目前共有 1 条投递记录。"
    assert result["model"]["used"] is False
    assert "模型调用超时" in result["model"]["fallback_reason"]
    assert result["data"]["applications"][0]["company"] == "回退公司"


def test_preview_confirm_and_unknown_never_call_model(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    provider = RecordingModelProvider()
    controller = AgentController(model_provider=provider)

    preview = controller.handle_agent_message(
        "今天在官网投递了安全边界公司的测试开发岗，地点西安。",
        db_path=db_path,
        base_date=BASE_DATE,
    )
    assert provider.calls == []

    controller.confirm_agent_preview(preview["preview"]["preview_id"], db_path=db_path)
    assert provider.calls == []

    unknown = controller.handle_agent_message("帮我写一首诗", db_path=db_path)
    assert unknown["intent"] == "unknown"
    assert provider.calls == []
