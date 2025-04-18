from fastapi.testclient import TestClient
from src.inference_server.main import app

client = TestClient(app)

def test_predict_valid():
    """
    Simula una petición válida y verifica que el servidor responde correctamente
    dependiendo de si el modelo está inicializado o no.
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
    assert response.status_code == 200
    assert "prediction" in response.json()
    

def test_model_not_initialized():
    """
    Simula una petición y verifica que el servidor responde con error 503
    (modelo no disponible).
    """
    response = client.post("/predict", json={})
    assert response.status_code == 503

def test_predict_invalid():
    """
    Simula una petición inválida (faltan campos) y verifica que el servidor responde
    con error 422 (validación) o 503 (modelo no disponible).
    """
    response = client.post("/predict", json={})
    assert response.status_code in (422, 503)
    if response.status_code == 503:
        assert "Model not available" in response.json()["detail"]

def test_health_endpoint():
    """
    Verifica que el endpoint /health refleja el estado de model_initialized.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert "model_initialized" in response.json()
    assert isinstance(response.json()["model_initialized"], bool)
