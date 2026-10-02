from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    inspections,
    analytics,
    seed,
)

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Sistem Sağlığı"]
)
api_router.include_router(
    inspections.router,
    prefix="/inspections",
    tags=["LangGraph Analiz & Etiketleme"]
)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Dashboard & İstatistik"]
)
api_router.include_router(
    seed.router,
    prefix="/seed",
    tags=["Seed Veri"]
)
