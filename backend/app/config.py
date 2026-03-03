"""Application configuration using Pydantic Settings."""

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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
    
    def validate_runtime(self) -> dict:
        """Validate runtime configuration and return status."""
        checks = {
            "mistral_api_key": bool(self.mistral_api_key),
            "output_dir_exists": self.output_dir.exists() if self.output_dir else False,
            "environment": self.environment,
        }
        
        # Create output directory if it doesn't exist
        if self.output_dir:
            try:
                if not self.output_dir.exists():
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    checks["output_dir_created"] = True

                checks["output_dir_exists"] = self.output_dir.exists() and self.output_dir.is_dir()
                if not checks["output_dir_exists"]:
                    raise RuntimeError(f"Output dir is not a directory: {self.output_dir}")

                # Basic writability check (fail fast on permission issues in production/Docker).
                probe = self.output_dir / ".tracenet_write_check"
                with open(probe, "wb") as fp:
                    fp.write(b"ok")
                os.remove(probe)
                checks["output_dir_writable"] = True
            except Exception as exc:
                logger.error("Output directory check failed for %s: %s", self.output_dir, exc, exc_info=True)
                checks["output_dir_exists"] = False
                checks["output_dir_writable"] = False
                checks["output_dir_error"] = str(exc)
        
        return checks


settings = Settings()
