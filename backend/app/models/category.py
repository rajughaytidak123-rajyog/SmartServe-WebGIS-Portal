from sqlalchemy import Column, Integer, String, DateTime, func
from backend.app.db.base import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(64), nullable=False, index=True)
    subcategory = Column(String(64), nullable=False, unique=True, index=True)
    slug = Column(String(64), nullable=False, unique=True)
    icon = Column(String(10), nullable=False)
    color = Column(String(20), nullable=False, default="#3182ce")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
