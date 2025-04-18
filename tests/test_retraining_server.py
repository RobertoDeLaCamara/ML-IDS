from fastapi.testclient import TestClient
from src.retraining_server.main import app

client = TestClient(app)

def test_retrain_endpoint():
    """
    Tests the /retrain endpoint of the retraining server.

    The endpoint should return a 501 status code and a JSON response indicating
    that the retraining functionality is not implemented.
    """
    response = client.post("/retrain")
    assert response.status_code == 200
    assert "detail" in response.json()
    assert response.json()["detail"] == "Retraining not implemented"
