"""
Тонкая обёртка над py3xui для одного сервера 3X-UI.

py3xui синхронный, поэтому все функции здесь синхронные — вызывающий код
(bot/vpn_core/provisioning.py, admin/app.py) оборачивает вызовы в
asyncio.to_thread(...), чтобы не блокировать event loop бота/FastAPI.

ВАЖНО: имена полей Client (id, email, flow, limit_ip, total_gb, expiry_time,
sub_id, enable) соответствуют README py3xui на момент написания. Если у тебя
установлена другая версия пакета — сверь сигнатуры `Client` и методы
`api.client.add/update/delete/get_by_email` в своём venv
(`python -c "import py3xui; help(py3xui)"`) и поправь при необходимости.
"""
import uuid
from py3xui import Api, Client


def _api_for(server: dict) -> Api:
    api = Api(server["xui_api_url"], server["xui_username"], server["xui_password"])
    api.login()
    return api


def upsert_client(server: dict, email: str, expiry_time_ms: int, device_limit: int,
                   sub_id: str, existing_uuid: str | None = None) -> str:
    """
    Создаёт или обновляет клиента в Inbound сервера с обязательным flow=xtls-rprx-vision
    (требование для VLESS + Reality). Возвращает uuid клиента.
    """
    api = _api_for(server)
    client_uuid = existing_uuid or str(uuid.uuid4())

    client = Client(
        id=client_uuid,
        email=email,
        enable=True,
        expiry_time=expiry_time_ms,   # 0 = без ограничения ("навсегда")
        flow="xtls-rprx-vision",
        limit_ip=device_limit,
        total_gb=0,                    # 0 = безлимитный трафик
        sub_id=sub_id,
    )

    if existing_uuid:
        api.client.update(existing_uuid, client)
    else:
        api.client.add(inbound_id=server["inbound_id"], clients=[client])

    return client_uuid


def set_enabled(server: dict, email: str, existing_uuid: str, enabled: bool,
                 expiry_time_ms: int, device_limit: int, sub_id: str):
    """Блокировка/разблокировка клиента (переключает enable, не удаляя его)."""
    api = _api_for(server)
    client = Client(
        id=existing_uuid,
        email=email,
        enable=enabled,
        expiry_time=expiry_time_ms,
        flow="xtls-rprx-vision",
        limit_ip=device_limit,
        total_gb=0,
        sub_id=sub_id,
    )
    api.client.update(existing_uuid, client)


def delete_client(server: dict, existing_uuid: str):
    api = _api_for(server)
    api.client.delete(server["inbound_id"], existing_uuid)


def get_stats(server: dict, email: str):
    """Возвращает объект клиента 3X-UI (up/down/total/expiry_time/enable) или None."""
    api = _api_for(server)
    try:
        return api.client.get_by_email(email)
    except Exception:
        return None
