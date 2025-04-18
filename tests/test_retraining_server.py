import pytest
from fastapi.testclient import TestClient
from src.retraining_server.main import app

client = TestClient(app)

def test_retrain_endpoint():
    response = client.post("/retrain")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] in ["retraining finished", "retraining started"]
