from fastapi import FastAPI, HTTPException
import pandas as pd
import os
import json
import numpy as np
import logging
from dotenv import load_dotenv

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

@app.get("/")
async def root():
    """
    Root endpoint for the inference server.

    :return: A JSON response with a message indicating that the inference server is running.
    """
    logger.info("Root endpoint called.")
    return {"message": "Inference server is running."}

@app.get("/health")
async def health():
    """
    Health check endpoint for the inference server.

    :return: A JSON response with two keys: "status" with value "healthy", and "model_initialized" with a boolean value indicating whether the model has been initialized.
    """
    return {"status": "healthy", "model_initialized": model_manager.initialized}

import mlflow
from mlflow.exceptions import MlflowException

class ModelManager:
    def __init__(self):
        """
        Initializes the ModelManager.

        Sets the model, features, and initialized attributes to None or False, respectively.
        """
        self.model = None
        self.features = None
        self.initialized = False
    
    def load_model(self):
        """
        Loads the ML model from MLflow.

        If the model has already been loaded, this method does nothing.
        Otherwise, it sets the MLflow tracking URI and model name from environment variables,
        loads the model, and extracts the feature names from the model.

        If the model cannot be loaded, this method logs an error and raises an HTTPException
        with status code 503 and a detail message indicating that the model is not available.
        """
        if self.initialized:
            return
        
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
        if not tracking_uri:
            raise HTTPException(status_code=503, detail="MLFLOW_TRACKING_URI environment variable is required")
        mlflow.set_tracking_uri(tracking_uri)
        model_name = os.environ.get("MLFLOW_MODEL_NAME", "models:/ML_IDS_Model_v1/Production")
        
        try:
            self.model = mlflow.sklearn.load_model(model_name)
            self.features = self.model.feature_names_in_
            self.initialized = True
            logger.info("Model loaded successfully.")
        except (MlflowException, AttributeError) as e:
            logger.error(f"Model not available: {e}")
            raise HTTPException(status_code=503, detail=f"Model not available: {e}")

model_manager = ModelManager()

# Load feature mapping from JSON file
try:
    with open(os.path.join(os.path.dirname(__file__), "feature_mapping.json")) as f:
        FEATURE_MAPPING = json.load(f)
except Exception as e:
    logger.error(f"Failed to load feature mapping: {e}")
    # Fallback or exit? For now, let's raise to fail fast as this is critical
    raise RuntimeError(f"Failed to load feature mapping: {e}")

@app.post("/predict")
def predict(features: dict):
    """
    Make a prediction with the model.
    """
    logger.info(f"Predict endpoint called with {len(features)} features")
    if not features:
        raise HTTPException(status_code=422, detail="No features provided")
    
    if not model_manager.initialized:
        model_manager.load_model()
    
    try:
        # Map features and fill missing ones with 0
        mapped_features = {FEATURE_MAPPING.get(k, k): v for k, v in features.items()}
        
        # Create input vector based on model features, defaulting to 0 for missing or None values
        input_vector = [mapped_features.get(feat, 0) or 0 for feat in model_manager.features]
        
        # Reshape for single sample
        input_array = np.array(input_vector).reshape(1, -1)
        
        prediction = model_manager.model.predict(input_array)
        
        # Log predictions with error handling
        try:
            log_dir = os.environ.get("LOG_DIR", "/app/logs")
            os.makedirs(log_dir, exist_ok=True)
            
            if prediction[0] != 0:
                log_file = os.path.join(log_dir, "positive_predictions.log")
                with open(log_file, "a") as f:
                    f.write(f"Timestamp: {pd.Timestamp.now()}, Prediction: {prediction[0]}\n")
            
            # Log negative predictions if enabled
            log_negative = os.environ.get("LOG_NEGATIVE_PREDICTIONS", "false").lower() == "true"
            if prediction[0] == 0 and log_negative:
                log_file = os.path.join(log_dir, "negative_predictions.log")
                with open(log_file, "a") as f:
                    f.write(f"Timestamp: {pd.Timestamp.now()}, Prediction: {prediction[0]}\n")
        except IOError as e:
            logger.warning(f"Failed to write prediction log: {e}")
        
        return {"prediction": prediction.tolist()}
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


try:
    model_manager.load_model()
except Exception as e:
    logger.warning(f"Model not available at startup: {e}")
