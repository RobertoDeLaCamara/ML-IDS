import os
import shutil
import time
import pytest
import requests
import docker
from fastapi.testclient import TestClient
from src.inference_server.main import app

client = TestClient(app)

def test_predict_valid():
    """
    Simulates a valid request and checks that the server responds correctly
    depending on whether the model is initialized or not.
    """
    features = {
        'Flow Duration': 1000,
        'Total Fwd Packet': 2,
        'Total Bwd packets': 2,
        'Total Length of Fwd Packet': 100.0,
        'Total Length of Bwd Packet': 100.0,
        'Fwd Packet Length Max': 50.0,
        'Fwd Packet Length Min': 0.0,
        'Fwd Packet Length Mean': 25.0,
        'Fwd Packet Length Std': 10.0,
        'Bwd Packet Length Max': 50.0,
        'Bwd Packet Length Min': 0.0,
        'Bwd Packet Length Mean': 25.0,
        'Bwd Packet Length Std': 10.0,
        'Flow Bytes/s': 1000.0,
        'Flow Packets/s': 2.0,
        'Flow IAT Mean': 500.0,
        'Flow IAT Std': 100.0,
        'Flow IAT Max': 1000.0,
        'Flow IAT Min': 0.0,
        'Fwd IAT Total': 1000.0,
        'Fwd IAT Mean': 500.0,
        'Fwd IAT Std': 100.0,
        'Fwd IAT Max': 1000.0,
        'Fwd IAT Min': 0.0,
        'Bwd IAT Total': 1000.0,
        'Bwd IAT Mean': 500.0,
        'Bwd IAT Std': 100.0,
        'Bwd IAT Max': 1000.0,
        'Bwd IAT Min': 0.0,
        'Fwd PSH Flags': 0,
        'Bwd PSH Flags': 0,
        'Fwd URG Flags': 0,
        'Bwd URG Flags': 0,
        'Fwd Header Length': 20,
        'Bwd Header Length': 20,
        'Fwd Packets/s': 2.0,
        'Bwd Packets/s': 2.0,
        'Packet Length Min': 0.0,
        'Packet Length Max': 50.0,
        'Packet Length Mean': 25.0,
        'Packet Length Std': 10.0,
        'Packet Length Variance': 5.0,
        'FIN Flag Count': 0,
        'SYN Flag Count': 0,
        'RST Flag Count': 0,
        'PSH Flag Count': 0,
        'ACK Flag Count': 0,
        'URG Flag Count': 0,
        'CWR Flag Count': 0,
        'ECE Flag Count': 0,
        'Down/Up Ratio': 1.0,
        'Average Packet Size': 25.0,
        'Fwd Segment Size Avg': 20.0,
        'Bwd Segment Size Avg': 20.0,
        'Fwd Bytes/Bulk Avg': 0.0,
        'Fwd Packet/Bulk Avg': 0.0,
        'Fwd Bulk Rate Avg': 0.0,
        'Bwd Bytes/Bulk Avg': 0.0,
        'Bwd Packet/Bulk Avg': 0.0,
        'Bwd Bulk Rate Avg': 0.0,
        'Subflow Fwd Packets': 1,
        'Subflow Fwd Bytes': 100,
        'Subflow Bwd Packets': 1,
        'Subflow Bwd Bytes': 100,
        'FWD Init Win Bytes': 0,
        'Bwd Init Win Bytes': 0,
        'Fwd Act Data Pkts': 0,
        'Fwd Seg Size Min': 0,
        'Active Mean': 0.0,
        'Active Std': 0.0,
        'Active Max': 0.0,
        'Active Min': 0.0,
        'Idle Mean': 0.0,
        'Idle Std': 0.0,
        'Idle Max': 0.0,
        'Idle Min': 0.0
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

def is_docker_available():
    return shutil.which("docker") is not None

@pytest.mark.skipif(not is_docker_available(), reason="Docker is not available on this system.")
def test_inference_server_docker():
    """
    Arranca el contenedor de inference_server, espera a que esté listo y envía requests de prueba.
    """
    client = docker.from_env()
    image_tag = "inference_server:test"
    dockerfile_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/inference_server'))
    # Build image
    image, _ = client.images.build(path=dockerfile_path, tag=image_tag)
    # Run container
    container = client.containers.run(
        image_tag,
        ports={"8000/tcp": 8000},
        detach=True,
        remove=True,
        environment={},
        working_dir="/app"
    )
    try:
        # Esperar a que el endpoint /health esté disponible
        url = "http://localhost:8000/health"
        for _ in range(30):
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.fail("El contenedor no respondió en /health tras 30 segundos")
        # Enviar request de prueba a /predict
        features = {
            'Flow Duration': 1000,
            'Total Fwd Packet': 2,
            'Total Bwd packets': 2,
            'Total Length of Fwd Packet': 100.0,
            'Total Length of Bwd Packet': 100.0,
            'Fwd Packet Length Max': 50.0,
            'Fwd Packet Length Min': 0.0,
            'Fwd Packet Length Mean': 25.0,
            'Fwd Packet Length Std': 10.0,
            'Bwd Packet Length Max': 50.0,
            'Bwd Packet Length Min': 0.0,
            'Bwd Packet Length Mean': 25.0,
            'Bwd Packet Length Std': 10.0,
            'Flow Bytes/s': 1000.0,
            'Flow Packets/s': 2.0,
            'Flow IAT Mean': 500.0,
            'Flow IAT Std': 100.0,
            'Flow IAT Max': 1000.0,
            'Flow IAT Min': 0.0,
            'Fwd IAT Total': 1000.0,
            'Fwd IAT Mean': 500.0,
            'Fwd IAT Std': 100.0,
            'Fwd IAT Max': 1000.0,
            'Fwd IAT Min': 0.0,
            'Bwd IAT Total': 1000.0,
            'Bwd IAT Mean': 500.0,
            'Bwd IAT Std': 100.0,
            'Bwd IAT Max': 1000.0,
            'Bwd IAT Min': 0.0,
            'Fwd PSH Flags': 0,
            'Bwd PSH Flags': 0,
            'Fwd URG Flags': 0,
            'Bwd URG Flags': 0,
            'Fwd Header Length': 20,
            'Bwd Header Length': 20,
            'Fwd Packets/s': 2.0,
            'Bwd Packets/s': 2.0,
            'Packet Length Min': 0.0,
            'Packet Length Max': 50.0,
            'Packet Length Mean': 25.0,
            'Packet Length Std': 10.0,
            'Packet Length Variance': 5.0,
            'FIN Flag Count': 0,
            'SYN Flag Count': 0,
            'RST Flag Count': 0,
            'PSH Flag Count': 0,
            'ACK Flag Count': 0,
            'URG Flag Count': 0,
            'CWR Flag Count': 0,
            'ECE Flag Count': 0,
            'Down/Up Ratio': 1.0,
            'Average Packet Size': 25.0,
            'Fwd Segment Size Avg': 20.0,
            'Bwd Segment Size Avg': 20.0,
            'Fwd Bytes/Bulk Avg': 0.0,
            'Fwd Packet/Bulk Avg': 0.0,
            'Fwd Bulk Rate Avg': 0.0,
            'Bwd Bytes/Bulk Avg': 0.0,
            'Bwd Packet/Bulk Avg': 0.0,
            'Bwd Bulk Rate Avg': 0.0,
            'Subflow Fwd Packets': 1,
            'Subflow Fwd Bytes': 100,
            'Subflow Bwd Packets': 1,
            'Subflow Bwd Bytes': 100,
            'FWD Init Win Bytes': 0,
            'Bwd Init Win Bytes': 0,
            'Fwd Act Data Pkts': 0,
            'Fwd Seg Size Min': 0,
            'Active Mean': 0.0,
            'Active Std': 0.0,
            'Active Max': 0.0,
            'Active Min': 0.0,
            'Idle Mean': 0.0,
            'Idle Std': 0.0,
            'Idle Max': 0.0,
            'Idle Min': 0.0
        }
        predict_url = "http://localhost:8000/predict"
        r = requests.post(predict_url, json=features)
        assert r.status_code == 200 or r.status_code == 503
        if r.status_code == 200:
            assert "prediction" in r.json()
        elif r.status_code == 503:
            assert "Model not available" in r.json()["detail"]
    finally:
        container.stop()
