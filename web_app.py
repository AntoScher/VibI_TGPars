# web_app.py
import logging
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Импортируем наши асинхронные функции из db.py
from db import fetch_last_messages, init_db, get_db_stats, fetch_paginated_messages

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web-app")

# Создаем экземпляр FastAPI
app = FastAPI(
    title="Telegram Data Visualizer",
    description="API для доступа к сообщениям, собранным из Telegram.",
    version="1.0.0",
)

# Настройка шаблонизатора
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    """Инициализирует базу данных при старте приложения."""
    await init_db()
    logger.info("Web-приложение запущено, база данных готова.")

@app.get("/api/messages/", summary="Получить сообщения из чата")
async def get_messages(
    chat_id: int = Query(..., description="ID чата в Telegram"),
    limit: int = Query(10, ge=1, le=100, description="Количество сообщений для получения")
):
    """
    Возвращает список последних сообщений для указанного чата.
    """
    try:
        messages = await fetch_last_messages(chat_id=chat_id, limit=limit)
        if not messages:
            raise HTTPException(
                status_code=404,
                detail=f"Сообщения для чата с ID {chat_id} не найдены."
            )
        return {"chat_id": chat_id, "messages": messages}
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений для чата {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/", response_class=HTMLResponse, summary="Главная страница со статистикой")
async def get_dashboard(request: Request):
    """
    Отображает главную страницу дашборда со статистикой.
    """
    stats = await get_db_stats()
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats}
    )

@app.get("/messages", response_class=HTMLResponse, summary="Страница со всеми сообщениями")
async def get_all_messages_page(
    request: Request,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(50, ge=10, le=200, description="Сообщений на странице")
):
    """
    Отображает страницу со списком всех сообщений из базы данных.
    """
    messages, total_pages = await fetch_paginated_messages(page=page, page_size=size)
    return templates.TemplateResponse(
        "messages.html", {
            "request": request,
            "messages": messages,
            "current_page": page,
            "total_pages": total_pages,
        }
    )
