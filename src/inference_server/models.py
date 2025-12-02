"""
SQLAlchemy ORM models for ML-IDS database.

Models:
- Alert: Detected attacks with severity, IP, attack type, timestamp
- Incident: Grouped alerts for tracking investigations
- Metric: Time-series metrics for dashboard
- NotificationChannel: Email, Slack configurations
- AlertRule: Custom alert thresholds and conditions
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class SeverityLevel(str, enum.Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    """Incident workflow statuses"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class NotificationChannelType(str, enum.Enum):
    """Types of notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class Alert(Base):
    """
    Represents a detected attack or security event.
    
    Attributes:
        id: Primary key
        attack_type: Type of attack detected (numeric from ML model)
        severity: Severity level (low, medium, high, critical)
        src_ip: Source IP address of the attack
        dst_ip: Destination IP address (optional)
        timestamp: When the attack was detected
        features: JSON snapshot of network flow features
        prediction_score: Confidence score from ML model
        acknowledged: Whether the alert has been acknowledged
        incident_id: Foreign key to associated incident (if any)
        notes: Additional notes about the alert
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    attack_type = Column(String(50), nullable=False, index=True)
    severity = Column(SQLEnum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM, index=True)
    src_ip = Column(String(45), nullable=False, index=True)  # Support IPv6
    dst_ip = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    features = Column(JSON, nullable=True)  # Snapshot of network features
    prediction_score = Column(Float, nullable=True)  # Confidence score
    acknowledged = Column(Boolean, default=False, nullable=False)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    incident = relationship("Incident", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.attack_type}, severity={self.severity}, src_ip={self.src_ip})>"


class Incident(Base):
    """
    Represents an incident (collection of related alerts).
    
    Attributes:
        id: Primary key
        title: Incident title/summary
        description: Detailed description
        status: Current status (open, investigating, resolved, closed)
        severity: Highest severity of associated alerts
        assigned_to: Person/team assigned to investigate
        created_at: When incident was created
        updated_at: When incident was last updated
        resolved_at: When incident was resolved
        notes: Investigation notes
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN, index=True)
    severity = Column(SQLEnum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM, index=True)
    assigned_to = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    alerts = relationship("Alert", back_populates="incident")

    def __repr__(self):
        return f"<Incident(id={self.id}, title={self.title}, status={self.status})>"


class Metric(Base):
    """
    Time-series metrics for dashboard and monitoring.
    
    Attributes:
        id: Primary key
        metric_name: Name of the metric (e.g., 'attacks_per_hour', 'predictions_count')
        value: Numeric value of the metric
        timestamp: When the metric was recorded
        tags: Additional metadata as JSON (e.g., {'attack_type': 'DDoS'})
    """
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    tags = Column(JSON, nullable=True)  # Additional metadata

    def __repr__(self):
        return f"<Metric(name={self.metric_name}, value={self.value}, timestamp={self.timestamp})>"


class NotificationChannel(Base):
    """
    Configuration for notification channels (Email, Slack, etc.).
    
    Attributes:
        id: Primary key
        name: Display name for the channel
        channel_type: Type of channel (email, slack, webhook)
        config: JSON configuration (e.g., {'webhook_url': '...'} for Slack)
        enabled: Whether this channel is active
        created_at: When channel was created
        updated_at: When channel was last updated
    """
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    channel_type = Column(SQLEnum(NotificationChannelType), nullable=False, index=True)
    config = Column(JSON, nullable=False)  # Channel-specific configuration
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<NotificationChannel(name={self.name}, type={self.channel_type}, enabled={self.enabled})>"


class AlertRule(Base):
    """
    Custom alert rules and thresholds.
    
    Attributes:
        id: Primary key
        name: Rule name
        description: Rule description
        condition: Condition expression (e.g., 'attack_count > 10')
        threshold: Numeric threshold value
        time_window_seconds: Time window for the rule (e.g., 60 for 1 minute)
        action: Action to take when rule triggers (e.g., 'create_incident', 'notify')
        severity: Severity to assign when rule triggers
        enabled: Whether this rule is active
        created_at: When rule was created
        updated_at: When rule was last updated
    """
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    condition = Column(String(255), nullable=False)  # e.g., "attack_count > threshold"
    threshold = Column(Float, nullable=False)
    time_window_seconds = Column(Integer, nullable=False, default=300)  # 5 minutes default
    action = Column(String(50), nullable=False, default="notify")  # notify, create_incident, etc.
    severity = Column(SQLEnum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AlertRule(name={self.name}, condition={self.condition}, enabled={self.enabled})>"
