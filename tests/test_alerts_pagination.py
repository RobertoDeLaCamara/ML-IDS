from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pytest
import sys
import os
import numpy as np
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock MLflow before importing app (same pattern as existing tests)
with patch('mlflow.set_tracking_uri'), \
     patch('mlflow.sklearn.load_model') as mock_load_model:
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([0])
    mock_model.feature_names_in_ = ['Flow Duration', 'Total Fwd Packet']
    mock_load_model.return_value = mock_model
    
    from src.inference_server.main import app

from src.inference_server.database import get_db
from src.inference_server.models import Base, Alert, SeverityLevel

# Test database - in-memory SQLite (fast, disposable)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """Replacement for get_db that uses our test database."""
    async with test_session_maker() as session:
        yield session


@pytest.fixture(autouse=True)
def setup_database():
    """
    Before each test: create tables, insert 25 test alerts, override get_db.
    After each test: drop tables so next test starts clean.
    """
    import asyncio

    async def setup():
        # Create all tables in the test database
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Insert 25 test alerts
        async with test_session_maker() as session:
            for i in range(25):
                alert = Alert(
                    attack_type="DDoS" if i % 2 == 0 else "PortScan",
                    severity=SeverityLevel.HIGH if i % 2 == 0 else SeverityLevel.LOW,
                    src_ip=f"192.168.1.{i}",
                    dst_ip=f"10.0.0.{i}",
                    prediction_score=0.95,
                    acknowledged=False,
                )
                session.add(alert)
            await session.commit()

    async def teardown():
        # Drop all tables — clean slate for next test
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # Run setup
    asyncio.run(setup())

    # Override the app's get_db with our test version
    app.dependency_overrides[get_db] = override_get_db

    yield  # --- test runs here ---

    # Run cleanup
    app.dependency_overrides.clear()
    asyncio.run(teardown())


# Create test client
client = TestClient(app)

def test_default_pagination():
    """No params — should return first page with default limit of 20."""
    response = client.get("/api/alerts")

    assert response.status_code == 200

    data = response.json()
    assert len(data["alerts"]) == 20
    assert data["total"] == 25
    assert data["limit"] == 20
    assert data["offset"] == 0

    # Check pagination headers
    assert response.headers["X-Total-Count"] == "25"
    assert response.headers["X-Page-Size"] == "20"
    assert response.headers["X-Page-Offset"] == "0"

def test_explicit_first_page():
    """Explicit limit=10, offset=0 — should return first 10 of 25 alerts."""
    response = client.get("/api/alerts?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 10
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 0

    # Check pagination headers
    assert response.headers["X-Total-Count"] == "25"
    assert response.headers["X-Page-Size"] == "10"
    assert response.headers["X-Page-Offset"] == "0"

def test_second_page():
    """limit=10, offset=10 — should return alerts 11-20 of 25."""
    response = client.get("/api/alerts?limit=10&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 10
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 10

    # Check pagination headers
    assert response.headers["X-Total-Count"] == "25"
    assert response.headers["X-Page-Size"] == "10"
    assert response.headers["X-Page-Offset"] == "10"

def test_last_page():
    """limit=10, offset=20 — should return alerts 21-25 of 25."""
    response = client.get("/api/alerts?limit=10&offset=20")
    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 5
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 20

    # Check pagination headers
    assert response.headers["X-Total-Count"] == "25"
    assert response.headers["X-Page-Size"] == "10"
    assert response.headers["X-Page-Offset"] == "20"

def test_offset_beyond_total():
    """offset beyond total data — should return empty list with correct total."""
    response = client.get("/api/alerts?limit=10&offset=100")
    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 0
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 100

def test_invalid_negative_limit():
    """Negative limit — should return 400."""
    response = client.get("/api/alerts?limit=-1")
    assert response.status_code == 400

def test_invalid_negative_offset():
    """Negative offset — should return 400."""
    response = client.get("/api/alerts?offset=-1")
    assert response.status_code == 400