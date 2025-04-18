from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/retrain")
def retrain():
    """
    Fake retrain endpoint. Does nothing for now.
    """
    return JSONResponse(content={"detail": "retraining not implemented yet"}, status_code=200)
