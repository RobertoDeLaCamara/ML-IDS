import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, UploadFile
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import io
import sys
from src.train_server import app,load_csv
import os

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def real_csv_files():
    """Load actual Data.csv and Label.csv files from repository"""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(repo_root, 'data', 'Data.csv')
    label_path = os.path.join(repo_root, 'data', 'Label.csv')
    
    # Verify files exist
    assert os.path.exists(data_path), f"Data file not found at {data_path}"
    assert os.path.exists(label_path), f"Label file not found at {label_path}"
    
    # Read files as bytes
    with open(data_path, 'rb') as data_file, open(label_path, 'rb') as label_file:
        return {
            'data': ('Data.csv', data_file.read(), 'text/csv'),
            'labels': ('Label.csv', label_file.read(), 'text/csv')
        }

@pytest.mark.integration
def test_train_with_real_data(test_client, real_csv_files):
    """Integration test using actual Data.csv and Label.csv files"""
    response = test_client.post(
        "/train",
        files={
            'data_file': real_csv_files['data'],
            'label_file': real_csv_files['labels']
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    
    # Verify response structure
    assert 'accuracy' in result
    assert 'mlflow_uri' in result
    assert 'run_id' in result
    
    # Verify accuracy is within reasonable range
    assert 0 <= result['accuracy'] <= 1
    
    # Verify MLflow tracking
    assert result['mlflow_uri'].startswith('http://')
    assert result['run_id'] is not None


@pytest.fixture
def mock_model_trainer():
    """Mock ModelTrainer for testing"""
    with patch('train_server.ModelTrainer') as mock:
        trainer_instance = Mock()
        trainer_instance.train.return_value = {
            "accuracy": 0.95,
            "mlflow_uri": "mock://test",
            "run_id": "test_run"
        }
        mock.return_value = trainer_instance
        yield trainer_instance

@pytest.fixture
def sample_csv_files():
    """Create sample CSV files for testing"""
    # Create sample data
    data = pd.DataFrame({
        'feature1': np.random.random(10),
        'feature2': np.random.random(10)
    })
    labels = pd.DataFrame({'Label': np.random.randint(0, 2, 10)})
    
    # Convert to CSV bytes
    data_bytes = io.BytesIO()
    data.to_csv(data_bytes, index=False)
    data_bytes.seek(0)
    
    labels_bytes = io.BytesIO()
    labels.to_csv(labels_bytes, index=False)
    labels_bytes.seek(0)
    
    return {
        'data': ('data.csv', data_bytes, 'text/csv'),
        'labels': ('labels.csv', labels_bytes, 'text/csv')
    }

def test_health_check(test_client):
    """Test the health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

def test_train_endpoint_success(test_client, mock_model_trainer, sample_csv_files):
    """Test successful training request"""
    response = test_client.post(
        "/train",
        files={
            'data_file': sample_csv_files['data'],
            'label_file': sample_csv_files['labels']
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {
        "accuracy": 0.95,
        "mlflow_uri": "mock://test",
        "run_id": "test_run"
    }
    mock_model_trainer.train.assert_called_once()

def test_train_endpoint_invalid_csv(test_client, mock_model_trainer):
    """Test training with invalid CSV file"""
    invalid_file = ('invalid.csv', b'invalid,csv,content', 'text/csv')
    
    response = test_client.post(
        "/train",
        files={
            'data_file': invalid_file,
            'label_file': invalid_file
        }
    )
    
    assert response.status_code == 400
    assert "Error loading CSV file" in response.json()['detail']

def test_train_endpoint_missing_files(test_client):
    """Test training without required files"""
    response = test_client.post("/train")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_load_csv_success(sample_csv_files):
    """Test successful CSV loading"""
    from fastapi import UploadFile
    
    # Create UploadFile mock
    file_mock = Mock(spec=UploadFile)
    file_mock.filename = "test.csv"
    file_mock.read = AsyncMock(return_value=sample_csv_files['data'][1].getvalue())
    
    result = await load_csv(file_mock)
    assert isinstance(result, pd.DataFrame)
    assert not result.empty

@pytest.mark.asyncio
async def test_load_csv_failure():
    """Test CSV loading failure"""
    from fastapi import UploadFile
    
    file_mock = Mock(spec=UploadFile)
    file_mock.filename = "test.csv"
    file_mock.read = AsyncMock(side_effect=Exception("Read error"))
    
    with pytest.raises(HTTPException) as exc_info:
        await load_csv(file_mock)
    
    assert exc_info.value.status_code == 400
    assert "Error loading CSV file" in str(exc_info.value.detail)

class AsyncMock(MagicMock):
    """Helper class for mocking async functions"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)