from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db
from backend.app.schemas.service import (
    ServiceResponse,
    NearbyListResponse,
    KNNListResponse,
    ServiceListResponse,
)
from backend.app.services.spatial_service import SpatialService

router = APIRouter()

@router.get(
    "/nearby",
    response_model=NearbyListResponse,
    summary="Radius Proximity Search (ST_DWithin)",
    description="Find all POIs within a given radius in meters of a user's location. Ordered by geodesic distance in meters."
)
def get_nearby_services(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of user location (e.g. 18.5204 for Pune)"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of user location (e.g. 73.8567 for Pune)"),
    radius_meters: float = Query(2000.0, ge=100, le=50000, description="Search radius in meters (default: 2000m = 2km)"),
    q: Optional[str] = Query(None, description="Search keyword by name, address, or brand"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. Healthcare, Food, Emergency)"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory (e.g. Hospital, Pharmacy, Restaurant)"),
    municipality: Optional[str] = Query(None, pattern="^(PMC|PCMC)$", description="Filter by municipality (PMC or PCMC)"),
    limit: int = Query(200, ge=1, le=1000, description="Max POIs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    items, total = SpatialService.get_nearby_services(
        db=db,
        lat=lat,
        lon=lon,
        radius_meters=radius_meters,
        q=q,
        category=category,
        subcategory=subcategory,
        municipality=municipality,
        limit=limit,
        offset=offset
    )
    return NearbyListResponse(
        total=total,
        center_latitude=lat,
        center_longitude=lon,
        radius_meters=radius_meters,
        items=items
    )

@router.get(
    "/knn",
    response_model=KNNListResponse,
    summary="K-Nearest Neighbors Fast Search (<-> Operator)",
    description="Retrieve the exact top K closest POIs to a location using PostGIS R-Tree index acceleration."
)
def get_knn_services(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of user location"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of user location"),
    k: int = Query(5, ge=1, le=50, description="Number of nearest neighbors to retrieve"),
    q: Optional[str] = Query(None, description="Search keyword by name, address, or brand"),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory (e.g. Hospital, Petrol Pump)"),
    municipality: Optional[str] = Query(None, pattern="^(PMC|PCMC)$", description="Filter by municipality"),
    db: Session = Depends(get_db)
):
    items = SpatialService.get_knn_services(
        db=db,
        lat=lat,
        lon=lon,
        k=k,
        q=q,
        category=category,
        subcategory=subcategory,
        municipality=municipality
    )
    return KNNListResponse(
        total=len(items),
        center_latitude=lat,
        center_longitude=lon,
        k=k,
        items=items
    )

@router.get(
    "/search",
    response_model=ServiceListResponse,
    summary="Text Search & Attribute Filter",
    description="Search POIs by keyword (name, address, brand) or filter by category and municipality."
)
def search_services(
    q: Optional[str] = Query(None, description="Search keyword (e.g. 'Ruby Hall', 'McDonalds', 'SBI')"),
    category: Optional[str] = Query(None, description="Category filter"),
    subcategory: Optional[str] = Query(None, description="Subcategory filter"),
    municipality: Optional[str] = Query(None, pattern="^(PMC|PCMC)$", description="Municipality filter"),
    limit: int = Query(50, ge=1, le=500, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    items, total = SpatialService.search_services(
        db=db,
        q=q,
        category=category,
        subcategory=subcategory,
        municipality=municipality,
        limit=limit,
        offset=offset
    )
    return ServiceListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )

@router.get(
    "/autocomplete",
    summary="Real-time Autocomplete Suggestions",
    description="Fast type-ahead suggestions for search bar with relevance ranking."
)
def get_autocomplete(
    q: str = Query(..., min_length=1, description="Prefix or keyword query"),
    limit: int = Query(8, ge=1, le=20, description="Max suggestions to return"),
    db: Session = Depends(get_db)
):
    return SpatialService.get_autocomplete_suggestions(db=db, q=q, limit=limit)

@router.get(
    "/geojson",
    summary="GeoJSON FeatureCollection Stream",
    description="Export POIs directly as RFC 7946 GeoJSON FeatureCollection generated natively in PostGIS for Leaflet/Mapbox rendering."
)
def get_services_geojson(
    category: Optional[str] = Query(None, description="Category filter"),
    subcategory: Optional[str] = Query(None, description="Subcategory filter"),
    municipality: Optional[str] = Query(None, pattern="^(PMC|PCMC)$", description="Municipality filter"),
    bbox: Optional[str] = Query(None, description="Bounding box filter in format 'min_lon,min_lat,max_lon,max_lat'"),
    limit: int = Query(1000, ge=1, le=10000, description="Max features to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    return SpatialService.get_services_geojson(
        db=db,
        category=category,
        subcategory=subcategory,
        municipality=municipality,
        bbox=bbox,
        limit=limit
    )

@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Get Service Detail by ID",
    description="Retrieve all attributes and coordinates for a single service POI."
)
def get_service_detail(
    service_id: int = Path(..., ge=1, description="Primary key ID of the service"),
    db: Session = Depends(get_db)
):
    query_sql = """
        SELECT 
            id, name, category, subcategory, latitude, longitude,
            municipality, address, phone, website, opening_hours,
            operator, brand, wheelchair, osm_id, source, created_at
        FROM services
        WHERE id = :id
    """
    row = db.execute(text(query_sql), {"id": service_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Service with ID {service_id} not found")

    return ServiceResponse(
        id=row.id,
        name=row.name,
        category=row.category,
        subcategory=row.subcategory,
        latitude=row.latitude,
        longitude=row.longitude,
        municipality=row.municipality,
        address=row.address,
        phone=row.phone,
        website=row.website,
        opening_hours=row.opening_hours,
        operator=row.operator,
        brand=row.brand,
        wheelchair=row.wheelchair,
        osm_id=row.osm_id,
        source=row.source,
        created_at=row.created_at
    )
