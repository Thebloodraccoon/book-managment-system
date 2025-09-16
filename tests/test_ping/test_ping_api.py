import pytest
from starlette.testclient import TestClient

from app.main import app


def test_ping_endpoint(client: TestClient):
    """Testing the work of ping endpoint."""
    response = client.get("/ping/")

    assert response.status_code == 200
    data = response.json()

    assert "ping" in data
    assert data["ping"] == "pong"
    assert "timestamp" in data
    assert "status" in data
    assert data["status"] == "healthy"
    assert isinstance(data["timestamp"], int | float)


def test_nonexistent_endpoint(client: TestClient):
    """Testing an appeal to a non-existent endpoint."""
    response = client.get("/nonexistent/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_app_startup():
    """Tests that the application is launched without errors."""
    assert app is not None
    assert app.title is not None
