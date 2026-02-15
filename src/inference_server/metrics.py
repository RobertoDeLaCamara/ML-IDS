"""Prometheus metrics for ML-IDS inference server."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Counters
PREDICTIONS_TOTAL = Counter(
    "mlids_predictions_total",
    "Total number of predictions made",
    ["result"],
)

ALERTS_CREATED_TOTAL = Counter(
    "mlids_alerts_created_total",
    "Total alerts created",
    ["severity"],
)

# Histograms
PREDICTION_LATENCY = Histogram(
    "mlids_prediction_latency_seconds",
    "Time spent on model prediction",
)

REQUEST_DURATION = Histogram(
    "mlids_request_duration_seconds",
    "Total HTTP request duration",
)

# Gauges
MODEL_LOADED = Gauge(
    "mlids_model_loaded",
    "Whether the ML model is currently loaded (1=yes, 0=no)",
)

ACTIVE_WS_CONNECTIONS = Gauge(
    "mlids_active_websocket_connections",
    "Number of active WebSocket connections",
)


def metrics_response() -> Response:
    """Generate a Prometheus-compatible metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
