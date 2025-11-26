import sys
import os
from unittest.mock import MagicMock, patch
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock mlflow before importing main
mock_mlflow = MagicMock()
mock_mlflow.__path__ = [] # Make it look like a package
sys.modules['mlflow'] = mock_mlflow
sys.modules['mlflow.sklearn'] = MagicMock()
sys.modules['mlflow.exceptions'] = MagicMock()

# Import app and model_manager after mocking
from inference_server.main import app, model_manager
from fastapi.testclient import TestClient

client = TestClient(app)

def test_prediction_logic():
    print("Starting verification of prediction logic...")
    
    # Setup mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([0])
    # Define a subset of features for testing
    test_features = ["Flow Duration", "Total Fwd Packet"]
    
    # Manually initialize model manager with mock
    model_manager.model = mock_model
    model_manager.features = test_features
    model_manager.initialized = True
    
    # Request data
    # "flow_duration" maps to "Flow Duration"
    # "tot_fwd_pkts" maps to "Total Fwd Packet"
    payload = {
        "flow_duration": 100,
        "tot_fwd_pkts": 5,
        "ignored_field": 999 
    }
    
    print(f"Sending payload: {payload}")
    response = client.post("/predict", json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200:
        print("FAILED: Status code is not 200")
        sys.exit(1)
        
    if response.json() != {"prediction": [0]}:
        print("FAILED: Unexpected response body")
        sys.exit(1)
    
    # Verify input passed to model.predict
    args, _ = mock_model.predict.call_args
    input_array = args[0]
    print(f"Input Array passed to model: \n{input_array}")
    
    # Expected: [[100, 5]]
    expected = np.array([[100, 5]])
    
    if not np.array_equal(input_array, expected):
        print(f"FAILED: Input array mismatch. Expected \n{expected}")
        sys.exit(1)
        
    print("SUCCESS: Verification passed!")

if __name__ == "__main__":
    test_prediction_logic()
