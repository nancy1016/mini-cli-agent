"""V2-01A interviews API tests."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import create_application, create_interview


def _seed_interviews(db_path):
    application = create_application(
        company="面试范围测试公司",
        position="测试开发",
        db_path=db_path,
    )
    today = date.today()
    for offset, stage in ((0, "今天"), (1, "明天"), (2, "后天"), (30, "第30天")):
        create_interview(
            application_id=application.id,
            company=application.company,
            position=application.position,
            stage=stage,
            interview_time=f"{(today + timedelta(days=offset)).isoformat()} 10:00",
            db_path=db_path,
        )


@pytest.mark.parametrize(
    ("range_name", "expected_stages"),
    [
        ("today", {"今天"}),
        ("tomorrow", {"明天"}),
        ("next_three_days", {"今天", "明天", "后天"}),
        ("next_thirty_days", {"今天", "明天", "后天", "第30天"}),
    ],
)
def test_interviews_api_supports_fixed_ranges(tmp_path, range_name, expected_stages):
    db_path = tmp_path / "jobhunt.db"
    _seed_interviews(db_path)
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/interviews", params={"range": range_name})

    assert response.status_code == 200
    assert {row["stage"] for row in response.json()} == expected_stages


def test_interviews_api_supports_this_week(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    _seed_interviews(db_path)
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/interviews", params={"range": "this_week"})

    assert response.status_code == 200
    assert "今天" in {row["stage"] for row in response.json()}


def test_interviews_api_rejects_unknown_range(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db"))

    response = client.get("/api/v1/interviews", params={"range": "unknown"})

    assert response.status_code == 400
    assert "unsupported interview range" in response.json()["detail"]
