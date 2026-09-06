from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def balance_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Пополнить", callback_data="balance_topup"))
    kb.row(InlineKeyboardButton(text="📜 История операций", callback_data="balance_history"))
    kb.row(InlineKeyboardButton(text="🤝 +50₽ за каждого друга", callback_data="referral"))
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
