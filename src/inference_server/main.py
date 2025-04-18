from fastapi import FastAPI
import mlflow
import pandas as pd

app = FastAPI()

# Carga el modelo registrado desde MLflow
model = mlflow.sklearn.load_model("models:/CICD_IDS_Model_v1/Production")

@app.post("/predict")
def predict(features: dict):
    # Convierte el input a DataFrame con las columnas en el mismo orden que el entrenamiento
    df = pd.DataFrame([features])
    prediction = model.predict(df)
    return {"prediction": prediction.tolist()}
