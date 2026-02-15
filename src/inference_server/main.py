import time as _time

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
from .auth import APIKeyMiddleware
from .metrics import metrics_response, PREDICTIONS_TOTAL, PREDICTION_LATENCY, MODEL_LOADED
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

app.add_middleware(APIKeyMiddleware)



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

@app.get("/metrics", include_in_schema=False)
async def get_metrics():
    """Prometheus metrics endpoint."""
    return metrics_response()


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
        "model_source": model_manager.model_source,
        "model_loaded_at": model_manager.model_loaded_at,
        "database": db_status
    }

import joblib
import mlflow
from mlflow.exceptions import MlflowException
from datetime import datetime as _dt

class ModelManager:
    MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/app/model_cache")
    LOCAL_MODEL_PATH = os.path.join(MODEL_CACHE_DIR, "model.joblib")
    LOCAL_META_PATH = os.path.join(MODEL_CACHE_DIR, "model_meta.json")

    def __init__(self):
        self.model = None
        self.features = None
        self.initialized = False
        self.model_source: str = "none"
        self.model_loaded_at: str | None = None

    def _save_to_cache(self):
        """Persist the current model and metadata to local disk."""
        try:
            os.makedirs(self.MODEL_CACHE_DIR, exist_ok=True)
            joblib.dump(self.model, self.LOCAL_MODEL_PATH)
            meta = {
                "features": list(self.features),
                "timestamp": _dt.utcnow().isoformat(),
                "source": "mlflow",
            }
            with open(self.LOCAL_META_PATH, "w") as f:
                json.dump(meta, f)
            logger.info(f"Model cached locally at {self.MODEL_CACHE_DIR}")
        except Exception as e:
            logger.warning(f"Failed to cache model locally: {e}")

    def _load_from_cache(self) -> bool:
        """Try loading a locally cached model. Returns True on success."""
        try:
            if not os.path.exists(self.LOCAL_MODEL_PATH) or not os.path.exists(self.LOCAL_META_PATH):
                return False
            self.model = joblib.load(self.LOCAL_MODEL_PATH)
            with open(self.LOCAL_META_PATH) as f:
                meta = json.load(f)
            self.features = meta["features"]
            self.model_source = "cache"
            self.model_loaded_at = _dt.utcnow().isoformat()
            self.initialized = True
            MODEL_LOADED.set(1)
            logger.info("Model loaded from local cache")
            return True
        except Exception as e:
            logger.error(f"Failed to load model from cache: {e}")
            return False

    def load_model(self):
        """Load the ML model from MLflow, falling back to local cache."""
        if self.initialized:
            return

        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
        model_name = os.environ.get("MLFLOW_MODEL_NAME", "models:/ML_IDS_Model_v1/Production")

        # Try MLflow first
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
            try:
                self.model = mlflow.sklearn.load_model(model_name)
                self.features = self.model.feature_names_in_
                self.initialized = True
                self.model_source = "mlflow"
                self.model_loaded_at = _dt.utcnow().isoformat()
                logger.info("Model loaded successfully from MLflow.")
                MODEL_LOADED.set(1)
                self._save_to_cache()
                return
            except (MlflowException, AttributeError, Exception) as e:
                logger.warning(f"MLflow model load failed: {e}. Trying local cache...")

        # Fallback to local cache
        if self._load_from_cache():
            return

        raise HTTPException(status_code=503, detail="Model not available: MLflow unreachable and no local cache")

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
        
        # Create input DataFrame with feature names to avoid warning
        input_df = pd.DataFrame([input_vector], columns=model_manager.features)

        _pred_start = _time.monotonic()
        prediction = model_manager.model.predict(input_df)
        PREDICTION_LATENCY.observe(_time.monotonic() - _pred_start)

        # Record prediction result
        pred_label = "attack" if prediction[0] != 0 else "benign"
        PREDICTIONS_TOTAL.labels(result=pred_label).inc()
        
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
        
        result = {"prediction": prediction.tolist()}
        if hasattr(features, '_validation_warnings') and features._validation_warnings:
            result["validation_warnings"] = features._validation_warnings
        return result
        
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
