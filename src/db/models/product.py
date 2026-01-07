"""Product database model."""
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class Product(Base):
    """Product model for storing e-commerce product data."""
    
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False, index=True)
    category = Column(String(200), nullable=False, index=True)
    price = Column(Float, nullable=False)
    discount_percentage = Column(Float)
    rating = Column(Float)
    num_reviews = Column(Integer, default=0)
    description = Column(Text)
    attributes = Column(JSON)  # Flexible JSON for additional attributes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())



