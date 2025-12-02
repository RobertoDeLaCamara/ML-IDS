# ML-IDS Inference Server API Documentation

**Version:** Phase 1 (with Alert Management & Dashboard)  
**OpenAPI Specification available:** [openapi.yaml](openapi.yaml)

## Overview

The ML-IDS inference server provides a comprehensive REST API for network intrusion detection, alert management, incident tracking, and real-time monitoring. The system integrates with CICFlowMeter for automatic network flow analysis and includes a PostgreSQL database for persistent storage.

## Architecture

- **FastAPI**: Async web framework
- **PostgreSQL**: Alert and incident persistence
- **WebSocket**: Real-time dashboard updates
- **Prometheus**: Metrics and monitoring
- **CICFlowMeter**: Automatic network flow feature extraction

---

## Core Prediction API

### POST /predict

Make predictions with the ML model and automatically create alerts for detected attacks.

**Request Body:**
```json
{
  "flow_duration": 1000.0,
  "tot_fwd_pkts": 100,
  "src_ip": "192.168.1.100",
  // ... 75 other network flow features
}
```

**Response:**
```json
{
  "prediction": [1]  // 0 = benign, != 0 = attack type
}
```

**Behavior:**
- If attack detected (prediction != 0), automatically creates alert in database
- Alert severity classification based on attack type
- Deduplication within 5-minute window (configurable)
- Triggers notification channels if configured
- Broadcasts to WebSocket clients

**Response Codes:**
- `200`: Successful prediction
- `400`: Invalid or missing features
- `422`: Invalid data format
- `503`: Model not available

### GET /health

Health check with model and database status.

**Response:**
```json
{
  "status": "healthy",  // "healthy", "degraded", or "unhealthy"
  "model_initialized": true,
  "database": {
    "database": "healthy",  // "healthy", "  "unavailable", or "unhealthy"
    "status": "ok"
  }
}
```

**Status Levels:**
- `healthy`: All systems operational
- `degraded`: Service works but database unavailable
- `unhealthy`: Database connection failed

### GET /

Root endpoint with server information.

**Response:**
```json
{
  "message": "Inference server is running."
}
```

### GET /metrics

Prometheus metrics endpoint.

**Metrics:**
- `ml_ids_detected_attacks_total{attack_type, src_ip}` - Counter of detected attacks
- Standard FastAPI metrics (requests, duration, errors)

---

## Alert Management API

### GET /api/alerts

List alerts with filtering and pagination.

**Query Parameters:**
- `severity` - Filter by severity (low, medium, high, critical)
- `src_ip` - Filter by source IP address
- `dst_ip` - Filter by destination IP address
- `attack_type` - Filter by attack type
- `acknowledged` - Filter by acknowledgment status (true/false)
- `hours` - Time window to query (default: 24)
- `limit` - Maximum results (default: 100, max: 1000)
- `offset` - Pagination offset

**Example:**
```bash
GET /api/alerts?severity=high&hours=24&limit=50
```

**Response:**
```json
[
  {
    "id": 1,
    "attack_type": "DDoS",
    "severity": "high",
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.50",
    "timestamp": "2025-12-02T20:00:00",
    "prediction_score": null,
    "acknowledged": false,
    "incident_id": null,
    "notes": null
  }
]
```

### GET /api/alerts/{alert_id}

Get specific alert details.

**Response:**
```json
{
  "id": 1,
  "attack_type": "DDoS",
  "severity": "high",
  "src_ip": "192.168.1.100",
  "dst_ip": "10.0.0.50",
  "timestamp": "2025-12-02T20:00:00",
  "prediction_score": null,
  "acknowledged": false,
  "incident_id": null,
  "notes": null
}
```

### PUT /api/alerts/{alert_id}

Update alert (add notes, acknowledge).

**Request Body:**
```json
{
  "acknowledged": true,
  "notes": "Investigated - determined to be penetration test"
}
```

**Response:** Updated alert object

### POST /api/alerts/{alert_id}/acknowledge

Acknowledge an alert (shortcut endpoint).

**Response:** Updated alert object with `acknowledged: true`

### DELETE /api/alerts/{alert_id}

Delete an alert.

**Response:**
```json
{
  "message": "Alert 1 deleted"
}
```

---

## Incident Management API

### GET /api/incidents

List incidents with filtering.

**Query Parameters:**
- `status` - Filter by status (open, investigating, resolved, closed)
- `severity` - Filter by severity (low, medium, high, critical)
- `limit` - Maximum results (default: 50, max: 500)
- `offset` - Pagination offset

**Response:**
```json
[
  {
    "id": 1,
    "title": "Multiple DDoS attacks from 192.168.1.100",
    "description": "Coordinated attack detected",
    "status": "open",
    "severity": "high",
    "assigned_to": null,
    "created_at": "2025-12-02T20:00:00",
    "updated_at": "2025-12-02T20:00:00",
    "resolved_at": null,
    "notes": null
  }
]
```

### GET /api/incidents/{incident_id}

Get incident details with related alerts.

### POST /api/incidents

Create new incident manually.

**Request Body:**
```json
{
  "title": "Suspected data exfiltration",
  "description": "Large data transfer detected",
  "severity": "critical",
  "assigned_to": "security-team@example.com"
}
```

### PUT /api/incidents/{incident_id}

Update incident.

**Request Body:**
```json
{
  "status": "investigating",
  "notes": "Contacted network admin, analyzing logs"
}
```

### POST /api/incidents/{incident_id}/alerts/{alert_id}

Link an alert to an incident.

**Response:**
```json
{
  "message": "Alert 5 linked to incident 1"
}
```

### GET /api/incidents/{incident_id}/alerts

Get all alerts related to an incident.

---

## Dashboard API

### GET /api/dashboard/stats

Get overall statistics.

**Query Parameters:**
- `hours` - Time window (default: 24)

**Response:**
```json
{
  "total_alerts": 42,
  "total_incidents": 3,
  "alerts_by_severity": {
    "critical": 5,
    "high": 12,
    "medium": 20,
    "low": 5
  },
  "active_incidents": 2,
  "time_period_hours": 24
}
```

### GET /api/dashboard/attack-timeline

Get time-series attack data for charts.

**Query Parameters:**
- `hours` - Time window (default: 24)
- `interval_minutes` - Time bucket size (default: 60)

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2025-12-02T19:00:00",
      "count": 5,
      "critical": 1,
      "high": 2,
      "medium": 2,
      "low": 0
    }
  ]
}
```

### GET /api/dashboard/top-attackers

Get top attacking source IPs.

**Query Parameters:**
- `hours` - Time window (default: 24)
- `limit` - Max attackers (default: 10)

**Response:**
```json
{
  "attackers": [
    {
      "src_ip": "192.168.1.100",
      "attack_count": 25,
      "max_severity": "high"
    }
  ]
}
```

### GET /api/dashboard/attack-distribution

Get attack type distribution for charts.

**Response:**
```json
{
  "distribution": [
    {
      "attack_type": "DDoS",
      "count": 15
    },
    {
      "attack_type": "PortScan",
      "count": 10
    }
  ]
}
```

### GET /api/dashboard/recent-alerts

Get most recent alerts for feed.

**Query Parameters:**
- `limit` - Max alerts (default: 20)

**Response:**
```json
{
  "alerts": [
    {
      "id": 1,
      "attack_type": "DDoS",
      "severity": "high",
      "src_ip": "192.168.1.100",
      "timestamp": "2025-12-02T20:00:00",
      "acknowledged": false
    }
  ]
}
```

### WS /api/dashboard/live

WebSocket endpoint for real-time updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/dashboard/live');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'alert') {
    console.log('New alert:', message.data);
  } else if (message.type === 'stats_update') {
    console.log('Stats updated:', message.data);
  }
};
```

**Message Types:**
- `alert` - New alert created
- `stats_update` - Statistics refreshed

---

## CICFlowMeter Integration

### Workflow

1. **Traffic Capture**: CICFlowMeter captures packets from network interface
2. **Feature Extraction**: 78 statistical features extracted per flow
3. **Auto-Submission**: Features sent to `/predict` endpoint
4. **Classification**: ML model predicts attack type
5. **Alert Creation**: Attacks automatically logged to database
6. **Notification**: Configured channels notified (Email, Slack)
7. **Dashboard Update**: WebSocket broadcast to connected clients

### Feature Mapping

The system automatically maps CICFlowMeter features to model features:

**Flow Statistics:**
- Duration, packet counts, byte counts
- Forward/backward statistics

**Packet Statistics:**
- Length (min, max, mean, std)
- Inter-arrival times (IAT)

**TCP Flags:**
- SYN, ACK, FIN, RST, PSH, URG, CWR, ECE counts

**Speed Statistics:**
- Bytes/second, packets/second

**Subflow Statistics:**
- Forward/backward subflow data

**TCP Window:**
- Initial window sizes

**Activity:**
- Active and idle times

---

## Alert Severity Classification

Automatic severity assignment based on attack type and confidence:

### Critical
- Infiltration attacks
- Botnet ARES

### High
- DDoS attacks
- SQL Injection
- Brute Force attacks
- High confidence (>0.9) attacks

### Medium
- Other attacks with medium confidence (0.8-0.9)
- Default level for most attacks

### Low
- Low confidence (<0.8) detections

---

## Alert Deduplication

Prevents alert fatigue by deduplicating similar alerts:

- **Window**: 5 minutes (configurable via `ALERT_DEDUP_WINDOW_SECONDS`)
- **Criteria**: Same source IP + same attack type
- **Behavior**: Subsequent duplicates are dropped, not stored

---

## Configuration

### Environment Variables

**Database:**
- `DATABASE_URL` - PostgreSQL connection string

**MLflow & Model:**
- `MLFLOW_TRACKING_URI` - MLflow server URI
- `MLFLOW_S3_ENDPOINT_URL` - S3 endpoint
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `MLFLOW_MODEL_NAME` - Model name (default: `models:/ML_IDS_Model_v1/latest`)

**Network Capture:**
- `CIC_INTERFACE` - Network interface (default: `eth0`)
- `START_CICFLOWMETER` - Enable CICFlowMeter (default: `true`)

**Alerts:**
- `ALERT_DEDUP_WINDOW_SECONDS` - Dedup window (default: `300`)
- `ALERT_NOTIFICATION_ENABLED` - Enable notifications (default: `false`)

**Notifications:**
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` - Email config
- `SLACK_WEBHOOK_URL` - Slack webhook

**Dashboard:**
- `DASHBOARD_ENABLED` - Enable dashboard (default: `true`)

---

## Database Schema

### Tables

**alerts:**
- `id`, `attack_type`, `severity`, `src_ip`, `dst_ip`
- `timestamp`, `features`, `prediction_score`
- `acknowledged`, `incident_id`, `notes`

**incidents:**
- `id`, `title`, `description`, `status`, `severity`
- `assigned_to`, `created_at`, `updated_at`, `resolved_at`, `notes`

**metrics:**
- `id`, `metric_name`, `value`, `timestamp`, `tags`

**notification_channels:**
- `id`, `name`, `channel_type`, `config`, `enabled`

**alert_rules:**
- `id`, `name`, `description`, `condition`, `threshold`
- `time_window_seconds`, `action`, `severity`, `enabled`

---

## Error Handling

### Graceful Degradation

If database is unavailable:
- `/predict` still works, alerts not stored
- `/health` returns `degraded` status
- Alert endpoints return 503 errors
- Service continues to function for predictions

### Common Errors

**503 Service Unavailable:**
- Model not loaded
- Database connection failed

**422 Unprocessable Entity:**
- Invalid request format
- Missing required fields

**404 Not Found:**
- Alert/incident ID doesn't exist

**400 Bad Request:**
- Invalid query parameters
- Invalid filter values

---

## Logging

### Log Files

- **Positive predictions**: `/app/logs/positive_predictions.log`
- **Negative predictions**: `/app/logs/negative_predictions.log` (if enabled)
- **Application logs**: Via `docker logs ml-ids`

### Database Logs

All alerts and incidents persisted to PostgreSQL for:
- Historical analysis
- Compliance and auditing
- Incident investigation
- Trend analysis

---

## Testing

### Manual Testing

```bash
# Test prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"flow_duration": 1000.0, "tot_fwd_pkts": 100, "src_ip": "192.168.1.100"}'

# List alerts
curl http://localhost:8000/api/alerts?limit=10

# Get stats
curl http://localhost:8000/api/dashboard/stats

# Health check
curl http://localhost:8000/health
```

### Automated Tests

```bash
pytest tests/test_inference_server.py
pytest tests/test_database.py
```

---

## Next Steps (Phase 2)

Future enhancements planned:
- JWT authentication
- API key management
- Rate limiting
- User roles and permissions
- Advanced analytics
- Threat intelligence integration

---

For more information, see:
- [Main README](../../README.md)
- [OpenAPI Specification](openapi.yaml)
- [Walkthrough Documentation](../../.gemini/antigravity/brain/1a9240d3-eaa8-4874-b2db-efdd780015d2/walkthrough.md)
