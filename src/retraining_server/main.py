from fastapi import FastAPI
import subprocess
import os

app = FastAPI()

@app.post("/retrain")
def retrain():
    # Convierte el notebook a script y ejecuta el script generado
    nb_path = os.path.abspath("../../notebooks/model_training.ipynb")
    py_path = os.path.abspath("model_training.py")
    result = subprocess.run([
        "jupyter", "nbconvert", "--to", "script", nb_path, "--output", "model_training"
    ], capture_output=True, text=True)
    script_result = subprocess.run([
        "python", py_path
    ], capture_output=True, text=True)
    return {
        "status": "retraining finished",
        "nbconvert_output": result.stdout,
        "script_output": script_result.stdout
    }
