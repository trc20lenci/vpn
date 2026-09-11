"""
Запускает бота (polling) и веб-часть (админка + /sub/<token>) параллельно
в одном процессе через asyncio. Для продакшена можно так и оставить (проще),
либо развести на два systemd-юнита — тогда просто используйте
`python -m bot.main` и `uvicorn admin.app:app` отдельно.

Запуск:
    python run.py
"""
import asyncio
import logging

import uvicorn

from bot.config import config
from bot.database import db
from bot.main import main as run_bot


async def run_admin():
    server_config = uvicorn.Config(
        "admin.app:app",
        host=config.admin_host,
        port=config.admin_port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main():
    logging.basicConfig(level=logging.INFO)
    # инициализируем БД один раз до старта обоих сервисов, чтобы не было гонки
    await db.init()
    await db.ensure_default_server_from_config()
    await asyncio.gather(run_bot(), run_admin())


if __name__ == "__main__":
    asyncio.run(main())
