"""Application settings and startup validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    environment: str = Field(default='development', alias='ENVIRONMENT')
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    mistral_api_key: str | None = Field(default=None, alias='MISTRAL_API_KEY')

    output_dir: Path = Field(default=Path('/tmp/tracenet'), alias='OUTPUT_DIR')
    pkt_template_path: Path | None = Field(default=None, alias='PKT_TEMPLATE_PATH')

    allowed_origins: str = Field(
        default='http://localhost:5173,https://tracenet.vercel.app',
        alias='ALLOWED_ORIGINS',
    )
    max_requests_per_minute: str = Field(default='10/minute', alias='MAX_REQUESTS_PER_MINUTE')

    @field_validator('output_dir')
    @classmethod
    def _normalize_output_dir(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator('pkt_template_path')
    @classmethod
    def _normalize_template_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return value.expanduser().resolve()

    def validate_runtime(self) -> dict[str, Any]:
        """Validate writable directories and template path at startup."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        test_file = self.output_dir / '.startup_healthcheck'
        test_file.write_text('ok', encoding='utf-8')
        test_file.unlink(missing_ok=True)

        template_path = self.pkt_template_path
        if template_path is not None and not template_path.exists():
            raise FileNotFoundError(f'PKT_TEMPLATE_PATH not found: {template_path}')

        return {
            'output_dir': str(self.output_dir),
            'template_override': str(template_path) if template_path else None,
            'mistral_configured': bool(self.mistral_api_key),
        }


settings = Settings()
