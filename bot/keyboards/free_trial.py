from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import config


def free_trial_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Подписаться", url=config.channel_url))
    kb.row(InlineKeyboardButton(text="✅ Проверить подписку", callback_data="free_trial_check"))
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
