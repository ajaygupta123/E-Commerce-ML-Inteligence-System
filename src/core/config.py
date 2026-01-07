"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=('settings_',),  # Exclude 'model_' from protected namespaces
    )
    
    # Database
    database_url: str = "postgresql+asyncpg://app:password@postgres:5432/ecommerce"
    
    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "products"
    
    # Ollama
    ollama_host: str = "ollama"
    ollama_port: int = 11434
    llm_model: str = "llama3.2:3b"
    
    # Cache
    cache_type: str = "memory"
    cache_ttl: int = 300
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    
    # Model
    model_path: str = "/app/models/tuned_catboost_model.cbm"  # Use tuned model by default
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_enabled: bool = True  # Can be disabled for load testing
    
    # Drift Detection
    drift_check_schedule: str = "0 2 1 * *"  # Monthly on 1st day at 2 AM (cron format)
    drift_data_threshold: float = 0.3  # Data drift threshold (0-1)
    drift_performance_threshold: float = 0.1  # Performance drift threshold (0-1)
    drift_reference_window_days: int = 30  # Reference period for comparison
    drift_current_window_days: int = 7  # Current period to check
    drift_min_samples: int = 100  # Minimum samples required for drift detection
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle string "false" from environment variables
        if isinstance(self.rate_limit_enabled, str):
            self.rate_limit_enabled = self.rate_limit_enabled.lower() in ('true', '1', 'yes', 'on')
    
    # Security
    allowed_origins: str = "*"
    
    @property
    def ollama_base_url(self) -> str:
        """Get Ollama base URL."""
        return f"http://{self.ollama_host}:{self.ollama_port}"
    
    @property
    def qdrant_url(self) -> str:
        """Get Qdrant URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


settings = Settings()


