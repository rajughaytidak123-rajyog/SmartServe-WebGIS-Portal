from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.stats import (
    OverviewStats,
    DensityResponse,
    NearbyCategorySummaryResponse
)
from backend.app.services.spatial_service import SpatialService

router = APIRouter()

@router.get(
    "/overview",
    response_model=OverviewStats,
    summary="Global System Analytics Overview",
    description="Retrieve high-level POI totals, municipality proportions, and category breakdowns."
)
def get_overview(db: Session = Depends(get_db)):
    return SpatialService.get_overview_statistics(db=db)

@router.get(
    "/density",
    response_model=DensityResponse,
    summary="Spatial POI Density Analysis (per km²)",
    description="Perform Point-in-Polygon spatial joins to calculate service density per square kilometer across PMC and PCMC."
)
def get_density_analysis(db: Session = Depends(get_db)):
    return SpatialService.get_density_analysis(db=db)

@router.get(
    "/nearby-summary",
    response_model=NearbyCategorySummaryResponse,
    summary="Nearby Category Breakdown Summary",
    description="Summarize nearby POI counts and minimum distance per category within a given radius."
)
def get_nearby_summary(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_meters: float = Query(2000.0, ge=100, le=50000, description="Radius in meters"),
    db: Session = Depends(get_db)
):
    return SpatialService.get_nearby_summary(
        db=db,
        lat=lat,
        lon=lon,
        radius_meters=radius_meters
    )
