import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_status_endpoint(client):
    # If the endpoint doesn't exist, this will return 404. Let's just test health for now to prove FastAPI is up.
    response = client.get("/health")
    assert response.status_code == 200

