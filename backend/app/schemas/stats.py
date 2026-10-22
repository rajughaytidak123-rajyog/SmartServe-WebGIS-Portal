from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class MunicipalityStat(BaseModel):
    municipality: str
    count: int
    percentage: float

class CategoryStat(BaseModel):
    category: str
    count: int
    percentage: float
    icon: Optional[str] = None
    color: Optional[str] = None

class SubcategoryStat(BaseModel):
    category: str
    subcategory: str
    count: int
    icon: Optional[str] = None

class OverviewStats(BaseModel):
    total_services: int
    total_categories: int
    total_subcategories: int
    municipalities: List[MunicipalityStat]
    top_categories: List[CategoryStat]
    top_subcategories: List[SubcategoryStat]

class DensityStat(BaseModel):
    boundary_name: str
    municipality: str
    area_sqkm: float
    total_pois: int
    density_per_sqkm: float

class DensityResponse(BaseModel):
    study_area: str
    total_area_sqkm: float
    overall_density_per_sqkm: float
    boundaries: List[DensityStat]

class NearbyCategorySummaryItem(BaseModel):
    category: str
    subcategory: str
    total_nearby: int
    nearest_distance_meters: float

class NearbyCategorySummaryResponse(BaseModel):
    center_latitude: float
    center_longitude: float
    radius_meters: float
    total_services_nearby: int
    breakdown: List[NearbyCategorySummaryItem]
