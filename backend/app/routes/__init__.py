from fastapi import APIRouter

from app.routes import documents, triplets, fraud, ai, stats, demo, vendors, contract_rates

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(triplets.router, prefix="/triplets", tags=["triplets"])
api_router.include_router(fraud.router, prefix="/fraud", tags=["fraud"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
api_router.include_router(disputes.router, prefix="/disputes", tags=["disputes"])
api_router.include_router(contract_rates.router, prefix="/contract-rates", tags=["contract-rates"])
