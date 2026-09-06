from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🆓 Получить VPN бесплатно на 1 час", callback_data="free_trial"))
    kb.row(InlineKeyboardButton(text="🪙 Купить подписку", callback_data="subscription"))
    kb.row(InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balance"))
    kb.row(InlineKeyboardButton(text="🔥 Скидка 30%", callback_data="discount"))
    kb.row(InlineKeyboardButton(text="🤝 50₽ за друга", callback_data="referral"))
    kb.row(InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about"))
    kb.row(InlineKeyboardButton(text="🛟 Поддержка", callback_data="support"))
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
