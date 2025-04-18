from fastapi.testclient import TestClient
from src.retraining_server.main import app

client = TestClient(app)

def test_retrain_endpoint():
    """
    Tests the /retrain endpoint of the retraining server.

    The endpoint should return a 200 status code and a JSON response containing the
    status of the retraining process. The status should be either "retraining started"
    or "retraining finished".
    """
    response = client.post("/retrain")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] in ["retraining finished", "retraining started"]
