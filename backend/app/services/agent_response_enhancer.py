"""使用本地模型对规则查询回答做可降级的表达润色。"""

from __future__ import annotations

import json
from typing import TypedDict

from backend.app.services.llm_provider import LLMProvider


QUERY_INTENTS = {
    "query_applications",
    "query_interviews",
    "query_missing_info",
    "query_application_status",
}
MAX_ENHANCED_MESSAGE_CHARS = 500
FORBIDDEN_ACTION_CLAIMS = (
    "我已经帮你保存",
    "我已帮你保存",
    "我已经替你修改",
    "我已替你修改",
    "我已写入数据库",
    "我已经写入数据库",
    "已为你保存",
    "已为你更新",
    "我会提醒你",
    "我会通知你",
    "我会主动通知",
    "我会及时通知",
    "我会定时提醒",
    "我会自动投递",
    "我会自动推送",
    "系统会自动推送",
)
PROVIDER_ERROR_CODES = {
    "模型调用超时": "timeout",
    "模型服务连接失败": "connection_error",
    "模型响应格式异常": "invalid_response",
    "模型返回空内容": "empty_content",
}

SYSTEM_PROMPT = """你是 JobHuntLedger-Agent 的本地回答润色模块。
你只能根据系统提供的真实工具结果进行表达优化。
禁止编造公司、岗位、时间、状态、面试记录或投递记录。
禁止修改事实，禁止声称你直接访问了数据库或完成了任何写入操作。
不要承诺主动通知或定时提醒用户，不要声称系统会自动推送消息。
除非系统真正提供了提醒任务，否则禁止说“我会提醒你”或“我会通知你”。
如果当前没有面试安排，只能说明当前没有记录，或提示用户后续可以随时回来查询。
禁止输出 JSON。请用简洁自然的中文回答，最多 200 字。
如果数据不足，只能说明数据不足。"""


class EnhancementModelUsage(TypedDict):
    used: bool
    provider: str | None
    name: str | None
    fallback_reason: str | None


class EnhancementResult(TypedDict):
    message: str
    model: EnhancementModelUsage
    rule_message: str


def _model_input_data(intent: str, data: object) -> object:
    """精简模型输入，不改变返回给前端的原始工具数据。"""
    if intent != "query_applications" or not isinstance(data, dict):
        return data
    applications = data.get("applications")
    if not isinstance(applications, list):
        return data

    visible_fields = (
        "company",
        "position",
        "status",
        "apply_date",
        "apply_source",
        "location",
        "recruit_type",
    )
    rows = []
    for item in applications:
        if isinstance(item, dict):
            rows.append({field: item.get(field) for field in visible_fields})
    return {"count": len(rows), "applications": rows}


def _rule_result(
    rule_message: str,
    *,
    provider: str | None = None,
    name: str | None = None,
    fallback_reason: str | None = None,
) -> EnhancementResult:
    return {
        "message": rule_message,
        "model": {
            "used": False,
            "provider": provider,
            "name": name,
            "fallback_reason": fallback_reason,
        },
        "rule_message": rule_message,
    }


def enhance_agent_response(
    user_text: str,
    intent: str,
    rule_message: str,
    data: object,
    model_provider: LLMProvider | None = None,
) -> EnhancementResult:
    """只替换查询回答 message；工具 data 始终由调用方原样保留。"""
    if intent not in QUERY_INTENTS:
        return _rule_result(rule_message)
    if model_provider is None:
        return _rule_result(
            rule_message,
            fallback_reason="provider_missing：未注入模型 Provider，已使用规则回答",
        )

    tool_data = json.dumps(_model_input_data(intent, data), ensure_ascii=False, default=str)
    user_prompt = f"""用户原始问题：
{user_text}

已识别意图：
{intent}

规则 Agent 原始回答：
{rule_message}

真实工具结果：
{tool_data}

请基于以上真实信息，输出给用户看的自然语言回答，控制在 150～200 字以内。"""

    try:
        result = model_provider.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
    except Exception:
        return _rule_result(
            rule_message,
            fallback_reason="provider_error：模型调用异常，已使用规则回答",
        )

    provider = result.get("provider")
    name = result.get("model")
    if not result.get("ok"):
        reason = result.get("error") or "模型调用失败"
        code = PROVIDER_ERROR_CODES.get(reason)
        if code is None:
            code = "http_error" if "HTTP" in reason else "provider_error"
        return _rule_result(
            rule_message,
            provider=provider,
            name=name,
            fallback_reason=f"{code}：{reason}，已使用规则回答",
        )

    content = result.get("content")
    if not isinstance(content, str) or not content.strip():
        return _rule_result(
            rule_message,
            provider=provider,
            name=name,
            fallback_reason="empty_content：模型返回空内容，已使用规则回答",
        )
    enhanced = content.strip()
    if len(enhanced) > MAX_ENHANCED_MESSAGE_CHARS:
        return _rule_result(
            rule_message,
            provider=provider,
            name=name,
            fallback_reason="too_long：模型回答过长，已使用规则回答",
        )
    if any(claim in enhanced for claim in FORBIDDEN_ACTION_CLAIMS):
        return _rule_result(
            rule_message,
            provider=provider,
            name=name,
            fallback_reason="unsafe_content：模型回答包含不允许的操作声明，已使用规则回答",
        )

    return {
        "message": enhanced,
        "model": {
            "used": True,
            "provider": provider,
            "name": name,
            "fallback_reason": None,
        },
        "rule_message": rule_message,
    }
