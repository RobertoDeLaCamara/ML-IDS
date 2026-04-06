# API Reference

Base URL: `http://localhost:8000`

Auth: `X-API-Key: <key>` header required on all endpoints except public paths.

Public paths (no auth): `/health`, `/docs`, `/redoc`, `/openapi.json`, `/`, `/dashboard`, `/metrics`

---

## Health

### GET /health

```json
{
  "status": "healthy",          // "healthy" | "degraded" | "unhealthy"
  "model_initialized": true,
  "model_source": "ML Tracking",     // "ML Tracking" | "cache" | null
  "database": "connected",
  "uptime_seconds": 3600
}
```

`degraded`: model loaded from cache fallback (ML Tracking unreachable at startup).
`unhealthy`: model not loaded — `/predict` returns 503.

---

## Prediction

### POST /predict

Classify a network flow. Returns attack type and triggers alert pipeline if attack detected.

**Request** (78 features, all float):

```json
{
  "flow_duration": 1000.0,
  "total_fwd_packets": 5.0,
  "total_backward_packets": 3.0,
  "total_length_of_fwd_packets": 500.0,
  "total_length_of_bwd_packets": 300.0,
  ...
}
```

Invalid values are coerced silently:
- NaN / Inf → replaced with `0.0`
- Negative values in 44 non-negative fields → clamped to `0.0`
- TCP flag values outside [0.0, 1.0] → clamped to range

**Response 200**:
```json
{
  "prediction": 0,
  "attack_type": "BENIGN",
  "confidence": 0.97,
  "validation_warnings": [],
  "alert_created": false,
  "alert_id": null
}
```

`prediction`: integer class label (0 = BENIGN, 1–14 = attack classes).
`confidence`: probability of the predicted class from the RF/Stacking ensemble.
`validation_warnings`: list of strings describing any coerced input values.
`alert_created`: true if an alert row was inserted (prediction != 0 and not duplicate).

**Response 503**: Model not loaded.

---

## Alerts

### GET /api/alerts

```
GET /api/alerts?severity=high&hours=24&attack_type=DDoS&limit=100&offset=0
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `severity` | string | — | Filter: low/medium/high/critical |
| `hours` | int | 24 | Lookback window in hours |
| `attack_type` | string | — | Exact match on attack_type |
| `src_ip` | string | — | Exact match on src_ip |
| `limit` | int | 100 | Max results |
| `offset` | int | 0 | Pagination offset |

**Response 200**:
```json
{
  "total": 42,
  "alerts": [
    {
      "id": 1,
      "timestamp": "2026-03-30T12:00:00Z",
      "src_ip": "10.0.0.1",
      "dst_ip": "[INTERNAL_IP]",
      "src_port": 54321,
      "dst_port": 80,
      "protocol": "TCP",
      "attack_type": "DDoS",
      "severity": "critical",
      "confidence": 0.97,
      "status": "open",
      "incident_id": null
    }
  ]
}
```

### GET /api/alerts/{id}

Returns single alert with full `features` JSON included.

### PATCH /api/alerts/{id}

Update `status` of an alert.

```json
{"status": "investigating"}
```

### DELETE /api/alerts/{id}

Soft delete (sets `status = "deleted"`). Alert remains in DB for audit.

---

## Incidents

### GET /api/incidents

```
GET /api/incidents?status=open&limit=50&offset=0
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | Filter: open/investigating/resolved/closed |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

### POST /api/incidents

Create a new incident manually.

```json
{
  "title": "DDoS campaign from 10.x subnet",
  "description": "Multiple DDoS alerts from 10.0.0.0/24 over 20 minutes",
  "severity": "critical"
}
```

### GET /api/incidents/{id}

Returns incident with linked alert list.

### PATCH /api/incidents/{id}

Update `status`, `description`, or `severity`.

```json
{"status": "resolved", "description": "Blocked at firewall"}
```

### POST /api/incidents/{id}/alerts/{alert_id}

Link an existing alert to an incident.

---

## Alert Rules

### GET /api/alert-rules

Returns all alert rules (enabled and disabled).

### POST /api/alert-rules

```json
{
  "name": "DDoS Surge",
  "description": "Auto-create incident on 10+ DDoS in 60s",
  "condition": "attack_count",
  "threshold": 10,
  "time_window_s": 60,
  "attack_type": "DDoS",
  "action": "create_incident",
  "enabled": true
}
```

### PATCH /api/alert-rules/{id}

Toggle enabled/disabled or update any field.

### DELETE /api/alert-rules/{id}

Permanently deletes the rule.

---

## Notification Channels

### GET /api/notification-channels

Returns all channels with config (passwords/tokens included).

### POST /api/notification-channels

See [Notification Channels](Notification-Channels.md) for per-type config schemas.

### PATCH /api/notification-channels/{id}

```json
{"enabled": false}
```

### DELETE /api/notification-channels/{id}

---

## Dashboard

### GET /api/dashboard/stats

```json
{
  "total_alerts_24h": 142,
  "alerts_by_severity": {
    "critical": 3,
    "high": 12,
    "medium": 47,
    "low": 80
  },
  "top_attack_types": [
    {"attack_type": "PortScan", "count": 55},
    {"attack_type": "DDoS", "count": 3}
  ],
  "active_incidents": 2,
  "model_status": "healthy"
}
```

### WebSocket /api/dashboard/live

Real-time alert stream. Auth via query parameter (not header):

```
ws://localhost:8000/api/dashboard/live?api_key=<key>
```

Messages pushed to client on each new alert:

```json
{
  "type": "alert",
  "data": {
    "id": 143,
    "timestamp": "2026-03-30T12:01:00Z",
    "attack_type": "DDoS",
    "severity": "critical",
    "src_ip": "10.0.0.1",
    "confidence": 0.97
  }
}
```

Connection drops are cleaned up automatically — disconnected clients are removed from the broadcast set on the next send attempt.

---

## Monitoring Service Metrics

### GET /metrics

Returns all metrics in Monitoring Service text format. No auth required.

```
# HELP mlids_predictions_total Total predictions by result
# TYPE mlids_predictions_total counter
mlids_predictions_total{result="attack"} 142
mlids_predictions_total{result="benign"} 8742

# HELP mlids_alerts_created_total Alerts created by severity
# TYPE mlids_alerts_created_total counter
mlids_alerts_created_total{severity="critical"} 3
mlids_alerts_created_total{severity="high"} 12
mlids_alerts_created_total{severity="medium"} 47
mlids_alerts_created_total{severity="low"} 80

# HELP mlids_prediction_latency_seconds Model inference time
# TYPE mlids_prediction_latency_seconds histogram
mlids_prediction_latency_seconds_bucket{le="0.005"} 7841
...

# HELP mlids_model_loaded Model loaded and ready
# TYPE mlids_model_loaded gauge
mlids_model_loaded 1

# HELP mlids_active_websocket_connections Active WebSocket clients
# TYPE mlids_active_websocket_connections gauge
mlids_active_websocket_connections 2
```

---

## Auto-generated Docs

```
GET /docs        Swagger UI
GET /redoc       ReDoc
GET /openapi.json
```
