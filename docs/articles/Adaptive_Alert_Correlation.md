# Database-Driven Alert Correlation: Moving Alert Rules Out of Code

When an IDS alert fires, two questions matter immediately: is this alert new information, or is it noise? And if it's real, does it belong to a larger campaign? The original Cognitive-Intrusion-Detection-System answered both questions with hardcoded logic. ML-IDS answers both with database rows that can be modified without redeployment.

---

## The Problem with Hardcoded Rules

The CIDS codebase contained alert rules as Python conditionals scattered through `alert_service.py`:

```python
# CIDS: hardcoded
if attack_type == "DDoS" and count_recent_alerts(src_ip, 60) > 10:
    create_incident(...)
```

This works until an operator needs to tune the threshold during an active incident. The answer in a hardcoded system: modify the file, redeploy the container, hope the incident is still ongoing when the new code lands. In a real SOC environment, incident response and deployment pipelines are on different timescales.

ML-IDS moves rules to the database:

```sql
INSERT INTO alert_rules (name, condition, threshold, time_window_s, attack_type, action, enabled)
VALUES ('DDoS Surge', 'attack_count', 10, 60, 'DDoS', 'create_incident', true);
```

Changing the threshold from 10 to 5 during an active incident is a one-query UPDATE. No redeploy, no service interruption.

---

## The Three Rule Conditions

ML-IDS implements three condition types that cover the majority of correlation scenarios:

### 1. attack_count

Count-based threshold within a time window:

```sql
SELECT count(*) FROM alerts
WHERE timestamp > now() - interval '60 seconds'
AND attack_type = 'DDoS'
```

Use case: "If we see more than N DDoS alerts in M seconds, this is a coordinated campaign — create an incident."

### 2. unique_attack_types

Distinct attack type count within a time window:

```sql
SELECT count(DISTINCT attack_type) FROM alerts
WHERE timestamp > now() - interval '300 seconds'
```

Use case: "If we see 5 different attack types in 5 minutes, this looks like a multistage intrusion — escalate severity." A single attacker probing with PortScan, then trying SSH-Patator, then Web Attack XSS in rapid succession triggers this rule even if none of the individual counts cross their own thresholds.

### 3. attack_severity

Direct match on the incoming alert's severity:

```python
if alert.severity == rule.severity:
    _execute_rule_action(rule, alert)
```

Use case: "Every critical alert should immediately trigger notification to the on-call channel, regardless of count." This is the simplest condition — no database query needed, evaluated inline.

---

## Three Actions

Each rule specifies one action:

**create_incident**: A new Incident row is created with the current alert linked. Subsequent related alerts can be linked to the same incident via the API. This turns a stream of alerts into a structured investigation record.

**escalate_severity**: The current alert's severity is bumped one level (medium → high, high → critical). This does not affect historical alerts or severity statistics — only the current alert object. The escalated severity propagates to Monitoring Service metrics and WebSocket broadcasts.

**notify**: Triggers `send_notifications(alert)` immediately, dispatching to all enabled notification channels. Useful when a rule condition represents a threshold that warrants immediate human attention regardless of normal notification timing.

---

## Alert Deduplication

Before any rule evaluation happens, the dedup check runs:

```python
async def check_duplicate(self, src_ip: str, attack_type: str, window_seconds: int = 300) -> bool:
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    count = await db.scalar(
        select(func.count(Alert.id))
        .where(Alert.src_ip == src_ip)
        .where(Alert.attack_type == attack_type)
        .where(Alert.timestamp >= cutoff)
    )
    return count > 0
```

The 300-second window is per `(src_ip, attack_type)` pair. If a host at 10.0.0.1 sends both DDoS and PortScan traffic, both alert types are tracked independently — the DDoS dedup window does not suppress the PortScan alert. This matters for the `unique_attack_types` condition: dedup prevents the same attack type from being counted multiple times, but different attack types from the same source still contribute distinct counts.

The dedup check is a fast indexed query (indexes on `src_ip` and `timestamp`). At high prediction rates, it runs on every positive prediction.

---

## Incident Correlation

The `create_incident` action does the minimum necessary: it creates an Incident row and links the triggering alert. The system does not attempt to automatically link subsequent related alerts to the same incident — that correlation requires human judgment about what "related" means in context.

The incident lifecycle supports four states:

```
open → investigating → resolved → closed
```

Operators move incidents through states via the API. Resolved incidents remain in the database for post-incident analysis. The `src_ips` JSON column on the Incident table stores the accumulated set of source IPs linked to that incident as alerts are manually associated.

This intentionally minimal correlation model avoids the false-negative risk of an automated system that groups attacks incorrectly and hides them under a single incident that gets dismissed.

---

## Notification Channels as Database Rows

The same "move configuration from code to database" principle applies to notification channels. In CIDS, the SMTP credentials were environment variables. In ML-IDS, each channel is a row:

```json
{
  "name": "slack-soc",
  "channel_type": "slack",
  "config": {"webhook_url": "..."},
  "enabled": true
}
```

Adding a PagerDuty webhook during an incident, disabling a noisy SMTP channel that's bouncing, or testing a new Slack destination are all API calls with immediate effect. The dispatcher queries `notification_channels WHERE enabled = true` on every alert — there is no startup caching that would cause a channel change to miss an alert.

---

## Operational Tradeoffs

The database-driven approach introduces a tradeoff: every alert now triggers additional database queries (dedup check + rule fetch + rule condition queries). For a deployment processing thousands of flows per second, this overhead can matter.

ML-IDS is designed for deployment where CICFlowMeter sends one HTTP POST per completed flow, not one per packet. Typical flow completion rates for monitoring a network segment are in the range of hundreds per second, not thousands. The additional queries (2–5 per alert, fast indexed reads) are well within PostgreSQL's capacity at that rate.

For higher-throughput deployments, the rule set could be cached in memory with a short TTL (30–60 seconds) to eliminate the per-alert rule fetch. The dedup check cannot be cached this way — it needs the actual alert timestamp data — but could be moved to an in-memory counter structure (e.g., a sliding window counter per `(src_ip, attack_type)`) if the database query becomes a bottleneck.

---

## Implementation Reference

| Component | File |
|-----------|------|
| Rule evaluation loop | `src/inference_server/alert_service.py: evaluate_alert_rules()` |
| Dedup check | `src/inference_server/alert_service.py: check_duplicate()` |
| Severity classification | `src/inference_server/alert_service.py: classify_severity()` |
| Notification dispatch | `src/inference_server/notifications.py: send_notifications()` |
| ORM models | `src/inference_server/models.py: AlertRule, NotificationChannel, Incident` |
| Rule CRUD API | `src/inference_server/routers/alerts.py` |
| Incident CRUD API | `src/inference_server/routers/incidents.py` |
| Rule eval tests | `tests/test_database.py` |
| Auth tests (44 total) | `tests/test_auth.py` (18), `tests/test_validation.py` (15) |
