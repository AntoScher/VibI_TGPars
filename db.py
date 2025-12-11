"""
Async SQLite helpers for storing Telegram messages.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
import os

import aiosqlite

# Путь к БД теперь настраивается через переменную окружения для гибкости при деплое
DB_PATH = os.getenv("DB_PATH", "messages.db")

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


async def search_messages(keyword: str, limit: int = 30, db_path: str = DB_PATH) -> list[dict]:
    """Search for messages containing a keyword."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, chat_id, sender, text, date
            FROM messages
            WHERE text LIKE ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (f"%{keyword}%", limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_db_stats(db_path: str = DB_PATH) -> dict[str, Any]:
    """Fetch statistics from the database."""
    stats = {"total_messages": 0, "unique_chats": 0, "last_message_date": None}
    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
                stats["total_messages"] = (await cursor.fetchone())[0]

            async with db.execute("SELECT COUNT(DISTINCT chat_id) FROM messages") as cursor:
                stats["unique_chats"] = (await cursor.fetchone())[0]

            async with db.execute("SELECT MAX(date) FROM messages") as cursor:
                date_val = await cursor.fetchone()
                if date_val and date_val[0]:
                    stats["last_message_date"] = date_val[0].split("T")[0]

        except aiosqlite.OperationalError:
            # Table might not exist yet if no messages are saved
            pass
    return stats


async def fetch_paginated_messages(
    page: int = 1, page_size: int = 50, db_path: str = DB_PATH
) -> tuple[list[dict], int]:
    """Fetch a paginated list of messages and the total number of pages."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # 1. Получаем общее количество сообщений для расчета страниц
        async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
            total_messages = (await cursor.fetchone())[0]

        total_pages = (total_messages + page_size - 1) // page_size or 1

        # 2. Получаем сообщения для текущей страницы
        offset = (page - 1) * page_size
        async with db.execute(
            """
            SELECT id, chat_id, sender, text, date FROM messages
            ORDER BY date DESC LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows], total_pages
