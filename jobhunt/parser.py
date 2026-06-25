"""将求职相关自然语言文本解析为 V1 统一结构化字段。"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from jobhunt.status import STATUS_ALIASES, SUPPORTED_STATUSES, normalize_status


_DEFAULT_VALUE = "待补充"
_WEEKDAY_NUMBERS = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}
_CHINESE_HOURS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}
_URL_PATTERN = re.compile(r"https?://[^\s，。；、]+")


def _clean_text(text: str) -> str:
    """清理输入首尾空白，并拒绝无法承载业务信息的空文本。"""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("待解析文本不能为空")
    return cleaned


def _reference_date(base_date: date | None) -> date:
    """返回时间解析基准日；调用方未指定时使用系统当天日期。"""
    return base_date if base_date is not None else date.today()


def _extract_company(text: str) -> str:
    """从常见投递、通知和状态句式中提取公司名称。"""
    patterns = [
        r"(?:投了|投递了|投递)(?P<company>[^，。]+?公司)的",
        r"(?P<company>[^，。]+?公司)通知我",
        r"[，,]\s*(?P<company>[^，。]+?公司)",
        r"^(?:今天|明天|下周[一二三四五六日天]|周[一二三四五六日天])?"
        r"(?:上午|下午)?(?:[一二两三四五六七八九十]{1,2}点)?[，,\s]*"
        r"(?P<company>[^，。]+?公司)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group("company").strip("，,。 ")
    return _DEFAULT_VALUE


def _extract_position(text: str, company: str) -> str:
    """提取“公司 + 岗位 + 岗”句式中的岗位，并去掉末尾“岗”字。"""
    if company != _DEFAULT_VALUE:
        company_start = text.find(company)
        if company_start >= 0:
            tail = text[company_start + len(company) :]
            match = re.search(r"(?:的)?(?P<position>[^，。]+?)岗", tail)
            if match:
                position = match.group("position").strip()
                if position and not any(
                    marker in position
                    for marker in ("通知", "今天", "明天", "下周", "一面", "二面", "三面")
                ):
                    return position

    match = re.search(r"(?P<position>[^，。的]+?)岗(?:一面|二面|三面|面试)", text)
    return match.group("position").strip() if match else _DEFAULT_VALUE


def _extract_location(text: str) -> str:
    """提取“工作地点”或“地点”后的城市名称。"""
    match = re.search(r"(?:工作地点|地点)\s*(?P<location>[^，。；\s]+)", text)
    return match.group("location").strip() if match else _DEFAULT_VALUE


def _extract_application_date(text: str, base_date: date | None) -> str:
    """解析简单相对投递日期；未说明日期时按 V1 规则使用基准日。"""
    target = _reference_date(base_date)
    if "明天" in text:
        target += timedelta(days=1)
    return target.isoformat()


def _extract_apply_source(text: str) -> str:
    """汇总文本中的投递渠道，保留双选会与纸质投递等组合来源。"""
    sources: list[str] = []
    if "官网" in text:
        sources.append("官网")
    if "双选会" in text:
        sources.append("双选会")
    if "纸质" in text:
        sources.append("纸质投递")
    return "、".join(sources) if sources else _DEFAULT_VALUE


def _extract_recruit_type(text: str) -> str:
    """提取 V1 常见招聘类型。"""
    for recruit_type in ("秋招", "春招", "校招", "社招", "实习"):
        if recruit_type in text:
            return recruit_type
    return _DEFAULT_VALUE


def _extract_stage(text: str) -> str:
    """提取面试轮次，无法识别时返回待补充。"""
    match = re.search(r"(HR面|一面|二面|三面|终面|初面|复面)", text, re.IGNORECASE)
    return match.group(1) if match else _DEFAULT_VALUE


def _extract_interview_method(text: str) -> str:
    """识别电话、腾讯会议等常见面试方式。"""
    for method in ("腾讯会议", "电话", "视频", "现场", "线下"):
        if method in text:
            return method
    return _DEFAULT_VALUE


def _resolve_interview_date(text: str, base_date: date) -> date:
    """将今天、明天、下周几和周几换算为确定日期。"""
    if "明天" in text:
        return base_date + timedelta(days=1)
    if "今天" in text:
        return base_date

    next_week = re.search(r"下周([一二三四五六日天])", text)
    if next_week:
        next_monday = base_date + timedelta(days=7 - base_date.weekday())
        return next_monday + timedelta(days=_WEEKDAY_NUMBERS[next_week.group(1)])

    weekday = re.search(r"(?<!下)周([一二三四五六日天])", text)
    if weekday:
        target_weekday = _WEEKDAY_NUMBERS[weekday.group(1)]
        days_ahead = (target_weekday - base_date.weekday()) % 7
        return base_date + timedelta(days=days_ahead)

    return base_date


def _extract_interview_time(text: str, base_date: date | None) -> str:
    """解析 V1 支持的相对日期与中文整点时间。"""
    target_date = _resolve_interview_date(text, _reference_date(base_date))
    time_match = re.search(
        r"(?P<period>上午|下午)(?P<hour>十二|十一|十|[一二两三四五六七八九])点",
        text,
    )
    if not time_match:
        return f"{target_date.isoformat()} 00:00"

    hour = _CHINESE_HOURS[time_match.group("hour")]
    if time_match.group("period") == "下午" and hour < 12:
        hour += 12
    return datetime.combine(target_date, datetime.min.time()).replace(
        hour=hour
    ).strftime("%Y-%m-%d %H:%M")


def _extract_status_phrase(text: str) -> str:
    """找到文本中的状态或别名，具体归一化交给 status 模块统一维护。"""
    cleaned = text.strip().rstrip("。！!，, ")
    candidates = sorted(
        set(STATUS_ALIASES) | set(SUPPORTED_STATUSES),
        key=len,
        reverse=True,
    )
    for candidate in candidates:
        if candidate in cleaned:
            return candidate
    raise ValueError("未识别到支持的求职状态")


def parse_application_text(
    text: str,
    base_date: date | None = None,
) -> dict[str, object]:
    """解析投递记录文本，返回 V1 统一的投递结构化字段。"""
    cleaned = _clean_text(text)
    company = _extract_company(cleaned)
    link_match = _URL_PATTERN.search(cleaned)

    # parser 只形成稳定字段，不负责保存记录或检查字段完整性。
    return {
        "intent": "add_application",
        "company": company,
        "position": _extract_position(cleaned, company),
        "location": _extract_location(cleaned),
        "recruit_type": _extract_recruit_type(cleaned),
        "apply_source": _extract_apply_source(cleaned),
        "apply_link": link_match.group(0) if link_match else "",
        "apply_date": _extract_application_date(cleaned, base_date),
        "status": "已投递",
        "notes": "",
    }


def parse_interview_text(
    text: str,
    base_date: date | None = None,
) -> dict[str, object]:
    """解析面试通知文本，返回 V1 统一的面试结构化字段。"""
    cleaned = _clean_text(text)
    company = _extract_company(cleaned)
    link_match = _URL_PATTERN.search(cleaned)
    notes = "链接还没发" if "链接还没发" in cleaned else ""

    return {
        "intent": "add_interview",
        "company": company,
        "position": _extract_position(cleaned, company),
        "stage": _extract_stage(cleaned),
        "interview_time": _extract_interview_time(cleaned, base_date),
        "interview_method": _extract_interview_method(cleaned),
        "meeting_link": link_match.group(0) if link_match else "",
        "notes": notes,
    }


def parse_status_update_text(text: str) -> dict[str, object]:
    """解析状态更新文本，并复用 status 模块完成状态归一化。"""
    cleaned = _clean_text(text)
    raw_status = _extract_status_phrase(cleaned)
    status_start = cleaned.find(raw_status)
    company_text = cleaned[:status_start].strip("，,。！! ")
    company_match = re.search(r"(?P<company>.+?公司)", company_text)

    return {
        "intent": "update_status",
        "company": (
            company_match.group("company").strip()
            if company_match
            else _DEFAULT_VALUE
        ),
        "position": _DEFAULT_VALUE,
        "status": normalize_status(raw_status),
        "notes": "",
    }


def parse_user_text(
    text: str,
    base_date: date | None = None,
) -> dict[str, object]:
    """识别用户意图，并分派给对应的 V1 文本解析函数。"""
    cleaned = _clean_text(text)

    status_markers = set(STATUS_ALIASES) | set(SUPPORTED_STATUSES)
    if any(marker in cleaned for marker in status_markers):
        return parse_status_update_text(cleaned)
    if any(marker in cleaned for marker in ("面试", "一面", "二面", "三面", "终面")):
        return parse_interview_text(cleaned, base_date=base_date)
    if any(marker in cleaned for marker in ("投了", "投递", "双选会", "官网")):
        return parse_application_text(cleaned, base_date=base_date)

    raise ValueError("无法识别用户文本意图")
