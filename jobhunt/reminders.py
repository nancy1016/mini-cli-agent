"""求职台账的面试提醒查询。"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path

from jobhunt.database import DEFAULT_DB_PATH
from jobhunt.models import Interview
from jobhunt.repository import list_interviews_between


DbPath = str | Path


def _resolve_today(today: date | None) -> date:
    return today or date.today()


def _start_of_day(day: date) -> str:
    return f"{day.isoformat()} 00:00"


def _end_of_day(day: date) -> str:
    return f"{day.isoformat()} 23:59"


def _list_interviews_in_range(
    start_day: date,
    end_day: date,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """按整天边界查询面试。"""
    return list_interviews_between(
        start_time=_start_of_day(start_day),
        end_time=_end_of_day(end_day),
        db_path=db_path,
    )


def list_interviews_today(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询今天 00:00 到 23:59 的面试。"""
    current_day = _resolve_today(today)
    return _list_interviews_in_range(current_day, current_day, db_path)


def list_interviews_tomorrow(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询明天 00:00 到 23:59 的面试。"""
    tomorrow = _resolve_today(today) + timedelta(days=1)
    return _list_interviews_in_range(tomorrow, tomorrow, db_path)


def list_interviews_next_three_days(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询未来三天的面试，包含今天、明天、后天。"""
    current_day = _resolve_today(today)
    return _list_interviews_in_range(
        current_day,
        current_day + timedelta(days=2),
        db_path,
    )


def list_interviews_next_thirty_days(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询未来 30 天的面试，包含今天和第 30 天当天。"""
    current_day = _resolve_today(today)
    return _list_interviews_in_range(
        current_day,
        current_day + timedelta(days=30),
        db_path,
    )


def list_interviews_this_week(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询本周面试，按 ISO 周计算为周一到周日。"""
    current_day = _resolve_today(today)
    monday = current_day - timedelta(days=current_day.weekday())
    sunday = monday + timedelta(days=6)
    return _list_interviews_in_range(monday, sunday, db_path)


def list_interviews_this_month(
    today: date | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    """查询本月面试，范围为当月 1 号到最后一天。"""
    current_day = _resolve_today(today)
    last_day = calendar.monthrange(current_day.year, current_day.month)[1]
    month_start = current_day.replace(day=1)
    month_end = current_day.replace(day=last_day)
    return _list_interviews_in_range(month_start, month_end, db_path)
