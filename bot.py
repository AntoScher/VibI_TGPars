"""
Простой Telegram-бот на pyTelegramBotAPI с функцией echo.
Бот повторяет все полученные сообщения обратно пользователю.
"""
import logging
import telebot
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
except ValueError as e:
    logger.error(str(e))
    raise

# Создаем экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Обработчик команд /start и /help."""
    welcome_text = (
        "Привет! Я echo-бот.\n\n"
        "Просто отправь мне любое сообщение, и я повторю его обратно тебе."
    )
    bot.reply_to(message, welcome_text)
    logger.info(f"User {message.from_user.id} used /start or /help")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Echo-функция: повторяет все полученные сообщения."""
    # Отправляем обратно то же сообщение
    bot.reply_to(message, message.text)
    logger.info(
        f"Echo message from user {message.from_user.id} (@{message.from_user.username}): {message.text}"
    )


def run_bot():
    """Запуск бота."""
    logger.info("Starting Telegram bot...")
    try:
        # Удаляем webhook, если он активен (необходимо для polling)
        try:
            bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted (if existed)")
        except Exception as e:
            logger.warning(f"Could not delete webhook (may not exist): {e}")
        
        # Запускаем polling
        logger.info("Starting polling...")
        bot.infinity_polling(none_stop=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Error occurred: {e}")
        raise


if __name__ == "__main__":
    run_bot()

