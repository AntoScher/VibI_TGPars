"""
Основной файл для запуска Telegram-клиента.
Собирает сообщения и слушает новые события в реальном времени.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from telethon import TelegramClient, events
from telethon.tl.types import Dialog, Message

from config import load_config
from db import fetch_last_messages, init_db, save_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_message(message: Message) -> None:
    """Обрабатывает и сохраняет одно сообщение."""
    sender_name = "Unknown"
    if message.sender:
        sender_name = getattr(message.sender, "first_name", "User") or str(
            message.sender_id
        )

    message_data = {
        "id": message.id,
        "chat_id": message.chat_id,
        "sender": sender_name,
        "text": message.text,
        "date": message.date.isoformat(),
    }
    await save_message(message_data)


async def main() -> int:
    """Основная функция для запуска клиента."""
    try:
        cfg = load_config()
        if cfg.api_id == 0 or cfg.api_hash == "your_api_hash_here":
            logger.error(
                "Пожалуйста, заполните TG_API_ID и TG_API_HASH в вашем .env файле."
            )
            return 1
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка в конфигурации: {e}")
        return 1

    await init_db()
    logger.info("База данных инициализирована.")

    client = TelegramClient(cfg.session_name, cfg.api_id, cfg.api_hash)

    @client.on(events.NewMessage())
    async def new_message_handler(event: events.NewMessage.Event):
        """Обработчик новых сообщений."""
        message = event.message
        if not message.text:
            return

        await process_message(message)

        chat = await event.get_chat()
        sender = await event.get_sender()
        sender_name = getattr(sender, "first_name", f"User {sender.id}")
        chat_title = getattr(chat, "title", f"Chat {chat.id}")

        logger.info(f"[{chat_title}] {sender_name}: {message.text}")

    try:
        await client.start()
        logger.info("Клиент успешно запущен.")

        # --- Пример использования ---
        # 1. Получаем список диалогов
        dialogs: list[Dialog] = await client.get_dialogs()
        logger.info("Получены диалоги:")
        for i, dialog in enumerate(dialogs[:10]):  # Показываем первые 10
            logger.info(f"  {i+1}. {dialog.name} (ID: {dialog.id})")

        # 2. Собираем сообщения из целевых чатов
        if cfg.target_chat_ids:
            logger.info(f"Начинается сбор сообщений из целевых чатов: {cfg.target_chat_ids}")
            for chat_id in cfg.target_chat_ids:
                try:
                    logger.info(f"Сбор из чата {chat_id}...")
                    async for message in client.iter_messages(chat_id, limit=cfg.history_fetch_limit):
                        if message and message.text:
                            await process_message(message)
                except Exception as e:
                    logger.error(f"Не удалось получить сообщения из чата {chat_id}: {e}")
        else:
            # Собираем последние 100 сообщений из первого диалога, если цели не указаны
            if not dialogs:
                logger.warning("Диалоги не найдены и TARGET_CHAT_IDS не указан. Сбор исторических сообщений пропущен.")
            else:
                target_chat = dialogs[0]
                logger.info(
                    f"TARGET_CHAT_IDS не указан. Сбор последних {cfg.history_fetch_limit} сообщений из первого чата '{target_chat.name}'..."
                )
                async for message in client.iter_messages(target_chat, limit=cfg.history_fetch_limit):
                    if message and message.text:
                        await process_message(message)

        logger.info("Сбор старых сообщений завершен.")

        # 3. Запускаем слушателя новых сообщений
        logger.info("Слушатель новых сообщений запущен. Нажмите Ctrl+C для выхода.")
        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Произошла критическая ошибка: {e}", exc_info=True)
        return 1
    finally:
        if client.is_connected():
            await client.disconnect()
        logger.info("Клиент остановлен.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
