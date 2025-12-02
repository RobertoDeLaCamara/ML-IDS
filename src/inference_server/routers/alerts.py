"""
API router for alert management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Alert, SeverityLevel
from ..schemas import AlertResponse, AlertUpdate
from ..alert_service import alert_service

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    src_ip: Optional[str] = Query(None, description="Filter by source IP"),
    attack_type: Optional[str] = Query(None, description="Filter by attack type"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    hours: Optional[int] = Query(24, description="Number of hours to look back"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    List alerts with optional filtering.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Build query
    query = select(Alert)
    
    # Apply filters
    conditions = []
    
    if severity:
        try:
            severity_enum = SeverityLevel(severity.lower())
            conditions.append(Alert.severity == severity_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    if src_ip:
        conditions.append(Alert.src_ip == src_ip)
    
    if attack_type:
        conditions.append(Alert.attack_type == attack_type)
    
    if acknowledged is not None:
        conditions.append(Alert.acknowledged == acknowledged)
    
    # Time filter
    if hours:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        conditions.append(Alert.timestamp >= cutoff_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by timestamp descending (newest first)
    query = query.order_by(desc(Alert.timestamp))
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific alert by ID.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    update_data: AlertUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an alert (add notes, change acknowledged status, etc.).
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Update fields
    if update_data.acknowledged is not None:
        alert.acknowledged = update_data.acknowledged
    
    if update_data.notes is not None:
        alert.notes = update_data.notes
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge an alert.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    success = await alert_service.acknowledge_alert(db, alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Fetch and return updated alert
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one()
    
    return alert


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert (admin only - not implemented auth yet).
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    await db.delete(alert)
    await db.commit()
    
    return {"message": f"Alert {alert_id} deleted"}
