"""Qdrant vector database client."""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, CollectionStatus
from typing import Optional

from ..core.config import settings
from ..core.logging import setup_logging

logger = setup_logging()

_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            timeout=30,
        )
    return _qdrant_client


async def init_qdrant(vector_size: int = 384) -> None:
    """Initialize Qdrant collection if it doesn't exist."""
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)
    
    if not collection_exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {collection_name}")
    else:
        logger.info(f"Qdrant collection already exists: {collection_name}")




