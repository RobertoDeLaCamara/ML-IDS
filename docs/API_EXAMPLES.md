# API usage examples (Python)

Runnable examples for the ML-IDS inference server using [`requests`](https://requests.readthedocs.io/) and [`websockets`](https://websockets.readthedocs.io/). For the endpoint reference see [API.md](API.md) or the live Swagger UI at `/docs`.

```bash
pip install requests websockets
```

Every snippet is a complete script. They read two environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MLIDS_URL` | `http://localhost:8000` | Base URL of the inference server |
| `MLIDS_API_KEY` | _(empty)_ | One of the keys in the server's `ML_IDS_API_KEYS` |

## Authentication

When `ML_IDS_AUTH_ENABLED` is true (the default) and `ML_IDS_API_KEYS` is set, every endpoint except `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/openapi.yaml`, `/metrics` and `/dashboard/*` requires an `X-API-Key` header. A missing or wrong key returns `401` with `{"detail": "Missing X-API-Key header"}` or `{"detail": "Invalid API key"}`. WebSockets take the key as an `api_key` query parameter instead (see below).

A shared session keeps the header and a timeout in one place; the other examples build on this pattern.

```python
import os
import requests

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")

session = requests.Session()
if API_KEY:
    session.headers["X-API-Key"] = API_KEY

try:
    resp = session.get(f"{BASE_URL}/api/alerts", params={"limit": 1}, timeout=10)
    if resp.status_code == 401:
        print("Authentication failed:", resp.json()["detail"])
    else:
        resp.raise_for_status()
        print("Authenticated OK")
except requests.RequestException as exc:
    print("Request failed:", exc)
```

## `GET /health`

Public, no key needed.

```python
import os
import requests

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")

try:
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    resp.raise_for_status()
    print(resp.json())
except requests.RequestException as exc:
    print("Health check failed:", exc)
```

Expected response:

```json
{
  "status": "healthy",
  "model_initialized": true,
  "model_source": "mlflow",
  "model_loaded_at": "2026-10-18T14:00:00.000000",
  "database": {"database": "healthy"}
}
```

`status` is `degraded` when the database is unavailable (predictions still work) and `unhealthy` when it is failing. `model_source` is `mlflow`, `cache` or `none`.

## `POST /predict` — single prediction

The body holds CICFlowMeter features in snake_case (see `PredictionRequest` in `src/inference_server/schemas.py`). Omitted features default to `0.0`; values must be numbers. `src_ip` is optional and is used on the alert if the flow is classified as an attack.

```python
import os
import requests

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")
headers = {"X-API-Key": API_KEY} if API_KEY else {}

flow = {
    "src_ip": "192.168.1.100",
    "flow_duration": 1200000,
    "tot_fwd_pkts": 10,
    "tot_bwd_pkts": 8,
    "flow_byts_s": 5400.5,
    "flow_pkts_s": 15.0,
    "syn_flag_cnt": 1,
    "ack_flag_cnt": 1,
}

try:
    resp = requests.post(f"{BASE_URL}/predict", json=flow, headers=headers, timeout=10)
    if resp.status_code == 422:
        print("Invalid features:", resp.json()["detail"])
    elif resp.status_code == 503:
        print("Model not available yet:", resp.json()["detail"])
    else:
        resp.raise_for_status()
        print(resp.json())
except requests.RequestException as exc:
    print("Request failed:", exc)
```

Expected response (`0` is benign, anything else is the predicted attack class):

```json
{"prediction": [0]}
```

When the request carries suspicious values the response may also include `"validation_warnings": [...]`. A non-zero prediction creates an alert (see below).

## `POST /predict` — batch prediction

The server has no batch endpoint: one request scores one flow. To score many flows, loop over them on the client and reuse a `Session` so the TCP connection is kept alive.

```python
import os
import requests

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")

flows = [
    {"src_ip": "10.0.0.5", "flow_duration": 3000, "tot_fwd_pkts": 2, "tot_bwd_pkts": 0},
    {"src_ip": "10.0.0.6", "flow_duration": 98000, "tot_fwd_pkts": 40, "tot_bwd_pkts": 35},
    {"src_ip": "10.0.0.7", "flow_duration": 120, "tot_fwd_pkts": 900, "tot_bwd_pkts": 0},
]

results = []
with requests.Session() as session:
    if API_KEY:
        session.headers["X-API-Key"] = API_KEY
    for flow in flows:
        try:
            resp = session.post(f"{BASE_URL}/predict", json=flow, timeout=10)
            resp.raise_for_status()
            results.append((flow["src_ip"], resp.json()["prediction"][0]))
        except requests.RequestException as exc:
            results.append((flow["src_ip"], f"error: {exc}"))

for src_ip, outcome in results:
    print(f"{src_ip}: {outcome}")
```

Example output (the labels depend on the active model; `0` is benign):

```text
10.0.0.5: 0
10.0.0.6: 3
10.0.0.7: 0
```

## `GET /api/alerts` — list and filter

Query parameters, all optional: `severity`, `src_ip`, `attack_type`, `acknowledged` (`true`/`false`), `hours` (look-back window, default `24`), `limit` (default `100`, max `1000`) and `offset` (default `0`). The response is a JSON array, newest first.

```python
import os
import requests

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")
headers = {"X-API-Key": API_KEY} if API_KEY else {}

params = {"severity": "high", "acknowledged": "false", "hours": 72, "limit": 50}

try:
    resp = requests.get(f"{BASE_URL}/api/alerts", params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    for alert in resp.json():
        print(alert["id"], alert["timestamp"], alert["src_ip"], alert["attack_type"])
except requests.RequestException as exc:
    print("Request failed:", exc)
```

Expected response:

```json
[
  {
    "id": 42,
    "attack_type": "DDoS",
    "severity": "high",
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.50",
    "timestamp": "2026-10-18T13:55:10",
    "prediction_score": null,
    "acknowledged": false,
    "incident_id": null,
    "notes": null
  }
]
```

To page through everything, increase `offset` by `limit` until `offset` reaches the `X-Total-Count` response header (also available: `X-Page-Size`, `X-Page-Offset`). Individual alerts are managed with `GET /api/alerts/{id}`, `PUT /api/alerts/{id}`, `POST /api/alerts/{id}/acknowledge` and `DELETE /api/alerts/{id}`.

## `WS /api/dashboard/live` — live alerts

Pass the key as the `api_key` query parameter. A missing or invalid key makes the server reject the connection (HTTP `403` during the handshake).

```python
import asyncio
import json
import os

import websockets

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")

ws_url = BASE_URL.replace("http", "ws", 1) + "/api/dashboard/live"
if API_KEY:
    ws_url += f"?api_key={API_KEY}"


async def listen() -> None:
    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            print("Connected, waiting for alerts (Ctrl+C to stop)")
            async for raw in ws:
                try:
                    print(json.loads(raw))
                except json.JSONDecodeError:
                    print("Non-JSON message:", raw)
    except websockets.InvalidStatus as exc:
        if exc.response.status_code == 403:
            print("Unauthorized: check MLIDS_API_KEY")
        else:
            print("Server rejected the connection:", exc)
    except websockets.ConnectionClosed as exc:
        print("Connection closed:", exc)
    except OSError as exc:
        print("Could not connect:", exc)


try:
    asyncio.run(listen())
except KeyboardInterrupt:
    pass
```

The server pushes an event whenever an alert is created, so the output is empty until a prediction classifies a flow as an attack.

## Error handling patterns

Use a timeout on every call, retry only what is safe to retry (connection errors and `502`/`503`/`504`, never a `4xx`), and surface the server's `detail` field when a request is rejected.

```python
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = os.environ.get("MLIDS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MLIDS_API_KEY", "")


def make_session() -> requests.Session:
    """Session with an API key and retries on connection errors and 502/503/504."""
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(502, 503, 504),
        allowed_methods=None,  # also retry POST: /predict has no side effect besides the alert it may create
    )
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    if API_KEY:
        session.headers["X-API-Key"] = API_KEY
    return session


def describe_error(resp: requests.Response) -> str:
    """Extract FastAPI's `detail` (a string, or a list for 422 validation errors)."""
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text
    if isinstance(detail, list):
        return "; ".join(f"{'.'.join(map(str, e.get('loc', [])))}: {e.get('msg')}" for e in detail)
    return str(detail)


session = make_session()
try:
    resp = session.post(f"{BASE_URL}/predict", json={"flow_duration": "not-a-number"}, timeout=(3, 10))
    if resp.ok:
        print(resp.json())
    else:
        print(f"HTTP {resp.status_code}: {describe_error(resp)}")
except requests.ConnectTimeout:
    print("Could not reach the server in time")
except requests.ReadTimeout:
    print("Server accepted the connection but did not answer in time")
except requests.RequestException as exc:
    print("Request failed:", exc)
```

Status codes you can expect:

| Code | Meaning |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `404` | Alert or incident not found |
| `422` | Request body or query parameters failed validation |
| `500` | Prediction failed inside the server (`detail` has the cause) |
| `503` | No model available (MLflow unreachable and no local cache) |
