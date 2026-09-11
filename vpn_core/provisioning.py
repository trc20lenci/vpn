"""
Высокоуровневая логика выдачи доступа: работает поверх xui_client.py и database.py.
Один вызов здесь = создание/продление клиента СРАЗУ на всех активных серверах,
плюс формирование одной sub-хаб ссылки на все локации.
"""
import asyncio
import time

from bot.config import config
from bot.database import db
from vpn_core import xui_client

PLAN_DAYS = {
    "forever": None,   # особый случай — expiry_time = 0 (без ограничения по времени)
    "2y": 730,
    "1y": 365,
    "6m": 182,
    "3m": 91,
    "1m": 30,
}

DEFAULT_DEVICE_LIMIT = 5
TRIAL_DEVICE_LIMIT = 1


def build_hub_link(hub_token: str) -> str:
    return f"{config.sub_hub_base_url.rstrip('/')}/sub/{hub_token}"


def _target_expiry_ms(existing_expiry_ms: int | None, days: int | None, hours: int = 0) -> int:
    """0 = без ограничения. Иначе продлевает от максимума(текущий остаток, сейчас)."""
    if days is None and hours == 0:
        return 0  # "навсегда"

    now_ms = int(time.time() * 1000)
    base_ms = existing_expiry_ms if existing_expiry_ms and existing_expiry_ms > now_ms else now_ms
    add_ms = (days or 0) * 86_400_000 + hours * 3_600_000
    return base_ms + add_ms


async def _provision(user_id: int, days: int | None, hours: int = 0,
                      device_limit: int = DEFAULT_DEVICE_LIMIT) -> str:
    servers = await db.get_active_servers()
    if not servers:
        raise RuntimeError(
            "Нет ни одного активного сервера 3X-UI в таблице servers. "
            "Добавь его через админ-панель или заполни XUI_* в .env для автосидирования."
        )

    hub_token = await db.get_or_create_hub_token(user_id)

    for server in servers:
        email = f"u{user_id}_s{server['id']}@aivpn"
        existing = await db.get_vpn_client(user_id, server["id"])
        existing_uuid = existing["xui_uuid"] if existing else None
        existing_expiry = existing["expiry_time_ms"] if existing else None

        target_expiry = _target_expiry_ms(existing_expiry, days, hours)

        new_uuid = await asyncio.to_thread(
            xui_client.upsert_client,
            server, email, target_expiry, device_limit, hub_token, existing_uuid,
        )
        await db.upsert_vpn_client(user_id, server["id"], new_uuid, email, target_expiry, enabled=True)

    return build_hub_link(hub_token)


async def provision_for_plan(user_id: int, plan_id: str,
                              device_limit: int = DEFAULT_DEVICE_LIMIT) -> str:
    """Выдача/продление платной подписки. plan_id — ключ из PLANS (subscription.py)."""
    days = PLAN_DAYS.get(plan_id)
    link = await _provision(user_id, days=days, device_limit=device_limit)

    expires_at = None if days is None else int(time.time()) + days * 86400
    await db.set_subscription(user_id, status="active", plan=plan_id, expires_at=expires_at)
    return link


async def provision_trial(user_id: int, hours: int = 1) -> str:
    """Бесплатный час. Отдельный (низкий) лимит устройств, чтобы не путать с платным тарифом."""
    link = await _provision(user_id, days=None, hours=hours, device_limit=TRIAL_DEVICE_LIMIT)
    expires_at = int(time.time()) + hours * 3600
    await db.set_subscription(user_id, status="trial", plan=None, expires_at=expires_at)
    return link


async def add_days(user_id: int, days: int, device_limit: int = DEFAULT_DEVICE_LIMIT) -> str:
    """Используется из админки: продлить пользователю доступ на N дней."""
    link = await _provision(user_id, days=days, device_limit=device_limit)
    user = await db.get_user(user_id)
    plan = user["subscription_plan"] if user and user.get("subscription_plan") else "custom"
    clients = await db.get_vpn_clients(user_id)
    max_expiry = max((c["expiry_time_ms"] for c in clients), default=0)
    expires_at = None if max_expiry == 0 else max_expiry // 1000
    await db.set_subscription(user_id, status="active", plan=plan, expires_at=expires_at)
    return link


async def block_user(user_id: int):
    servers = {s["id"]: s for s in await db.get_active_servers()}
    for client in await db.get_vpn_clients(user_id):
        server = servers.get(client["server_id"])
        if not server:
            continue
        await asyncio.to_thread(
            xui_client.set_enabled, server, client["xui_email"], client["xui_uuid"],
            False, client["expiry_time_ms"], DEFAULT_DEVICE_LIMIT,
            await db.get_or_create_hub_token(user_id),
        )
    await db.set_vpn_clients_enabled(user_id, enabled=False)
    await db.set_subscription(user_id, status="blocked", plan=None, expires_at=None)


async def unblock_user(user_id: int):
    servers = {s["id"]: s for s in await db.get_active_servers()}
    for client in await db.get_vpn_clients(user_id):
        server = servers.get(client["server_id"])
        if not server:
            continue
        await asyncio.to_thread(
            xui_client.set_enabled, server, client["xui_email"], client["xui_uuid"],
            True, client["expiry_time_ms"], DEFAULT_DEVICE_LIMIT,
            await db.get_or_create_hub_token(user_id),
        )
    await db.set_vpn_clients_enabled(user_id, enabled=True)
    await db.set_subscription(user_id, status="active", plan=None, expires_at=None)


async def delete_user_access(user_id: int):
    servers = {s["id"]: s for s in await db.get_active_servers()}
    for client in await db.get_vpn_clients(user_id):
        server = servers.get(client["server_id"])
        if not server:
            continue
        try:
            await asyncio.to_thread(xui_client.delete_client, server, client["xui_uuid"])
        except Exception:
            pass  # клиента могло уже не быть на сервере — не блокируем локальное удаление
    await db.delete_vpn_clients(user_id)
    await db.set_subscription(user_id, status="none", plan=None, expires_at=None)
