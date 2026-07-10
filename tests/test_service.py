"""service 核心业务编排的 V1 场景测试。"""

from datetime import date

import pytest

from jobhunt.repository import (
    create_application,
    create_interview,
    list_applications,
    list_interviews,
)
from jobhunt.service import (
    check_missing_info,
    confirm_update_application_status,
    confirm_create_application,
    confirm_create_interview,
    get_next_three_days_interviews,
    get_today_interviews,
    get_tomorrow_interviews,
    get_weekly_interviews,
    list_all_applications,
    preview_application_from_text,
    preview_interview_from_text,
    preview_status_update_from_text,
    update_application_status_from_text,
)


BASE_DATE = date(2026, 6, 20)


@pytest.fixture
def db_path(tmp_path):
    # 每个测试使用独立临时库，避免污染真实求职台账数据。
    return tmp_path / "jobhunt.db"


def add_interview(db_path, application, interview_time, stage="一面"):
    return create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage=stage,
        interview_time=interview_time,
        interview_method="腾讯会议",
        db_path=db_path,
    )


def test_preview_application_does_not_save_to_database(db_path):
    preview = preview_application_from_text(
        "今天在官网投了西安某科技公司的测试开发岗，地点西安。",
        base_date=BASE_DATE,
    )

    assert preview["action"] == "preview_application"
    assert preview["parsed"]["company"] == "西安某科技公司"
    assert preview["parsed"]["position"] == "测试开发"
    assert preview["will_save"] is False
    assert list_applications(db_path=db_path) == []


def test_confirm_create_application_saves_preview_result(db_path):
    preview = preview_application_from_text(
        "今天在官网投了西安某科技公司的测试开发岗，地点西安。",
        base_date=BASE_DATE,
    )

    application = confirm_create_application(preview, db_path=db_path)

    applications = list_applications(db_path=db_path)
    assert application.id == 1
    assert len(applications) == 1
    assert applications[0].company == "西安某科技公司"
    assert applications[0].position == "测试开发"


def test_preview_interview_matches_existing_application(db_path):
    create_application(
        company="西安某科技公司",
        position="测试开发",
        db_path=db_path,
    )

    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    assert preview["matched_application"] is not None
    assert preview["matched_application"]["company"] == "西安某科技公司"
    assert preview["needs_application_creation"] is False


def test_confirm_create_interview_uses_matched_application_id(db_path):
    application = create_application(
        company="西安某科技公司",
        position="测试开发",
        db_path=db_path,
    )
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )
    result = confirm_create_interview(preview, db_path=db_path)
    assert result["interview"].application_id == application.id


def test_preview_interview_requires_application_creation_when_no_match(db_path):
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    assert preview["matched_application"] is None
    assert preview["needs_application_creation"] is True
    assert preview["will_save"] is False


def test_confirm_create_interview_saves_interview_and_updates_status(db_path):
    create_application(
        company="西安某科技公司",
        position="测试开发",
        db_path=db_path,
    )
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    result = confirm_create_interview(preview, db_path=db_path)

    interviews = list_interviews(db_path=db_path)
    applications = list_applications(db_path=db_path)
    assert result["interview"].id == 1
    assert interviews[0].stage == "一面"
    assert applications[0].status == "一面待进行"
    assert result["updated_status"] == "一面待进行"


def test_confirm_create_interview_can_create_missing_application(db_path):
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    result = confirm_create_interview(
        preview,
        create_application_if_missing=True,
        db_path=db_path,
    )

    applications = list_applications(db_path=db_path)
    interviews = list_interviews(db_path=db_path)
    assert len(applications) == 1
    assert len(interviews) == 1
    assert result["application"].company == "西安某科技公司"
    assert result["interview"].application_id == result["application"].id


def test_confirm_create_interview_raises_when_application_missing_without_confirm(db_path):
    preview = preview_interview_from_text(
        "明天下午三点，西安某科技公司测试开发岗一面，电话通知的。",
        base_date=BASE_DATE,
        db_path=db_path,
    )

    with pytest.raises(ValueError):
        confirm_create_interview(
            preview,
            create_application_if_missing=False,
            db_path=db_path,
        )


def test_list_all_applications_returns_all_records(db_path):
    create_application(company="陕西某软件公司", position="软件测试", db_path=db_path)
    create_application(company="西安某科技公司", position="测试开发", db_path=db_path)

    applications = list_all_applications(db_path=db_path)

    assert len(applications) == 2
    assert [item.company for item in applications] == [
        "陕西某软件公司",
        "西安某科技公司",
    ]


def test_get_today_interviews_returns_only_today(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    today_interview = add_interview(db_path, application, "2026-06-20 10:00")
    add_interview(db_path, application, "2026-06-21 10:00")

    interviews = get_today_interviews(today=BASE_DATE, db_path=db_path)

    assert interviews == [today_interview]


def test_get_tomorrow_interviews_returns_only_tomorrow(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    add_interview(db_path, application, "2026-06-20 10:00")
    tomorrow_interview = add_interview(db_path, application, "2026-06-21 10:00")

    interviews = get_tomorrow_interviews(today=BASE_DATE, db_path=db_path)

    assert interviews == [tomorrow_interview]


def test_get_next_three_days_interviews_includes_today_tomorrow_and_day_after(
    db_path,
):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    # 未来三天包含今天、明天、后天，不包含大后天。
    first = add_interview(db_path, application, "2026-06-20 09:00", "一面")
    second = add_interview(db_path, application, "2026-06-21 10:00", "二面")
    third = add_interview(db_path, application, "2026-06-22 11:00", "HR面")
    add_interview(db_path, application, "2026-06-23 09:00", "终面")

    interviews = get_next_three_days_interviews(today=BASE_DATE, db_path=db_path)

    assert interviews == [first, second, third]


def test_get_weekly_interviews_uses_iso_week(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    # BASE_DATE 是 2026-06-20，所在 ISO 周为 6 月 15 日到 6 月 21 日。
    monday = add_interview(db_path, application, "2026-06-15 09:00", "周一")
    sunday = add_interview(db_path, application, "2026-06-21 18:00", "周日")
    add_interview(db_path, application, "2026-06-14 18:00", "上周日")
    add_interview(db_path, application, "2026-06-22 09:00", "下周一")

    interviews = get_weekly_interviews(today=BASE_DATE, db_path=db_path)

    assert interviews == [monday, sunday]


def test_check_missing_info_groups_application_and_interview_missing_fields(db_path):
    application = create_application(
        company="陕西某软件公司",
        position="软件测试",
        location=None,
        apply_source="官网",
        apply_link="",
        db_path=db_path,
    )
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time="2026-06-20 10:00",
        interview_method="腾讯会议",
        meeting_link="",
        db_path=db_path,
    )

    result = check_missing_info(db_path=db_path)

    assert result["applications"][0]["missing"]["recommended"] == [
        "location",
        "apply_link",
    ]
    assert result["interviews"][0]["missing"]["recommended"] == ["meeting_link"]


def test_update_application_status_from_text_updates_existing_application(db_path):
    create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )

    updated = update_application_status_from_text(
        "陕西某软件公司一面通过了。",
        db_path=db_path,
    )

    assert updated.status == "一面通过"
    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_preview_status_update_from_text_does_not_save_to_database(db_path):
    create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )

    preview = preview_status_update_from_text(
        "陕西某软件公司一面通过了。",
        db_path=db_path,
    )

    assert preview["action"] == "preview_status_update"
    assert preview["parsed"]["status"] == "一面通过"
    assert preview["matched_application"]["company"] == "陕西某软件公司"
    assert preview["needs_application_match"] is False
    assert preview["new_status"] == "一面通过"
    assert preview["will_save"] is False
    assert list_applications(db_path=db_path)[0].status == "已投递"


def test_confirm_update_application_status_saves_preview_result(db_path):
    create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )
    preview = preview_status_update_from_text(
        "陕西某软件公司一面通过了。",
        db_path=db_path,
    )

    updated = confirm_update_application_status(preview, db_path=db_path)

    assert updated.status == "一面通过"
    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_update_application_status_from_text_normalizes_rejected_alias(db_path):
    create_application(
        company="陕西某软件公司",
        position="软件测试",
        db_path=db_path,
    )

    updated = update_application_status_from_text(
        "陕西某软件公司挂了。",
        db_path=db_path,
    )
    assert updated.status == "未通过"
    assert list_applications(db_path=db_path)[0].status == "未通过"


def test_update_application_status_from_text_raises_when_company_missing(db_path):
    with pytest.raises(ValueError):
        update_application_status_from_text(
            "陕西某软件公司挂了。",
            db_path=db_path,
        )
