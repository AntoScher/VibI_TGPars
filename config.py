"""
Configuration for the Telegram client.
Fill in your Telegram API credentials below before running the project.
And other services like the bot and AI models.
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
    bot_token: str
    allowed_user_ids: list[int]


def load_config() -> TelegramConfig:
    """
    Load configuration from environment variables.
    Raises ValueError if essential variables are missing or invalid.
    """
    api_id_str = os.getenv("TG_API_ID")
    if not api_id_str or not api_id_str.isdigit():
        raise ValueError("TG_API_ID is not set or invalid in .env file.")
    api_id = int(api_id_str)

    api_hash = os.getenv("TG_API_HASH")
    if not api_hash or api_hash == "your_api_hash_here":
        raise ValueError("TG_API_HASH is not set or is a placeholder in .env file.")

    session_name = os.getenv("TG_SESSION_NAME", "telethon_session")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token or bot_token == "your_bot_token_from_botfather":
        raise ValueError("BOT_TOKEN is not set or is a placeholder in .env file.")

    allowed_users_str = os.getenv("ALLOWED_USER_IDS")
    if not allowed_users_str:
        raise ValueError("ALLOWED_USER_IDS is not set in .env file.")

    try:
        allowed_user_ids = [int(uid.strip()) for uid in allowed_users_str.split(',')]
    except ValueError as e:
        raise ValueError(f"Invalid user ID in ALLOWED_USER_IDS: {e}") from e

    return TelegramConfig(
        api_id=api_id,
        api_hash=api_hash,
        session_name=session_name,
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
    )
