"""Runtime ASGI application behaviour tests."""

from starlette.testclient import TestClient
from iw.web.app import app


def test_runtime_health_endpoint_returns_ok():
    """Health check returns status 200 and json payload."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "tinkerspace"}


def test_runtime_index_page_renders_html():
    """Landing index page renders successfully with status 200."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Tinkerspace" in response.text
    assert "Innovator&#39;s Workspace" in response.text or "Innovator's Workspace" in response.text
