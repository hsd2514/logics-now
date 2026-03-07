from fastapi import APIRouter

from app.routes import documents, triplets, fraud, ai, stats

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(triplets.router, prefix="/triplets", tags=["triplets"])
api_router.include_router(fraud.router, prefix="/fraud", tags=["fraud"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
