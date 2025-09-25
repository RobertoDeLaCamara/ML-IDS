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
        
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI"))
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

FEATURE_MAPPING = {
    "flow_duration": "Flow Duration", "tot_fwd_pkts": "Total Fwd Packet", "tot_bwd_pkts": "Total Bwd packets",
    "totlen_fwd_pkts": "Total Length of Fwd Packet", "totlen_bwd_pkts": "Total Length of Bwd Packet",
    "fwd_pkt_len_max": "Fwd Packet Length Max", "fwd_pkt_len_min": "Fwd Packet Length Min",
    "fwd_pkt_len_mean": "Fwd Packet Length Mean", "fwd_pkt_len_std": "Fwd Packet Length Std",
    "bwd_pkt_len_max": "Bwd Packet Length Max", "bwd_pkt_len_min": "Bwd Packet Length Min",
    "bwd_pkt_len_mean": "Bwd Packet Length Mean", "bwd_pkt_len_std": "Bwd Packet Length Std",
    "flow_byts_s": "Flow Bytes/s", "flow_pkts_s": "Flow Packets/s", "flow_iat_mean": "Flow IAT Mean",
    "flow_iat_std": "Flow IAT Std", "flow_iat_max": "Flow IAT Max", "flow_iat_min": "Flow IAT Min",
    "fwd_iat_tot": "Fwd IAT Total", "fwd_iat_mean": "Fwd IAT Mean", "fwd_iat_std": "Fwd IAT Std",
    "fwd_iat_max": "Fwd IAT Max", "fwd_iat_min": "Fwd IAT Min", "bwd_iat_tot": "Bwd IAT Total",
    "bwd_iat_mean": "Bwd IAT Mean", "bwd_iat_std": "Bwd IAT Std", "bwd_iat_max": "Bwd IAT Max",
    "bwd_iat_min": "Bwd IAT Min", "fwd_psh_flags": "Fwd PSH Flags", "bwd_psh_flags": "Bwd PSH Flags",
    "fwd_urg_flags": "Fwd URG Flags", "bwd_urg_flags": "Bwd URG Flags", "fwd_header_len": "Fwd Header Length",
    "bwd_header_len": "Bwd Header Length", "fwd_pkts_s": "Fwd Packets/s", "bwd_pkts_s": "Bwd Packets/s",
    "pkt_len_min": "Packet Length Min", "pkt_len_max": "Packet Length Max", "pkt_len_mean": "Packet Length Mean",
    "pkt_len_std": "Packet Length Std", "pkt_len_var": "Packet Length Variance", "fin_flag_cnt": "FIN Flag Count",
    "syn_flag_cnt": "SYN Flag Count", "rst_flag_cnt": "RST Flag Count", "psh_flag_cnt": "PSH Flag Count",
    "ack_flag_cnt": "ACK Flag Count", "urg_flag_cnt": "URG Flag Count", "cwr_flag_count": "CWR Flag Count",
    "ece_flag_cnt": "ECE Flag Count", "down_up_ratio": "Down/Up Ratio", "pkt_size_avg": "Average Packet Size",
    "fwd_seg_size_avg": "Fwd Segment Size Avg", "bwd_seg_size_avg": "Bwd Segment Size Avg",
    "fwd_byts_b_avg": "Fwd Bytes/Bulk Avg", "fwd_pkts_b_avg": "Fwd Packet/Bulk Avg",
    "fwd_blk_rate_avg": "Fwd Bulk Rate Avg", "bwd_byts_b_avg": "Bwd Bytes/Bulk Avg",
    "bwd_pkts_b_avg": "Bwd Packet/Bulk Avg", "bwd_blk_rate_avg": "Bwd Bulk Rate Avg",
    "subflow_fwd_pkts": "Subflow Fwd Packets", "subflow_fwd_byts": "Subflow Fwd Bytes",
    "subflow_bwd_pkts": "Subflow Bwd Packets", "subflow_bwd_byts": "Subflow Bwd Bytes",
    "init_fwd_win_byts": "FWD Init Win Bytes", "init_bwd_win_byts": "Bwd Init Win Bytes",
    "fwd_act_data_pkts": "Fwd Act Data Pkts", "fwd_seg_size_min": "Fwd Seg Size Min",
    "active_mean": "Active Mean", "active_std": "Active Std", "active_max": "Active Max",
    "active_min": "Active Min", "idle_mean": "Idle Mean", "idle_std": "Idle Std",
    "idle_max": "Idle Max", "idle_min": "Idle Min"
}

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
    if not features:
        raise HTTPException(status_code=422, detail="No features provided")
    
    if not model_manager.initialized:
        model_manager.load_model()
    
    mapped_features = {FEATURE_MAPPING[k]: v for k, v in features.items() if k in FEATURE_MAPPING}
    df = pd.DataFrame([mapped_features]).reindex(columns=model_manager.features)
    prediction = model_manager.model.predict(df)

    # Log predictions
    log_dir = os.environ.get("LOG_DIR", "/app/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    if prediction[0] != 0:
        log_file = os.path.join(log_dir, "positive_predictions.log")
        with open(log_file, "a") as f:
            f.write(f"Timestamp: {pd.Timestamp.now()}, Prediction: {prediction[0]}, Features: {features}\n")
    
    # Log negative predictions if enabled
    log_negative = os.environ.get("LOG_NEGATIVE_PREDICTIONS", "false").lower() == "true"
    if prediction[0] == 0 and log_negative:
        log_file = os.path.join(log_dir, "negative_predictions.log")
        with open(log_file, "a") as f:
            f.write(f"Timestamp: {pd.Timestamp.now()}, Prediction: {prediction[0]}, Features: {features}\n")

    return {"prediction": prediction.tolist()}


try:
    model_manager.load_model()
except Exception as e:
    logger.warning(f"Model not available at startup: {e}")
