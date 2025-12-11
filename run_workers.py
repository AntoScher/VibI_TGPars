"""
Этот скрипт запускает и управляет обоими фоновыми процессами:
1. Телеграм-бот (`bot.py`)
2. Сборщик сообщений Telethon (`main.py`)
"""
import asyncio
import logging

from bot import run_bot
from main import main as run_collector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("worker-manager")

async def start_all():
    """Запускает все воркеры параллельно."""
    logger.info("Запуск всех фоновых процессов...")
    await asyncio.gather(
        run_bot(),
        run_collector()
    )

if __name__ == "__main__":
    asyncio.run(start_all())