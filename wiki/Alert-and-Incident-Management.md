# Alert and Incident Management

## Alert Lifecycle

```
/predict receives flow → prediction != 0 (attack detected)
        │
        ▼
AlertService.create_alert(src_ip, attack_type, confidence, features)
        │
        ├─ 1. check_duplicate(src_ip, attack_type, window=300s)
        │      SELECT count(*) FROM alerts
        │      WHERE src_ip = ? AND attack_type = ? AND timestamp > now()-300s
        │      → count > 0: DROP (log "Duplicate alert suppressed"), return None
        │
        ├─ 2. classify_severity(attack_type, prediction_score)
        │      → returns: "low" | "medium" | "high" | "critical"
        │
        ├─ 3. INSERT INTO alerts (...) RETURNING id
        │
        ├─ 4. evaluate_alert_rules(alert)
        │      → SELECT * FROM alert_rules WHERE enabled = true
        │      → For each rule: evaluate condition against DB count queries
        │      → Actions: create_incident | escalate_severity | notify
        │
        ├─ 5. send_notifications(alert)
        │      → SELECT * FROM notification_channels WHERE enabled = true
        │      → Dispatch to each channel concurrently
        │
        └─ 6. ws_manager.send_alert(alert_data)
               → Broadcast to all connected WebSocket clients
               → Remove clients on send failure (cleanup)
```

## Severity Classification

```python
# alert_service.py: classify_severity()

SEVERITY_MAP = {
    # Critical — immediate threat
    "DDoS": "critical",
    "DoS Hulk": "critical",
    "DoS GoldenEye": "critical",
    "DoS slowloris": "critical",
    "DoS Slowhttptest": "critical",
    "Heartbleed": "critical",

    # High — active exploitation
    "Web Attack – Brute Force": "high",
    "Web Attack – XSS": "high",
    "Web Attack – Sql Injection": "high",
    "FTP-Patator": "high",
    "SSH-Patator": "high",
    "Infiltration": "high",
    "Botnet": "high",

    # Medium — reconnaissance / scanning
    "PortScan": "medium",

    # Default
    "BENIGN": "low",
}

# Score adjustment:
# prediction_score >= 0.9 → escalate one level (medium → high, high → critical)
# prediction_score < 0.5  → de-escalate one level
```

## Alert Schema

```sql
CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT now(),
    src_ip          VARCHAR(45) NOT NULL,
    dst_ip          VARCHAR(45),
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    attack_type     VARCHAR(100) NOT NULL,
    severity        VARCHAR(20) NOT NULL,   -- low/medium/high/critical
    confidence      FLOAT,                  -- prediction_score [0.0, 1.0]
    features        JSON,                   -- raw 78-feature dict
    status          VARCHAR(20) DEFAULT 'open',
    incident_id     INTEGER REFERENCES incidents(id),
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_alerts_severity    ON alerts(severity);
CREATE INDEX idx_alerts_src_ip      ON alerts(src_ip);
CREATE INDEX idx_alerts_timestamp   ON alerts(timestamp);
CREATE INDEX idx_alerts_attack_type ON alerts(attack_type);
```

## Incident Management

Incidents group related alerts. Created automatically by alert rules or manually via the API.

```sql
CREATE TABLE incidents (
    id          INTEGER PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    severity    VARCHAR(20),
    status      VARCHAR(20) DEFAULT 'open',
                -- open | investigating | resolved | closed
    created_at  TIMESTAMP DEFAULT now(),
    updated_at  TIMESTAMP DEFAULT now(),
    resolved_at TIMESTAMP,
    alert_count INTEGER DEFAULT 0,
    src_ips     JSON    -- list of involved src_ip strings
);
```

### Incident Status Transitions

```
open → investigating → resolved → closed
 │                                   ▲
 └───────────────────────────────────┘
         (skip directly to closed)
```

- `open`: newly created, not yet assigned
- `investigating`: actively being worked
- `resolved`: root cause identified, remediation applied
- `closed`: confirmed resolved, no further action

Resolved/closed incidents still appear in history. Only `status` changes — incidents are never deleted.

## Alert Rules

Alert rules are stored as database rows and evaluated after each new alert is inserted. They can be created, enabled, disabled, and modified at runtime without restart.

```sql
CREATE TABLE alert_rules (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    description    TEXT,
    condition      VARCHAR(50),   -- "attack_count" | "unique_attack_types" | "attack_severity"
    threshold      INTEGER,       -- numeric threshold for count conditions
    time_window_s  INTEGER,       -- lookback window in seconds
    action         VARCHAR(50),   -- "create_incident" | "escalate_severity" | "notify"
    severity       VARCHAR(20),   -- severity filter (optional)
    attack_type    VARCHAR(100),  -- attack_type filter (optional)
    enabled        BOOLEAN DEFAULT true,
    created_at     TIMESTAMP DEFAULT now()
);
```

### Rule Evaluation Logic

```python
# alert_service.py: evaluate_alert_rules()

for rule in enabled_rules:
    if rule.condition == "attack_count":
        # Count alerts in time window matching optional filters
        count = SELECT count(*) FROM alerts
                WHERE timestamp > now() - rule.time_window_s
                AND (rule.attack_type IS NULL OR attack_type = rule.attack_type)
                AND (rule.severity IS NULL OR severity = rule.severity)

        if count > rule.threshold:
            _execute_rule_action(rule, alert)

    elif rule.condition == "unique_attack_types":
        # Count distinct attack types in time window
        count = SELECT count(DISTINCT attack_type) FROM alerts
                WHERE timestamp > now() - rule.time_window_s

        if count > rule.threshold:
            _execute_rule_action(rule, alert)

    elif rule.condition == "attack_severity":
        # Match on incoming alert's severity
        if alert.severity == rule.severity:
            _execute_rule_action(rule, alert)
```

### Rule Actions

| Action | Behavior |
|--------|----------|
| `create_incident` | Creates a new Incident row, links current alert via `incident_id` |
| `escalate_severity` | Updates `alert.severity` one level up (low→medium→high→critical) |
| `notify` | Triggers immediate notification to all enabled channels |

### Example Rule Configuration

```json
{
  "name": "DDoS Surge",
  "condition": "attack_count",
  "threshold": 10,
  "time_window_s": 60,
  "attack_type": "DDoS",
  "action": "create_incident",
  "severity": null,
  "enabled": true
}
```

```json
{
  "name": "Critical Auto-Escalate",
  "condition": "attack_severity",
  "threshold": null,
  "time_window_s": null,
  "severity": "critical",
  "action": "notify",
  "enabled": true
}
```

## Deduplication Window

The 300-second deduplication window prevents alert storms from a single attacking host. Key properties:

- **Per (src_ip, attack_type) pair** — different attack types from the same IP are not deduplicated against each other
- **Rolling window** — each new unique alert resets the 5-minute window for that pair
- **Counted, not dropped silently** — duplicates are logged at DEBUG level with count

```python
# alert_service.py
async def check_duplicate(self, src_ip: str, attack_type: str, window_seconds: int = 300) -> bool:
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    result = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.src_ip == src_ip)
        .where(Alert.attack_type == attack_type)
        .where(Alert.timestamp >= cutoff)
    )
    count = result.scalar()
    if count > 0:
        logger.debug(f"Duplicate alert suppressed: {src_ip} / {attack_type} ({count} in window)")
        return True
    return False
```
