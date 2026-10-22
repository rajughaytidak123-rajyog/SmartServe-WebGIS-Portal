from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from geoalchemy2 import Geometry, Geography
from backend.app.db.base import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    subcategory = Column(String(64), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    opening_hours = Column(String(255), nullable=True)
    operator = Column(String(150), nullable=True)
    brand = Column(String(150), nullable=True)
    wheelchair = Column(String(50), nullable=True)
    municipality = Column(String(10), nullable=False, index=True)
    osm_id = Column(String(50), nullable=True)
    source = Column(String(50), default="OpenStreetMap")
    
    # PostGIS Spatial columns
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    geog = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
