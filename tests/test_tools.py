"""Agent 工具层的 JobHuntLedger V1 接入测试。"""

from __future__ import annotations

import json
from datetime import date

import pytest

import jobhunt.parser
from jobhunt.repository import (
    create_application,
    create_interview,
    list_applications,
    list_interviews,
)
from tools import (
    TOOL_SCHEMAS,
    TOOL_FUNCTIONS,
    jobhunt_list_applications,
    jobhunt_list_interviews,
    jobhunt_preview_application,
    jobhunt_preview_interview,
    jobhunt_preview_status_update,
    jobhunt_save_application,
    jobhunt_save_interview,
    jobhunt_update_status,
    run_tool_call,
    tool_names,
)


@pytest.fixture
def db_path(tmp_path):
    # 工具层测试也使用临时库，避免污染真实求职台账。
    return tmp_path / "jobhunt.db"


def _load_json(text: str):
    return json.loads(text)


class FixedToday(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 11)


def test_jobhunt_tools_are_registered():
    expected = {
        "jobhunt_preview_application",
        "jobhunt_save_application",
        "jobhunt_preview_interview",
        "jobhunt_save_interview",
        "jobhunt_preview_status_update",
        "jobhunt_update_status",
        "jobhunt_list_applications",
        "jobhunt_list_interviews",
        "jobhunt_check_missing_info",
    }

    assert expected.issubset(set(tool_names()))
    assert expected.issubset(set(TOOL_FUNCTIONS))


def test_preview_tool_schemas_do_not_expose_base_date():
    schemas = {
        schema["function"]["name"]: schema["function"]
        for schema in TOOL_SCHEMAS
    }

    application_properties = schemas["jobhunt_preview_application"]["parameters"][
        "properties"
    ]
    interview_properties = schemas["jobhunt_preview_interview"]["parameters"][
        "properties"
    ]
    assert "base_date" not in application_properties
    assert "base_date" not in interview_properties


def test_list_interviews_schema_includes_next_thirty_days_range():
    schemas = {
        schema["function"]["name"]: schema["function"]
        for schema in TOOL_SCHEMAS
    }
    range_schema = schemas["jobhunt_list_interviews"]["parameters"]["properties"][
        "range"
    ]

    assert "next_thirty_days" in range_schema["enum"]


def test_jobhunt_preview_application_returns_wrapped_json():
    result = jobhunt_preview_application(
        text="今天在官网投了西安某科技公司的测试开发岗，地点西安。",
        base_date="2026-06-20",
    )

    data = _load_json(result)
    assert data["ok"] is True
    assert data["data"]["action"] == "preview_application"
    assert data["data"]["parsed"]["company"] == "西安某科技公司"
    assert data["data"]["will_save"] is False


def test_jobhunt_preview_interview_ignores_model_generated_base_date(monkeypatch):
    monkeypatch.setattr(jobhunt.parser, "date", FixedToday)

    result = _load_json(
        jobhunt_preview_interview(
            text="明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
            base_date="2023-04-15",
        )
    )

    assert result["ok"] is True
    assert result["data"]["parsed"]["interview_time"] == "2026-07-12 15:00"


def test_jobhunt_save_application_unconfirmed_returns_error_and_does_not_write(db_path):
    preview = _load_json(
        jobhunt_preview_application(
            text="今天在官网投了西安某科技公司的测试开发岗，地点西安。",
            base_date="2026-06-20",
        )
    )

    result = _load_json(
        jobhunt_save_application(preview=preview, confirmed=False, db_path=str(db_path))
    )

    assert result["ok"] is False
    assert "error" in result
    assert list_applications(db_path=db_path) == []


def test_run_tool_call_returns_error_when_write_tool_not_confirmed(db_path):
    preview = _load_json(
        jobhunt_preview_application(
            text="今天在官网投了西安某科技公司的测试开发岗，地点西安。",
            base_date="2026-06-20",
        )
    )
    tool_call = {
        "id": "call_1",
        "function": {
            "name": "jobhunt_save_application",
            "arguments": json.dumps(
                {
                    "preview": preview,
                    "confirmed": False,
                    "db_path": str(db_path),
                },
                ensure_ascii=False,
            ),
        },
    }

    result = run_tool_call(tool_call)

    content = _load_json(result["content"])
    assert result["tool_name"] == "jobhunt_save_application"
    assert content["ok"] is False
    assert "error" in content
    assert list_applications(db_path=db_path) == []


def test_jobhunt_save_application_writes_after_confirmed(db_path):
    preview = _load_json(
        jobhunt_preview_application(
            text="今天在官网投了西安某科技公司的测试开发岗，地点西安。",
            base_date="2026-06-20",
        )
    )

    result = _load_json(
        jobhunt_save_application(
            preview=preview,
            confirmed=True,
            db_path=str(db_path),
        )
    )

    assert result["ok"] is True
    assert result["data"]["saved"] is True
    assert result["data"]["application"]["company"] == "西安某科技公司"
    assert list_applications(db_path=db_path)[0].company == "西安某科技公司"


def test_jobhunt_list_applications_returns_json_records(db_path):
    create_application(company="陕西某软件公司", position="软件测试", db_path=db_path)
    create_application(company="西安某科技公司", position="测试开发", db_path=db_path)

    result = _load_json(jobhunt_list_applications(db_path=str(db_path)))

    assert result["ok"] is True
    assert [item["company"] for item in result["data"]["applications"]] == [
        "陕西某软件公司",
        "西安某科技公司",
    ]


def test_jobhunt_list_interviews_uses_unified_range_parameter(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    today_interview = create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time="2026-06-20 10:00",
        db_path=db_path,
    )
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="二面",
        interview_time="2026-06-21 10:00",
        db_path=db_path,
    )

    result = _load_json(
        jobhunt_list_interviews(
            range="today",
            today="2026-06-20",
            db_path=str(db_path),
        )
    )

    assert result["ok"] is True
    assert result["data"]["range"] == "today"
    assert result["data"]["interviews"] == [
        {
            "id": today_interview.id,
            "application_id": application.id,
            "company": "陕西某软件公司",
            "position": "软件测试",
            "stage": "一面",
            "interview_time": "2026-06-20 10:00",
            "interview_method": None,
            "meeting_link": None,
            "notes": None,
        }
    ]


def test_jobhunt_list_interviews_supports_next_thirty_days(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    inside = create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time="2026-08-01 10:00",
        db_path=db_path,
    )
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="二面",
        interview_time="2026-08-12 10:00",
        db_path=db_path,
    )

    result = _load_json(
        jobhunt_list_interviews(
            range="next_thirty_days",
            today="2026-07-12",
            db_path=str(db_path),
        )
    )

    assert result["ok"] is True
    assert result["data"]["range"] == "next_thirty_days"
    assert [item["id"] for item in result["data"]["interviews"]] == [inside.id]


def test_jobhunt_list_interviews_unknown_range_returns_error(db_path):
    result = _load_json(
        jobhunt_list_interviews(
            range="unknown",
            today="2026-06-20",
            db_path=str(db_path),
        )
    )

    assert result["ok"] is False
    assert "error" in result


def test_jobhunt_update_status_requires_preview_and_confirmation(db_path):
    create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    preview = _load_json(
        jobhunt_preview_status_update(
            text="陕西某软件公司一面通过了。",
            db_path=str(db_path),
        )
    )

    result = _load_json(
        jobhunt_update_status(preview=preview, confirmed=False, db_path=str(db_path))
    )

    assert result["ok"] is False
    assert list_applications(db_path=db_path)[0].status == "已投递"

    updated = _load_json(
        jobhunt_update_status(preview=preview, confirmed=True, db_path=str(db_path))
    )

    assert updated["ok"] is True
    assert updated["data"]["updated"] is True
    assert updated["data"]["application"]["status"] == "一面通过"
    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_jobhunt_save_interview_unconfirmed_returns_error_and_does_not_write(db_path):
    create_application(
        company="西安某科技公司",
        position="测试开发",
        db_path=db_path,
    )
    preview = _load_json(
        jobhunt_preview_interview(
            text="明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
            base_date="2026-06-20",
            db_path=str(db_path),
        )
    )

    result = _load_json(
        jobhunt_save_interview(
            preview=preview["data"],
            confirmed=False,
            db_path=str(db_path),
        )
    )

    assert result["ok"] is False
    assert "error" in result
    assert list_interviews(db_path=db_path) == []
    assert list_applications(db_path=db_path)[0].status == "已投递"


def test_jobhunt_save_interview_confirmed_saves_and_updates_status(db_path):
    create_application(
        company="西安某科技公司",
        position="测试开发",
        db_path=db_path,
    )
    preview = _load_json(
        jobhunt_preview_interview(
            text="明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
            base_date="2026-06-20",
            db_path=str(db_path),
        )
    )

    result = _load_json(
        jobhunt_save_interview(
            preview=preview["data"],
            confirmed=True,
            db_path=str(db_path),
        )
    )

    assert result["ok"] is True
    assert result["data"]["saved"] is True
    assert result["data"]["interview"]["stage"] == "一面"
    assert result["data"]["updated_status"] == "一面待进行"
    assert list_interviews(db_path=db_path)[0].stage == "一面"
    assert list_applications(db_path=db_path)[0].status == "一面待进行"
