"""
Notification service for sending alerts via Email and Slack.

Supports multiple notification channels configured in the database.
"""

import os
import logging
import aiohttp
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime

from .models import NotificationChannel, NotificationChannelType, Alert

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through various channels"""
    
    def __init__(self):
        self.enabled = os.getenv("ALERT_NOTIFICATION_ENABLED", "false").lower() == "true"
    
    async def send_alert_notification(
        self,
        alert: Alert,
        channels: List[NotificationChannel]
    ) -> Dict[str, bool]:
        """
        Send alert notification through all enabled channels.
        
        Args:
            alert: Alert object to notify about
            channels: List of notification channels to use
            
        Returns:
            Dict mapping channel name to success status
        """
        if not self.enabled:
            logger.info("Notifications disabled, skipping")
            return {}
        
        results = {}
        
        for channel in channels:
            if not channel.enabled:
                logger.debug(f"Channel {channel.name} is disabled, skipping")
                continue
            
            try:
                if channel.channel_type == NotificationChannelType.EMAIL:
                    success = await self._send_email(alert, channel)
                    results[channel.name] = success
                
                elif channel.channel_type == NotificationChannelType.SLACK:
                    success = await self._send_slack(alert, channel)
                    results[channel.name] = success
                
                elif channel.channel_type == NotificationChannelType.WEBHOOK:
                    success = await self._send_webhook(alert, channel)
                    results[channel.name] = success
                
                else:
                    logger.warning(f"Unknown channel type: {channel.channel_type}")
                    results[channel.name] = False
            
            except Exception as e:
                logger.error(f"Error sending notification via {channel.name}: {e}")
                results[channel.name] = False
        
        return results
    
    async def _send_email(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send email notification"""
        try:
            config = channel.config
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[ML-IDS] {alert.severity.value.upper()} Alert: {alert.attack_type}"
            msg['From'] = config.get('smtp_from', 'ML-IDS <alerts@mlids.local>')
            msg['To'] = ', '.join(config.get('recipients', []))
            
            # Create email body
            text_content = f"""
ML-IDS Security Alert

Severity: {alert.severity.value.upper()}
Attack Type: {alert.attack_type}
Source IP: {alert.src_ip}
Destination IP: {alert.dst_ip or 'N/A'}
Timestamp: {alert.timestamp}
Prediction Score: {alert.prediction_score or 'N/A'}

This is an automated alert from the ML-IDS system.
"""
            
            html_content = f"""
<html>
  <body>
    <h2 style="color: {'#dc3545' if alert.severity.value in ['high', 'critical'] else '#ffc107'};">
      ML-IDS Security Alert
    </h2>
    <table style="border-collapse: collapse; width: 100%;">
      <tr style="background-color: #f2f2f2;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Severity</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.severity.value.upper()}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Attack Type</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.attack_type}</td>
      </tr>
      <tr style="background-color: #f2f2f2;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Source IP</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.src_ip}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Destination IP</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.dst_ip or 'N/A'}</td>
      </tr>
      <tr style="background-color: #f2f2f2;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Timestamp</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.timestamp}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Prediction Score</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.prediction_score or 'N/A'}</td>
      </tr>
    </table>
    <p style="margin-top: 20px; color: #666;">
      This is an automated alert from the ML-IDS system.
    </p>
  </body>
</html>
"""
            
            # Attach both text and HTML versions
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=config.get('smtp_host'),
                port=config.get('smtp_port', 587),
                username=config.get('smtp_user'),
                password=config.get('smtp_password'),
                start_tls=True,
            )
            
            logger.info(f"Email notification sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _send_slack(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send Slack notification"""
        try:
            config = channel.config
            webhook_url = config.get('webhook_url')
            
            if not webhook_url:
                logger.error("Slack webhook URL not configured")
                return False
            
            # Determine color based on severity
            color_map = {
                'low': '#36a64f',  # Green
                'medium': '#ffc107',  # Yellow
                'high': '#ff9800',  # Orange
                'critical': '#dc3545'  # Red
            }
            color = color_map.get(alert.severity.value, '#808080')
            
            # Create Slack message
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 {alert.severity.value.upper()} Security Alert",
                        "fields": [
                            {
                                "title": "Attack Type",
                                "value": alert.attack_type,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Source IP",
                                "value": alert.src_ip,
                                "short": True
                            },
                            {
                                "title": "Destination IP",
                                "value": alert.dst_ip or "N/A",
                                "short": True
                            },
                            {
                                "title": "Prediction Score",
                                "value": f"{alert.prediction_score:.2f}" if alert.prediction_score else "N/A",
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": str(alert.timestamp),
                                "short": True
                            }
                        ],
                        "footer": "ML-IDS",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                        "ts": int(alert.timestamp.timestamp()) if alert.timestamp else int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for alert {alert.id}")
                        return True
                    else:
                        logger.error(f"Slack API returned status {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    async def _send_webhook(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send generic webhook notification"""
        try:
            config = channel.config
            webhook_url = config.get('url')
            
            if not webhook_url:
                logger.error("Webhook URL not configured")
                return False
            
            # Create webhook payload
            payload = {
                "alert_id": alert.id,
                "attack_type": alert.attack_type,
                "severity": alert.severity.value,
                "src_ip": alert.src_ip,
                "dst_ip": alert.dst_ip,
                "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                "prediction_score": alert.prediction_score,
                "features": alert.features
            }
            
            # Send webhook
            headers = config.get('headers', {})
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Webhook notification sent for alert {alert.id}")
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


# Global notification service instance
notification_service = NotificationService()
