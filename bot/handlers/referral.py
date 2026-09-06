"""
Реферальная система.

Правила начисления (заданы в ТЗ):
- Реферер получает 50₽ + 2 билета, когда приглашённый им друг ВЫПОЛНИЛ условие:
  взял бесплатный час С подпиской на каналы, ИЛИ купил платную подписку.
- Если реферер сам был приглашён кем-то ("друг пригласил друга"), то по цепочке
  наверх начисляется 1 билет тому, кто пригласил самого реферера.
- Бонусный баланс (₽) тратится только на базовый тариф — это ограничение
  проверяется в момент списания баланса в handlers/subscription.py и handlers/balance.py.

Функция complete_referral_if_eligible(...) — единая точка входа, которую нужно
вызывать из free_trial.py (после успешной проверки подписки на канал) и из
subscription.py (после успешной оплаты платной подписки).
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database import db
from bot.keyboards.referral import referral_kb
from bot.keyboards.main_menu import back_to_menu_kb
from bot.utils import texts

router = Router(name="referral")


def build_ref_link(user_id: int) -> str:
    return f"https://t.me/{config.bot_username}?start=ref{user_id}"


async def complete_referral_if_eligible(referred_user_id: int) -> None:
    """
    Вызывается в момент, когда пользователь выполнил условие реферальной программы
    (бесплатный час с подпиской ИЛИ покупка платной подписки).
    Начисляет бонус пригласившему, а также 1 билет тому, кто пригласил самого пригласившего.
    """
    referral = await db.complete_referral(
        referred_id=referred_user_id,
        reward_rub=config.referral_bonus_rub,
        reward_tickets=config.referral_bonus_tickets,
    )
    if referral is None:
        return  # у этого пользователя не было активного реферера — начислять некому

    referrer_id = referral["referrer_id"]

    # "друг друга приглашает" — цепочка на уровень выше получает 1 билет
    grand_referrer = await db.get_user(referrer_id)
    if grand_referrer and grand_referrer.get("referrer_id"):
        await db.add_tickets(grand_referrer["referrer_id"], config.referral_mutual_tickets)


@router.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.get_or_create_user(user_id, callback.from_user.username)

    stats = await db.get_referral_stats(user_id)
    ref_link = build_ref_link(user_id)

    text = texts.REFERRAL_INFO.format(
        invited_total=stats["invited_total"],
        completed_count=stats["completed_count"],
        pending_count=stats["pending_count"],
        tickets_earned=stats["tickets_earned"],
        rub_earned=stats["rub_earned"],
        ref_link=ref_link,
    )

    await callback.message.delete()
    await callback.message.answer(text, reply_markup=referral_kb(ref_link))
    await callback.answer()


@router.callback_query(F.data == "ref_copy_link")
async def cb_copy_link(callback: CallbackQuery):
    ref_link = build_ref_link(callback.from_user.id)
    await callback.answer(f"Ссылка скопирована:\n{ref_link}", show_alert=True)


@router.callback_query(F.data == "ref_create_promo")
async def cb_create_promo(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    promo = user["referral_code"] if user else f"AIVPN{callback.from_user.id}"
    await callback.message.answer(
        f"🏷️ Ваш персональный промокод: <code>{promo}</code>\n\n"
        f"Поделитесь им с друзьями — активация промокода засчитывается как переход "
        f"по вашей реферальной ссылке.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
