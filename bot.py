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
from db import get_db_stats, search_messages

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

# --- Фильтры ---
class IsAllowedUser(telebot.asyncio_filters.SimpleCustomFilter):
    """Проверяет, есть ли у пользователя доступ к боту."""
    key = 'is_allowed'
    @staticmethod
    async def check(message: types.Message):
        is_allowed = message.from_user.id in ALLOWED_USERS
        if not is_allowed:
            logger.warning(f"Доступ запрещен для пользователя {message.from_user.id}")
        return is_allowed

# --- Обработчики команд ---
@bot.message_handler(commands=["start", "help"], is_allowed=True)
async def send_welcome(message: types.Message) -> None:
    """Обработчик команд /start и /help."""

    welcome_text = (
        "👋 <b>Привет! Я умный бот.</b>\n\n"
        "Я умею:\n"
        "• Показывать эту справку (/help)\n"
        "• Отображать статистику по базе данных (/stats)\n"
        "• Искать сообщения по слову (/search <слово>)\n"
        "• Суммаризировать текст (/summary)\n\n"
        "Просто отправь мне текст, и я помогу с его обработкой."
    )

    try:
        await bot.reply_to(message, welcome_text, parse_mode="HTML")
        logger.info(f"User {message.from_user.id} used {message.text}")
    except ApiTelegramException as e:
        logger.error(f"Error sending welcome message: {e}")

@bot.message_handler(commands=["stats"], is_allowed=True)
async def handle_stats(message: types.Message) -> None:
    """Обработчик команды для получения статистики из БД."""
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        stats = await get_db_stats()

        stats_text = (
            "📊 <b>Статистика базы данных:</b>\n\n"
            f"Всего сообщений: <b>{stats['total_messages']}</b>\n"
            f"Уникальных чатов: <b>{stats['unique_chats']}</b>\n"
            f"Дата последнего сообщения: <b>{stats['last_message_date'] or 'Нет данных'}</b>"
        )

        await bot.reply_to(message, stats_text, parse_mode="HTML")
        logger.info(f"Sent DB stats to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        await bot.reply_to(message, "❌ Не удалось получить статистику из базы данных.")

@bot.message_handler(commands=["summary"], is_allowed=True)
async def handle_summary(message: types.Message) -> None:
    """Обработчик команды суммаризации."""
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

@bot.message_handler(commands=["search"], is_allowed=True)
async def handle_search(message: types.Message) -> None:
    """Обработчик команды для поиска сообщений в БД."""
    keyword = message.text.replace('/search', '').strip()
    if not keyword:
        await bot.reply_to(message, "Пожалуйста, укажите слово для поиска после команды /search.")
        return

    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        found_messages = await search_messages(keyword)

        if not found_messages:
            await bot.reply_to(message, f"Сообщений со словом «{keyword}» не найдено.")
            return

        response_lines = [f"🔎 <b>Найдено {len(found_messages)} сообщ. по запросу «{keyword}»:</b>\n"]
        for msg in found_messages:
            # Обрезаем длинные сообщения для красивого вывода
            text_preview = msg['text'][:70] + '...' if len(msg['text']) > 70 else msg['text']
            date_short = msg['date'].split('T')[0]
            response_lines.append(
                f"\n- <i>({date_short})</i> <b>{msg['sender']}:</b> {text_preview}"
            )
        
        # Telegram имеет лимит на длину сообщения
        response = "\n".join(response_lines)
        if len(response) > 4096:
            response = response[:4090] + "\n..."

        await bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Search error for user {message.from_user.id}: {e}")
        await bot.reply_to(message, "❌ Произошла ошибка во время поиска.")

@bot.message_handler(func=lambda message: True, is_allowed=True)
async def handle_message(message: types.Message) -> None:
    """Обработчик всех текстовых сообщений."""
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
    # Регистрируем наш кастомный фильтр
    bot.add_custom_filter(IsAllowedUser())

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