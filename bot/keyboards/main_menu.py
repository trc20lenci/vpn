from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(discount_minutes_left: int | None = None) -> InlineKeyboardMarkup:
    """
    Компактное меню: 2 крупные кнопки (основные действия) + 4 маленькие в сетке 2x2.
    "Поддержка" вынесена в командное меню слева (/support) и не дублируется здесь,
    чтобы не раздувать список.
    """
    discount_label = "🔥 Скидка 30%"
    if discount_minutes_left is not None and discount_minutes_left > 0:
        discount_label = f"🔥 Скидка 30% ({discount_minutes_left} мин)"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🆓 Получить VPN бесплатно на 1 час", callback_data="free_trial"))
    kb.row(InlineKeyboardButton(text="🪙 Купить подписку", callback_data="subscription"))
    kb.row(
        InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
        InlineKeyboardButton(text=discount_label, callback_data="discount"),
    )
    kb.row(
        InlineKeyboardButton(text="🤝 50₽ за друга", callback_data="referral"),
        InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about"),
    )
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()
