"""Database connection helpers."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from common.constants import DEFAULT_DB_PATH


def get_db_path() -> Path:
    """Return configured SQLite database path."""

    return Path(os.getenv("NETCOURIER_DB_PATH", DEFAULT_DB_PATH))


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign key enforcement enabled."""

    path = Path(db_path) if db_path is not None else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
