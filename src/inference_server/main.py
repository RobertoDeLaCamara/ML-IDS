from fastapi import FastAPI, HTTPException
import pandas as pd
import os
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
    Health check endpoint to verify if the server is running and if the model is initialized.

    :return: A JSON response indicating the server is healthy and the model initialization status.
    """
    global model_initialized
    logger.info("Health endpoint called. model_initialized=%s", model_initialized)
    return {"status": "healthy", "model_initialized": model_initialized}

def init_model():
    """
    Initialize the model by loading it from MLflow model registry.

    This function is global in scope and should only be called once, as it
    sets the global variables `model` and `model_initialized`.

    If the model is not available, it raises an HTTPException with a 503
    status code.

    :raises: HTTPException
    """
    global model, model_initialized
    import mlflow
    from mlflow.exceptions import MlflowException
    import os
    logger.info("[init_model] Starting model load from MLflow registry...")
    # Load configuration from environment variables
    mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    logger.info(f"[init_model] MLFLOW_TRACKING_URI: {mlflow_tracking_uri}")
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = os.environ.get("MLFLOW_S3_ENDPOINT_URL", "")
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get("AWS_ACCESS_KEY_ID", "")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    logger.info(f"[init_model] MLFLOW_S3_ENDPOINT_URL: {os.environ.get('MLFLOW_S3_ENDPOINT_URL')}")
    logger.info(f"[init_model] AWS_ACCESS_KEY_ID: {os.environ.get('AWS_ACCESS_KEY_ID')}")
    logger.info(f"[init_model] AWS_SECRET_ACCESS_KEY: {'***' if os.environ.get('AWS_SECRET_ACCESS_KEY') else ''}")
    try:
        logger.info("[init_model] Loading model 'models:/ML_IDS_Model_v1/Production' from MLflow...")
        model = mlflow.sklearn.load_model("models:/ML_IDS_Model_v1/Production")
        model_initialized = True
        logger.info("[init_model] Model loaded successfully.")
    except MlflowException as e:
        model = None
        model_initialized = False
        logger.error(f"[init_model] Model not available: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Model not available: {str(e)}")

@app.post("/predict")
def predict(features: dict):
    """
    Make a prediction with the model.

    This function will be called for every inference request. It is
    responsible for loading the model (if it has not been loaded before)
    and running the prediction.

    :param features: The input features as a dictionary.
    :return: The prediction as a dictionary containing a single key
             "prediction" with a value of a list of predicted classes.
    :raises: HTTPException if the model is not available.
    """
    logger.info("Predict endpoint called with features: %s", features)
    global model_initialized, model
    if not features or not isinstance(features, dict):
        logger.error("Prediction failed: No features provided.")
        raise HTTPException(status_code=422, detail="No features provided for prediction.")
    if not model_initialized:
        logger.warning("Model not initialized. Attempting to initialize.")
        try:
            init_model()
        except HTTPException as e:
            logger.error("Model initialization failed: %s", e.detail)
            raise e
    if model is None:
        logger.error("Prediction failed: Model not available.")
        raise HTTPException(status_code=503, detail="Model not available.")
    df = pd.DataFrame([features])
    if df.empty or df.shape[1] == 0:
        logger.error("Prediction failed: Features DataFrame is empty or has no columns.")
        raise HTTPException(status_code=400, detail="Invalid or empty features for prediction.")
    prediction = model.predict(df)
    logger.info("Prediction result: %s", prediction.tolist())
    return {"prediction": prediction.tolist()}


model_initialized = False
# Attempt to initialize the model when the server starts
try:
    init_model()
except Exception as e:
    logger.warning("Model not available at startup: %s", str(e))
    pass
