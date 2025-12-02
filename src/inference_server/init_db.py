"""
Database initialization script for ML-IDS.

This script:
1. Creates all database tables
2. Seeds default alert rules
3. Seeds default notification channels (if configured)

Can be run manually or during container startup.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.inference_server.database import init_db, get_db, is_db_available
from src.inference_server.models import (
    AlertRule, NotificationChannel, SeverityLevel,
    NotificationChannelType
)
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_default_alert_rules():
    """Create default alert rules if they don't exist"""
    
    default_rules = [
        {
            "name": "High Frequency Attacks from Single IP",
            "description": "Trigger when more than 5 attacks detected from the same IP within 1 minute",
            "condition": "attack_count > threshold",
            "threshold": 5.0,
            "time_window_seconds": 60,
            "action": "create_incident",
            "severity": SeverityLevel.HIGH,
        },
        {
            "name": "Critical Attack Type Detected",
            "description": "Immediately escalate critical attack types",
            "condition": "attack_severity == 'critical'",
            "threshold": 1.0,
            "time_window_seconds": 1,
            "action": "create_incident",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "name": "Multiple Attack Types from Single Source",
            "description": "Detect diverse attack patterns from single source",
            "condition": "unique_attack_types > threshold",
            "threshold": 3.0,
            "time_window_seconds": 300,
            "action": "notify",
            "severity": SeverityLevel.MEDIUM,
        },
    ]
    
    async for db in get_db():
        if db is None:
            logger.warning("Database not available, skipping alert rules seeding")
            return
        
        for rule_data in default_rules:
            # Check if rule already exists
            result = await db.execute(
                select(AlertRule).where(AlertRule.name == rule_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                rule = AlertRule(**rule_data)
                db.add(rule)
                logger.info(f"Created alert rule: {rule_data['name']}")
            else:
                logger.info(f"Alert rule already exists: {rule_data['name']}")
        
        await db.commit()
        logger.info("Alert rules seeded successfully")
        break  # Only need one iteration


async def seed_notification_channels():
    """Create notification channels based on environment variables"""
    
    channels = []
    
    # Email channel
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    if smtp_host and smtp_user:
        channels.append({
            "name": "Primary Email Notifications",
            "channel_type": NotificationChannelType.EMAIL,
            "config": {
                "smtp_host": smtp_host,
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": smtp_user,
                "smtp_password": os.getenv("SMTP_PASSWORD", ""),
                "smtp_from": os.getenv("SMTP_FROM", "ML-IDS Alerts <alerts@mlids.local>"),
                "recipients": [smtp_user]  # Default to sending to self
            },
            "enabled": True,
        })
    
    # Slack channel
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook and slack_webhook.startswith("http"):
        channels.append({
            "name": "Primary Slack Notifications",
            "channel_type": NotificationChannelType.SLACK,
            "config": {
                "webhook_url": slack_webhook
            },
            "enabled": True,
        })
    
    if not channels:
        logger.info("No notification channels configured in environment")
        return
    
    async for db in get_db():
        if db is None:
            logger.warning("Database not available, skipping notification channels seeding")
            return
        
        for channel_data in channels:
            # Check if channel already exists
            result = await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.name == channel_data["name"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                channel = NotificationChannel(**channel_data)
                db.add(channel)
                logger.info(f"Created notification channel: {channel_data['name']}")
            else:
                logger.info(f"Notification channel already exists: {channel_data['name']}")
        
        await db.commit()
        logger.info("Notification channels seeded successfully")
        break  # Only need one iteration


async def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")
    
    # Initialize database connection
    success = await init_db()
    
    if not success:
        logger.error("Failed to initialize database")
        sys.exit(1)
    
    logger.info("Database connection established")
    
    # Seed default data
    await seed_default_alert_rules()
    await seed_notification_channels()
    
    logger.info("Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())
