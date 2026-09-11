"""
Команда /stats — быстрая сводка по базе прямо в Telegram, без захода в веб-админку.
Доступна только пользователям из config.admin_ids.
"""
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import config
from bot.database import db

router = Router(name="admin_stats")


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not _is_admin(message.from_user.id):
        return  # молча игнорируем для не-админов, чтобы не палить наличие команды

    users = await db.get_all_users_admin()
    now = int(time.time())
    today_start = now - (now % 86400)
    week_ago = now - 7 * 86400

    total_users = len(users)
    active_subs = sum(1 for u in users if u["subscription_status"] == "active")
    trial_users = sum(1 for u in users if u["subscription_status"] == "trial")
    blocked_users = sum(1 for u in users if u["subscription_status"] == "blocked")
    free_trial_claimed = sum(1 for u in users if u["free_trial_used"])

    new_today = sum(1 for u in users if u["created_at"] >= today_start)
    new_week = sum(1 for u in users if u["created_at"] >= week_ago)

    total_balance = sum(u["balance"] for u in users)
    total_tickets = sum(u["tickets_count"] for u in users)

    referred_users = sum(1 for u in users if u["referrer_id"])

    payments = await db.get_payment_history_all()
    successful = [p for p in payments if p["status"] == "success"]
    revenue = sum(p["amount"] for p in successful)
    payments_line = (
        f"\n💳 <b>Платежи</b>\n"
        f"Успешных: <b>{len(successful)}</b>\n"
        f"Выручка (успешные): <b>{revenue}₽</b>\n"
    )

    conversion = f"{(active_subs / total_users * 100):.1f}%" if total_users else "0%"

    text = (
        "📊 <b>Статистика Ai VPN</b>\n\n"
        f"👥 <b>Пользователи</b>\n"
        f"Всего: <b>{total_users}</b>\n"
        f"Новых сегодня: <b>{new_today}</b>\n"
        f"Новых за 7 дней: <b>{new_week}</b>\n"
        f"Пришли по рефералке: <b>{referred_users}</b>\n\n"
        f"💰 <b>Подписки</b>\n"
        f"Платящих (active): <b>{active_subs}</b>\n"
        f"На триале: <b>{trial_users}</b>\n"
        f"Заблокировано: <b>{blocked_users}</b>\n"
        f"Использовали бесплатный час: <b>{free_trial_claimed}</b>\n"
        f"Конверсия в платящих: <b>{conversion}</b>\n"
        f"{payments_line}\n"
        f"🎫 Суммарно билетов у пользователей: <b>{total_tickets}</b>\n"
        f"🏦 Суммарный бонусный баланс пользователей: <b>{total_balance}₽</b>"
    )

    await message.answer(text)
