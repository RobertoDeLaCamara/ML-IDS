# Development Guide

## Prerequisites

- Docker + Docker Compose
- Python 3.10+ (for local dev without Docker)
- MLflow tracking server + S3-compatible storage (MinIO)
- PostgreSQL or SQLite (auto-fallback)

## Setup

```bash
cp .env.example .env
# Edit .env: MLFLOW_TRACKING_URI, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
#            ML_IDS_API_KEYS, DATABASE_URL

docker-compose up -d
docker-compose exec ml-ids python src/inference_server/init_db.py
```

## Quick Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","model_initialized":true,...}

curl http://localhost:8000/metrics
# Prometheus text format

curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"flow_duration":1000.0,"total_fwd_packets":5.0,...}'
```

## Testing

```bash
# Full suite (44 tests)
pytest tests/ -v

# By module
pytest tests/test_auth.py -v          # 18 tests: key validation, public paths, dev mode
pytest tests/test_database.py -v      # 7 tests: CRUD, migrations
pytest tests/test_inference_server.py -v  # 4 tests: predict endpoint, health
pytest tests/test_validation.py -v    # 15 tests: NaN/Inf, clamping, TCP flags

# Single test
pytest tests/test_auth.py::test_api_key_required -v
pytest tests/test_validation.py::test_nan_replacement -v
```

Tests use SQLite (`sqlite+aiosqlite:////app/logs/mlids.db`) by default — no PostgreSQL required for testing.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | Yes | — | MLflow server URL |
| `MLFLOW_MODEL_NAME` | No | `ml-ids-model` | Registered model name |
| `MODEL_CACHE_DIR` | No | `/app/models` | Local joblib cache directory |
| `DATABASE_URL` | No | SQLite | PostgreSQL or SQLite URL |
| `ML_IDS_API_KEYS` | No | — | Comma-separated API keys |
| `ML_IDS_AUTH_ENABLED` | No | `true` | Set `false` to disable auth |
| `AWS_ACCESS_KEY_ID` | Yes* | — | S3/MinIO access key (*if using MLflow S3) |
| `AWS_SECRET_ACCESS_KEY` | Yes* | — | S3/MinIO secret key |
| `AWS_S3_ENDPOINT_URL` | No | — | MinIO endpoint (if not AWS S3) |
| `START_CICFLOWMETER` | No | `false` | Start CICFlowMeter at container start |
| `CIC_INTERFACE` | No | `eth0` | Network interface for CICFlowMeter |

## Auth Dev Mode

Set `ML_IDS_AUTH_ENABLED=false` in `.env` to bypass all auth checks. Useful for local development without configuring API keys. Do not use in production.

Alternatively, leave `ML_IDS_API_KEYS` empty — the server treats this as dev mode and passes all requests.

## Database Operations

```bash
# Initialize schema (first run)
docker-compose exec ml-ids python src/inference_server/init_db.py

# Run Alembic migrations
docker-compose exec ml-ids alembic upgrade head

# Direct SQLite access (test/dev)
sqlite3 /app/logs/mlids.db
.tables
SELECT count(*) FROM alerts;
SELECT * FROM alert_rules;

# Seed default alert rules
docker-compose exec ml-ids python -c "
from src.inference_server.init_db import seed_default_rules
import asyncio
asyncio.run(seed_default_rules())
"
```

## Manual Alert Rule Management

```bash
# Create rule via API
curl -X POST http://localhost:8000/api/alert-rules \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DDoS Surge",
    "condition": "attack_count",
    "threshold": 5,
    "time_window_s": 60,
    "attack_type": "DDoS",
    "action": "create_incident",
    "enabled": true
  }'

# Disable a rule
curl -X PATCH http://localhost:8000/api/alert-rules/1 \
  -H "X-API-Key: <key>" \
  -d '{"enabled": false}'
```

## Notification Channel Setup

```bash
# Add Slack channel
curl -X POST http://localhost:8000/api/notification-channels \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "slack-soc",
    "channel_type": "slack",
    "config": {"webhook_url": "https://hooks.slack.com/services/..."},
    "enabled": true
  }'

# Test channel (send test alert)
curl -X POST http://localhost:8000/api/notification-channels/1/test \
  -H "X-API-Key: <key>"
```

## Project Structure

```
src/inference_server/
├── main.py                  FastAPI app, /predict, ModelManager
├── auth.py                  X-API-Key middleware + WebSocket auth helper
├── alert_service.py         Dedup, severity, rule evaluation, incident creation
├── notifications.py         SMTP / Slack / webhook dispatch (asyncio.gather)
├── metrics.py               Prometheus counters / histograms / gauges
├── websocket_manager.py     Connection set + broadcast (cleanup on failure)
├── models.py                SQLAlchemy ORM: Alert, Incident, Metric,
│                            NotificationChannel, AlertRule
├── schemas.py               Pydantic PredictionRequest (78 fields, validators)
├── init_db.py               Schema creation + default data seeding
└── routers/
    ├── alerts.py            /api/alerts CRUD + status update
    ├── incidents.py         /api/incidents CRUD + alert linking
    └── dashboard.py         /api/dashboard/stats + WebSocket /api/dashboard/live

tests/
├── test_auth.py             18 tests: single key, multi-key, public paths,
│                            disabled auth, WebSocket auth
├── test_database.py         7 tests: alert CRUD, incident CRUD, rule eval
├── test_inference_server.py 4 tests: /predict, /health, 503 on model failure
└── test_validation.py       15 tests: NaN/Inf replace, negative clamp (44 fields),
                             TCP flag clamp [0,1], warning collection

docker-compose.yml
.env.example
```

## CI/CD

Jenkins pipeline targets `192.168.1.86:5000` (private registry). SonarQube integration via `sonar-project.properties`. Pipeline stages: lint (flake8 --max-line-length=100) → test (pytest) → build → push → deploy.

## Differences from Cognitive-Intrusion-Detection-System

ML-IDS adds to CIDS without replacing it:

| Addition | Location |
|----------|----------|
| `NotificationChannel` model + CRUD | `models.py`, `routers/` |
| `AlertRule` model + eval loop | `models.py`, `alert_service.py` |
| `Incident` management | `models.py`, `routers/incidents.py` |
| Multi-key auth (`ML_IDS_API_KEYS`) | `auth.py` |
| Feature validation (NaN/clamp) | `schemas.py` |
| MLflow + local joblib fallback | `main.py` ModelManager |
| Full Prometheus metrics suite | `metrics.py` |
| 40 additional tests | `tests/` |

The core `/predict` → `AlertService` → PostgreSQL flow is identical between the two projects.
