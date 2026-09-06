import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import config
from bot.database import db
from bot.utils import texts

from bot.handlers import start, free_trial, subscription, balance, referral, support


async def set_commands(bot: Bot):
    """Меню команд слева от поля ввода (кнопка 'Menu' в клиенте Telegram)."""
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="subscription", description="🪙 Купить подписку"),
        BotCommand(command="balance", description="💰 Баланс"),
        BotCommand(command="referral", description="🤝 50₽ за друга"),
        BotCommand(command="about", description="ℹ️ О сервисе"),
        BotCommand(command="support", description="🛟 Поддержка"),
    ])


async def set_bot_description(bot: Bot):
    """
    Описание бота, которое видно ДО нажатия /start — на пустом экране чата
    (description) и в предпросмотрах/шаринге (short_description).
    Именно сюда идёт "что умеет бот".
    """
    await bot.set_my_description(texts.BOT_FULL_DESCRIPTION)
    await bot.set_my_short_description(texts.BOT_SHORT_DESCRIPTION)


async def main():
    logging.basicConfig(level=logging.INFO)

    await db.init()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(free_trial.router)
    dp.include_router(subscription.router)
    dp.include_router(balance.router)
    dp.include_router(referral.router)
    dp.include_router(support.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await set_bot_description(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
