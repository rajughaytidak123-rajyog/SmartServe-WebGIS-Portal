from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from backend.app.db.base import Base

class StudyAreaBoundary(Base):
    __tablename__ = "study_area_boundaries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    municipality = Column(String(20), nullable=True)
    area_sqkm = Column(Float, nullable=True)
    source = Column(String(100), default="DataMeet / OpenStreetMap")
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)
