"""文本解析模块的 V1 业务场景测试。"""

from datetime import date

import pytest

from jobhunt.parser import (
    parse_application_text,
    parse_interview_text,
    parse_status_update_text,
    parse_user_text,
)


BASE_DATE = date(2026, 6, 20)


def test_parse_application_text_from_job_fair():
    text = (
        "今天在双选会投了陕西某软件公司的软件测试岗，"
        "工作地点西安，秋招，纸质简历投递。"
    )

    result = parse_application_text(text, base_date=BASE_DATE)

    assert result["intent"] == "add_application"
    assert result["company"] == "陕西某软件公司"
    assert result["position"] == "软件测试"
    assert result["location"] == "西安"
    assert result["recruit_type"] == "秋招"
    assert "双选会" in result["apply_source"]
    assert "纸质投递" in result["apply_source"]
    assert result["apply_date"] == "2026-06-20"
    assert result["status"] == "已投递"


def test_parse_application_text_from_official_site():
    text = "今天在官网投了西安某科技公司的测试开发岗，地点西安。"

    result = parse_application_text(text, base_date=BASE_DATE)

    assert result["intent"] == "add_application"
    assert result["company"] == "西安某科技公司"
    assert result["position"] == "测试开发"
    assert result["location"] == "西安"
    assert result["apply_source"] == "官网"
    assert result["apply_date"] == "2026-06-20"

def test_parse_application_text_extracts_apply_link():
    text = (
        "今天在官网投了西安某科技公司的测试开发岗，"
        "链接 https://career.example.com/job/123，地点西安。"
    )
    result = parse_application_text(text, base_date=BASE_DATE)

    assert result["intent"] == "add_application"
    assert result["company"] == "西安某科技公司"
    assert result["position"] == "测试开发"
    assert result["apply_source"] == "官网"
    assert result["apply_link"] == "https://career.example.com/job/123"



def test_parse_interview_text_from_next_week():
    text = (
        "陕西某软件公司通知我下周二下午三点一面，"
        "腾讯会议，链接还没发。"
    )

    result = parse_interview_text(text, base_date=BASE_DATE)

    assert result["intent"] == "add_interview"
    assert result["company"] == "陕西某软件公司"
    assert result["position"] == "待补充"
    assert result["stage"] == "一面"
    assert result["interview_method"] == "腾讯会议"
    assert result["meeting_link"] == ""
    assert "链接还没发" in result["notes"]
    assert result["interview_time"] == "2026-06-23 15:00"


def test_parse_interview_text_from_tomorrow():
    text = "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。"

    result = parse_interview_text(text, base_date=BASE_DATE)

    assert result["intent"] == "add_interview"
    assert result["company"] == "西安某科技公司"
    assert result["position"] == "测试开发"
    assert result["stage"] == "一面"
    assert result["interview_method"] == "电话"
    assert result["interview_time"] == "2026-06-21 15:00"


def test_parse_interview_text_uses_explicit_base_date_for_tomorrow():
    text = "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。"

    result = parse_interview_text(text, base_date=date(2026, 7, 11))

    assert result["interview_time"] == "2026-07-12 15:00"


def test_parse_interview_text_supports_day_after_tomorrow_and_digit_hour():
    result = parse_interview_text(
        "西安吉利科技公司后天下午4点二面",
        base_date=date(2026, 7, 12),
    )

    assert result["company"] == "西安吉利科技公司"
    assert result["stage"] == "二面"
    assert result["interview_time"] == "2026-07-14 16:00"


def test_parse_interview_text_supports_tomorrow_from_july_base_date():
    result = parse_interview_text(
        "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
        base_date=date(2026, 7, 12),
    )

    assert result["interview_time"] == "2026-07-13 15:00"


def test_parse_interview_text_supports_absolute_chinese_date():
    result = parse_interview_text(
        "2026年7月18日下午5点，上海百胜软件公司开发岗要一面。",
        base_date=date(2026, 7, 12),
    )

    assert result["company"] == "上海百胜软件公司"
    assert result["stage"] == "一面"
    assert result["interview_time"] == "2026-07-18 17:00"


@pytest.mark.parametrize(
    "text",
    [
        "2026-07-18 下午5点，上海百胜软件公司开发岗一面。",
        "2026/07/18 下午5点，上海百胜软件公司开发岗一面。",
        "7月18日下午5点，上海百胜软件公司开发岗一面。",
    ],
)
def test_parse_interview_text_supports_absolute_date_variants(text):
    result = parse_interview_text(text, base_date=date(2026, 7, 12))

    assert result["interview_time"] == "2026-07-18 17:00"


def test_parse_interview_text_supports_evening_digit_hour():
    result = parse_interview_text(
        "明天晚上7点，西安吉利科技公司测试开发岗一面。",
        base_date=date(2026, 7, 12),
    )

    assert result["interview_time"] == "2026-07-13 19:00"


def test_parse_status_update_passed_first_interview():
    result = parse_status_update_text("陕西某软件公司一面通过了。")

    assert result["intent"] == "update_status"
    assert result["company"] == "陕西某软件公司"
    assert result["position"] == "待补充"
    assert result["status"] == "一面通过"
    assert result["notes"] == ""


def test_parse_status_update_rejected_alias():
    result = parse_status_update_text("陕西某软件公司挂了。")

    assert result["company"] == "陕西某软件公司"
    assert result["status"] == "未通过"


def test_parse_status_update_offer_alias():
    result = parse_status_update_text("陕西某软件公司拿到 offer 了。")

    assert result["company"] == "陕西某软件公司"
    assert result["status"] == "offer"


def test_parse_user_text_dispatches_to_application_parser():
    result = parse_user_text(
        "今天在官网投了西安某科技公司的测试开发岗，地点西安。",
        base_date=BASE_DATE,
    )

    assert result["intent"] == "add_application"
    assert result["company"] == "西安某科技公司"


def test_parse_user_text_dispatches_to_interview_parser():
    result = parse_user_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
    )

    assert result["intent"] == "add_interview"
    assert result["interview_time"] == "2026-06-21 15:00"


def test_parse_user_text_dispatches_to_status_update_parser():
    result = parse_user_text("陕西某软件公司挂了。")

    assert result["intent"] == "update_status"
    assert result["status"] == "未通过"


@pytest.mark.parametrize(
    ("text", "expected_time"),
    [
        ("今天上午十点，某公司一面。", "2026-06-20 10:00"),
        ("今天下午三点，某公司一面。", "2026-06-20 15:00"),
        ("明天上午十点，某公司一面。", "2026-06-21 10:00"),
        ("下周一上午十点，某公司一面。", "2026-06-22 10:00"),
        ("周五上午十点，某公司一面。", "2026-06-26 10:00"),
    ],
)
def test_parse_interview_text_supports_v1_time_expressions(text, expected_time):
    # 固定 base_date，避免测试结果随真实运行日期变化。
    result = parse_interview_text(text, base_date=BASE_DATE)

    assert result["interview_time"] == expected_time
