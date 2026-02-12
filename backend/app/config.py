"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral AI API key")
    
    # Directories
    output_dir: Path = Field(default=Path("/tmp/tracenet"), description="Output directory for generated files")
    
    # Rate Limiting
    max_requests_per_minute: str = Field(default="10/minute", description="Max PKT generation requests per minute")
    
    # CORS
    allowed_origins: str = Field(
        default="http://localhost:5173,https://tracenet.vercel.app",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
