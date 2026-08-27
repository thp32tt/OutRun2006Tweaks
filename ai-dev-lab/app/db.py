from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def db_path() -> Path:
    return Path(os.getenv("AGENTBOARD_DB", "agentboard.db"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 1 AND 3),
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'doing', 'done')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
