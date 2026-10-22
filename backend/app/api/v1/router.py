from fastapi import APIRouter
from backend.app.api.v1.endpoints import services, categories, boundaries, analytics

api_router = APIRouter()

api_router.include_router(
    services.router,
    prefix="/services",
    tags=["Services & Spatial Queries"]
)

api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories & Taxonomy"]
)

api_router.include_router(
    boundaries.router,
    prefix="/boundaries",
    tags=["Study Area Boundaries (GeoJSON)"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Spatial Analytics & Density"]
)
