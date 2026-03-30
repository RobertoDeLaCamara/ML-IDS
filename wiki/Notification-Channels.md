# Notification Channels

## Overview

Notification channels are stored as rows in the `notification_channels` table and loaded at runtime. Add, enable, disable, or modify channels without restarting the service.

```sql
CREATE TABLE notification_channels (
    id           INTEGER PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    channel_type VARCHAR(20) NOT NULL,  -- "smtp" | "slack" | "webhook"
    config       JSON NOT NULL,         -- channel-specific settings
    enabled      BOOLEAN DEFAULT true,
    created_at   TIMESTAMP DEFAULT now()
);
```

## Channel Types

### SMTP (Email)

```json
{
  "channel_type": "smtp",
  "config": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "alerts@example.com",
    "smtp_password": "secret",
    "smtp_use_tls": true,
    "from_email": "alerts@example.com",
    "to_emails": ["soc@example.com", "oncall@example.com"]
  }
}
```

Email format:
- Subject: `[ML-IDS] {severity.upper()} Alert: {attack_type} from {src_ip}`
- Body: plain text with alert fields + link to dashboard

### Slack Webhook

```json
{
  "channel_type": "slack",
  "config": {
    "webhook_url": "https://hooks.slack.com/services/T.../B.../...",
    "channel": "#security-alerts",
    "username": "ML-IDS Bot",
    "icon_emoji": ":warning:"
  }
}
```

Slack payload:
```json
{
  "channel": "#security-alerts",
  "username": "ML-IDS Bot",
  "text": "*[CRITICAL]* DDoS attack detected from 10.0.0.1",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Attack Type", "value": "DDoS", "short": true},
      {"title": "Confidence", "value": "0.97", "short": true},
      {"title": "Source IP", "value": "10.0.0.1", "short": true},
      {"title": "Severity", "value": "critical", "short": true}
    ]
  }]
}
```

Color mapping: `critical` → `danger`, `high` → `warning`, `medium` → `good`, `low` → `#439FE0`

### Generic Webhook

```json
{
  "channel_type": "webhook",
  "config": {
    "url": "https://your-siem.example.com/api/ingest",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer <token>",
      "Content-Type": "application/json"
    },
    "timeout_seconds": 10
  }
}
```

Payload: full alert JSON object as returned by `GET /api/alerts/{id}`.

## Dispatch Flow

```python
# notifications.py

async def send_notifications(alert: Alert):
    channels = await db.execute(
        select(NotificationChannel).where(NotificationChannel.enabled == True)
    )
    tasks = [send_to_channel(channel, alert) for channel in channels.scalars()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for channel, result in zip(channels.scalars(), results):
        if isinstance(result, Exception):
            logger.error(f"Notification failed [{channel.name}]: {result}")
        # Failures are logged but do not block other channels
```

All enabled channels dispatch concurrently via `asyncio.gather`. A failure in one channel does not affect others.

## Managing Channels via API

```bash
# List all channels
curl http://localhost:8000/api/notification-channels \
  -H "X-API-Key: <key>"

# Create a Slack channel
curl -X POST http://localhost:8000/api/notification-channels \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "slack-soc",
    "channel_type": "slack",
    "config": {"webhook_url": "https://hooks.slack.com/..."},
    "enabled": true
  }'

# Disable a channel (without deleting)
curl -X PATCH http://localhost:8000/api/notification-channels/1 \
  -H "X-API-Key: <key>" \
  -d '{"enabled": false}'

# Delete a channel
curl -X DELETE http://localhost:8000/api/notification-channels/1 \
  -H "X-API-Key: <key>"
```

## Severity Filtering

Each channel receives all alerts regardless of severity. To filter by severity, use an alert rule with `action: notify` and a severity condition to trigger targeted notifications. Example: notify only on `critical`:

```json
{
  "name": "Critical Notify",
  "condition": "attack_severity",
  "severity": "critical",
  "action": "notify",
  "enabled": true
}
```

Without such a rule, all alerts trigger notifications to all enabled channels.

## Retry Behavior

No automatic retry. If a channel fails (network error, HTTP 4xx/5xx, SMTP reject), the failure is logged and the alert is marked as delivered to remaining channels. Implement retry at the receiving end (e.g., Slack retry for webhook delivery) rather than in ML-IDS.
