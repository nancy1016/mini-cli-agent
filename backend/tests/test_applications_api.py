"""V2-01A applications API tests."""

from fastapi.testclient import TestClient

from backend.app.main import create_app
from jobhunt.repository import create_application


def _seed_applications(db_path):
    create_application(
        company="西安未来科技公司",
        position="测试开发",
        location="西安",
        apply_source="官网",
        status="已投递",
        db_path=db_path,
    )
    create_application(
        company="上海示例软件公司",
        position="后端开发",
        location="上海",
        apply_source="内推",
        status="offer",
        db_path=db_path,
    )


def test_applications_api_returns_rows(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    _seed_applications(db_path)
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/applications")

    assert response.status_code == 200
    assert [row["company"] for row in response.json()] == [
        "西安未来科技公司",
        "上海示例软件公司",
    ]


def test_applications_api_filters_by_status(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    _seed_applications(db_path)
    client = TestClient(create_app(db_path))

    response = client.get("/api/v1/applications", params={"status": "offer"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["company"] == "上海示例软件公司"


def test_applications_api_searches_company_position_and_location(tmp_path):
    db_path = tmp_path / "jobhunt.db"
    _seed_applications(db_path)
    client = TestClient(create_app(db_path))

    company = client.get("/api/v1/applications", params={"keyword": "未来科技"})
    position = client.get("/api/v1/applications", params={"keyword": "后端"})
    location = client.get("/api/v1/applications", params={"keyword": "西安"})

    assert [row["position"] for row in company.json()] == ["测试开发"]
    assert [row["company"] for row in position.json()] == ["上海示例软件公司"]
    assert [row["company"] for row in location.json()] == ["西安未来科技公司"]
