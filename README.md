# ML-IDS

Machine Learning-based Intrusion Detection System

## Purpose

The ML-IDS (Machine Learning-based Intrusion Detection System) is a comprehensive network intrusion detection system that uses machine learning techniques to identify malicious traffic in real-time. The system integrates CICFlowMeter for network flow feature extraction and a machine learning model trained on the CIC-IDS2017 dataset for traffic classification.

### Key Features

- **Real-time Detection**: Continuous network traffic analysis using CICFlowMeter
- **Advanced ML Model**: Uses Random Forest and Stacking Classifier for classification
- **REST API**: Inference server with prediction endpoints
- **Docker Deployment**: Complete system containerization
- **MLflow Integration**: Experiment tracking and model versioning
- **Automatic Feature Extraction**: 78 network flow features extracted automatically


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

## CICFlowMeter Integration

### What is CICFlowMeter?

CICFlowMeter is a tool developed by the Canadian Institute for Cybersecurity (CIC) that extracts network flow features in real-time. It is the standard tool used to generate the CIC-IDS2017 dataset and allows the extraction of 78 statistical features from each network flow.

### Extracted Features

The system automatically extracts the following categories of features:

- **Flow Statistics**: Duration, packet count, total bytes
- **Packet Statistics**: Length, inter-arrival times (IAT)
- **TCP Flags Statistics**: Count of SYN, ACK, FIN, RST flags, etc.
- **Speed Statistics**: Bytes per second, packets per second
- **Subflow Statistics**: Information about bidirectional subflows
- **TCP Window Statistics**: Initial and current window sizes
- **Activity Statistics**: Active and idle connection times

### Workflow

1. **Traffic Capture**: CICFlowMeter captures network packets from the specified interface
2. **Feature Extraction**: 78 statistical features are extracted from each flow
3. **API Submission**: Features are automatically sent to the `/predict` endpoint
4. **Classification**: The ML model classifies the flow as benign or specific attack type
5. **Alert Logging**: Malicious flows are logged for further analysis

### Configuration

The system can be configured through environment variables:

- `CIC_INTERFACE`: Network interface for capture (default: `eth0`)
- `MLFLOW_TRACKING_URI`: MLflow server URI
- `MLFLOW_S3_ENDPOINT_URL`: S3 endpoint for model storage
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: AWS credentials for S3

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

## Deployment

### Prerequisites

- Docker and Docker Compose installed
- Access to an MLflow server with registered model
- Network interface configured for packet capture
- Administrator privileges for network packet capture

### Docker Image Build

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ML-IDS
   ```

2. **Build the image**:
   ```bash
   cd src/inference_server
   docker build -t ml-ids:latest .
   ```

   Or using the command from the project root:
   ```bash
   docker build -f src/inference_server/Dockerfile -t ml-ids:latest .
   ```

### Container Execution

#### Option 1: Basic Execution

```bash
docker run -d \
  --name ml-ids \
  --network host \
  --cap-add=NET_RAW \
  --cap-add=NET_ADMIN \
  -e MLFLOW_TRACKING_URI=http://your-mlflow-server:5000 \
  -e MLFLOW_S3_ENDPOINT_URL=http://your-s3-endpoint:9000 \
  -e AWS_ACCESS_KEY_ID=your-access-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret-key \
  -e CIC_INTERFACE=eth0 \
  -v /var/log/ml-ids:/app/logs \
  ml-ids:latest
```

#### Option 2: Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  ml-ids:
    build:
      context: .
      dockerfile: src/inference_server/Dockerfile
    container_name: ml-ids
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - MLFLOW_TRACKING_URI=http://your-mlflow-server:5000
      - MLFLOW_S3_ENDPOINT_URL=http://your-s3-endpoint:9000
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
      - CIC_INTERFACE=eth0
      - LOG_NEGATIVE_PREDICTIONS=true
    volumes:
      - /var/log/ml-ids:/app/logs
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

### Deployment Verification

1. **Verify container is running**:
   ```bash
   docker ps | grep ml-ids
   ```

2. **Verify model status**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Verify CICFlowMeter is capturing traffic**:
   ```bash
   docker logs ml-ids
   ```

4. **Test manual prediction**:
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"flow_duration": 1.0, "tot_fwd_pkts": 10, ...}'
   ```

### Advanced Configuration

#### Available Environment Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `CIC_INTERFACE` | Network interface for capture | `eth0` |
| `MLFLOW_TRACKING_URI` | MLflow server URI | Required |
| `MLFLOW_S3_ENDPOINT_URL` | S3 endpoint for models | Required |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `LOG_DIR` | Directory for logs | `/app/logs` |
| `LOG_NEGATIVE_PREDICTIONS` | Enable logging of negative predictions | `false` |

#### Monitoring and Logs

- **Application logs**: Available in `/app/logs/` inside the container
- **Positive prediction logs**: Saved in `positive_predictions.log`
- **Negative prediction logs**: Saved in `negative_predictions.log` (when enabled)
- **Container logs**: `docker logs ml-ids`

#### Troubleshooting

1. **Network permissions error**:
   - Ensure container has `NET_RAW` and `NET_ADMIN` capabilities
   - Verify that the specified network interface exists

2. **MLflow connection error**:
   - Verify environment variables are configured correctly
   - Check network connectivity to MLflow server

3. **Model not initialized**:
   - Verify model is registered in MLflow
   - Check AWS/S3 credentials

### Scalability

For production environments, consider:

- **Load balancer**: For multiple service instances
- **Database**: For persistent alert storage
- **Monitoring system**: For system metrics and alerts
- **Orchestration**: Kubernetes for container management

---

## Summary

This repository provides a complete pipeline for developing, evaluating, and deploying machine learning models for network intrusion detection, using real-world datasets and modern ML engineering practices. The system is structured for reproducibility, extensibility, and ease of deployment in production environments, with complete CICFlowMeter integration for real-time analysis.

---
