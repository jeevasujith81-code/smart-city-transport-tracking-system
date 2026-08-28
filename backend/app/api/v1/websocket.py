import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter(tags=["WebSocket Real-Time Tracking"])

logger = logging.getLogger("citytrack.ws_route")

@router.websocket("/ws/live-tracking")
async def websocket_live_tracking(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial confirmation message
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to CityTrack Real-Time Bus Tracking Stream"
        })
        
        while True:
            # Keep listening for incoming ping/pong or simulation client messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle client-sent messages if any (e.g. heartbeat)
                if message.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
                elif message.get("type") == "BUS_LOCATION_UPDATE":
                    # Broadcast location update to all other connected passengers
                    await manager.broadcast(message)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
