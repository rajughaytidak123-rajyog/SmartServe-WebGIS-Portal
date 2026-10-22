from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class SubcategoryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    subcategory: str
    slug: str
    icon: str
    color: str
    count: Optional[int] = 0

class CategorySummary(BaseModel):
    category: str
    icon: str
    color: str
    total_count: int
    subcategories: List[SubcategoryDetail]

class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    subcategory: str
    slug: str
    icon: str
    color: str
    count: Optional[int] = 0
