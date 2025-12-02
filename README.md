# Cognitive Intrusion Detection System

Machine Learning-based Intrusion Detection System

## Purpose

The ML-IDS (Machine Learning-based Intrusion Detection System) is a comprehensive network intrusion detection system that uses machine learning techniques to identify malicious traffic in real-time. The system integrates CICFlowMeter for network flow feature extraction and a machine learning model trained on the CIC-IDS2017 dataset for traffic classification.

### Key Features

- **Real-time Detection**: Continuous network traffic analysis using CICFlowMeter
- **Advanced ML Model**: Uses Random Forest and Stacking Classifier for classification
- **REST API**: Inference server with prediction and alert endpoints
- **PostgreSQL Database**: Persistent storage for alerts, incidents, and metrics
- **Alert Management**: Intelligent alerting with severity classification and deduplication
- **Notification System**: Email (SMTP), Slack, and webhook notifications
- **Real-time Dashboard**: WebSocket-powered monitoring interface with live updates
- **Docker Deployment**: Complete system containerization with PostgreSQL
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
├── TEST_RESULTS.md              # Phase 1 test results
├── docker-compose.yml           # Docker Compose configuration (PostgreSQL + ML-IDS)
├── alembic.ini                  # Database migration configuration
├── requirements.txt             # Python dependencies for the root project
│
├── data/
│   └── CIC-IDS2017/
│       ├── Data.csv             # Main dataset with network features
│       ├── Label.csv            # Corresponding labels for classification
│       ├── readme.txt           # Dataset description
│       └── source.txt           # Source information
│
├── migrations/                  # Database migration scripts
│   ├── env.py                   # Alembic environment
│   ├── script.py.mako           # Migration template
│   └── versions/                # Migration versions
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
│       ├── Dockerfile           # Docker image definition
│       ├── main.py              # Main FastAPI application
│       ├── schemas.py           # Pydantic models for requests/responses
│       ├── models.py            # SQLAlchemy database models
│       ├── database.py          # Database connection management
│       ├── alert_service.py     # Alert management service
│       ├── notifications.py     # Notification service (Email/Slack)
│       ├── websocket_manager.py # WebSocket for real-time updates
│       ├── init_db.py           # Database initialization script
│       ├── requirements.txt     # Python dependencies
│       ├── routers/
│       │   ├── alerts.py        # Alert API endpoints
│       │   ├── incidents.py     # Incident management endpoints
│       │   └── dashboard.py     # Dashboard API and WebSocket
│       └── static/              # Dashboard frontend
│           ├── index.html       # Dashboard HTML
│           ├── app.js           # Dashboard JavaScript
│           └── styles.css       # Dashboard CSS
│
└── tests/
    ├── __init__.py
    ├── curl_predict_full.sh
    ├── test_inference_server.py # API tests
    └── test_database.py         # Database model tests
```

---


## Documentation Index

- [Inference Server API](src/inference_server/API.md)
- **Interactive API Documentation:**
  - [Swagger UI](http://localhost:8000/docs) - Interactive API explorer
  - [ReDoc](http://localhost:8000/redoc) - Alternative documentation UI
  - [OpenAPI JSON](http://localhost:8000/openapi.json) - OpenAPI 3.0 specification (JSON)
  - [OpenAPI YAML](http://localhost:8000/openapi.yaml) - OpenAPI 3.0 specification (YAML)
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

#### Option 2: Using Docker Compose (Recommended)

The repository includes a complete `docker-compose.yml` file with PostgreSQL database:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    container_name: ml-ids-postgres
    environment:
      - POSTGRES_USER=mlids
      - POSTGRES_PASSWORD=mlids_password
      - POSTGRES_DB=mlids
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mlids"]
      interval: 10s
      timeout: 5s
      retries: 5

  ml-ids:
    build:
      context: .
      dockerfile: src/inference_server/Dockerfile
    container_name: ml-ids
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://mlids:mlids_password@localhost:5432/mlids
      - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
      - MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT_URL}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - CIC_INTERFACE=eth0
      # Notifications (optional)
      - SMTP_HOST=${SMTP_HOST:-}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
    volumes:
      - /var/log/ml-ids:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
```

**Setup Steps:**

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your MLflow and notification settings
   ```

2. Start services:
   ```bash
   docker-compose up -d
   ```

3. Initialize database:
   ```bash
   docker-compose exec ml-ids python src/inference_server/init_db.py
   ```

4. Access dashboard:
   ```
   http://localhost:8000/dashboard
   ```

### Deployment Verification

1. **Verify containers are running**:
   ```bash
   docker-compose ps
   ```

2. **Verify model and database status**:
   ```bash
   curl http://localhost:8000/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "model_initialized": true,
     "database": {
       "database": "healthy",
       "status": "ok"
     }
   }
   ```

3. **Verify CICFlowMeter is capturing traffic**:
   ```bash
   docker-compose logs ml-ids
   ```

4. **Test manual prediction with alert creation**:
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"flow_duration": 1000.0, "tot_fwd_pkts": 100, "src_ip": "192.168.1.100"}'
   ```

5. **View dashboard**:
   Open browser to `http://localhost:8000/dashboard`

6. **Check recent alerts**:
   ```bash
   curl http://localhost:8000/api/alerts?limit=10
   ```

### Advanced Configuration

#### Available Environment Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| **Database** | | |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://mlids:mlids_password@localhost:5432/mlids` |
| **MLflow & Model** | | |
| `MLFLOW_TRACKING_URI` | MLflow server URI | Required |
| `MLFLOW_S3_ENDPOINT_URL` | S3 endpoint for models | Required |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `MLFLOW_MODEL_NAME` | Model name in MLflow | `models:/ML_IDS_Model_v1/latest` |
| **Network Capture** | | |
| `CIC_INTERFACE` | Network interface for capture | `eth0` |
| `START_CICFLOWMETER` | Enable CICFlowMeter | `true` |
| **Logging** | | |
| `LOG_DIR` | Directory for logs | `/app/logs` |
| `LOG_NEGATIVE_PREDICTIONS` | Log benign traffic | `false` |
| **Alerts** | | |
| `ALERT_DEDUP_WINDOW_SECONDS` | Alert deduplication window | `300` (5 min) |
| `ALERT_NOTIFICATION_ENABLED` | Enable notifications | `false` |
| **Notifications** | | |
| `SMTP_HOST` | SMTP server hostname | - |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `SMTP_FROM` | From address | `ML-IDS Alerts <alerts@mlids.local>` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | - |
| **Dashboard** | | |
| `DASHBOARD_ENABLED` | Enable dashboard | `true` |

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

---

## API Reference

The ML-IDS inference server provides a comprehensive REST API for predictions, alert management, and monitoring.

### Core Endpoints

#### `/predict` - Make Predictions
```bash
POST /predict
Content-Type: application/json

{
  "flow_duration": 1000.0,
  "tot_fwd_pkts": 100,
  "src_ip": "192.168.1.100"
  # ... other 75 features
}
```

If an attack is detected (prediction != 0), an alert is automatically created in the database.

#### `/health` - Health Check
```bash
GET /health
```

Returns service status, model initialization state, and database health.

### Alert Management API

#### List Alerts
```bash
GET /api/alerts?severity=high&hours=24&limit=50
```

Query parameters:
- `severity`: Filter by severity (low, medium, high, critical)
- `src_ip`: Filter by source IP
- `attack_type`: Filter by attack type
- `acknowledged`: Filter by acknowledgment status
- `hours`: Time window to query (default: 24)
- `limit`: Maximum results (default: 100, max: 1000)
- `offset`: Pagination offset

#### Get Alert Details  
```bash
GET /api/alerts/{alert_id}
```

#### Update Alert
```bash
PUT /api/alerts/{alert_id}
Content-Type: application/json

{
  "acknowledged": true,
  "notes": "Investigated - false positive"
}
```

#### Acknowledge Alert
```bash
POST /api/alerts/{alert_id}/acknowledge
```

### Incident Management API

#### List Incidents
```bash
GET /api/incidents?status=open&severity=critical
```

#### Create Incident
```bash
POST /api/incidents
Content-Type: application/json

{
  "title": "Multiple attacks from 192.168.1.100",
  "description": "Investigating coordinated attack",
  "severity": "high",
  "assigned_to": "security-team@example.com"
}
```

#### Update Incident
```bash
PUT /api/incidents/{incident_id}
Content-Type: application/json

{
  "status": "investigating",
  "notes": "Found malware on source machine"
}
```

#### Link Alert to Incident
```bash
POST /api/incidents/{incident_id}/alerts/{alert_id}
```

### Dashboard API

#### Get Statistics
```bash
GET /api/dashboard/stats?hours=24
```

Returns total alerts, active incidents, and alerts by severity.

#### Get Attack Timeline
```bash
GET /api/dashboard/attack-timeline?hours=24&interval_minutes=60
```

Returns time-series data for charts.

#### Get Top Attackers
```bash
GET /api/dashboard/top-attackers?hours=24&limit=10
```

#### Get Recent Alerts
```bash
GET /api/dashboard/recent-alerts?limit=20
```

#### WebSocket (Real-time Updates)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/dashboard/live');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'alert') {
    // New alert received
    console.log('New alert:', message.data);
  }
};
```

### Metrics

Prometheus metrics available at `/metrics`:
- `ml_ids_detected_attacks_total` - Counter of detected attacks by type and source IP
- Standard FastAPI metrics (request count, duration, etc.)

---

## Real-time Dashboard

The ML-IDS includes a professional web dashboard for real-time monitoring at `/dashboard`.

### Features

**Stats Overview**:
- Total alerts in last 24 hours
- Active incidents count  
- Critical and high severity counts
- Live connection status

**Attack Timeline Chart**:
- Line chart showing attacks over time
- Grouped by severity level
- Hourly intervals (configurable)

**Attack Distribution**:
- Doughnut chart of attack types
- Color-coded visualization

**Recent Alerts Feed**:
- Live scrolling feed of alerts
- Real-time WebSocket updates
- Color-coded severity badges
- Acknowledgment status

**Top Attackers Table**:
- Most active source IPs
- Attack counts per IP
- Maximum severity levels

### Dashboard Technology Stack

- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Charts**: Chart.js for visualizations
- **Real-time**: WebSocket for live updates
- **Design**: Responsive dark theme optimized for SOC environments
- **Notifications**: Browser notifications for new critical alerts

### Accessing the Dashboard

1. Start the services: `docker-compose up -d`
2. Open browser to: `http://localhost:8000/dashboard`
3. Dashboard updates automatically via WebSocket
4. No login required (authentication coming in Phase 2)

---

## Notification System

Configure email and Slack notifications for real-time alerting.

### Email Notifications (SMTP)

Set environment variables:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=ML-IDS Alerts <alerts@mlids.local>
ALERT_NOTIFICATION_ENABLED=true
```

Notifications include:
- Alert severity and attack type
- Source and destination IPs
- Timestamp and prediction score
- HTML formatted with color-coded severity

### Slack Notifications

Set webhook URL:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERT_NOTIFICATION_ENABLED=true
```

Slack messages include rich attachments with:
- Color-coded severity (red for critical, orange for high, etc.)
- Structured fields for easy reading
- Attack details and timestamp

### Custom Webhooks

Configure generic webhooks for integration with other systems:
```sql
INSERT INTO notification_channels (name, channel_type, config, enabled)
VALUES (
  'Custom Webhook',
  'webhook',
  '{"url": "https://your-system.com/webhook", "headers": {"Authorization": "Bearer token"}}',
  true
);
```

---

## Database Schema

PostgreSQL database with the following main tables:

- **alerts**: Detected attacks with severity, IPs, timestamps, and features
- **incidents**: Investigation tracking for grouped alerts
- **metrics**: Time-series metrics for analytics
- **notification_channels**: Email, Slack, and webhook configurations
- **alert_rules**: Custom alert conditions and automated actions

### Database Management

**Initialize database**:
```bash
docker-compose exec ml-ids python src/inference_server/init_db.py
```

**Run migrations**:
```bash
docker-compose exec ml-ids alembic upgrade head
```

**Create migration**:
```bash
docker-compose exec ml-ids alembic revision --autogenerate -m "description"
```

**Access database directly**:
```bash
docker-compose exec postgres psql -U mlids -d mlids
```

---

### Scalability

For production environments, Phase 1 provides:

- **PostgreSQL Database**: For persistent alert and incident storage
- **Real-time Dashboard**: WebSocket-based monitoring
- **Alert Deduplication**: Reduces noise and database load
- **Async Architecture**: Non-blocking database operations
- **Connection Pooling**: Efficient database connection management

Phase 2 (Future) will add:
- **Authentication**: JWT tokens and API keys
- **Rate Limiting**: Per-endpoint rate limits
- **User Management**: Role-based access control
- **Advanced Analytics**: Pattern detection and threat intelligence

---

## Summary

This repository provides a complete pipeline for developing, evaluating, and deploying machine learning models for network intrusion detection, using real-world datasets and modern ML engineering practices.

**Phase 1 Enhancements** (Current):
- ✅ PostgreSQL database integration
- ✅ Intelligent alert management with severity classification
- ✅ Multi-channel notifications (Email, Slack, Webhooks)
- ✅ Real-time dashboard with WebSocket updates
- ✅ Comprehensive REST API for alerts and incidents
- ✅ Alert deduplication and rules engine
- ✅ Incident tracking and management

The system is structured for reproducibility, extensibility, and ease of deployment in production environments, with complete CICFlowMeter integration for real-time analysis.

---
