"""GET /api/alerts reports pagination metadata in response headers."""

import pytest

import src.inference_server.database as db_module
from src.inference_server.models import Alert

from tests.test_api_serialization import api  # noqa: F401  (fixture)


async def _seed(n_high, n_low=0):
    async with db_module.async_session_maker() as session:
        for i in range(n_high):
            session.add(Alert(attack_type="DDoS", severity="high", src_ip=f"10.0.0.{i}", dst_ip="10.0.1.1"))
        for i in range(n_low):
            session.add(Alert(attack_type="Scan", severity="low", src_ip=f"10.1.0.{i}", dst_ip="10.0.1.1"))
        await session.commit()


@pytest.mark.asyncio
async def test_first_page_headers(api):  # noqa: F811
    await _seed(5)
    r = await api.get("/api/alerts", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "5"
    assert r.headers["X-Page-Size"] == "2"
    assert r.headers["X-Page-Offset"] == "0"


@pytest.mark.asyncio
async def test_last_page_is_short_and_total_unchanged(api):  # noqa: F811
    await _seed(5)
    r = await api.get("/api/alerts", params={"limit": 2, "offset": 4})
    assert len(r.json()) == 1
    assert r.headers["X-Total-Count"] == "5"
    assert r.headers["X-Page-Offset"] == "4"


@pytest.mark.asyncio
async def test_total_respects_filters(api):  # noqa: F811
    await _seed(3, n_low=4)
    r = await api.get("/api/alerts", params={"severity": "low", "limit": 1})
    assert len(r.json()) == 1
    assert r.headers["X-Total-Count"] == "4"


@pytest.mark.asyncio
async def test_no_params_is_backward_compatible(api):  # noqa: F811
    await _seed(2)
    r = await api.get("/api/alerts")
    assert isinstance(r.json(), list) and len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "2"


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"limit": -1}, {"offset": -1}, {"limit": "abc"}, {"limit": 5000}])
async def test_invalid_params_rejected(api, params):  # noqa: F811
    r = await api.get("/api/alerts", params=params)
    assert r.status_code == 422
