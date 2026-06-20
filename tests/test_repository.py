from datetime import date

import pytest

from jobhunt.repository import (
    create_application,
    create_interview,
    find_applications_by_company,
    list_applications,
    list_interviews,
    list_interviews_between,
    update_application_status,
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "jobhunt.db"


def test_create_application_uses_defaults(db_path):
    application = create_application(
        company="Acme",
        position="Backend Engineer",
        db_path=db_path,
    )

    assert application.id == 1
    assert application.company == "Acme"
    assert application.position == "Backend Engineer"
    assert application.apply_date == date.today().isoformat()
    assert application.status == "已投递"


def test_list_and_find_applications_by_company(db_path):
    create_application(
        company="Acme",
        position="Backend Engineer",
        location="Shanghai",
        db_path=db_path,
    )
    create_application(
        company="Beta",
        position="Data Engineer",
        db_path=db_path,
    )

    applications = list_applications(db_path=db_path)
    acme_applications = find_applications_by_company("Acme", db_path=db_path)

    assert [item.company for item in applications] == ["Acme", "Beta"]
    assert len(acme_applications) == 1
    assert acme_applications[0].position == "Backend Engineer"
    assert acme_applications[0].location == "Shanghai"


def test_update_application_status(db_path):
    application = create_application(
        company="Acme",
        position="Backend Engineer",
        db_path=db_path,
    )

    updated = update_application_status(
        application_id=application.id,
        status="一面通过",
        db_path=db_path,
    )

    assert updated.status == "一面通过"
    assert list_applications(db_path=db_path)[0].status == "一面通过"


def test_create_interview(db_path):
    application = create_application(
        company="Acme",
        position="Backend Engineer",
        db_path=db_path,
    )

    interview = create_interview(
        application_id=application.id,
        company="Acme",
        position="Backend Engineer",
        stage="一面",
        interview_time="2026-06-21 10:30",
        interview_method="视频",
        meeting_link="https://meeting.example/acme",
        notes="Prepare system design examples",
        db_path=db_path,
    )

    interviews = list_interviews(db_path=db_path)

    assert interview.id == 1
    assert interviews == [interview]
    assert interview.application_id == application.id
    assert interview.stage == "一面"


def test_list_interviews_between(db_path):
    application = create_application(
        company="Acme",
        position="Backend Engineer",
        db_path=db_path,
    )

    create_interview(
        application_id=application.id,
        company="Acme",
        position="Backend Engineer",
        stage="一面",
        interview_time="2026-06-20 09:00",
        db_path=db_path,
    )
    target = create_interview(
        application_id=application.id,
        company="Acme",
        position="Backend Engineer",
        stage="二面",
        interview_time="2026-06-21 10:30",
        db_path=db_path,
    )
    create_interview(
        application_id=application.id,
        company="Acme",
        position="Backend Engineer",
        stage="HR 面",
        interview_time="2026-06-22 14:00",
        db_path=db_path,
    )

    interviews = list_interviews_between(
        start_time="2026-06-21 00:00",
        end_time="2026-06-21 23:59",
        db_path=db_path,
    )

    assert interviews == [target]
