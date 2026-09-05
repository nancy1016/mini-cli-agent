"""V2-01B-1 确定性意图路由测试。"""

import pytest

from backend.app.services.intent_router import route_intent


@pytest.mark.parametrize(
    ("text", "intent", "arguments"),
    [
        ("我现在投了哪些公司？", "query_applications", {}),
        ("查看我的投递记录", "query_applications", {}),
        ("这周有哪些面试？", "query_interviews", {"range": "this_week"}),
        ("未来三天有哪些面试？", "query_interviews", {"range": "next_three_days"}),
        ("未来30天有哪些面试？", "query_interviews", {"range": "next_thirty_days"}),
        ("哪些信息没填完整？", "query_missing_info", {}),
        (
            "西安吉利科技公司目前是什么状态？",
            "query_application_status",
            {"company": "西安吉利科技公司"},
        ),
        (
            "西安吉利科技公司目前我的面试状态是什么？",
            "query_application_status",
            {"company": "西安吉利科技公司"},
        ),
        (
            "今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。",
            "preview_application",
            {},
        ),
        (
            "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
            "preview_interview",
            {},
        ),
        ("西安吉利科技公司一面通过了。", "preview_status_update", {}),
        ("这个岗位我放弃了。", "preview_status_update", {}),
    ],
)
def test_route_intent_common_phrases(text, intent, arguments):
    result = route_intent(text)

    assert result["intent"] == intent
    assert result["arguments"] == arguments
    assert result["confidence"] == "rule"


@pytest.mark.parametrize("text", ["", "   ", "今天天气不错", "帮我写一封邮件"])
def test_route_intent_returns_unknown_for_empty_or_unrelated_text(text):
    assert route_intent(text)["intent"] == "unknown"


def test_query_words_win_over_application_action_words():
    assert route_intent("帮我看看我投了哪些公司？")["intent"] == "query_applications"


def test_status_result_wins_over_interview_stage_words():
    assert route_intent("西安吉利科技公司一面通过了")["intent"] == "preview_status_update"
