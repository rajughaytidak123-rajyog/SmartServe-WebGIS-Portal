import time
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure Cross-Origin Resource Sharing (CORS) for GIS Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["General"])
def root():
    """
    Root endpoint displaying API metadata, version, and documentation links.
    """
    return {
        "title": "SmartServe GIS API",
        "description": "Location-Based Multi-Service WebGIS Spatial Engine for Pune & PCMC",
        "version": settings.PROJECT_VERSION,
        "status": "online",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": f"{settings.API_V1_STR}/openapi.json"
        },
        "endpoints": {
            "services_nearby": f"{settings.API_V1_STR}/services/nearby?lat=18.5204&lon=73.8567&radius_meters=2000",
            "services_knn": f"{settings.API_V1_STR}/services/knn?lat=18.5204&lon=73.8567&k=5",
            "services_geojson": f"{settings.API_V1_STR}/services/geojson",
            "categories_tree": f"{settings.API_V1_STR}/categories/tree",
            "boundaries_geojson": f"{settings.API_V1_STR}/boundaries/",
            "spatial_density": f"{settings.API_V1_STR}/analytics/density",
            "overview_stats": f"{settings.API_V1_STR}/analytics/overview"
        }
    }

@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check verifying PostGIS database connectivity, spatial extensions, and POI counts.
    """
    start_time = time.time()
    try:
        # Check PostGIS extension and POI count
        postgis_ver = db.execute(text("SELECT PostGIS_Version()")).scalar()
        poi_count = db.execute(text("SELECT COUNT(*) FROM services")).scalar()
        boundary_count = db.execute(text("SELECT COUNT(*) FROM study_area_boundaries")).scalar()
        query_time_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "healthy",
            "database": "connected",
            "postgis_version": postgis_ver,
            "total_services_indexed": poi_count,
            "study_area_boundaries_loaded": boundary_count,
            "latency_ms": query_time_ms
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
