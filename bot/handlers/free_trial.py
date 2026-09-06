import time
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from bot.config import config
from bot.database import db
from bot.keyboards.free_trial import free_trial_kb
from bot.keyboards.main_menu import back_to_menu_kb
from bot.utils import texts
from bot.handlers.referral import complete_referral_if_eligible

router = Router(name="free_trial")

FREE_TRIAL_SECONDS = 60 * 60


@router.callback_query(F.data == "free_trial")
async def cb_free_trial(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if user and user["free_trial_used"]:
        await callback.answer(texts.FREE_TRIAL_ALREADY_USED, show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(texts.FREE_TRIAL_TEXT, reply_markup=free_trial_kb())
    await callback.answer()


@router.callback_query(F.data == "free_trial_check")
async def cb_free_trial_check(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)

    if user and user["free_trial_used"]:
        await callback.answer(texts.FREE_TRIAL_ALREADY_USED, show_alert=True)
        return

    try:
        member = await callback.bot.get_chat_member(chat_id=config.channel_id, user_id=user_id)
    except TelegramBadRequest:
        await callback.answer(texts.FREE_TRIAL_NOT_SUBSCRIBED, show_alert=True)
        return

    is_subscribed = member.status in ("member", "administrator", "creator")
    if not is_subscribed:
        await callback.answer(texts.FREE_TRIAL_NOT_SUBSCRIBED, show_alert=True)
        return

    # --- выдаём доступ ---
    await db.mark_free_trial_used(user_id)
    expires_at = int(time.time()) + FREE_TRIAL_SECONDS
    await db.set_subscription(user_id, status="trial", plan=None, expires_at=expires_at)

    # TODO: здесь же вызвать VPN-панель (например 3x-ui/Marzban API), чтобы реально
    # выдать конфиг/ключ пользователю на 1 час — вынесено за рамки текущего ТЗ.

    # реферальная программа: бесплатный час с подпиской засчитывается как выполненное условие
    await complete_referral_if_eligible(user_id)

    await callback.message.delete()
    await callback.message.answer(texts.FREE_TRIAL_ACTIVATED, reply_markup=back_to_menu_kb())
    await callback.answer()
