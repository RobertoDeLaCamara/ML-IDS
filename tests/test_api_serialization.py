"""Regression tests: alerts and incidents that exist in the database must serialise.

The response schemas declared the timestamp fields as ``str`` while the ORM hands back ``datetime``,
so every list/get endpoint answered 500 (ResponseValidationError) as soon as one row existed.
"""

import os
import sys

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.inference_server.database as db_module
from src.inference_server.main import app
from src.inference_server.models import Alert, Incident


@pytest_asyncio.fixture
async def api(tmp_path, monkeypatch):
    """An ASGI client wired to a fresh SQLite database, with authentication off."""
    monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "false")
    monkeypatch.setattr(db_module, "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    assert await db_module.init_db()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await db_module.close_db()


@pytest.mark.asyncio
async def test_alert_endpoints_serialise_stored_alerts(api):
    async with db_module.async_session_maker() as session:
        session.add(Alert(attack_type="DDoS", severity="high", src_ip="10.0.0.1", dst_ip="10.0.0.2"))
        await session.commit()

    listed = await api.get("/api/alerts")
    assert listed.status_code == 200
    alert = listed.json()[0]
    assert isinstance(alert["timestamp"], str) and "T" in alert["timestamp"]

    single = await api.get(f"/api/alerts/{alert['id']}")
    assert single.status_code == 200
    assert single.json()["timestamp"] == alert["timestamp"]


@pytest.mark.asyncio
async def test_incident_endpoints_serialise_stored_incidents(api):
    async with db_module.async_session_maker() as session:
        session.add(Incident(title="Scan from 10.0.0.1", severity="medium", status="open"))
        await session.commit()

    listed = await api.get("/api/incidents")
    assert listed.status_code == 200
    incident = listed.json()[0]
    assert isinstance(incident["created_at"], str) and "T" in incident["created_at"]
    assert incident["resolved_at"] is None

    single = await api.get(f"/api/incidents/{incident['id']}")
    assert single.status_code == 200
