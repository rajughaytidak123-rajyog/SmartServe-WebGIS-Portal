from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

class BoundaryProperties(BaseModel):
    id: int
    name: str
    municipality: Optional[str] = None
    area_sqkm: Optional[float] = None
    source: Optional[str] = None

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
