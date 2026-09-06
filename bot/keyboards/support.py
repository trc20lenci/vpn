from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def support_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎫 Создать тикет", callback_data="ticket_create"))
    kb.row(InlineKeyboardButton(text="📋 Мои тикеты", callback_data="ticket_list"))
    kb.row(InlineKeyboardButton(text="💬 Связаться", callback_data="ticket_contact"))
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
