"""Create (or update) the SQLite database from the canonical schema.

Run after cloning, or to reseed: delete the database file first, then run this.

    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import init_schema


def main() -> None:
    init_schema()
    print(f"schema applied: {get_settings().db_path}")


if __name__ == "__main__":
    main()
