"""
API router for dashboard endpoints.

Provides statistics, timeline data, and real-time updates for the dashboard.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Alert, Incident, Metric, SeverityLevel, IncidentStatus
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall dashboard statistics.
    
    Returns:
        - Total alerts in time period
        - Total incidents
        - Alerts by severity
        - Active incidents
    """
    if db is None:
        return {
            "error": "Database not available",
            "total_alerts": 0,
            "total_incidents": 0,
            "alerts_by_severity": {},
            "active_incidents": 0
        }
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Total alerts
    total_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.timestamp >= cutoff_time)
    )
    total_alerts = total_alerts_result.scalar() or 0
    
    # Total incidents
    total_incidents_result = await db.execute(
        select(func.count(Incident.id)).where(Incident.created_at >= cutoff_time)
    )
    total_incidents = total_incidents_result.scalar() or 0
    
    # Alerts by severity
    severity_result = await db.execute(
        select(
            Alert.severity,
            func.count(Alert.id)
        ).where(
            Alert.timestamp >= cutoff_time
        ).group_by(Alert.severity)
    )
    alerts_by_severity = {
        str(severity.value): count
        for severity, count in severity_result.all()
    }
    
    # Active incidents (open or investigating)
    active_incidents_result = await db.execute(
        select(func.count(Incident.id)).where(
            and_(
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                Incident.created_at >= cutoff_time
            )
        )
    )
    active_incidents = active_incidents_result.scalar() or 0
    
    return {
        "total_alerts": total_alerts,
        "total_incidents": total_incidents,
        "alerts_by_severity": alerts_by_severity,
        "active_incidents": active_incidents,
        "time_period_hours": hours
    }


@router.get("/attack-timeline")
async def get_attack_timeline(
    hours: int = Query(24, description="Number of hours to look back"),
    interval_minutes: int = Query(60, description="Time interval in minutes"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get attack timeline data for charts.
    
    Returns time-series data of attacks per interval.
    """
    if db is None:
        return {"error": "Database not available", "data": []}
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all alerts in time range
    result = await db.execute(
        select(Alert.timestamp, Alert.severity).where(
            Alert.timestamp >= cutoff_time
        ).order_by(Alert.timestamp)
    )
    alerts = result.all()
    
    # Group by time intervals
    interval_delta = timedelta(minutes=interval_minutes)
    timeline_data = []
    
    current_time = cutoff_time
    end_time = datetime.utcnow()
    
    while current_time < end_time:
        interval_end = current_time + interval_delta
        
        # Count alerts in this interval
        interval_alerts = [
            a for a in alerts
            if current_time <= a.timestamp < interval_end
        ]
        
        timeline_data.append({
            "timestamp": current_time.isoformat(),
            "count": len(interval_alerts),
            "critical": sum(1 for a in interval_alerts if a.severity == SeverityLevel.CRITICAL),
            "high": sum(1 for a in interval_alerts if a.severity == SeverityLevel.HIGH),
            "medium": sum(1 for a in interval_alerts if a.severity == SeverityLevel.MEDIUM),
            "low": sum(1 for a in interval_alerts if a.severity == SeverityLevel.LOW)
        })
        
        current_time = interval_end
    
    return {"data": timeline_data}


@router.get("/top-attackers")
async def get_top_attackers(
    hours: int = Query(24, description="Number of hours to look back"),
    limit: int = Query(10, description="Maximum number of attackers"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top attacking source IPs.
    
    Returns list of IPs with attack counts and severities.
    """
    if db is None:
        return {"error": "Database not available", "attackers": []}
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by source IP and count attacks
    result = await db.execute(
        select(
            Alert.src_ip,
            func.count(Alert.id).label('attack_count'),
            func.max(Alert.severity).label('max_severity')
        ).where(
            Alert.timestamp >= cutoff_time
        ).group_by(
            Alert.src_ip
        ).order_by(
            desc('attack_count')
        ).limit(limit)
    )
    
    attackers = []
    for src_ip, count, max_severity in result.all():
        attackers.append({
            "src_ip": src_ip,
            "attack_count": count,
            "max_severity": max_severity.value if max_severity else "unknown"
        })
    
    return {"attackers": attackers}


@router.get("/attack-distribution")
async def get_attack_distribution(
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get distribution of attack types.
    
    Returns attack types with counts for pie/bar charts.
    """
    if db is None:
        return {"error": "Database not available", "distribution": []}
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by attack type
    result = await db.execute(
        select(
            Alert.attack_type,
            func.count(Alert.id).label('count')
        ).where(
            Alert.timestamp >= cutoff_time
        ).group_by(
            Alert.attack_type
        ).order_by(
            desc('count')
        )
    )
    
    distribution = [
        {"attack_type": attack_type, "count": count}
        for attack_type, count in result.all()
    ]
    
    return {"distribution": distribution}


@router.get("/recent-alerts")
async def get_recent_alerts(
    limit: int = Query(20, description="Maximum number of alerts"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most recent alerts for the alert feed.
    """
    if db is None:
        return {"error": "Database not available", "alerts": []}
    
    result = await db.execute(
        select(Alert).order_by(desc(Alert.timestamp)).limit(limit)
    )
    alerts = result.scalars().all()
    
    return {
        "alerts": [
            {
                "id": alert.id,
                "attack_type": alert.attack_type,
                "severity": alert.severity.value,
                "src_ip": alert.src_ip,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in alerts
        ]
    }


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients connect here to receive live alert notifications.
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            logger.debug(f"Received from client: {data}")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


import logging
logger = logging.getLogger(__name__)
