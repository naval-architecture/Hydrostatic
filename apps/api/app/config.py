"""
Application configuration.

MVP assumptions (confirmed 2026-07-01):
- Full-hull meshes only. No half-hull mirroring.
- Mesh Z=0 in the source .3dm IS the Baseline. No offset correction applied.
- Monohull geometry only. Cb/Cm/Cp/Cw use standard Lpp * Bwl * T formulas.
"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Naval Architecture Suite API"
    # Comma-separated string, not list[str] — pydantic-settings requires JSON-array
    # syntax for list-typed env vars, which is easy to mangle in a web UI text field.
    # validation_alias pins this to NAVAL_ARCH_CORS_ORIGINS (not *_RAW) so existing
    # deployments don't need to rename their env var.
    cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias="NAVAL_ARCH_CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    # Where uploaded .3dm files are temporarily written before parsing.
    upload_dir: str = "/tmp/naval-arch-uploads"

    # Max upload size in bytes (100 MB default — hull meshes can be large).
    max_upload_size: int = 100 * 1024 * 1024

    class Config:
        env_prefix = "NAVAL_ARCH_"


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
