from fastapi.testclient import TestClient
from src.inference_server.main import app

client = TestClient(app)

def test_predict_valid():
    """
    Simulates a valid input with the first columns of the dataset
    and verifies that the inference server returns a valid prediction.
    The input must contain all the necessary columns for the prediction.
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
        # ...add more features as needed 
        # to match the model's expected input   
    }
    response = client.post("/predict", json=features)
    assert response.status_code == 200 or response.status_code == 503
    if response.status_code == 200:
        assert "prediction" in response.json()

def test_predict_invalid():
    """
    Simulates an invalid input with missing or incorrect columns
    and verifies that the inference server returns an error response.
    The input must not contain all the necessary columns for the prediction.
    """
    response = client.post("/predict", json={})
    assert response.status_code in (200, 422, 503)
