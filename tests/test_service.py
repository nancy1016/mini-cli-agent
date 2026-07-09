"""service 核心业务编排的 V1 场景测试。"""

from datetime import date

import pytest

from jobhunt.repository import (
    create_application,
    list_applications,
    list_interviews,
)
from jobhunt.service import (
    confirm_create_application,
    confirm_create_interview,
    preview_application_from_text,
    preview_interview_from_text,
)


BASE_DATE = date(2026, 6, 20)


@pytest.fixture
def db_path(tmp_path):
    # 每个测试使用独立临时库，避免污染真实求职台账数据。
    return tmp_path / "jobhunt.db"


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
