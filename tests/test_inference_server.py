from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pytest
import sys
import os

# Add src to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock MLflow before importing main
with patch('mlflow.set_tracking_uri'), \
     patch('mlflow.sklearn.load_model') as mock_load_model:
    
    # Setup mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = [0]
    mock_model.feature_names_in_ = ['Flow Duration', 'Total Fwd Packet'] # Minimal set for testing
    mock_load_model.return_value = mock_model
    
    from src.inference_server.main import app, model_manager

client = TestClient(app)

import numpy as np

@pytest.fixture(autouse=True)
def mock_mlflow_setup(tmp_path):
    """
    Fixture to mock MLflow for all tests.
    """
    # Set environment variables required by ModelManager
    os.environ["MLFLOW_TRACKING_URI"] = "http://mock-mlflow"
    os.environ["LOG_DIR"] = str(tmp_path / "logs")
    
    with patch('mlflow.set_tracking_uri'), \
         patch('mlflow.sklearn.load_model') as mock_load_model:
        
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])
        # Mock features to match what the ModelManager expects (usually all of them, but we can mock a subset for unit tests)
        # In main.py, it iterates over model_manager.features. Let's give it a few known ones.
        mock_model.feature_names_in_ = ['Flow Duration', 'Total Fwd Packet']
        mock_load_model.return_value = mock_model
        
        # Reset model manager state
        model_manager.initialized = False
        model_manager.model = None
        model_manager.features = None
        
        yield mock_load_model
    
    # Cleanup
    if "MLFLOW_TRACKING_URI" in os.environ:
        del os.environ["MLFLOW_TRACKING_URI"]
    if "LOG_DIR" in os.environ:
        del os.environ["LOG_DIR"]

def test_predict_valid():
    """
    Simulates a valid request and checks that the server responds correctly.
    """
    features = {
        'flow_duration': 1000.0,
        'tot_fwd_pkts': 2.0,
        # Add other fields as needed, Pydantic will fill defaults for missing ones
    }
    
    # We need to mock the model loading inside the request if it's not initialized
    with patch('mlflow.sklearn.load_model') as mock_load:
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])
        mock_model.feature_names_in_ = ['Flow Duration', 'Total Fwd Packet']
        mock_load.return_value = mock_model
        
        response = client.post("/predict", json=features)
        
        assert response.status_code == 200
        assert "prediction" in response.json()
        assert response.json()["prediction"] == [0]

def test_predict_unprocessable():
    """
    Simulates a request with invalid data types and checks for 422 Unprocessable Entity.
    """
    # Sending string where float is expected
    features = {
        'flow_duration': "invalid_string"
    }
    response = client.post("/predict", json=features)
    assert response.status_code == 422

def test_predict_empty_body():
    """
    Simulates a request with no body.
    """
    response = client.post("/predict")
    assert response.status_code == 422

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    # Health endpoint now returns database status
    # Status will be "degraded" when database is not available (which is expected in tests)
    assert response.json()["status"] in ["healthy", "degraded"]
    assert "model_initialized" in response.json()
    assert "database" in response.json()


