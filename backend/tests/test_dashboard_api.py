"""V2-01A Dashboard API tests."""

from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import create_application, create_interview


def test_dashboard_api_returns_real_summary(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    active = create_application(
        company="西安测试公司",
        position="测试开发",
        status="一面待进行",
        db_path=db_path,
    )
    create_application(
        company="上海样例公司",
        position="后端开发",
        location="上海",
        apply_source="内推",
        status="offer",
        db_path=db_path,
    )
    create_interview(
        application_id=active.id,
        company=active.company,
        position=active.position,
        stage="一面",
        interview_time=f"{date.today().isoformat()} 15:00",
        db_path=db_path,
    )
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "total_applications",
        "active_applications",
        "offer_count",
        "next_three_days_interviews",
        "next_thirty_days_interviews",
        "missing_info_count",
        "recent_applications",
        "upcoming_interviews",
    }
    assert data["total_applications"] == 2
    assert data["active_applications"] == 1
    assert data["offer_count"] == 1
    assert data["next_three_days_interviews"] == 1
    assert data["next_thirty_days_interviews"] == 1
    assert data["missing_info_count"] >= 1
    assert len(data["recent_applications"]) == 2
    assert len(data["upcoming_interviews"]) == 1


def test_empty_database_endpoints_return_empty_results(tmp_path):
    client = TestClient(create_app(tmp_path / "empty.db"))

    dashboard = client.get("/api/v1/dashboard/summary")
    applications = client.get("/api/v1/applications")
    interviews = client.get("/api/v1/interviews")
    missing = client.get("/api/v1/missing-info")

    assert dashboard.status_code == 200
    assert dashboard.json()["total_applications"] == 0
    assert dashboard.json()["recent_applications"] == []
    assert dashboard.json()["upcoming_interviews"] == []
    assert applications.status_code == 200
    assert applications.json() == []
    assert interviews.status_code == 200
    assert interviews.json() == []
    assert missing.status_code == 200
    assert missing.json() == []
