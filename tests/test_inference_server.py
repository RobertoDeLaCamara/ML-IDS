from fastapi.testclient import TestClient
from src.inference_server.main import app

client = TestClient(app)

def test_predict_valid():
    """
    Simulates a valid request and checks that the server responds correctly
    depending on whether the model is initialized or not.
    """
    features = {
        "Flow Duration": 1000,
        "Total Fwd Packet": 2,
        "Total Bwd packets": 2,
        "Total Length of Fwd Packet": 100.0,
        "Total Length of Bwd Packet": 100.0,
        "Fwd Packet Length Max": 50.0,
        "Fwd Packet Length Min": 0.0,
        "Fwd Packet Length Mean": 25.0,
        "Fwd Packet Length Std": 10.0,
        "Bwd Packet Length Max": 50.0,
        "Bwd Packet Length Min": 0.0,
        "Bwd Packet Length Mean": 25.0,
        "Bwd Packet Length Std": 10.0,
        "Flow Bytes/s": 1000.0,
        "Flow Packets/s": 2.0,
        "Flow IAT Mean": 500.0,
        "Flow IAT Std": 100.0,
        "Flow IAT Max": 1000.0,
        "Flow IAT Min": 0.0,
    }
    response = client.post("/predict", json=features)
    assert response.status_code == 200 or response.status_code == 503
    if response.status_code == 200:
        assert "prediction" in response.json()
    elif response.status_code == 503:
        assert "Model not available" in response.json()["detail"]

def test_predict_unprocessable():
    """
    Simulates a request with no features and checks for 422 Unprocessable Entity.
    """
    response = client.post("/predict")  # No JSON body sent
    assert response.status_code == 422
    # FastAPI returns a validation error list if body is missing
    if isinstance(response.json(), list) or isinstance(response.json(), dict) and 'detail' in response.json():
        detail = response.json().get('detail', response.json())
        assert any('Field required' in str(item) or 'No features provided' in str(item) for item in (detail if isinstance(detail, list) else [detail]))

def test_predict_invalid():
    """
    Simulates an invalid request (empty features) and checks for 400 Bad Request, 422 Unprocessable Entity, or 503 Service Unavailable.
    """
    response = client.post("/predict", json={})
    assert response.status_code in (400, 422, 503)
    if response.status_code == 400:
        assert "Invalid or empty features" in response.json()["detail"]
    if response.status_code == 422:
        # Accept both FastAPI validation and custom error
        detail = response.json().get('detail', response.json())
        assert any('Field required' in str(item) or 'No features provided' in str(item) or 'Invalid or empty features' in str(item) for item in (detail if isinstance(detail, list) else [detail]))
    if response.status_code == 503:
        assert "Model not available" in response.json()["detail"]

def test_health_endpoint():
    """
    Checks that the /health endpoint reflects the state of model_initialized.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert "model_initialized" in response.json()
    assert isinstance(response.json()["model_initialized"], bool)
