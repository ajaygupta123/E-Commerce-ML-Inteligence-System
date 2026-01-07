"""Script to generate embeddings for existing products."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.postgres import AsyncSessionLocal
from src.db.models.product import Product
from src.db.qdrant import get_qdrant_client
from src.services.embedding_service import EmbeddingService
from src.core.config import settings
from src.core.logging import setup_logging

logger = setup_logging()


async def generate_embeddings():
    """Generate embeddings for all products in database."""
    embedding_service = EmbeddingService()
    qdrant = get_qdrant_client()
    collection_name = settings.qdrant_collection_name
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        logger.info(f"Generating embeddings for {len(products)} products...")
        
        for product in products:
            product_text = f"{product.name} {product.category} {product.description or ''}"
            embedding = embedding_service.encode_single(product_text)
            
            qdrant.upsert(
                collection_name=collection_name,
                points=[{
                    "id": str(product.id),
                    "vector": embedding,
                    "payload": {
                        "name": product.name,
                        "category": product.category,
                        "price": product.price,
                    }
                }]
            )
        
        logger.info("Embeddings generated successfully")


if __name__ == "__main__":
    asyncio.run(generate_embeddings())




