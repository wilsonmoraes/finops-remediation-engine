"""Shared test fixtures.

The ``client`` fixture points the engine at a throwaway SQLite file under the
test's tmp dir, so API tests run against a real database without touching the
developer's local data.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FINOPS_DB_PATH", str(tmp_path / "test.db"))

    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


@pytest.fixture()
def inventory_bytes() -> bytes:
    return (_SAMPLES / "aws_inventory.json").read_bytes()
