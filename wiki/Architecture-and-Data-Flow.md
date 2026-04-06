# Architecture & Data Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Network Interface                                              │
│  CICFlowMeter (NET_RAW + NET_ADMIN capabilities)               │
│  → 78 flow features per bidirectional flow                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /predict (JSON, 78 features)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI — src/inference_server/main.py :8000                   │
│                                                                 │
│  auth.py: X-API-Key middleware                                  │
│  (bypassed for /health, /docs, /metrics, /dashboard, /)         │
│                                                                 │
│  ModelManager.predict(features)                                 │
│  ├─ Primary: ML Tracking.sklearn.load_model(ML Tracking_MODEL_NAME)       │
│  │   └─ Save copy to MODEL_CACHE_DIR/model_cache.joblib         │
│  └─ Fallback: joblib.load(MODEL_CACHE_DIR/model_cache.joblib)  │
│                                                                 │
│  PredictionRequest validation (schemas.py):                    │
│  ├─ NaN/Inf → replace with 0.0                                  │
│  ├─ Non-negative clamping (44 fields)                           │
│  ├─ TCP flag range clamp to [0.0, 1.0]                         │
│  └─ Collect validation warnings                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ prediction != 0 (attack)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  AlertService — alert_service.py                                │
│                                                                 │
│  1. check_duplicate(src_ip, attack_type, 300s window)           │
│     → if duplicate: drop, log, return                           │
│                                                                 │
│  2. classify_severity(attack_type, prediction_score)            │
│                                                                 │
│  3. INSERT into alerts table                                    │
│                                                                 │
│  4. evaluate_alert_rules(alert)                                  │
│     → Query enabled AlertRule rows from DB                      │
│     → For each rule: count-based condition evaluation           │
│     → Actions: create_incident | escalate_severity | notify     │
│                                                                 │
│  5. send_notifications(alert)                                   │
│     → Query enabled NotificationChannel rows from DB           │
│     → SMTP / Slack webhook / generic webhook                    │
│                                                                 │
│  6. ws_manager.send_alert(alert_data)                           │
│     → Broadcast to all WebSocket clients                        │
└──────────────┬───────────────────┬─────────────────────────────┘
               │                   │
               ▼                   ▼
         PostgreSQL/SQLite    WebSocket clients
         + Monitoring Service         ws://.../api/dashboard/live
         metrics update       (auth: ?api_key=<key>)
```

## Model Loading Strategy

```
Startup → load_model():
  1. Try: ML Tracking.sklearn.load_model(ML Tracking_MODEL_NAME)
     → On success: save to MODEL_CACHE_DIR/model_cache.joblib
     → Set model_initialized = True
  2. If ML Tracking fails: joblib.load(MODEL_CACHE_DIR/model_cache.joblib)
     → Set model_initialized = True, log warning
  3. If both fail: model_initialized = False
     → /health returns degraded/unhealthy
     → /predict returns 503
```

## Authentication Flow

```
Request arrives
  │
  auth.py middleware:
  │
  ├─ Path in public_paths? (/health, /docs, /redoc, /openapi.*,
  │   /, /dashboard, /metrics) → PASS
  │
  ├─ ML_IDS_AUTH_ENABLED == false → PASS
  │
  ├─ No API keys configured → PASS (dev mode)
  │
  └─ Check X-API-Key header:
      ├─ Missing → 401 Unauthorized
      └─ Not in ML_IDS_API_KEYS list → 403 Forbidden
          (constant-time comparison for each key)
```

## Monitoring Service Metrics

```python
# src/inference_server/metrics.py

mlids_predictions_total          Counter  labels: result=[attack/benign]
mlids_alerts_created_total       Counter  labels: severity=[low/medium/high/critical]
mlids_prediction_latency_seconds Histogram  (model inference time)
mlids_request_duration_seconds   Histogram  (full request time)
mlids_model_loaded               Gauge    (0 or 1)
mlids_active_websocket_connections Gauge  (count of connected clients)
```

Available at `GET /metrics` in Monitoring Service text format.

## Database Schema

```sql
-- Core tables
alerts (16 columns, indexes on severity/src_ip/timestamp/attack_type)
incidents (10 columns, status: open/investigating/resolved/closed)
metrics (5 columns, time-series for dashboard)

-- ML-IDS additions (not in CIDS)
notification_channels (6 columns: name, channel_type, config JSON, enabled)
alert_rules (11 columns: name, condition, threshold, time_window_s, action, severity, enabled)

-- Alembic migration tracking
alembic_version
```

## Container Startup

```
start.sh:
1. uvicorn main:app --host 0.0.0.0 --port 8000 &
2. Health loop: wait for model_initialized == true (max 300s)
3. Validate network interface (validate_interface.py)
4. If START_CICFLOWMETER=true:
   cicflowmeter -i ${CIC_INTERFACE} -u http://localhost:8000/predict
```

Docker Compose: host network mode, NET_RAW + NET_ADMIN capabilities.
