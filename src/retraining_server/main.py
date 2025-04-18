from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

@app.post("/retrain")
def retrain():
    """
    Fake retrain endpoint. Does nothing for now.
    """
    logger.info("Retrain endpoint called. Not implemented yet.")
    return JSONResponse(content={"detail": "retraining not implemented yet"}, status_code=200)
