import pytest
from fastapi.testclient import TestClient
from src.inference_server.main import app

client = TestClient(app)

def test_predict_valid():
    # Simula un input válido con las primeras columnas del dataset
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
        # ...agrega el resto de las features necesarias...
    }
    response = client.post("/predict", json=features)
    assert response.status_code == 200
    assert "prediction" in response.json()

def test_predict_invalid():
    # Input vacío o inválido
    response = client.post("/predict", json={})
    assert response.status_code == 200 or response.status_code == 422
