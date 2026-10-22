from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ServiceBase(BaseModel):
    name: str
    category: str
    subcategory: str
    latitude: float
    longitude: float
    municipality: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    operator: Optional[str] = None
    brand: Optional[str] = None
    wheelchair: Optional[str] = None
    osm_id: Optional[str] = None
    source: Optional[str] = "OpenStreetMap"

class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None

class NearbyServiceResponse(ServiceResponse):
    distance_meters: float
    distance_km: float
    walk_time_min: float
    drive_time_min: float

class ServiceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ServiceResponse]

class NearbyListResponse(BaseModel):
    total: int
    center_latitude: float
    center_longitude: float
    radius_meters: float
    items: List[NearbyServiceResponse]

class KNNListResponse(BaseModel):
    total: int
    center_latitude: float
    center_longitude: float
    k: int
    items: List[NearbyServiceResponse]
