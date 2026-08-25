"""V2-01A health API tests."""

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_api_returns_running_status(tmp_path):
    client = TestClient(create_app(tmp_path / "jobhunt.db"))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "JobHuntLedger-Agent",
        "version": "v2-01a",
        "message": "backend is running",
    }
