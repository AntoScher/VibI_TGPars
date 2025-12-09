"""
Улучшенный Telegram-бот с функциями эхо и суммаризации текста.
"""
import logging
from typing import Optional
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from config import get_bot_token

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-bot")

# Получаем токен бота из .env файла
try:
    BOT_TOKEN = get_bot_token()
    # Список разрешенных пользователей (можно вынести в конфиг)
    ALLOWED_USERS = [1507961620]  # Замените на нужные ID
except ValueError as e:
    logger.error(str(e))
    raise

# Создаем экземпляр бота с улучшенными настройками
bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


def is_user_allowed(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к боту."""
    return user_id in ALLOWED_USERS


@bot.message_handler(commands=["start", "help"])
def send_welcome(message: types.Message) -> None:
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
        bot.reply_to(message, welcome_text, parse_mode="HTML")
        logger.info(f"User {message.from_user.id} used {message.text}")
    except ApiTelegramException as e:
        logger.error(f"Error sending welcome message: {e}")


@bot.message_handler(commands=["summary"])
def handle_summary(message: types.Message) -> None:
    """Обработчик команды суммаризации."""
    if not is_user_allowed(message.from_user.id):
        return

    # Получаем текст из сообщения (после команды)
    text_to_summarize = message.text.replace('/summary', '').strip()

    if not text_to_summarize:
        bot.reply_to(
            message,
            "Пожалуйста, укажите текст для суммаризации после команды /summary"
        )
        return

    try:
        # Показываем "печатает..."
        bot.send_chat_action(message.chat.id, 'typing')

        # Здесь будет вызов функции суммаризации
        # summary = generate_summary(text_to_summarize)
        summary = f"🔍 <b>Суммаризация:</b>\n\n{text_to_summarize[:100]}..."

        bot.reply_to(message, summary, parse_mode="HTML")
        logger.info(f"Generated summary for user {message.from_user.id}")

    except Exception as e:
        error_msg = "❌ Произошла ошибка при обработке запроса"
        bot.reply_to(message, error_msg)
        logger.error(f"Summary error for user {message.from_user.id}: {str(e)}")


@bot.message_handler(func=lambda message: True)
def handle_message(message: types.Message) -> None:
    """Обработчик всех текстовых сообщений."""
    if not is_user_allowed(message.from_user.id):
        logger.warning(f"Попытка доступа от неавторизованного пользователя: {message.from_user.id}")
        return

    try:
        # Показываем "печатает..."
        bot.send_chat_action(message.chat.id, 'typing')

        # Эхо-ответ с улучшенным форматированием
        response = f"📝 <b>Вы написали:</b>\n\n{message.text}"
        bot.reply_to(message, response, parse_mode="HTML")

        logger.info(f"Echo reply to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            bot.reply_to(message, "⚠️ Произошла ошибка при обработке сообщения")
        except:
            logger.critical("Critical error: cannot send error message to user")


def run_bot() -> None:
    """Запуск бота с обработкой ошибок."""
    logger.info("Starting Telegram bot...")

    try:
        # Удаляем webhook, если он активен
        try:
            bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted (if existed)")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")

        # Запускаем с обработкой ошибок
        logger.info("Starting polling...")
        bot.infinity_polling(
            none_stop=True,
            timeout=30,
            long_polling_timeout=20
        )

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_bot()