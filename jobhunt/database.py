"""SQLite connection and schema setup for JobHuntLedger."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


DEFAULT_DB_PATH = Path("data/jobhunt.db")


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with closing(get_connection(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    location TEXT,
                    recruit_type TEXT,
                    apply_source TEXT,
                    apply_link TEXT,
                    apply_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    interview_time TEXT NOT NULL,
                    interview_method TEXT,
                    meeting_link TEXT,
                    notes TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications(id)
                )
                """
            )
