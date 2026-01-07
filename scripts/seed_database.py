"""Script to seed database with products from the actual dataset."""
import asyncio
import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.postgres import AsyncSessionLocal, init_db
from src.db.models.product import Product
from src.db.qdrant import get_qdrant_client, init_qdrant
from src.services.embedding_service import EmbeddingService
from src.core.logging import setup_logging

logger = setup_logging()


async def seed_products():
    """Seed database with products from the actual dataset."""
    await init_db()
    await init_qdrant()
    
    # Load actual dataset
    dataset_path = Path(__file__).parent.parent / "data" / "raw" / "amazon_sales_dataset.csv"
    
    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}")
        return
    
    logger.info(f"Loading dataset from {dataset_path}")
    df = pd.read_csv(dataset_path, nrows=50)  # Load first 50 products for seeding
    
    # Clean and prepare data
    # Remove currency symbols and convert prices to float
    def clean_price(price_str):
        if pd.isna(price_str):
            return None
        # Remove currency symbols and commas
        price_str = str(price_str).replace('₹', '').replace(',', '').strip()
        try:
            return float(price_str)
        except:
            return None
    
    def clean_discount(discount_str):
        if pd.isna(discount_str):
            return None
        # Remove % sign
        discount_str = str(discount_str).replace('%', '').strip()
        try:
            return float(discount_str)
        except:
            return None
    
    def clean_rating_count(count_str):
        if pd.isna(count_str):
            return None
        # Remove commas
        count_str = str(count_str).replace(',', '').strip()
        try:
            return int(float(count_str))
        except:
            return None
    
    # Prepare products from dataset
    # Map dataset fields to Product model fields
    sample_products = []
    for _, row in df.iterrows():
        actual_price = clean_price(row.get("actual_price"))
        product_name = str(row.get("product_name", "")).strip()
        category = str(row.get("category", "")).strip()
        
        # Only add if we have essential fields
        if not product_name or not category or actual_price is None:
            continue
        
        # Map dataset columns to Product model fields
        product_data = {
            "name": product_name[:500],  # Product model uses 'name' not 'product_name'
            "category": category[:200],
            "price": actual_price,  # Product model uses 'price' not 'actual_price'
            "discount_percentage": clean_discount(row.get("discount_percentage")),
            "rating": float(row.get("rating", 0)) if pd.notna(row.get("rating")) else None,
            "num_reviews": clean_rating_count(row.get("rating_count")) or 0,  # Product model uses 'num_reviews' not 'rating_count'
            "description": str(row.get("about_product", ""))[:5000] if pd.notna(row.get("about_product")) else None,  # Product model uses 'description' not 'about_product'
            # Store additional dataset fields in attributes JSON
            "attributes": {
                "product_id": str(row.get("product_id", "")),
                "discounted_price": clean_price(row.get("discounted_price")),
                "img_link": str(row.get("img_link", ""))[:500] if pd.notna(row.get("img_link")) else None,
                "product_link": str(row.get("product_link", ""))[:500] if pd.notna(row.get("product_link")) else None,
            }
        }
        
        sample_products.append(product_data)
    
    embedding_service = EmbeddingService()
    qdrant = get_qdrant_client()
    collection_name = "products"
    
    async with AsyncSessionLocal() as session:
        for product_data in sample_products:
            # Create product
            product = Product(**product_data)
            session.add(product)
            await session.flush()
            
            # Generate embedding
            product_text = f"{product.name} {product.category}"
            if product.description:
                product_text += f" {product.description}"
            embedding = embedding_service.encode_single(product_text)
            
            # Add to Qdrant
            product_id = product.attributes.get("product_id") if product.attributes else None
            qdrant.upsert(
                collection_name=collection_name,
                points=[{
                    "id": str(product.id),
                    "vector": embedding,
                    "payload": {
                        "name": product.name,
                        "category": product.category,
                        "price": product.price,
                        "product_id": product_id,
                    }
                }]
            )
            
            logger.info(f"Added product: {product.name}")
        
        await session.commit()
    
    logger.info(f"Seeded {len(sample_products)} products")


if __name__ == "__main__":
    asyncio.run(seed_products())


