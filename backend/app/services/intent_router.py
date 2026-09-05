"""V2-01B-1 的确定性自然语言意图路由。"""

from __future__ import annotations

import re


UNKNOWN_RESULT = {
    "intent": "unknown",
    "arguments": {},
    "confidence": "rule",
    "reason": "未命中支持的求职意图",
}

_QUESTION_MARKERS = ("哪些", "多少", "有没有", "是什么", "怎么样", "如何", "哪一步", "查看", "查询", "列表", "安排")
_STATUS_UPDATE_MARKERS = (
    "一面通过", "二面通过", "三面通过", "通过了", "过了", "挂了", "没过", "未过",
    "被拒", "拒了", "拿到 offer", "拿到offer", "offer了", "已放弃", "放弃了",
    "待测评", "测评已完成", "待笔试", "笔试已完成", "面已完成",
)
_INTERVIEW_STAGE_MARKERS = ("面试", "一面", "二面", "三面", "HR面", "终面", "初面", "复面")
_INTERVIEW_CREATE_MARKERS = ("今天", "明天", "后天", "下周", "上午", "下午", "晚上", "通知")
_APPLICATION_CREATE_MARKERS = ("投递了", "投了", "投递", "内推了", "内推", "双选会", "官网")


def _result(intent: str, reason: str, **arguments: object) -> dict[str, object]:
    return {
        "intent": intent,
        "arguments": arguments,
        "confidence": "rule",
        "reason": reason,
    }


def _has_question_marker(text: str) -> bool:
    return any(marker in text for marker in _QUESTION_MARKERS) or text.endswith(("?", "？"))


def _extract_company(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9\u4e00-\u9fff]+?公司)", text)
    if not match:
        return None
    company = match.group(1)
    for prefix in ("请问", "查询", "查看", "帮我看看", "我想知道"):
        if company.startswith(prefix):
            company = company[len(prefix):]
    return company or None


def _interview_range(text: str) -> str:
    if "明天" in text:
        return "tomorrow"
    if "今天" in text:
        return "today"
    if "这周" in text or "本周" in text:
        return "this_week"
    if "未来三天" in text or "未来3天" in text:
        return "next_three_days"
    if any(marker in text for marker in ("最近一个月", "未来一个月", "未来30天", "未来 30 天")):
        return "next_thirty_days"
    return "next_three_days"


def route_intent(text: str) -> dict[str, object]:
    """按固定优先级识别 V2-01B-1 支持的八类意图。"""
    cleaned = text.strip()
    if not cleaned:
        return dict(UNKNOWN_RESULT)

    if any(marker in cleaned for marker in ("没填完整", "未填完整", "缺失信息", "哪些信息待补充", "信息不完整")):
        return _result("query_missing_info", "包含缺失信息查询词")

    if (
        any(marker in cleaned for marker in _INTERVIEW_STAGE_MARKERS)
        and _has_question_marker(cleaned)
        and "状态" not in cleaned
        and "进展" not in cleaned
    ):
        return _result(
            "query_interviews",
            "包含面试和查询词",
            range=_interview_range(cleaned),
        )

    if (
        ("状态" in cleaned and _has_question_marker(cleaned))
        or "进展到哪一步" in cleaned
        or "进展如何" in cleaned
    ):
        company = _extract_company(cleaned)
        return _result("query_application_status", "包含公司进展或状态查询词", company=company)

    if (
        "投递列表" in cleaned
        or "投递记录" in cleaned and _has_question_marker(cleaned)
        or "投了哪些公司" in cleaned
        or "有哪些投递" in cleaned
    ):
        return _result("query_applications", "包含投递查询词")

    if any(marker in cleaned for marker in _STATUS_UPDATE_MARKERS):
        return _result("preview_status_update", "包含明确的状态变化词")

    if (
        any(marker in cleaned for marker in _INTERVIEW_STAGE_MARKERS)
        and any(marker in cleaned for marker in _INTERVIEW_CREATE_MARKERS)
    ):
        return _result("preview_interview", "包含面试阶段和时间或通知信息")

    if any(marker in cleaned for marker in _APPLICATION_CREATE_MARKERS):
        return _result("preview_application", "包含明确的投递动作词")

    return dict(UNKNOWN_RESULT)
