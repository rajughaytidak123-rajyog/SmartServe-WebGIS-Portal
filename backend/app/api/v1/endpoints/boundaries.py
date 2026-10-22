from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.services.spatial_service import SpatialService

router = APIRouter()

@router.get(
    "/",
    summary="Get Study Area Boundaries GeoJSON",
    description="Export PMC (Pune) and PCMC (Pimpri-Chinchwad) municipal boundary polygons formatted as RFC 7946 GeoJSON."
)
def get_boundaries(
    municipality: Optional[str] = Query(None, pattern="^(PMC|PCMC)$", description="Filter by municipality (PMC or PCMC)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    return SpatialService.get_boundaries_geojson(db=db, municipality=municipality)
