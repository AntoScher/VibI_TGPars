"""
CLI tool for summarizing text via Deepseek API.

Usage examples:
  python main.py summary --file messages.txt
  python main.py summary --text "любой текст" --max-tokens 256 --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict

from deepseek import DeepseekError, generate_summary
from utils import (
    DEFAULT_CHUNK_SIZE,
    chunk_text,
    read_text_from_file,
    warn_if_too_long,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deepseek-cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deepseek summarization CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary", help="Create a summary")
    summary_parser.add_argument(
        "--file", type=str, help="Path to a text file with messages"
    )
    summary_parser.add_argument(
        "--text", type=str, help="Text to summarize (takes priority over --file)"
    )
    summary_parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens for the model response (default: 512)",
    )
    summary_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    return parser


def summarize_text(text: str, *, max_tokens: int) -> str:
    """
    Handle long texts by chunking and summarizing progressively.
    """
    warn_if_too_long(text)

    CHUNK_LIMIT = DEFAULT_CHUNK_SIZE
    if len(text) <= CHUNK_LIMIT:
        return generate_summary(text, max_tokens=max_tokens)

    # Chunk the text and summarize each part, then summarize the combined summaries.
    chunks = chunk_text(text, chunk_size=CHUNK_LIMIT)
    logger.info("Text will be processed in %d chunks", len(chunks))
    partial_summaries = []
    for idx, chunk in enumerate(chunks, start=1):
        logger.info("Summarizing chunk %d/%d (%d chars)", idx, len(chunks), len(chunk))
        partial = generate_summary(chunk, max_tokens=max_tokens)
        partial_summaries.append(partial)

    combined = "\n\n".join(partial_summaries)
    logger.info("Summarizing combined %d partial summaries", len(partial_summaries))
    final_summary = generate_summary(combined, max_tokens=max_tokens)
    return final_summary


def handle_summary(args: argparse.Namespace) -> int:
    text: str | None = None

    if args.text:
        text = args.text
    elif args.file:
        try:
            text = read_text_from_file(args.file)
        except FileNotFoundError as exc:
            logger.error(str(exc))
            return 1
    else:
        logger.error("Please provide --text or --file")
        return 1

    try:
        summary = summarize_text(text, max_tokens=args.max_tokens)
    except DeepseekError as exc:
        logger.error(str(exc))
        return 1

    if args.json:
        output: Dict[str, Any] = {"summary": summary}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "summary":
        return handle_summary(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
"""
Telegram scraper/listener built with Telethon.

Features:
- Connect to Telegram via Telethon.
- List available dialogs.
- Fetch last N messages from a chosen chat.
- Persist messages into SQLite with duplicate protection.
- Live listener for new messages with logging and auto-reconnect.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.custom.dialog import Dialog
from telethon.tl.custom.message import Message

from config import load_config
from db import init_db, save_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telethon-app")


async def list_dialogs(client: TelegramClient) -> list[Dialog]:
    """Return the list of dialogs (chats, channels, groups, etc.)."""
    dialogs = [dialog async for dialog in client.iter_dialogs()]
    for idx, dialog in enumerate(dialogs, start=1):
        logger.info("%d. %s (id=%s)", idx, dialog.title, dialog.id)
    return dialogs


async def collect_messages(client: TelegramClient, dialog: Dialog, limit: int = 100):
    """
    Collect last N messages from a dialog and store them in the database.
    """
    logger.info("Fetching last %d messages from '%s'", limit, dialog.title)
    async for msg in client.iter_messages(dialog.id, limit=limit):
        await persist_message(dialog, msg)
    logger.info("Finished fetching messages from '%s'", dialog.title)


async def persist_message(dialog: Dialog, msg: Message) -> None:
    """Transform and persist a Telethon message."""
    message_data = {
        "id": msg.id,
        "chat_id": dialog.id,
        "sender": (msg.sender.username or msg.sender_id) if msg.sender else "unknown",
        "text": msg.message or "",
        "date": msg.date.isoformat(),
    }
    inserted = await save_message(message_data)
    if inserted:
        logger.debug("Saved message %s from chat %s", msg.id, dialog.id)


async def run_listener(client: TelegramClient) -> None:
    """
    Start the live listener for new messages.
    Telethon handles reconnections automatically.
    """

    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        dialog = await event.get_chat()
        msg: Message = event.message
        await persist_message(dialog, msg)
        sender = (msg.sender.username or msg.sender_id) if msg.sender else "unknown"
        logger.info("[%s] %s: %s", dialog.title, sender, (msg.message or "").strip())

    logger.info("Listener started. Press Ctrl+C to stop.")
    await client.run_until_disconnected()


async def main() -> None:
    config = load_config()
    await init_db()

    async with TelegramClient(config.session_name, config.api_id, config.api_hash) as client:
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.error("Session not authorized. Please sign in via Telethon.")
                return

            dialogs = await list_dialogs(client)
            if not dialogs:
                logger.warning("No dialogs available.")
                return

            # Example: choose the first dialog. Replace with your selection logic.
            target_dialog = dialogs[0]
            await collect_messages(client, target_dialog, limit=100)

            # Start live listener for new messages.
            await run_listener(client)
        except RPCError as rpc_err:
            logger.exception("Telegram RPC error: %s", rpc_err)
        except asyncio.CancelledError:
            logger.info("Shutdown requested.")
        except Exception:
            logger.exception("Unexpected error occurred.")


if __name__ == "__main__":
    asyncio.run(main())

