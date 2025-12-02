"""
WebSocket manager for real-time dashboard updates.

Manages WebSocket connections and broadcasts alerts to connected clients.
"""

import logging
from typing import List, Set
from fastapi import WebSocket
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket connection closed. Remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message:  dict):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Dictionary to broadcast as JSON
        """
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
        
        # Convert to JSON
        message_json = json.dumps(message)
        
        # Send to all connections and remove any that fail
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
        
        if disconnected:
            logger.info(f"Removed {len(disconnected)} disconnected WebSocket(s)")
    
    async def send_alert(self, alert_data: dict):
        """
        Broadcast a new alert to all connected clients.
        
        Args:
            alert_data: Alert information to broadcast
        """
        message = {
            "type": "alert",
            "data": alert_data
        }
        await self.broadcast(message)
        logger.debug(f"Broadcasted alert to {len(self.active_connections)} clients")
    
    async def send_stats_update(self, stats: dict):
        """
        Broadcast updated statistics to all connected clients.
        
        Args:
            stats: Statistics to broadcast
        """
        message = {
            "type": "stats_update",
            "data": stats
        }
        await self.broadcast(message)


# Global WebSocket manager instance
ws_manager = WebSocketManager()
