import logging
from logging.handlers import RotatingFileHandler
import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import pandas as pd
import io
from model_trainer import ModelTrainer

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create handlers
file_handler = RotatingFileHandler(
    'logs/train_server.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = FastAPI()
logger.info("Initializing FastAPI application")

try:
    model_trainer = ModelTrainer()
    logger.info("ModelTrainer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ModelTrainer: {str(e)}", exc_info=True)
    raise

async def load_csv(file: UploadFile):
    try:
        logger.info(f"Loading CSV file: {file.filename}")
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        logger.info(f"Successfully loaded CSV with shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading CSV file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error loading CSV file: {str(e)}")

@app.post("/train")
async def train_endpoint(data_file: UploadFile = File(...), label_file: UploadFile = File(...)):
    logger.info("Received training request")
    
    try:
        logger.info(f"Processing data file: {data_file.filename}")
        data = await load_csv(data_file)
        
        logger.info(f"Processing label file: {label_file.filename}")
        labels = await load_csv(label_file)
        
        logger.info("Starting model training")
        result = model_trainer.train(data, labels['Label'])
        
        logger.info(f"Training completed successfully. Accuracy: {result.get('accuracy', 'N/A')}")
        return result
        
    except Exception as e:
        error_msg = f"Error during training process: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
def health_check():
    logger.debug("Health check requested")
    return {"status": "running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up train server")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down train server")