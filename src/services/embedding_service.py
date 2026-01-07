"""Embedding service for generating vector embeddings."""
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

from ..core.config import settings
from ..core.logging import setup_logging

logger = setup_logging()

_embedding_model: SentenceTransformer = None


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        global _embedding_model
        if _embedding_model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            _embedding_model = SentenceTransformer(self.model_name)
        return _embedding_model
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings
    
    def encode_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.encode([text])[0]
        return embedding.tolist()




