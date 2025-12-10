"""
Улучшенный Telegram-бот с функциями эхо и суммаризации текста.
"""
import logging
from typing import Optional
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.apihelper import ApiTelegramException
from config import load_config
from deepseek import generate_summary, DeepseekError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-bot")
# Загружаем конфигурацию
try:
    cfg = load_config()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Создаем экземпляр бота
bot = AsyncTeleBot(
    cfg.bot_token,
    parse_mode="HTML"
)



ALLOWED_USERS = cfg.allowed_user_ids


# --- Обработчики ---
def is_user_allowed(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к боту."""
    return user_id in ALLOWED_USERS


@bot.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message) -> None:
    """Обработчик команд /start и /help."""
    if not is_user_allowed(message.from_user.id):
        logger.warning(f"Доступ запрещен для пользователя {message.from_user.id}")
        return

    welcome_text = (
        "👋 <b>Привет! Я умный бот.</b>\n\n"
        "Я умею:\n"
        "• Отвечать на сообщения (/help)\n"
        "• Суммаризировать текст (/summary)\n\n"
        "Просто отправь мне текст, и я помогу с его обработкой."
    )

    try:
        await bot.reply_to(message, welcome_text, parse_mode="HTML")
        logger.info(f"User {message.from_user.id} used {message.text}")
    except ApiTelegramException as e:
        logger.error(f"Error sending welcome message: {e}")


@bot.message_handler(commands=["summary"])
async def handle_summary(message: types.Message) -> None:
    """Обработчик команды суммаризации."""
    if not is_user_allowed(message.from_user.id):
        return

    # Получаем текст из сообщения (после команды)
    text_to_summarize = message.text.replace('/summary', '').strip()

    if not text_to_summarize:
        await bot.reply_to(
            message,
            "Пожалуйста, укажите текст для суммаризации после команды /summary"
        )
        return

    try:
        # Показываем "печатает..."
        await bot.send_chat_action(message.chat.id, 'typing')

        # Вызов функции суммаризации из deepseek.py
        raw_summary = await generate_summary(text_to_summarize)
        summary = f"🔍 <b>Краткая выжимка:</b>\n\n{raw_summary}"

        await bot.reply_to(message, summary, parse_mode="HTML")
        logger.info(f"Generated summary for user {message.from_user.id}")

    except DeepseekError as e:
        error_msg = f"❌ Ошибка при обращении к сервису суммиризации: {e}"
        await bot.reply_to(message, error_msg)
        logger.error(f"Deepseek API error for user {message.from_user.id}: {str(e)}")
    except Exception as e:
        error_msg = "❌ Произошла ошибка при обработке запроса"
        await bot.reply_to(message, error_msg)
        logger.error(f"Summary error for user {message.from_user.id}: {str(e)}")


@bot.message_handler(func=lambda message: True)
async def handle_message(message: types.Message) -> None:
    """Обработчик всех текстовых сообщений."""
    if not is_user_allowed(message.from_user.id):
        logger.warning(f"Попытка доступа от неавторизованного пользователя: {message.from_user.id}")
        return

    try:
        # Показываем "печатает..."
        await bot.send_chat_action(message.chat.id, 'typing')

        # Эхо-ответ с улучшенным форматированием
        response = f"📝 <b>Вы написали:</b>\n\n{message.text}"
        await bot.reply_to(message, response, parse_mode="HTML")

        logger.info(f"Echo reply to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await bot.reply_to(message, "⚠️ Произошла ошибка при обработке сообщения")
        except:
            logger.critical("Critical error: cannot send error message to user")


# --- Запуск бота ---
async def run_bot() -> None:
    """Запуск бота с обработкой ошибок."""
    logger.info("Starting Telegram bot...")

    try:
        # Удаляем webhook, если он активен
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted (if existed)")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")

        # Запускаем с обработкой ошибок
        logger.info("Starting polling...")
        await bot.infinity_polling(timeout=30)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot())