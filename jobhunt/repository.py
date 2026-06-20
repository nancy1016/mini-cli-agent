"""Repository functions for JobHuntLedger persistence."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from jobhunt.database import DEFAULT_DB_PATH, get_connection, init_db
from jobhunt.models import (
    DEFAULT_APPLICATION_STATUS,
    Application,
    Interview,
    today_string,
)


DbPath = str | Path


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _application_from_row(row) -> Application:
    return Application(
        id=row["id"],
        company=row["company"],
        position=row["position"],
        location=row["location"],
        recruit_type=row["recruit_type"],
        apply_source=row["apply_source"],
        apply_link=row["apply_link"],
        apply_date=row["apply_date"],
        status=row["status"],
        notes=row["notes"],
    )


def _interview_from_row(row) -> Interview:
    return Interview(
        id=row["id"],
        application_id=row["application_id"],
        company=row["company"],
        position=row["position"],
        stage=row["stage"],
        interview_time=row["interview_time"],
        interview_method=row["interview_method"],
        meeting_link=row["meeting_link"],
        notes=row["notes"],
    )


def create_application(
    company: str,
    position: str,
    location: str | None = None,
    recruit_type: str | None = None,
    apply_source: str | None = None,
    apply_link: str | None = None,
    apply_date: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Application:
    init_db(db_path)

    application = Application(
        id=None,
        company=_require_text(company, "company"),
        position=_require_text(position, "position"),
        location=location,
        recruit_type=recruit_type,
        apply_source=apply_source,
        apply_link=apply_link,
        apply_date=apply_date or today_string(),
        status=status or DEFAULT_APPLICATION_STATUS,
        notes=notes,
    )

    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO applications (
                    company,
                    position,
                    location,
                    recruit_type,
                    apply_source,
                    apply_link,
                    apply_date,
                    status,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    application.company,
                    application.position,
                    application.location,
                    application.recruit_type,
                    application.apply_source,
                    application.apply_link,
                    application.apply_date,
                    application.status,
                    application.notes,
                ),
            )

    return Application(
        id=cursor.lastrowid,
        company=application.company,
        position=application.position,
        location=application.location,
        recruit_type=application.recruit_type,
        apply_source=application.apply_source,
        apply_link=application.apply_link,
        apply_date=application.apply_date,
        status=application.status,
        notes=application.notes,
    )


def list_applications(db_path: DbPath = DEFAULT_DB_PATH) -> list[Application]:
    init_db(db_path)

    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM applications
            ORDER BY id ASC
            """
        ).fetchall()

    return [_application_from_row(row) for row in rows]


def find_applications_by_company(
    company: str,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Application]:
    init_db(db_path)

    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM applications
            WHERE company = ?
            ORDER BY id ASC
            """,
            (_require_text(company, "company"),),
        ).fetchall()

    return [_application_from_row(row) for row in rows]


def update_application_status(
    application_id: int,
    status: str,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Application:
    init_db(db_path)
    normalized_status = _require_text(status, "status")

    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE applications
                SET status = ?
                WHERE id = ?
                """,
                (normalized_status, application_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(f"application not found: {application_id}")

            row = connection.execute(
                """
                SELECT *
                FROM applications
                WHERE id = ?
                """,
                (application_id,),
            ).fetchone()

    return _application_from_row(row)


def create_interview(
    application_id: int,
    company: str,
    position: str,
    stage: str,
    interview_time: str,
    interview_method: str | None = None,
    meeting_link: str | None = None,
    notes: str | None = None,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> Interview:
    init_db(db_path)

    interview = Interview(
        id=None,
        application_id=application_id,
        company=_require_text(company, "company"),
        position=_require_text(position, "position"),
        stage=_require_text(stage, "stage"),
        interview_time=_require_text(interview_time, "interview_time"),
        interview_method=interview_method,
        meeting_link=meeting_link,
        notes=notes,
    )

    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO interviews (
                    application_id,
                    company,
                    position,
                    stage,
                    interview_time,
                    interview_method,
                    meeting_link,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interview.application_id,
                    interview.company,
                    interview.position,
                    interview.stage,
                    interview.interview_time,
                    interview.interview_method,
                    interview.meeting_link,
                    interview.notes,
                ),
            )

    return Interview(
        id=cursor.lastrowid,
        application_id=interview.application_id,
        company=interview.company,
        position=interview.position,
        stage=interview.stage,
        interview_time=interview.interview_time,
        interview_method=interview.interview_method,
        meeting_link=interview.meeting_link,
        notes=interview.notes,
    )


def list_interviews(db_path: DbPath = DEFAULT_DB_PATH) -> list[Interview]:
    init_db(db_path)

    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM interviews
            ORDER BY interview_time ASC, id ASC
            """
        ).fetchall()

    return [_interview_from_row(row) for row in rows]


def list_interviews_between(
    start_time: str,
    end_time: str,
    db_path: DbPath = DEFAULT_DB_PATH,
) -> list[Interview]:
    init_db(db_path)

    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM interviews
            WHERE interview_time >= ?
              AND interview_time <= ?
            ORDER BY interview_time ASC, id ASC
            """,
            (
                _require_text(start_time, "start_time"),
                _require_text(end_time, "end_time"),
            ),
        ).fetchall()

    return [_interview_from_row(row) for row in rows]
