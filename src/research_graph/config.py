from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RG_", extra="ignore")

    github_token: str | None = None
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    request_timeout: float = Field(default=30.0, gt=0, le=300)
    max_concurrency: int = Field(default=8, ge=1, le=64)

    @field_validator("log_level")
    @classmethod
    def _check_level(cls, v: str) -> str:
        v = v.upper()
        if v not in _LEVELS:
            raise ValueError(f"log_level must be one of {sorted(_LEVELS)}")
        return v

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


def get_settings() -> Settings:
    return Settings()
