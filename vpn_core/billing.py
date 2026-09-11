"""
Единая точка входа, которую нужно вызвать из ВАШЕЙ уже работающей логики оплат
(там, где вы сейчас подтверждаете платёж от CryptoBot/ЮKassa/Stars), сразу после
того как платёж подтверждён:

    from vpn_core.billing import fulfill_payment
    await fulfill_payment(bot, payment_id)

Дальше эта функция сама:
1. Читает payment из БД, разбирает purpose ("subscription:<plan>" / "balance_topup:<amount>").
2. Создаёт/продлевает клиента на всех активных серверах 3X-UI.
3. Помечает платёж success и подписку active.
4. Шлёт пользователю сообщение с готовой sub-ссылкой.
5. Засчитывает реферальную программу, если это первая платная подписка.
"""
from aiogram import Bot

from bot.database import db
from bot.handlers.referral import complete_referral_if_eligible
from vpn_core import provisioning


async def fulfill_payment(bot: Bot, payment_id: int):
    payment = await _get_payment(payment_id)
    if payment is None:
        return
    if payment["status"] == "success":
        return  # уже обработан — защита от повторного вебхука

    user_id = payment["user_id"]
    purpose = payment["purpose"]

    if purpose.startswith("subscription:"):
        plan_id = purpose.split(":", 1)[1]
        link = await provisioning.provision_for_plan(user_id, plan_id)
        await db.set_payment_status(payment_id, "success")
        await complete_referral_if_eligible(user_id)

        await bot.send_message(
            user_id,
            "✅ Оплата прошла успешно! Ваша подписка активирована.\n\n"
            "🔗 Ваша ссылка подписки (вставьте в Happ / V2Box / V2RayNG):\n"
            f"<code>{link}</code>\n\n"
            "Приложение само подтянет конфиг с красивым названием сервера.",
        )

    elif purpose == "balance_topup" or purpose.startswith("balance_topup:"):
        await db.change_balance(user_id, payment["amount"])
        await db.set_payment_status(payment_id, "success")
        await bot.send_message(user_id, f"✅ Баланс пополнен на {payment['amount']}₽.")

    else:
        # gift:<target_id>:<plan> и другие кастомные purpose — дополните здесь по необходимости
        await db.set_payment_status(payment_id, "success")


async def _get_payment(payment_id: int) -> dict | None:
    import aiosqlite
    async with aiosqlite.connect(db.path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
