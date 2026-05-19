from fastapi.testclient import TestClient


def test_root_returns_html_with_webpilot():
    from webpilot.api import app

    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "WebPilot" in resp.text
