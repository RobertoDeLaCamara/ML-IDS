# ML-IDS — Wiki

Production-grade evolution of the Cognitive-Intrusion-Detection-System. Same core (FastAPI + CICFlowMeter + sklearn RF + PostgreSQL) with added incident correlation, adaptive alert rules stored in database, notification channels stored in database, enhanced Prometheus observability, and a 44-test suite covering auth, database, inference, and validation.

## Quick Start

```bash
cp .env.example .env
# Configure MLflow, S3, API keys

docker-compose up -d
docker-compose exec ml-ids python src/inference_server/init_db.py

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Key Differences from Cognitive-Intrusion-Detection-System

| Feature | CIDS | ML-IDS |
|---------|------|--------|
| Incident management | No | Yes (open/investigating/resolved/closed) |
| Alert rules | Hardcoded in code | Database rows (runtime editable) |
| Notification channels | Env vars only | Database rows (runtime editable) |
| Prometheus metrics | Minimal | `mlids_*` counters + histograms + gauges |
| Authentication | No auth | X-API-Key header + WebSocket query param |
| Multi-key support | No | `ML_IDS_API_KEYS=key1,key2,key3` |
| Feature validation | Basic | NaN/Inf replace + non-negative clamp + flag range |
| Model fallback | MLflow only | MLflow → local joblib cache |
| Test suite | 4 tests | 44 tests |
| DB default | PostgreSQL | SQLite (fallback) or PostgreSQL |

## Stack

| Component | Technology |
|-----------|-----------|
| API | FastAPI + Uvicorn |
| ML model | sklearn RF + Stacking (CIC-IDS2017, 78 features) |
| Model registry | MLflow + local joblib cache |
| Database | PostgreSQL or SQLite (aiosqlite) via async SQLAlchemy |
| Auth | X-API-Key header (multi-key) |
| Real-time | WebSocket (Starlette) |
| Monitoring | Prometheus (custom metrics) |
| Alerts | SMTP / Slack / webhook (DB-managed channels) |
| Capture | CICFlowMeter (NET_RAW + NET_ADMIN) |

## Wiki Pages

- [Architecture and Data Flow](Architecture-and-Data-Flow.md)
- [Alert and Incident Management](Alert-and-Incident-Management.md)
- [Notification Channels](Notification-Channels.md)
- [API Reference](API-Reference.md)
- [Development Guide](Development-Guide.md)

## Key Layout

```
src/inference_server/
├── main.py                  FastAPI app, /predict, ModelManager (MLflow + cache fallback)
├── auth.py                  X-API-Key middleware + WebSocket auth
├── alert_service.py         Alert dedup, severity, rule evaluation, incident correlation
├── notifications.py         Email/Slack/webhook dispatch
├── metrics.py               Prometheus counters/histograms/gauges
├── websocket_manager.py     WebSocket connection set + broadcast
├── models.py                Alert, Incident, Metric, NotificationChannel, AlertRule
├── schemas.py               PredictionRequest (78 fields, NaN/clamp validation)
└── routers/
    ├── alerts.py            /api/alerts CRUD
    ├── incidents.py         /api/incidents CRUD + alert linking
    └── dashboard.py         Stats + WebSocket /api/dashboard/live

tests/
├── test_auth.py         18 tests
├── test_database.py      7 tests
├── test_inference_server.py  4 tests
└── test_validation.py   15 tests
```

## Non-Obvious Facts

- **SQLite is the default in tests** — `DATABASE_URL` defaults to `sqlite+aiosqlite:////app/logs/mlids.db`. PostgreSQL is for production.
- **MLflow has a local cache fallback** — if MLflow is unreachable on startup, the model is loaded from `MODEL_CACHE_DIR/model_cache.joblib`.
- **Auth has a dev mode** — if `ML_IDS_AUTH_ENABLED=false` or no keys configured, all requests pass. Public paths (`/health`, `/docs`, `/metrics`, etc.) always bypass auth.
- **Alert rules are evaluated per alert** — after each alert is inserted, all enabled `AlertRule` rows are evaluated against the database (count queries within time windows).
- **Notification channels are DB rows** — add, enable/disable, or modify channels at runtime without restart.
- **WebSocket auth uses query param** — `ws://host/api/dashboard/live?api_key=<key>` (not header).
