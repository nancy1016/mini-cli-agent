"""JobHuntLedger V1 end-to-end regression tests without a real LLM."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

import main
from jobhunt.parser import parse_interview_text
from jobhunt.repository import (
    create_application,
    create_interview,
    list_applications,
    list_interviews,
)
from jobhunt.service import (
    check_missing_info,
    confirm_create_application,
    confirm_create_interview,
    confirm_update_application_status,
    get_next_three_days_interviews,
    get_next_thirty_days_interviews,
    get_today_interviews,
    get_tomorrow_interviews,
    preview_application_from_text,
    preview_interview_from_text,
    preview_status_update_from_text,
)
from tools import tool_names


BASE_DATE = date(2026, 7, 13)


def _save_application(text: str, db_path, base_date: date = BASE_DATE):
    preview = preview_application_from_text(text, base_date=base_date)
    return confirm_create_application(preview, db_path=db_path)


def _save_interview(text: str, db_path, base_date: date = BASE_DATE):
    preview = preview_interview_from_text(
        text,
        base_date=base_date,
        db_path=db_path,
    )
    result = confirm_create_interview(preview, db_path=db_path)
    return preview, result


def _update_status(text: str, db_path):
    preview = preview_status_update_from_text(text, db_path=db_path)
    updated = confirm_update_application_status(preview, db_path=db_path)
    return preview, updated


def test_v1_full_flow_with_two_companies(tmp_path):
    db_path = tmp_path / "jobhunt.db"

    shanghai = _save_application(
        "今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。",
        db_path,
    )

    applications = list_applications(db_path=db_path)
    assert len(applications) == 1
    assert shanghai.company == "上海百胜软件公司"
    assert shanghai.position == "软件开发"
    assert shanghai.location == "上海"
    assert shanghai.apply_source == "官网"
    assert shanghai.status == "已投递"

    shanghai_preview, shanghai_interview_result = _save_interview(
        "2026年7月18日下午5点，上海百胜软件公司开发岗要一面。",
        db_path,
    )
    shanghai_interview = shanghai_interview_result["interview"]

    assert shanghai_preview["parsed"]["interview_time"] == "2026-07-18 17:00"
    assert shanghai_preview["parsed"]["position"] == "软件开发"
    assert shanghai_interview.position == "软件开发"
    assert shanghai_interview.interview_time == "2026-07-18 17:00"
    assert list_applications(db_path=db_path)[0].status == "一面待进行"

    xian = _save_application(
        "今天在官网投递了西安吉利科技公司的测试开发岗，地点西安。",
        db_path,
    )

    assert xian.company == "西安吉利科技公司"
    assert xian.position == "测试开发"
    assert xian.location == "西安"
    assert xian.status == "已投递"

    xian_preview, _ = _save_interview(
        "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
        db_path,
    )
    applications = list_applications(db_path=db_path)
    xian_application = next(item for item in applications if item.company == "西安吉利科技公司")

    assert xian_preview["parsed"]["interview_time"] == "2026-07-14 15:00"
    assert xian_preview["parsed"]["interview_method"] == "电话"
    assert xian_application.status == "一面待进行"

    status_preview, updated = _update_status("西安吉利科技公司一面通过了", db_path)

    assert status_preview["new_status"] == "一面通过"
    assert updated.status == "一面通过"

    next_three_days = get_next_three_days_interviews(
        today=BASE_DATE,
        db_path=db_path,
    )
    next_three_companies = {item.company for item in next_three_days}
    assert next_three_companies == {"西安吉利科技公司"}

    next_thirty_days = get_next_thirty_days_interviews(
        today=BASE_DATE,
        db_path=db_path,
    )
    next_thirty_companies = {item.company for item in next_thirty_days}
    assert next_thirty_companies == {"西安吉利科技公司", "上海百胜软件公司"}
    assert len(next_thirty_days) == 2

    display = main.format_jobhunt_result(
        {
            "ok": True,
            "data": {
                "interviews": [asdict(item) for item in next_thirty_days],
                "applications": [
                    asdict(item) for item in list_applications(db_path=db_path)
                ],
            },
        }
    )

    assert (
        "上海百胜软件公司 | 软件开发 | 时间：2026-07-18 17:00 | 进度：一面待进行"
        in display
    )
    assert (
        "西安吉利科技公司 | 测试开发 | 时间：2026-07-14 15:00 | 进度：一面通过"
        in display
    )
    assert "当前整体进度：" not in display
    assert "阶段：一面" not in display


def test_v1_create_applications_from_common_sources(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    official = _save_application(
        "今天在官网投递了西安吉利科技公司的测试开发岗，地点西安。",
        db_path,
    )
    fair = _save_application(
        "今天在双选会投了陕西某软件公司的软件测试岗，工作地点西安，秋招，纸质简历投递。",
        db_path,
    )
    linked = _save_application(
        "今天在官网投了上海某科技公司的后端开发岗，链接 https://career.example.com/job/123，地点上海。",
        db_path,
    )

    assert official.apply_source == "官网"
    assert official.status == "已投递"
    assert fair.company == "陕西某软件公司"
    assert fair.position == "软件测试"
    assert fair.location == "西安"
    assert fair.recruit_type == "秋招"
    assert "双选会" in fair.apply_source or "纸质" in fair.apply_source
    assert linked.apply_link == "https://career.example.com/job/123"
    assert linked.apply_source == "官网"
    assert len(list_applications(db_path=db_path)) == 3


def test_v1_interview_can_create_missing_application(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    assert preview["needs_application_creation"] is True
    assert preview["matched_application"] is None

    result = confirm_create_interview(
        preview,
        create_application_if_missing=True,
        db_path=db_path,
    )

    applications = list_applications(db_path=db_path)
    interviews = list_interviews(db_path=db_path)
    assert len(applications) == 1
    assert len(interviews) == 1
    assert applications[0].company == "西安某科技公司"
    assert applications[0].position == "测试开发"
    assert applications[0].status == "一面待进行"
    assert result["interview"].company == "西安某科技公司"
    assert result["interview"].position == "测试开发"
    assert result["interview"].interview_time == "2026-07-14 15:00"


def test_v1_status_update_common_aliases(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    create_application(company="西安吉利科技公司", position="测试开发", db_path=db_path)
    create_application(company="上海百胜软件公司", position="软件开发", db_path=db_path)
    create_application(company="陕西某软件公司", position="软件测试", db_path=db_path)
    create_application(company="北京某科技公司", position="信息科技岗", db_path=db_path)

    cases = [
        ("西安吉利科技公司一面通过了", "西安吉利科技公司", "一面通过"),
        ("上海百胜软件公司二面通过了", "上海百胜软件公司", "二面通过"),
        ("陕西某软件公司挂了", "陕西某软件公司", "未通过"),
        ("北京某科技公司拿到 offer 了", "北京某科技公司", "offer"),
    ]

    for text, company, expected_status in cases:
        _, updated = _update_status(text, db_path)
        assert updated.company == company
        assert updated.status == expected_status


def test_v1_parse_common_interview_times():
    cases = [
        (
            "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
            BASE_DATE,
            "2026-07-14 15:00",
        ),
        (
            "西安吉利科技公司后天下午4点二面",
            BASE_DATE,
            "2026-07-15 16:00",
        ),
        (
            "2026年7月18日下午5点，上海百胜软件公司开发岗要一面。",
            BASE_DATE,
            "2026-07-18 17:00",
        ),
        (
            "2026-07-18 下午5点，上海百胜软件公司开发岗一面。",
            BASE_DATE,
            "2026-07-18 17:00",
        ),
        (
            "2026/07/18 下午5点，上海百胜软件公司开发岗一面。",
            BASE_DATE,
            "2026-07-18 17:00",
        ),
        (
            "7月18日下午5点，上海百胜软件公司开发岗一面。",
            BASE_DATE,
            "2026-07-18 17:00",
        ),
        (
            "陕西某软件公司通知我下周二下午三点一面，腾讯会议，链接还没发。",
            date(2026, 6, 20),
            "2026-06-23 15:00",
        ),
    ]

    for text, base_date, expected_time in cases:
        assert parse_interview_text(text, base_date=base_date)["interview_time"] == expected_time


def test_v1_interview_query_ranges_and_boundaries(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    application = create_application(
        company="边界测试公司",
        position="测试开发",
        db_path=db_path,
    )
    interviews = [
        create_interview(application.id, application.company, application.position, "今天", "2026-07-13 10:00", db_path=db_path),
        create_interview(application.id, application.company, application.position, "明天", "2026-07-14 10:00", db_path=db_path),
        create_interview(application.id, application.company, application.position, "后天", "2026-07-15 10:00", db_path=db_path),
        create_interview(application.id, application.company, application.position, "三天外", "2026-07-16 10:00", db_path=db_path),
        create_interview(application.id, application.company, application.position, "第30天", "2026-08-12 10:00", db_path=db_path),
        create_interview(application.id, application.company, application.position, "第31天", "2026-08-13 10:00", db_path=db_path),
    ]

    assert get_today_interviews(today=BASE_DATE, db_path=db_path) == [interviews[0]]
    assert get_tomorrow_interviews(today=BASE_DATE, db_path=db_path) == [interviews[1]]
    assert get_next_three_days_interviews(today=BASE_DATE, db_path=db_path) == interviews[:3]
    assert get_next_thirty_days_interviews(today=BASE_DATE, db_path=db_path) == interviews[:5]


def test_v1_missing_info_common_cases(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    official = create_application(
        company="官网缺链接公司",
        position="测试开发",
        location="西安",
        apply_source="官网",
        apply_link="",
        db_path=db_path,
    )
    incomplete = create_application(
        company="信息待补充公司",
        position="软件测试",
        location="待补充",
        recruit_type="待补充",
        apply_source="待补充",
        db_path=db_path,
    )
    create_interview(
        application_id=official.id,
        company=official.company,
        position=official.position,
        stage="一面",
        interview_time="2026-07-14 10:00",
        interview_method="腾讯会议",
        meeting_link="",
        db_path=db_path,
    )

    result = check_missing_info(db_path=db_path)
    application_missing = {
        item["id"]: item["missing"]["recommended"]
        for item in result["applications"]
    }
    interview_missing = [
        field
        for item in result["interviews"]
        for field in item["missing"]["recommended"]
    ]

    assert "apply_link" in application_missing[official.id]
    assert {"location", "apply_source"}.issubset(application_missing[incomplete.id])
    assert "meeting_link" in interview_missing


def test_v1_fixed_query_common_phrases():
    assert main.detect_fixed_query("今天有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "today"},
    )
    assert main.detect_fixed_query("明天有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "tomorrow"},
    )
    assert main.detect_fixed_query("未来3天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("未来三天我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_three_days"},
    )
    assert main.detect_fixed_query("未来一个月我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("最近我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "next_thirty_days"},
    )
    assert main.detect_fixed_query("本周我有哪些面试？") == (
        "jobhunt_list_interviews",
        {"range": "this_week"},
    )
    assert main.detect_fixed_query("我现在投了哪些公司？") == (
        "jobhunt_list_applications",
        {},
    )
    assert main.detect_fixed_query("帮我看看哪些求职记录信息没填完整。") == (
        "jobhunt_check_missing_info",
        {},
    )
    assert main.is_application_status_query("西安吉利科技公司目前我的面试状态是什么？") is True


def test_v1_interview_and_status_detection_do_not_conflict():
    assert main.is_interview_input("西安吉利科技公司后天下午4点二面") is True
    assert (
        main.is_interview_input(
            "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。"
        )
        is True
    )
    assert main.is_interview_input("西安吉利科技公司二面通过了") is False
    assert main.is_status_update_input("西安吉利科技公司二面通过了") is True
    assert main.is_status_update_input("陕西某软件公司挂了") is True


def test_v1_interview_display_format_and_related_progress_only():
    text = main.format_jobhunt_result(
        {
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
    )

    assert (
        "西安吉利科技公司 | 测试开发 | 时间：2026-07-14 15:00 | 进度：一面通过"
        in text
    )
    assert "当前整体进度：" not in text
    assert "阶段：一面" not in text
    assert "陕西某软件公司" not in text
    assert "已投递" not in text


def test_v1_application_list_display_still_shows_all_statuses():
    text = main.format_jobhunt_result(
        {
            "ok": True,
            "data": {
                "applications": [
                    {
                        "company": "西安吉利科技公司",
                        "position": "测试开发",
                        "status": "一面通过",
                    },
                    {
                        "company": "上海百胜软件公司",
                        "position": "软件开发",
                        "status": "一面待进行",
                    },
                ]
            },
        }
    )

    assert "当前投递记录：" in text
    assert "西安吉利科技公司 | 测试开发 | 状态：一面通过" in text
    assert "上海百胜软件公司 | 软件开发 | 状态：一面待进行" in text


def test_v1_delete_is_not_part_of_supported_tooling():
    names = set(tool_names())

    assert "jobhunt_delete_application" not in names
    assert "jobhunt_delete_interview" not in names
