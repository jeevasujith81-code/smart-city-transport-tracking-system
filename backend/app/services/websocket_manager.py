import json
import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger("citytrack.websocket")

class ConnectionManager:
    def __init__(self):
        # Active websocket connections
        self.active_connections: List[WebSocket] = []
        # Bus-specific subscriptions if needed
        self.bus_subscriptions: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for bus_id in list(self.bus_subscriptions.keys()):
            if websocket in self.bus_subscriptions[bus_id]:
                self.bus_subscriptions[bus_id].remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast live location or status update to all connected WebSocket clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()
