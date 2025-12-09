"""
Configuration for the Telegram client.
Fill in your Telegram API credentials below before running the project.
"""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    session_name: str


def load_config() -> TelegramConfig:
    """
    Load configuration from environment variables if present,
    otherwise fall back to hardcoded defaults.
    """
    api_id = int(os.getenv("TG_API_ID", "0"))  # set in .env: TG_API_ID
    api_hash = os.getenv("TG_API_HASH", "your_api_hash_here")  # set in .env
    session_name = os.getenv("TG_SESSION_NAME", "telethon_session")
    return TelegramConfig(api_id=api_id, api_hash=api_hash, session_name=session_name)


def get_bot_token() -> str:
    """
    Load bot token from environment variables (.env file).
    Raises ValueError if token is not found.
    """
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError(
            "BOT_TOKEN not found in environment variables. "
            "Please create a .env file with BOT_TOKEN=your_bot_token"
        )
    return token

