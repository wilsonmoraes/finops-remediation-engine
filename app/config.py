"""Application settings.

Centralizes the tunables the engine needs: where the SQLite file lives and the
thresholds the detection rules use to decide a resource is idle. Values come from
the environment (prefix ``FINOPS_``) with sensible defaults so the app runs with
zero configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration, overridable via ``FINOPS_*`` environment variables."""

    model_config = SettingsConfigDict(env_prefix="FINOPS_", env_file=".env", extra="ignore")

    db_path: Path = Field(default=_REPO_ROOT / "data" / "finops.db")
    schema_path: Path = Field(default=_REPO_ROOT / "db" / "init_db.sql")

    idle_vm_days: int = Field(
        default=14,
        description="A running VM with no activity for this many days is treated as idle.",
    )
    stale_snapshot_days: int = Field(
        default=90,
        description="An unattached snapshot older than this many days is treated as stale.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""

    return Settings()
