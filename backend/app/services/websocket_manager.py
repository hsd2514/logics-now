from typing import List, Dict
from fastapi import WebSocket
import json
import asyncio

class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_json(self, data: Dict):
        """Broadcast JSON data to all connections."""
        await self.broadcast(json.dumps(data))
    
    async def send_processing_update(
        self,
        document_id: str,
        stage: str,
        progress: float,
        message: str
    ):
        """Send document processing update."""
        await self.broadcast_json({
            'type': 'processing_update',
            'document_id': document_id,
            'stage': stage,
            'progress': progress,
            'message': message
        })
    
    async def send_match_found(self, triplet_id: str, confidence: float):
        """Send notification when a match is found."""
        await self.broadcast_json({
            'type': 'match_found',
            'triplet_id': triplet_id,
            'confidence': confidence
        })
    
    async def send_fraud_alert(self, alert_id: str, risk_score: float, alert_type: str):
        """Send fraud alert notification."""
        await self.broadcast_json({
            'type': 'fraud_alert',
            'alert_id': alert_id,
            'risk_score': risk_score,
            'alert_type': alert_type
        })

# Global instance
ws_manager = WebSocketManager()
