import pytest
import pandas as pd
import numpy as np
import mlflow
import os
from unittest.mock import Mock, patch, MagicMock
from sklearn.pipeline import Pipeline
from src.model_trainer import ModelTrainer

@pytest.fixture
def sample_data():
    """Create sample data for testing"""
    X = pd.DataFrame({
        'feature1': np.random.random(100),
        'feature2': np.random.random(100),
        'feature3': np.random.random(100)
    })
    y = pd.Series(np.random.randint(0, 10, 100))
    return X, y

@pytest.fixture
def mock_mlflow():
    """Mock MLflow functionality"""
    with patch('mlflow.set_tracking_uri') as mock_uri, \
         patch('mlflow.set_experiment') as mock_exp, \
         patch('mlflow.start_run') as mock_run, \
         patch('mlflow.log_params') as mock_params, \
         patch('mlflow.log_metric') as mock_metric, \
         patch('mlflow.log_text') as mock_text, \
         patch('mlflow.sklearn.log_model') as mock_model:
        
        mock_run.return_value.__enter__.return_value = MagicMock(
            info=MagicMock(run_id='test_run_id')
        )
        
        yield {
            'uri': mock_uri,
            'exp': mock_exp,
            'run': mock_run,
            'params': mock_params,
            'metric': mock_metric,
            'text': mock_text,
            'model': mock_model
        }

@pytest.fixture
def trainer(mock_mlflow):
    """Create ModelTrainer instance with mocked MLflow"""
    return ModelTrainer(mlflow_uri="mock://test")

def test_init(mock_mlflow):
    """Test ModelTrainer initialization"""
    trainer = ModelTrainer(mlflow_uri="mock://test")
    
    assert trainer.mlflow_uri == "mock://test"
    assert trainer.experiment_name == "CICD_IDS_Model_v1"
    assert trainer.model_path == "model.pkl"
    
    mock_mlflow['uri'].assert_called_once_with("mock://test")
    mock_mlflow['exp'].assert_called_once_with("CICD_IDS_Model_v1")

def test_load_nonexistent_model(trainer):
    """Test loading a model that doesn't exist"""
    assert trainer.pipeline is None

@patch('joblib.load')
def test_load_existing_model(mock_joblib, mock_mlflow):
    """Test loading an existing model"""
    # Create a dummy model file
    mock_pipeline = Mock(spec=Pipeline)
    mock_joblib.return_value = mock_pipeline
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        trainer = ModelTrainer(mlflow_uri="mock://test")
        
        assert trainer.pipeline is not None
        mock_joblib.assert_called_once_with("model.pkl")

def test_train(trainer, sample_data, mock_mlflow):
    """Test model training process"""
    X, y = sample_data
    
    with patch('joblib.dump') as mock_dump:
        result = trainer.train(X, y)
        
        assert isinstance(result, dict)
        assert "accuracy" in result
        assert "run_id" in result
        assert result["run_id"] == "test_run_id"
        assert result["mlflow_uri"] == "mock://test"
        
        # Verify MLflow interactions
        mock_mlflow['params'].assert_called_once()
        mock_mlflow['metric'].assert_called_once()
        mock_mlflow['text'].assert_called_once()
        mock_mlflow['model'].assert_called_once()
        
        # Verify model was saved locally
        mock_dump.assert_called_once()

def test_train_error_handling(trainer):
    """Test error handling during training"""
    with pytest.raises(Exception):
        trainer.train(None, None)

@pytest.mark.integration
def test_full_training_pipeline(trainer, sample_data):
    """Integration test for full training pipeline"""
    X, y = sample_data
    
    result = trainer.train(X, y)
    
    assert isinstance(result, dict)
    assert 0 <= result["accuracy"] <= 1
    assert os.path.exists(trainer.model_path)

def test_class_weights_configuration(trainer, sample_data):
    """Test the class weights configuration in the model"""
    X, y = sample_data
    
    with patch('sklearn.ensemble.RandomForestClassifier') as mock_rf:
        trainer.train(X, y)
        
        # Verify class weights were set correctly
        call_kwargs = mock_rf.call_args[1]
        assert 'class_weight' in call_kwargs
        assert call_kwargs['class_weight'] == {
            0:1, 1:1, 2:1, 3:1, 4:4, 5:5, 6:1, 7:1, 8:1, 9:1
        }

def test_logging_configuration(caplog):
    """Test that logging is configured correctly"""
    with caplog.at_level(logging.INFO):
        trainer = ModelTrainer(mlflow_uri="mock://test")
        assert "Initializing ModelTrainer" in caplog.text
        
        # Test logging during model operations
        assert "MLflow experiment" in caplog.text
        assert "No existing model found" in caplog.text