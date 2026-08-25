"""V2-01A missing-info API tests."""

from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import create_application, create_interview


def test_missing_info_api_flattens_application_and_interview_gaps(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    application = create_application(
        company="信息待补充公司",
        position="测试开发",
        location="待补充",
        apply_source="官网",
        apply_link="",
        db_path=db_path,
    )
    create_interview(
        application_id=application.id,
        company=application.company,
        position=application.position,
        stage="一面",
        interview_time=f"{date.today().isoformat()} 15:00",
        interview_method="腾讯会议",
        meeting_link="",
        db_path=db_path,
    )
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/missing-info")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    application_row = next(row for row in rows if "location" in row["missing_fields"])
    interview_row = next(row for row in rows if "meeting_link" in row["missing_fields"])
    assert application_row["company"] == "信息待补充公司"
    assert "apply_link" in application_row["missing_fields"]
    assert "工作地点" in application_row["suggestion"]
    assert "会议链接" in interview_row["suggestion"]
