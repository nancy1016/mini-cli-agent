"""main.py 中 CLI 兜底逻辑的轻量测试。"""

import json

import main


def test_is_status_update_input_matches_status_text_only():
    assert main.is_status_update_input("西安吉利科技公司一面通过了。") is True
    assert main.is_status_update_input("西安吉利科技公司挂了。") is True
    assert main.is_status_update_input("我现在投了哪些公司？") is False
    assert main.is_status_update_input("明天有哪些面试？") is False


def test_is_interview_input_matches_interview_notice_only():
    assert (
        main.is_interview_input(
            "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。"
        )
        is True
    )
    assert main.is_interview_input("陕西某软件公司通知我下周二下午三点一面。") is True
    assert main.is_interview_input("西安吉利科技公司后天下午4点二面") is True
    assert main.is_interview_input("西安吉利科技公司一面通过了。") is False
    assert main.is_interview_input("西安吉利科技公司二面通过了。") is False


def test_is_application_status_query_matches_progress_questions():
    assert main.is_application_status_query("西安吉利科技公司目前我的面试状态是什么？") is True
    assert main.is_application_status_query("西安吉利科技公司现在到哪一步了？") is True
    assert main.is_application_status_query("西安吉利科技公司的投递状态是什么？") is True
    assert main.is_application_status_query("明天有哪些面试？") is False


def test_detect_fixed_query_supports_interview_ranges():
    assert main.detect_fixed_query("未来三天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("未来3天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("未来 3 天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("近3天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("本周我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "this_week"},
    )
    assert main.detect_fixed_query("未来一个月我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("未来30天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("一个月内我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("最近我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("近期我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("未来一周我有哪些面试？") == (
        "unsupported_interview_range",
        {},
    )


def test_format_jobhunt_result_inlines_application_progress_by_id():
    result = {
        "ok": True,
        "data": {
            "interviews": [
                {
                    "application_id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "stage": "一面",
                    "interview_time": "2026-07-14 15:00",
                }
            ],
            "applications": [
                {
                    "id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "status": "一面通过",
                }
            ],
        },
    }

    text = main.format_jobhunt_result(result)

    assert "西安吉利科技公司" in text
    assert "测试开发" in text
    assert "时间：2026-07-14 15:00" in text
    assert "进度：一面通过" in text
    assert "阶段：一面" not in text
    assert "当前整体进度：" not in text
    assert "状态：一面通过" not in text


def test_format_jobhunt_result_inlines_each_matching_application_progress():
    result = {
        "ok": True,
        "data": {
            "interviews": [
                {
                    "application_id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "stage": "一面",
                    "interview_time": "2026-07-14 15:00",
                },
                {
                    "application_id": 2,
                    "company": "上海百胜软件公司",
                    "position": "软件开发",
                    "stage": "一面",
                    "interview_time": "2026-07-18 17:00",
                },
            ],
            "applications": [
                {
                    "id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "status": "一面通过",
                },
                {
                    "id": 2,
                    "company": "上海百胜软件公司",
                    "position": "软件开发",
                    "status": "一面待进行",
                },
            ],
        },
    }

    text = main.format_jobhunt_result(result)

    assert (
        "- 西安吉利科技公司 | 测试开发 | 时间：2026-07-14 15:00 | 进度：一面通过"
        in text
    )
    assert (
        "- 上海百胜软件公司 | 软件开发 | 时间：2026-07-18 17:00 | 进度：一面待进行"
        in text
    )
    assert "当前整体进度：" not in text
    assert "状态：" not in text


def test_format_jobhunt_result_does_not_show_progress_when_interviews_empty():
    result = {
        "ok": True,
        "data": {
            "interviews": [],
            "applications": [
                {
                    "id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "status": "二面待进行",
                },
                {
                    "id": 2,
                    "company": "陕西某软件公司",
                    "position": "软件测试",
                    "status": "已投递",
                },
            ],
        },
    }

    text = main.format_jobhunt_result(result)

    assert text == "该范围内没有面试记录。"
    assert "当前整体进度：" not in text
    assert "陕西某软件公司" not in text


def test_format_jobhunt_result_filters_progress_by_company_and_position():
    result = {
        "ok": True,
        "data": {
            "interviews": [
                {
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "stage": "二面",
                    "interview_time": "2026-07-14 16:00",
                }
            ],
            "applications": [
                {
                    "id": 1,
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "status": "二面待进行",
                },
                {
                    "id": 2,
                    "company": "西安吉利科技公司",
                    "position": "后端开发",
                    "status": "已投递",
                },
            ],
        },
    }

    text = main.format_jobhunt_result(result)

    assert "进度：二面待进行" in text
    assert "后端开发 | 时间：" not in text
    assert "状态：" not in text


def test_format_jobhunt_result_application_list_format_unchanged():
    result = {
        "ok": True,
        "data": {
            "applications": [
                {
                    "company": "西安吉利科技公司",
                    "position": "测试开发",
                    "status": "一面通过",
                }
            ],
        },
    }

    text = main.format_jobhunt_result(result)

    assert text == "当前投递记录：\n- 西安吉利科技公司 | 测试开发 | 状态：一面通过"


def test_handle_status_update_preview_records_pending_preview(monkeypatch):
    state = {"base_messages": [], "pending_preview": None}
    preview = {
        "action": "preview_status_update",
        "parsed": {"company": "西安吉利科技公司", "status": "一面通过"},
        "matched_application": {
            "id": 1,
            "company": "西安吉利科技公司",
            "position": "测试开发",
            "status": "一面待进行",
        },
        "needs_application_match": False,
        "new_status": "一面通过",
        "will_save": False,
    }

    monkeypatch.setattr(
        main,
        "jobhunt_preview_status_update",
        lambda text: json.dumps({"ok": True, "data": preview}, ensure_ascii=False),
    )
    monkeypatch.setattr(main, "save_direct_turn", lambda state, user_input, message: None)

    handled = main.handle_status_update_preview("西安吉利科技公司一面通过了。", state)

    assert handled is True
    assert state["pending_preview"] == preview


def test_handle_status_update_preview_does_not_keep_pending_when_no_match(monkeypatch):
    state = {"base_messages": [], "pending_preview": {"action": "preview_application"}}
    preview = {
        "action": "preview_status_update",
        "parsed": {"company": "西安吉利科技公司", "status": "未通过"},
        "matched_application": None,
        "needs_application_match": True,
        "new_status": "未通过",
        "will_save": False,
    }

    monkeypatch.setattr(
        main,
        "jobhunt_preview_status_update",
        lambda text: json.dumps({"ok": True, "data": preview}, ensure_ascii=False),
    )
    monkeypatch.setattr(main, "save_direct_turn", lambda state, user_input, message: None)

    handled = main.handle_status_update_preview("西安吉利科技公司挂了。", state)

    assert handled is True
    assert state["pending_preview"] is None


def test_handle_interview_preview_fallback_records_pending_preview(monkeypatch):
    state = {"base_messages": [], "pending_preview": None}
    preview = {
        "action": "preview_interview",
        "parsed": {
            "company": "西安吉利科技公司",
            "position": "测试开发",
            "stage": "一面",
            "interview_time": "2026-07-13 15:00",
            "interview_method": "电话",
        },
        "matched_application": {
            "id": 1,
            "company": "西安吉利科技公司",
            "position": "测试开发",
            "status": "已投递",
        },
        "needs_application_creation": False,
        "missing": {"required": [], "recommended": []},
        "will_save": False,
    }

    monkeypatch.setattr(
        main,
        "jobhunt_preview_interview",
        lambda text: json.dumps({"ok": True, "data": preview}, ensure_ascii=False),
    )
    monkeypatch.setattr(main, "save_direct_turn", lambda state, user_input, message: None)

    handled = main.handle_interview_preview_fallback(
        "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
        state,
    )

    assert handled is True
    assert state["pending_preview"] == preview


def test_pending_interview_confirmation_uses_interview_save(monkeypatch):
    state = {
        "base_messages": [],
        "pending_preview": {
            "action": "preview_interview",
            "needs_application_creation": False,
        },
    }
    calls = {"application": 0, "interview": 0}

    def fake_save_application(**kwargs):
        calls["application"] += 1
        return json.dumps({"ok": True, "data": {"saved": True}}, ensure_ascii=False)

    def fake_save_interview(**kwargs):
        calls["interview"] += 1
        return json.dumps(
            {
                "ok": True,
                "data": {
                    "saved": True,
                    "interview": {
                        "company": "西安吉利科技公司",
                        "stage": "一面",
                        "interview_time": "2026-07-13 15:00",
                    },
                    "updated_status": "一面待进行",
                },
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(main, "jobhunt_save_application", fake_save_application)
    monkeypatch.setattr(main, "jobhunt_save_interview", fake_save_interview)
    monkeypatch.setattr(main, "save_direct_turn", lambda state, user_input, message: None)

    handled = main.handle_pending_confirmation("确认保存", state)

    assert handled is True
    assert calls == {"application": 0, "interview": 1}
    assert state["pending_preview"] is None


def test_handle_application_status_query_uses_application_status(monkeypatch):
    state = {"base_messages": [], "pending_preview": None}

    monkeypatch.setattr(
        main,
        "jobhunt_list_applications",
        lambda: json.dumps(
            {
                "ok": True,
                "data": {
                    "applications": [
                        {
                            "company": "西安吉利科技公司",
                            "position": "测试开发",
                            "status": "一面通过",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(main, "save_direct_turn", lambda state, user_input, message: None)

    handled = main.handle_application_status_query(
        "西安吉利科技公司目前我的面试状态是什么？",
        state,
    )

    assert handled is True
