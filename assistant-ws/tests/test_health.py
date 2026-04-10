from fastapi.testclient import TestClient


def test_health():
    from assistant_ws.app import fastapi_app

    client = TestClient(fastapi_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
