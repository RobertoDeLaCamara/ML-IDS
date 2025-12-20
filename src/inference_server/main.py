from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import os
import json
import numpy as np
import logging
from dotenv import load_dotenv

from .schemas import PredictionRequest
from .database import init_db, close_db, health_check as db_health_check, is_db_available, get_db
from .alert_service import alert_service
from .routers import alerts, incidents, dashboard
from sqlalchemy.ext.asyncio import AsyncSession
import yaml

# FastAPI app with OpenAPI configuration
app = FastAPI(
    title="ML-IDS Inference Server API",
    version="1.0.0-phase1",
    description="""
    Machine Learning-based Intrusion Detection System API
    
    **Phase 1 Features:**
    - Real-time network traffic prediction
    - Automatic alert creation and management
    - Incident tracking and investigation
    - Real-time dashboard with WebSocket updates
    - Multi-channel notifications (Email, Slack, Webhooks)
    
    **Documentation:**
    - Interactive API docs: `/docs` (Swagger UI)
    - Alternative docs: `/redoc` (ReDoc)
    - OpenAPI JSON spec: `/openapi.json`
    - OpenAPI YAML spec: `/openapi.yaml`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)





logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Include routers
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)

# Mount static files for dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="dashboard")
    logger.info("Dashboard static files mounted at /dashboard")

@app.get("/")
async def root():
    """
    Root endpoint for the inference server.

    :return: A JSON response with a message indicating that the inference server is running.
    """
    logger.info("Root endpoint called.")
    return {"message": "Inference server is running."}

@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml():
    """
    Serve the OpenAPI specification as YAML file.
    
    Returns the openapi.yaml file for API documentation.
    """
    openapi_file = os.path.join(os.path.dirname(__file__), "openapi.yaml")
    if os.path.exists(openapi_file):
        return FileResponse(
            openapi_file,
            media_type="application/x-yaml",
            filename="openapi.yaml"
        )
    else:
        raise HTTPException(status_code=404, detail="OpenAPI YAML file not found")


@app.get("/health")
async def health():
    """
    Health check endpoint for the inference server.

    :return: A JSON response with status, model availability, and database health.
    """
    db_status = await db_health_check()
    
    overall_status = "healthy"
    if db_status.get("database") == "unavailable":
        overall_status = "degraded"  # Service works without DB
    elif db_status.get("database") == "unhealthy":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "model_initialized": model_manager.initialized,
        "database": db_status
    }

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
async def predict(features: PredictionRequest, db: AsyncSession = Depends(get_db)):
    """
    Make a prediction with the model.
    """
    # Convert Pydantic model to dict, using aliases (snake_case)
    features_dict = features.model_dump(by_alias=True)
    logger.info(f"Predict endpoint called with {len(features_dict)} features")
    
    if not model_manager.initialized:
        model_manager.load_model()
    
    try:
        # Map features and fill missing ones with 0
        mapped_features = {FEATURE_MAPPING.get(k, k): v for k, v in features_dict.items()}
        
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
                # Log attack to database and file
                attack_type = str(prediction[0])
                src_ip = features.src_ip or "unknown"

                # Create alert in database
                if db is not None:
                    try:
                        await alert_service.create_alert(
                            db=db,
                            attack_type=attack_type,
                            src_ip=src_ip,
                            features=features_dict,
                            prediction_score=None  # Can add confidence from model if available
                        )
                    except Exception as e:
                        logger.warning(f"Failed to create alert in database: {e}")

                # Log to file
                log_file = os.path.join(log_dir, "positive_predictions.log")
                with open(log_file, "a") as f:
                    f.write(f"Timestamp: {pd.Timestamp.now()}, Prediction: {prediction[0]}, SrcIP: {features.src_ip}\n")
            
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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize database
    logger.info("Initializing database...")
    db_success = await init_db()
    
    if db_success:
        logger.info("Database initialized successfully")
    else:
        logger.warning("Database initialization failed, running with limited functionality")
    
    # Load ML model
    try:
        model_manager.load_model()
    except Exception as e:
        logger.warning(f"Model not available at startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    await close_db()
