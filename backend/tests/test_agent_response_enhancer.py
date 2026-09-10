"""查询回答润色服务的纯 Stub 测试。"""

from copy import deepcopy

import pytest

from backend.app.services.agent_response_enhancer import enhance_agent_response
from backend.app.services.llm_provider import ModelChatResult


class StubProvider:
    def __init__(self, result: ModelChatResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def chat(self, messages, *, temperature=0.2, max_tokens=300) -> ModelChatResult:
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.result


def chat_result(*, ok: bool = True, content: str | None = "自然的查询回答。", error=None):
    return {
        "ok": ok,
        "content": content,
        "provider": "LM Studio",
        "model": "qwen2.5-7b-instruct",
        "error": error,
    }


def test_query_response_is_enhanced_without_modifying_data():
    provider = StubProvider(chat_result())
    data = {
        "applications": [
            {
                "company": "真实公司",
                "position": "测试开发",
                "status": "已投递",
                "notes": "不需要提供给模型的内部备注",
            }
        ]
    }
    original = deepcopy(data)

    result = enhance_agent_response(
        "我投了哪些公司？",
        "query_applications",
        "目前共有 1 条投递记录。",
        data,
        provider,
    )

    assert result["message"] == "自然的查询回答。"
    assert result["rule_message"] == "目前共有 1 条投递记录。"
    assert result["model"]["used"] is True
    assert result["model"]["fallback_reason"] is None
    assert data == original
    prompt = provider.calls[0]["messages"]
    assert "禁止编造" in prompt[0]["content"]
    assert "不要承诺主动通知或定时提醒用户" in prompt[0]["content"]
    assert "禁止说“我会提醒你”或“我会通知你”" in prompt[0]["content"]
    assert "后续可以随时回来查询" in prompt[0]["content"]
    assert "真实公司" in prompt[1]["content"]
    assert '"count": 1' in prompt[1]["content"]
    assert "内部备注" not in prompt[1]["content"]
    assert "150～200 字以内" in prompt[1]["content"]


def test_query_applications_normal_status_language_is_not_unsafe():
    content = (
        "目前有 3 条投递记录，可以查看各公司的投递状态；其中部分记录已完成投递，"
        "建议补充投递链接，也可以补充来源以便后续区分重复记录。"
    )
    provider = StubProvider(chat_result(content=content))
    data = {
        "applications": [
            {"company": "上海百胜软件公司", "position": "软件开发", "status": "已投递"},
            {"company": "西安吉利科技公司", "position": "测试开发", "status": "一面待进行"},
            {"company": "西安吉利科技公司", "position": "测试开发", "status": "一面通过"},
        ]
    }
    original = deepcopy(data)

    result = enhance_agent_response(
        "我现在投了哪些公司？",
        "query_applications",
        "目前共有 3 条投递记录。",
        data,
        provider,
    )

    assert result["message"] == content
    assert result["model"]["used"] is True
    assert result["model"]["fallback_reason"] is None
    assert data == original


@pytest.mark.parametrize(
    "intent",
    ["preview_application", "preview_interview", "preview_status_update", "unknown"],
)
def test_non_query_intent_does_not_call_model(intent):
    provider = StubProvider(chat_result())

    result = enhance_agent_response("输入", intent, "规则回答", {}, provider)

    assert result["message"] == "规则回答"
    assert result["model"]["used"] is False
    assert provider.calls == []


@pytest.mark.parametrize(
    ("provider_result", "expected_reason"),
    [
        (
            chat_result(ok=False, content=None, error="模型调用超时"),
            "timeout：模型调用超时，已使用规则回答",
        ),
        (chat_result(content=""), "empty_content：模型返回空内容，已使用规则回答"),
        (chat_result(content="过" * 501), "too_long：模型回答过长，已使用规则回答"),
        (
            chat_result(content="已为你保存这条记录"),
            "unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        ),
        (
            chat_result(content="我已写入数据库。"),
            "unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        ),
        (
            chat_result(content="我已经替你修改投递状态。"),
            "unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        ),
        (
            chat_result(content="如果有新的面试安排，我会及时通知您。"),
            "unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        ),
        (
            chat_result(content="我会主动通知你新的进展。"),
            "unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        ),
    ],
)
def test_invalid_model_result_falls_back_to_rule_message(provider_result, expected_reason):
    result = enhance_agent_response(
        "查询",
        "query_applications",
        "规则回答",
        {},
        StubProvider(provider_result),
    )

    assert result["message"] == "规则回答"
    assert result["model"]["used"] is False
    assert result["model"]["fallback_reason"] == expected_reason


@pytest.mark.parametrize(
    ("error", "code"),
    [
        ("模型服务连接失败", "connection_error"),
        ("LM Studio /v1/chat/completions 返回 HTTP 502", "http_error"),
        ("模型响应格式异常", "invalid_response"),
        ("模型返回空内容", "empty_content"),
    ],
)
def test_provider_failures_have_diagnostic_fallback_reason(error, code):
    result = enhance_agent_response(
        "查询",
        "query_applications",
        "规则回答",
        {},
        StubProvider(chat_result(ok=False, content=None, error=error)),
    )

    assert result["model"]["fallback_reason"].startswith(f"{code}：")


def test_missing_provider_uses_rule_message():
    result = enhance_agent_response("查询", "query_applications", "规则回答", {}, None)

    assert result["message"] == "规则回答"
    assert result["model"]["used"] is False
    assert result["model"]["fallback_reason"] == (
        "provider_missing：未注入模型 Provider，已使用规则回答"
    )
