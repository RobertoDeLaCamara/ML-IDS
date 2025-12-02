"""
Alert service for managing security alerts and incidents.

Handles:
- Alert creation with severity classification
- Alert deduplication
- Alert rules evaluation
- Incident creation
- Notification triggering
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from .models import (
    Alert, Incident, AlertRule, NotificationChannel,
    SeverityLevel, IncidentStatus, Metric
)
from .notifications import notification_service
from .websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts and incidents"""
    
    def __init__(self):
        self.dedup_window_seconds = int(os.getenv("ALERT_DEDUP_WINDOW_SECONDS", "300"))
    
    def classify_severity(self, attack_type: str, prediction_score: Optional[float] = None) -> SeverityLevel:
        """
        Classify alert severity based on attack type and prediction score.
        
        Args:
            attack_type: Type of attack detected
            prediction_score: Confidence score from ML model
            
        Returns:
            SeverityLevel enum value
        """
        # Map of attack types to severity (this can be customized)
        high_severity_attacks = {
            "DDoS", "SQL Injection", "Brute Force", "Infiltration",
            "Botnet", "Web Attack"
        }
        
        critical_severity_attacks = {
            "Infiltration", "Botnet ARES"
        }
        
        # Check attack type
        if attack_type in critical_severity_attacks:
            return SeverityLevel.CRITICAL
        
        if attack_type in high_severity_attacks:
            # If we have high confidence, escalate to high
            if prediction_score and prediction_score > 0.9:
                return SeverityLevel.HIGH
            return SeverityLevel.MEDIUM
        
        # For other attacks, use prediction score
        if prediction_score:
            if prediction_score > 0.95:
                return SeverityLevel.HIGH
            elif prediction_score > 0.8:
                return SeverityLevel.MEDIUM
            else:
                return SeverityLevel.LOW
        
        # Default to medium
        return SeverityLevel.MEDIUM
    
    async def check_duplicate(
        self,
        db: AsyncSession,
        src_ip: str,
        attack_type: str
    ) -> Optional[Alert]:
        """
        Check if a similar alert already exists within the deduplication window.
        
        Args:
            db: Database session
            src_ip: Source IP address
            attack_type: Type of attack
            
        Returns:
            Existing alert if found, None otherwise
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.dedup_window_seconds)
        
        result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.src_ip == src_ip,
                    Alert.attack_type == attack_type,
                    Alert.timestamp >= cutoff_time
                )
            ).order_by(Alert.timestamp.desc()).limit(1)
        )
        
        return result.scalar_one_or_none()
    
    async def create_alert(
        self,
        db: AsyncSession,
        attack_type: str,
        src_ip: str,
        dst_ip: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
        prediction_score: Optional[float] = None
    ) -> Optional[Alert]:
        """
        Create a new alert with deduplication and severity classification.
        
        Args:
            db: Database session
            attack_type: Type of attack detected
            src_ip: Source IP address
            dst_ip: Destination IP address (optional)
            features: Network flow features
            prediction_score: ML model confidence score
            
        Returns:
            Created alert or None if deduplicated
        """
        # Check for duplicates
        existing = await self.check_duplicate(db, src_ip, attack_type)
        
        if existing:
            logger.info(
                f"Duplicate alert detected: {attack_type} from {src_ip} "
                f"(original alert ID: {existing.id})"
            )
            return None  # Deduplicated
        
        # Classify severity
        severity = self.classify_severity(attack_type, prediction_score)
        
        # Create alert
        alert = Alert(
            attack_type=attack_type,
            severity=severity,
            src_ip=src_ip,
            dst_ip=dst_ip,
            features=features,
            prediction_score=prediction_score
        )
        
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        
        logger.info(
            f"Created alert ID {alert.id}: {attack_type} from {src_ip} "
            f"(severity: {severity.value})"
        )
        
        # Evaluate alert rules
        await self.evaluate_alert_rules(db, alert)
        
        # Send notifications
        await self.send_notifications(db, alert)
        
        # Record metric
        await self.record_alert_metric(db, alert)
        
        # Broadcast to WebSocket clients
        await ws_manager.send_alert({
            "id": alert.id,
            "attack_type": alert.attack_type,
            "severity": alert.severity.value,
            "src_ip": alert.src_ip,
            "dst_ip": alert.dst_ip,
            "timestamp": alert.timestamp.isoformat(),
            "acknowledged": alert.acknowledged
        })
        
        return alert
    
    async def evaluate_alert_rules(self, db: AsyncSession, alert: Alert):
        """
        Evaluate alert rules and take appropriate actions.
        
        Args:
            db: Database session
            alert: Alert to evaluate
        """
        # Get all enabled alert rules
        result = await db.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        rules = result.scalars().all()
        
        for rule in rules:
            triggered = await self._check_rule_condition(db, rule, alert)
            
            if triggered:
                logger.info(f"Alert rule '{rule.name}' triggered for alert {alert.id}")
                
                # Execute rule action
                if rule.action == "create_incident":
                    await self.create_incident_for_alert(db, alert, rule)
                elif rule.action == "escalate_severity":
                    # Escalate to rule severity if higher
                    if self._severity_level(rule.severity) > self._severity_level(alert.severity):
                        alert.severity = rule.severity
                        await db.commit()
                        logger.info(f"Escalated alert {alert.id} to {rule.severity.value}")
    
    async def _check_rule_condition(
        self,
        db: AsyncSession,
        rule: AlertRule,
        alert: Alert
    ) -> bool:
        """
        Check if an alert rule condition is met.
        
        Args:
            db: Database session
            rule: Alert rule to check
            alert: Alert to evaluate
            
        Returns:
            True if condition is met, False otherwise
        """
        # Simple condition evaluation
        # In production, you might use a proper expression evaluator
        
        if "attack_count > threshold" in rule.condition:
            # Count recent attacks from same IP
            cutoff_time = datetime.utcnow() - timedelta(seconds=rule.time_window_seconds)
            
            result = await db.execute(
                select(func.count(Alert.id)).where(
                    and_(
                        Alert.src_ip == alert.src_ip,
                        Alert.timestamp >= cutoff_time
                    )
                )
            )
            count = result.scalar()
            
            return count > rule.threshold
        
        elif "unique_attack_types > threshold" in rule.condition:
            # Count unique attack types from same IP
            cutoff_time = datetime.utcnow() - timedelta(seconds=rule.time_window_seconds)
            
            result = await db.execute(
                select(func.count(func.distinct(Alert.attack_type))).where(
                    and_(
                        Alert.src_ip == alert.src_ip,
                        Alert.timestamp >= cutoff_time
                    )
                )
            )
            count = result.scalar()
            
            return count > rule.threshold
        
        elif "attack_severity == 'critical'" in rule.condition:
            return alert.severity == SeverityLevel.CRITICAL
        
        return False
    
    def _severity_level(self, severity: SeverityLevel) -> int:
        """Convert severity enum to numeric level for comparison"""
        levels = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4
        }
        return levels.get(severity, 0)
    
    async def create_incident_for_alert(
        self,
        db: AsyncSession,
        alert: Alert,
        rule: Optional[AlertRule] = None
    ) -> Incident:
        """
        Create an incident for an alert.
        
        Args:
            db: Database session
            alert: Alert to create incident for
            rule: Alert rule that triggered (optional)
            
        Returns:
            Created incident
        """
        # Generate incident title
        if rule:
            title = f"{rule.name}: {alert.attack_type} from {alert.src_ip}"
        else:
            title = f"{alert.severity.value.upper()} Alert: {alert.attack_type} from {alert.src_ip}"
        
        # Create incident
        incident = Incident(
            title=title,
            description=f"Automatically created incident for alert {alert.id}",
            status=IncidentStatus.OPEN,
            severity=alert.severity
        )
        
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        
        # Link alert to incident
        alert.incident_id = incident.id
        await db.commit()
        
        logger.info(f"Created incident {incident.id} for alert {alert.id}")
        
        return incident
    
    async def send_notifications(self, db: AsyncSession, alert: Alert):
        """
        Send notifications for an alert through all enabled channels.
        
        Args:
            db: Database session
            alert: Alert to notify about
        """
        # Get enabled notification channels
        result = await db.execute(
            select(NotificationChannel).where(NotificationChannel.enabled == True)
        )
        channels = result.scalars().all()
        
        if not channels:
            logger.debug("No notification channels configured")
            return
        
        # Send notifications
        results = await notification_service.send_alert_notification(alert, channels)
        
        for channel_name, success in results.items():
            if success:
                logger.info(f"Notification sent via {channel_name} for alert {alert.id}")
            else:
                logger.warning(f"Failed to send notification via {channel_name} for alert {alert.id}")
    
    async def record_alert_metric(self, db: AsyncSession, alert: Alert):
        """
        Record metrics for dashboard.
        
        Args:
            db: Database session
            alert: Alert to record metric for
        """
        try:
            # Record alert count metric
            metric = Metric(
                metric_name="alert_created",
                value=1.0,
                tags={
                    "attack_type": alert.attack_type,
                    "severity": alert.severity.value,
                    "src_ip": alert.src_ip
                }
            )
            db.add(metric)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    async def acknowledge_alert(self, db: AsyncSession, alert_id: int) -> bool:
        """
        Mark an alert as acknowledged.
        
        Args:
            db: Database session
            alert_id: Alert ID to acknowledge
            
        Returns:
            True if successful, False otherwise
        """
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            return False
        
        alert.acknowledged = True
        await db.commit()
        
        logger.info(f"Alert {alert_id} acknowledged")
        return True


# Global alert service instance
alert_service = AlertService()
