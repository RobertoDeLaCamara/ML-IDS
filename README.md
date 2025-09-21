# ML-IDS

ML-based Intrusion Detection System

## Purpose

The ML-IDS (Mac- **Description:** The CIC-IDS2017 dataset is a widely used benchmark for intrusion detection research, containing realistic network traffic with labeled attack and benign samples.


---

## Repository Structure

```
ML-IDS/
│
├── Jenkinsfile                  # CI/CD pipeline configuration
├── LICENSE                      # License information
├── README.md                    # Project overview and instructions
├── requirements.txt             # Python dependencies for the root project
│
├── data/
│   └── CIC-IDS2017/
│       ├── Data.csv             # Main dataset with network features
│       ├── Label.csv            # Corresponding labels for classification
│       ├── readme.txt           # Dataset description
│       └── source.txt           # Source information
│
├── notebooks/
│   ├── cic-unsw-nb15_exploratory_analysis.ipynb  # Exploratory analysis notebook
│   ├── feature_engineering.ipynb                 # Feature engineering steps
│   ├── model_selection.ipynb                     # Model selection and comparison
│   └── model_training.ipynb                      # Main model training and evaluation
│   
│
├── src/
│   └── inference_server/
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
│
└── tests/
    ├── __init__.py
    ├── curl_predict_full.sh
    └── test_inference_server.py
```

---


## Documentation Index

- [Inference Server API](src/inference_server/API.md)
- [Inference Server OpenAPI Spec](src/inference_server/openapi.yaml)
- [Model Details](notebooks/MODEL_DETAILS.md)
- [CIC-IDS2017 Dataset Details](data/CIC-IDS2017/DATASET_DETAILS.md)

---

## Datasets Used

### CIC-IDS2017

- **Location:** `data/CIC-IDS2017/`
- **Files:**
  - `Data.csv`: Contains the network traffic features for each sample.
  - `Label.csv`: Contains the corresponding labels (attack types or benign) for each sample.
  - `readme.txt` and `source.txt`: Provide additional context and source information about the dataset.
- **Description:** The CIC-IDS2017 dataset is a widely used benchmark for intrusion detection research, containing realistic network traffic with labeled attack and benign samples.

#### Dataset Usage Conditions
This repository includes the CICIDS2017 dataset provided by the Canadian Institute for Cybersecurity (CIC) of the University of New Brunswick.
The dataset is intended for academic and research purposes only.
Use of the dataset is subject to the terms and conditions of the CIC. Citation of the original source is required when using this data.
Permission for public or commercial redistribution is not guaranteed. It is recommended to review the official conditions at:
https://www.unb.ca/cic/datasets/ids-2017.html

---

## Machine Learning Models

### Model Training and Evaluation

- **Notebooks:** The main workflow is in `notebooks/model_training.ipynb`.
- **Workflow:**
  1. **Data Loading:** Reads features from `Data.csv` and labels from `Label.csv`.
  2. **Train/Test Split:** Splits the data into training and testing sets (80/20 split, stratified).
  3. **Modeling:**
     - **Random Forest Classifier:** Trained with class balancing and custom class weights to address class imbalance, especially for underrepresented classes.
     - **Stacking Classifier:** Combines Random Forest and Logistic Regression as base estimators, with Logistic Regression as the meta-classifier, wrapped in a pipeline with feature scaling.
  4. **Evaluation:**
     - Accuracy, classification report, confusion matrix, and ROC curves for each class.
     - Feature importance analysis (both built-in and permutation-based).
     - Analysis of misclassified samples, especially for critical classes.
  5. **Experiment Tracking:** Uses MLflow for logging metrics, artifacts (classification reports, feature importances), and model versions.
  6. **Model Deployment:** Models are registered and can be loaded for inference using MLflow.

### Model Deployment

- **Inference Server:** Located in `src/inference_server/`, provides an API for model inference.

---

## Testing

- **Location:** `tests/`
- **Files:** Unit and integration tests for inference, as well as a shell script for testing prediction endpoints.

---

## Experiment Tracking

- **MLflow:** All experiments, metrics, and models are tracked and versioned using MLflow.

---

## Summary

This repository provides a full pipeline for developing, evaluating, and deploying machine learning models for network intrusion detection, using real-world datasets and modern ML engineering practices. It is structured for reproducibility, extensibility, and ease of deployment in production environments.

---
