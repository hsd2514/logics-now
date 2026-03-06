from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.routes import api_router
from app.services.websocket_manager import ws_manager

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title="FreightIQ",
    description="AI Document Intelligence for LR-POD-Invoice Matching",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# WebSocket endpoint for real-time updates
@app.websocket("/ws/processing")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or handle incoming messages
            await ws_manager.send_personal_message(f"Received: {data}", websocket)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/")
def root():
    return {
        "name": "FreightIQ",
        "version": "1.0.0",
        "description": "AI Document Intelligence for LR-POD-Invoice Matching",
        "features": [
            "6-Stage AI Pipeline",
            "Explainable AI Heatmaps",
            "Natural Language Query",
            "AI Audit Trail",
            "Predictive Fraud Alerts",
            "Document Chat"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
