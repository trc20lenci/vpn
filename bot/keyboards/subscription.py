from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ключ плана -> (подпись, базовая цена в рублях, None = "навсегда")
PLANS = {
    "forever": ("Навсегда", 4990, None),
    "2y": ("2 года", 3490, 730),
    "1y": ("1 год", 1990, 365),
    "6m": ("6 месяцев", 1190, 182),
    "3m": ("3 месяца", 690, 91),
    "1m": ("1 месяц", 299, 30),
}


def subscription_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for plan_id, (label, price, _) in PLANS.items():
        kb.row(InlineKeyboardButton(text=f"{label} — {price}₽", callback_data=f"plan:{plan_id}"))
    kb.row(InlineKeyboardButton(text="🎁 Подарить VPN", callback_data="gift_vpn"))
    kb.row(InlineKeyboardButton(text="⬇️ Перейти на базовый", callback_data="downgrade_basic"))
    kb.row(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu"))
    return kb.as_markup()


def payment_method_kb(context: str) -> InlineKeyboardMarkup:
    """context — например 'plan:1m' или 'balance_topup', пробрасывается дальше в callback_data."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📱 СБП", callback_data=f"pay:sbp:{context}"))
    kb.row(InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"pay:card:{context}"))
    kb.row(InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay:stars:{context}"))
    kb.row(InlineKeyboardButton(text="🪙 Криптовалюта (CryptoBot)", callback_data=f"pay:crypto:{context}"))
    kb.row(InlineKeyboardButton(text="🏦 СБП — другой банк", callback_data=f"pay:sbp_other:{context}"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="subscription"))
    return kb.as_markup()
