from datetime import date

import pytest

from jobhunt.reminders import (
    list_interviews_next_three_days,
    list_interviews_this_month,
    list_interviews_this_week,
    list_interviews_today,
    list_interviews_tomorrow,
)
from jobhunt.repository import create_application, create_interview


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "jobhunt.db"


@pytest.fixture
def application(db_path):
    return create_application(
        company="Acme",
        position="Backend Engineer",
        db_path=db_path,
    )


def add_interview(db_path, application, interview_time, stage="一面"):
    return create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage=stage,
        interview_time=interview_time,
        db_path=db_path,
    )


def test_list_interviews_today(db_path, application):
    today = date(2026, 6, 20)
    today_interview = add_interview(
        db_path,
        application,
        "2026-06-20 10:00",
    )
    add_interview(db_path, application, "2026-06-21 10:00")

    interviews = list_interviews_today(today=today, db_path=db_path)

    assert interviews == [today_interview]


def test_list_interviews_tomorrow(db_path, application):
    today = date(2026, 6, 20)
    tomorrow_interview = add_interview(
        db_path,
        application,
        "2026-06-21 10:00",
    )
    add_interview(db_path, application, "2026-06-22 10:00")

    interviews = list_interviews_tomorrow(today=today, db_path=db_path)

    assert interviews == [tomorrow_interview]


def test_list_interviews_next_three_days_includes_today_tomorrow_and_day_after(
    db_path,
    application,
):
    today = date(2026, 6, 20)
    first = add_interview(db_path, application, "2026-06-20 09:00", "一面")
    second = add_interview(db_path, application, "2026-06-21 10:00", "二面")
    third = add_interview(db_path, application, "2026-06-22 11:00", "HR面")
    add_interview(db_path, application, "2026-06-23 09:00", "终面")

    interviews = list_interviews_next_three_days(today=today, db_path=db_path)

    assert interviews == [first, second, third]


def test_list_interviews_this_week_uses_iso_week(db_path, application):
    today = date(2026, 6, 20)
    monday = add_interview(db_path, application, "2026-06-15 09:00", "周一")
    sunday = add_interview(db_path, application, "2026-06-21 18:00", "周日")
    add_interview(db_path, application, "2026-06-14 18:00", "上周日")
    add_interview(db_path, application, "2026-06-22 09:00", "下周一")

    interviews = list_interviews_this_week(today=today, db_path=db_path)

    assert interviews == [monday, sunday]


def test_list_interviews_this_month_uses_month_start_and_end(db_path, application):
    today = date(2026, 2, 14)
    first_day = add_interview(db_path, application, "2026-02-01 00:00", "月初")
    middle = add_interview(db_path, application, "2026-02-14 10:00", "月中")
    last_day = add_interview(db_path, application, "2026-02-28 23:59", "月末")
    add_interview(db_path, application, "2026-01-31 23:59", "上月")
    add_interview(db_path, application, "2026-03-01 00:00", "下月")

    interviews = list_interviews_this_month(today=today, db_path=db_path)

    assert interviews == [first_day, middle, last_day]
