"""Product repository for database operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from ..models.product import Product


class ProductRepository:
    """Repository for product database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, product: Product) -> Product:
        """Create a new product."""
        self.session.add(product)
        await self.session.flush()
        return product
    
    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        """Get product by ID."""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Get all products with pagination."""
        result = await self.session.execute(
            select(Product).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_by_category(self, category: str, limit: int = 100) -> List[Product]:
        """Get products by category."""
        result = await self.session.execute(
            select(Product).where(Product.category == category).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_ids(self, product_ids: List[UUID]) -> List[Product]:
        """Get multiple products by IDs in one query (batch fetch)."""
        if not product_ids:
            return []
        result = await self.session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        return list(result.scalars().all())




