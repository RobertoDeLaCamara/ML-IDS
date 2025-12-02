"""
API router for incident management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Incident, Alert, IncidentStatus, SeverityLevel
from ..schemas import IncidentResponse, IncidentCreate, IncidentUpdate

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    List incidents with optional filtering.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Build query
    query = select(Incident)
    
    # Apply filters
    conditions = []
    
    if status:
        try:
            status_enum = IncidentStatus(status.lower())
            conditions.append(Incident.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if severity:
        try:
            severity_enum = SeverityLevel(severity.lower())
            conditions.append(Incident.severity == severity_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by created_at descending (newest first)
    query = query.order_by(desc(Incident.created_at))
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    return incidents


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific incident by ID with related alerts.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    return incident


@router.post("", response_model=IncidentResponse)
async def create_incident(
    incident_data: IncidentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new incident manually.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Create incident
    incident = Incident(
        title=incident_data.title,
        description=incident_data.description,
        status=incident_data.status or IncidentStatus.OPEN,
        severity=incident_data.severity or SeverityLevel.MEDIUM,
        assigned_to=incident_data.assigned_to
    )
    
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    
    return incident


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    update_data: IncidentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an incident.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    # Update fields
    if update_data.title is not None:
        incident.title = update_data.title
    
    if update_data.description is not None:
        incident.description = update_data.description
    
    if update_data.status is not None:
        incident.status = update_data.status
        # Set resolved_at if status changed to resolved/closed
        if update_data.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            if not incident.resolved_at:
                incident.resolved_at = datetime.utcnow()
    
    if update_data.severity is not None:
        incident.severity = update_data.severity
    
    if update_data.assigned_to is not None:
        incident.assigned_to = update_data.assigned_to
    
    if update_data.notes is not None:
        # Append notes
        if incident.notes:
            incident.notes += f"\n\n[{datetime.utcnow()}] {update_data.notes}"
        else:
            incident.notes = f"[{datetime.utcnow()}] {update_data.notes}"
    
    await db.commit()
    await db.refresh(incident)
    
    return incident


@router.post("/{incident_id}/alerts/{alert_id}")
async def link_alert_to_incident(
    incident_id: int,
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Link an alert to an incident.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Verify incident exists
    incident_result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = incident_result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    # Verify alert exists
    alert_result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = alert_result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Link alert to incident
    alert.incident_id = incident_id
    await db.commit()
    
    return {"message": f"Alert {alert_id} linked to incident {incident_id}"}


@router.get("/{incident_id}/alerts", response_model=List[dict])
async def get_incident_alerts(
    incident_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all alerts related to an incident.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await db.execute(
        select(Alert).where(Alert.incident_id == incident_id).order_by(desc(Alert.timestamp))
    )
    alerts = result.scalars().all()
    
    return alerts
