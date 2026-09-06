import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile

from bot.config import config
from bot.database import db
from bot.states import GiftSubscription
from bot.keyboards.subscription import subscription_kb, payment_method_kb, PLANS
from bot.keyboards.main_menu import back_to_menu_kb
from bot.utils import texts
from bot.handlers.referral import complete_referral_if_eligible

router = Router(name="subscription")

SUBSCRIPTION_PHOTO = f"{config.assets_dir}/subscription.jpg"
DISCOUNT_SECONDS = 60 * 60
DISCOUNT_RATE = 0.30
DISCOUNT_COOLDOWN_SECONDS = 24 * 60 * 60  # использовать скидку можно раз в сутки

PLAN_DAYS = {plan_id: days for plan_id, (_, _, days) in PLANS.items()}


def _price_for(user: dict, plan_id: str) -> int:
    _, base_price, _ = PLANS[plan_id]
    now = int(time.time())
    if user.get("discount_active_until") and user["discount_active_until"] > now:
        return round(base_price * (1 - DISCOUNT_RATE))
    return base_price


async def send_subscription_menu(message: Message):
    await message.answer_photo(
        photo=FSInputFile(SUBSCRIPTION_PHOTO),
        caption=texts.SUBSCRIPTION_TEXT,
        reply_markup=subscription_kb(),
    )


@router.callback_query(F.data == "subscription")
async def cb_subscription(callback: CallbackQuery):
    await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    await callback.message.delete()
    await send_subscription_menu(callback.message)
    await callback.answer()


@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await send_subscription_menu(message)


@router.callback_query(F.data == "discount")
async def cb_discount(callback: CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    now = int(time.time())

    # уже активна прямо сейчас
    if user.get("discount_active_until") and user["discount_active_until"] > now:
        remaining_min = max(1, (user["discount_active_until"] - now) // 60)
        await callback.answer(
            texts.DISCOUNT_ALREADY_ACTIVE.format(time=f"{remaining_min} мин"), show_alert=True
        )
        return

    # лимит: использовать скидку можно раз в сутки
    last_claimed = user.get("last_discount_claimed_at")
    if last_claimed and (now - last_claimed) < DISCOUNT_COOLDOWN_SECONDS:
        next_available = last_claimed + DISCOUNT_COOLDOWN_SECONDS
        hours_left = max(1, (next_available - now) // 3600)
        await callback.answer(
            f"⏳ Скидку 30% можно использовать раз в сутки. "
            f"Следующая попытка будет доступна примерно через {hours_left} ч.",
            show_alert=True,
        )
        return

    until_ts = now + DISCOUNT_SECONDS
    await db.set_discount(callback.from_user.id, until_ts, claimed_at=now)

    await callback.message.answer(texts.DISCOUNT_ACTIVATED, reply_markup=back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def cb_choose_plan(callback: CallbackQuery):
    plan_id = callback.data.split(":", 1)[1]
    if plan_id not in PLANS:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    price = _price_for(user, plan_id)
    label = PLANS[plan_id][0]

    await callback.message.delete()
    await callback.message.answer(
        f"{texts.PAYMENT_METHOD_TEXT}\n\nТариф: <b>{label}</b>\nСумма к оплате: <b>{price}₽</b>",
        reply_markup=payment_method_kb(context=f"plan:{plan_id}"),
    )
    await callback.answer()


@router.callback_query(F.data == "downgrade_basic")
async def cb_downgrade(callback: CallbackQuery):
    await db.set_subscription(callback.from_user.id, status="none", plan=None, expires_at=None)
    await callback.answer("Вы перешли на базовый тариф.", show_alert=True)


@router.callback_query(F.data == "gift_vpn")
async def cb_gift_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiftSubscription.entering_target)
    await callback.message.answer(
        "🎁 Перешлите сюда сообщение получателя подарка или отправьте его @username, "
        "чтобы мы могли начислить доступ на его аккаунт после оплаты."
    )
    await callback.answer()


@router.message(GiftSubscription.entering_target)
async def process_gift_target(message, state: FSMContext):
    target = None
    if message.forward_from:
        target = message.forward_from.id
    elif message.text and message.text.startswith("@"):
        target = message.text  # username сохраняем как есть, резолвим при оплате

    if target is None:
        await message.answer("Не удалось определить получателя. Отправьте @username или перешлите его сообщение.")
        return

    await state.update_data(gift_target=target)
    await state.clear()
    await message.answer(
        "Отлично! Теперь выберите тариф, который хотите подарить:",
        reply_markup=subscription_kb(),
    )


@router.callback_query(F.data.startswith("pay:"))
async def cb_choose_payment_method(callback: CallbackQuery):
    """
    callback_data формата pay:<method>:<context>
    method: sbp | card | stars | crypto | sbp_other
    context: plan:<id> | balance_topup:<amount>
    """
    _, method, context = callback.data.split(":", 2)

    if context.startswith("plan:"):
        plan_id = context.split(":", 1)[1]
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
        amount = _price_for(user, plan_id)
        purpose = f"subscription:{plan_id}"
    else:
        amount = None
        purpose = context

    payment_id = await db.create_payment(
        user_id=callback.from_user.id, amount=amount or 0, method=method, purpose=purpose
    )

    # --- Точка интеграции с платёжными системами ---
    # method == "crypto"     -> CryptoBot Crypto Pay API: createInvoice, дальше polling/webhook getInvoices
    # method in ("sbp","card")-> ЮKassa: Payment.create(...), redirect на confirmation_url
    # method == "sbp_other"  -> тот же ЮKassa-провайдер, но с параметром другого банка/QR
    # method == "stars"      -> bot.send_invoice(currency="XTR", ...) — оплата Stars внутри Telegram
    #
    # После подтверждения оплаты (вебхук/успешный send_invoice) нужно вызвать:
    #   await db.set_payment_status(payment_id, "success")
    #   await db.set_subscription(user_id, "active", plan_id, expires_at)
    #   await complete_referral_if_eligible(user_id)   # если это была первая платная подписка
    #
    # Ниже — временная заглушка, чтобы бот был рабочим без реальных ключей.

    await callback.message.answer(
        f"⏳ Счёт №{payment_id} создан. Ссылка на оплату через выбранный способ "
        f"будет отправлена, как только подключён платёжный провайдер "
        f"(см. TODO в bot/handlers/subscription.py)."
    )
    await callback.answer()
