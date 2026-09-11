"""
Sub-хаб: одна ссылка вида {SUB_HUB_BASE_URL}/sub/<token>, которая отдаёт клиенту
(Happ/V2Box/V2RayNG и т.п.) base64-список vless:// строк — по одной на каждый
активный сервер, где у пользователя есть клиент. Именно это даёт "выбор стран"
в приложении при подключении второго/третьего сервера в будущем — просто
добавляешь сервер в таблицу servers, и он сам появится в подписке всех
пользователей при следующем обновлении конфига в приложении.
"""
import base64
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from bot.database import db

router = APIRouter()


def build_vless_uri(server: dict, client_uuid: str) -> str:
    remark = quote(server["name"])
    return (
        f"vless://{client_uuid}@{server['connect_host']}:{server['connect_port']}"
        f"?type=tcp&security=reality&pbk={server['public_key']}&fp=chrome"
        f"&sni={server['sni']}&sid={server['short_id']}&spx=%2F&flow=xtls-rprx-vision"
        f"#{remark}"
    )


@router.get("/sub/{token}")
async def get_subscription(token: str):
    user_id = await db.get_user_id_by_hub_token(token)
    if not user_id:
        raise HTTPException(status_code=404, detail="subscription not found")

    servers = {s["id"]: s for s in await db.get_active_servers()}
    clients = await db.get_vpn_clients(user_id)

    lines = []
    for client in clients:
        if not client["enabled"]:
            continue
        server = servers.get(client["server_id"])
        if not server:
            continue
        lines.append(build_vless_uri(server, client["xui_uuid"]))

    payload = "\n".join(lines)
    encoded = base64.b64encode(payload.encode()).decode()
    return Response(content=encoded, media_type="text/plain; charset=utf-8")
