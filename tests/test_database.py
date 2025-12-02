"""
Tests for database models and operations.
"""

import pytest
import pytest_asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.inference_server.database import init_db, get_db, close_db
from src.inference_server.models import (
    Alert, Incident, Metric, NotificationChannel, AlertRule,
    SeverityLevel, IncidentStatus, NotificationChannelType
)
from sqlalchemy import select


# Set test database URL
os.environ["DATABASE_URL"] = "postgresql+asyncpg://mlids:mlids_password@localhost:5432/mlids_test"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create test database session"""
    # Initialize database
    await init_db()
    
    # Get session
    async for session in get_db():
        yield session
        break
    
    # Cleanup
    await close_db()


@pytest.mark.asyncio
async def test_create_alert(db_session):
    """Test creating an alert"""
    if db_session is None:
        pytest.skip("Database not available")
    
    alert = Alert(
        attack_type="DDoS",
        severity=SeverityLevel.HIGH,
        src_ip="192.168.1.100",
        dst_ip="10.0.0.50",
        features={"flow_duration": 1000, "tot_fwd_pkts": 100},
        prediction_score=0.95
    )
    
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    
    assert alert.id is not None
    assert alert.attack_type == "DDoS"
    assert alert.severity == SeverityLevel.HIGH
    assert alert.src_ip == "192.168.1.100"


@pytest.mark.asyncio
async def test_create_incident(db_session):
    """Test creating an incident"""
    if db_session is None:
        pytest.skip("Database not available")
    
    incident = Incident(
        title="Multiple DDoS Attacks",
        description="Several DDoS attacks detected from same source",
        status=IncidentStatus.OPEN,
        severity=SeverityLevel.HIGH
    )
    
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    
    assert incident.id is not None
    assert incident.title == "Multiple DDoS Attacks"
    assert incident.status == IncidentStatus.OPEN


@pytest.mark.asyncio
async def test_alert_incident_relationship(db_session):
    """Test relationship between alerts and incidents"""
    if db_session is None:
        pytest.skip("Database not available")
    
    # Create incident
    incident = Incident(
        title="Test Incident",
        status=IncidentStatus.INVESTIGATING,
        severity=SeverityLevel.CRITICAL
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    
    # Create alert linked to incident
    alert = Alert(
        attack_type="SQL Injection",
        severity=SeverityLevel.CRITICAL,
        src_ip="1.2.3.4",
        incident_id=incident.id
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    
    # Verify relationship
    assert alert.incident_id == incident.id
    
    # Query incident with alerts
    result = await db_session.execute(
        select(Incident).where(Incident.id == incident.id)
    )
    incident_with_alerts = result.scalar_one()
    
    # Note: Need to explicitly load relationship in async
    assert incident_with_alerts.id == incident.id


@pytest.mark.asyncio
async def test_create_metric(db_session):
    """Test creating a metric"""
    if db_session is None:
        pytest.skip("Database not available")
    
    metric = Metric(
        metric_name="attacks_per_hour",
        value=42.0,
        tags={"attack_type": "DDoS", "severity": "high"}
    )
    
    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)
    
    assert metric.id is not None
    assert metric.metric_name == "attacks_per_hour"
    assert metric.value == 42.0


@pytest.mark.asyncio
async def test_create_notification_channel(db_session):
    """Test creating a notification channel"""
    if db_session is None:
        pytest.skip("Database not available")
    
    channel = NotificationChannel(
        name="Test Slack Channel",
        channel_type=NotificationChannelType.SLACK,
        config={"webhook_url": "https://hooks.slack.com/test"},
        enabled=True
    )
    
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    assert channel.id is not None
    assert channel.name == "Test Slack Channel"
    assert channel.channel_type == NotificationChannelType.SLACK


@pytest.mark.asyncio
async def test_create_alert_rule(db_session):
    """Test creating an alert rule"""
    if db_session is None:
        pytest.skip("Database not available")
    
    rule = AlertRule(
        name="Test Rule",
        description="Test alert rule",
        condition="attack_count > threshold",
        threshold=5.0,
        time_window_seconds=60,
        action="create_incident",
        severity=SeverityLevel.HIGH,
        enabled=True
    )
    
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    
    assert rule.id is not None
    assert rule.name == "Test Rule"
    assert rule.threshold == 5.0


@pytest.mark.asyncio
async def test_query_alerts_by_severity(db_session):
    """Test querying alerts by severity"""
    if db_session is None:
        pytest.skip("Database not available")
    
    # Create alerts with different severities
    for i, severity in enumerate([SeverityLevel.LOW, SeverityLevel.HIGH, SeverityLevel.CRITICAL]):
        alert = Alert(
            attack_type=f"Attack{i}",
            severity=severity,
            src_ip=f"192.168.1.{i}"
        )
        db_session.add(alert)
    
    await db_session.commit()
    
    # Query high severity alerts
    result = await db_session.execute(
        select(Alert).where(Alert.severity == SeverityLevel.HIGH)
    )
    high_alerts = result.scalars().all()
    
    assert len(high_alerts) >= 1
    assert all(a.severity == SeverityLevel.HIGH for a in high_alerts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
