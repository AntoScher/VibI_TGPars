"""
Async SQLite helpers for storing Telegram messages.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import aiosqlite

DB_PATH = "messages.db"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    sender TEXT,
    text TEXT,
    date TEXT,
    PRIMARY KEY (id, chat_id)
);
"""


async def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database and ensure tables exist."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def save_message(message_data: Dict[str, Any], db_path: str = DB_PATH) -> bool:
    """
    Save a single message to SQLite.
    Returns True if inserted, False when it was a duplicate.
    """
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute(
                """
                INSERT INTO messages (id, chat_id, sender, text, date)
                VALUES (:id, :chat_id, :sender, :text, :date)
                """,
                message_data,
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Duplicate detected (PRIMARY KEY violation).
            return False


async def fetch_last_messages(
    chat_id: int, limit: int = 100, db_path: str = DB_PATH
) -> list[dict]:
    """Fetch last N stored messages for a chat (ordered descending by id)."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, chat_id, sender, text, date
            FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

