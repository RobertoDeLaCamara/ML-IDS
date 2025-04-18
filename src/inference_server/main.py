from fastapi import FastAPI, HTTPException
import pandas as pd
import os

app = FastAPI()

model_initialized = False


def init_model():
    global model, model_initialized
    import mlflow
    from mlflow.exceptions import MlflowException
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://192.168.1.189:9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "roberto"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "patilla1"
    try:
        model = mlflow.sklearn.load_model("models:/CICD_IDS_Model_v1/Production")
        model_initialized = True
    except MlflowException as e:
        model = None
        model_initialized = False
        raise HTTPException(status_code=503, detail=f"Model not available: {str(e)}")

@app.post("/predict")
def predict(features: dict):
    global model_initialized, model
    if not model_initialized:
        try:
            init_model()
        except HTTPException as e:
            raise e
    if model is None:
        raise HTTPException(status_code=503, detail="Model not available.")
    df = pd.DataFrame([features])
    prediction = model.predict(df)
    return {"prediction": prediction.tolist()}
