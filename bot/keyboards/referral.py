from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def referral_kb(ref_link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="📤 Пригласить друга",
        switch_inline_query=f"Забирай бесплатный VPN на 1 час 🔒 {ref_link}",
    ))
    kb.row(InlineKeyboardButton(text="🔗 Скопировать ссылку", callback_data="ref_copy_link"))
    kb.row(InlineKeyboardButton(text="🏷️ Создать свой промокод", callback_data="ref_create_promo"))
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
