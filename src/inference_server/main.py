from fastapi import FastAPI
import mlflow
import pandas as pd
import os

app = FastAPI()

def init_model():
    """
    Initializes the machine learning model by setting the necessary
    environment variables for MLflow S3 endpoint and AWS credentials.
    Loads the registered model 'CICD_IDS_Model_v1' in production stage
    from MLflow Model Registry and assigns it to a global variable.
    """

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://192.168.1.189:9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "roberto"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "patilla1"
    global model
    model = mlflow.sklearn.load_model("models:/CICD_IDS_Model_v1/Production")

init_model()

@app.post("/predict")
def predict(features: dict):
    """
    Receives a dictionary of features, converts it into a DataFrame,
    and returns a prediction from the pre-loaded machine learning model.

    Parameters:
    features (dict): A dictionary containing feature names as keys and 
                     their corresponding values as values.

    Returns:
    dict: A dictionary containing the prediction result in a list form.
    """

    df = pd.DataFrame([features])
    prediction = model.predict(df)
    return {"prediction": prediction.tolist()}
