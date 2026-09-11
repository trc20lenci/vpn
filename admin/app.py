import time
import hmac

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.config import config
from bot.database import db
from vpn_core import provisioning, hub
from admin.auth import (
    create_session_cookie, is_valid_session, require_admin,
    _RedirectException, COOKIE_NAME, SESSION_MAX_AGE,
)

templates = Jinja2Templates(directory="admin/templates")

app = FastAPI(title="Ai VPN Admin")
app.include_router(hub.router)  # /sub/{token} — доступен без авторизации, это публичная sub-ссылка

PREFIX = f"/{config.admin_url_path}"


@app.exception_handler(_RedirectException)
async def _redirect_handler(request: Request, exc: _RedirectException):
    return RedirectResponse(exc.url, status_code=302)


def _status_label(user: dict) -> str:
    return {
        "none": "—",
        "trial": "🎁 Триал",
        "active": "✅ Активна",
        "blocked": "⛔ Заблокирован",
        "expired": "⌛ Истекла",
    }.get(user["subscription_status"], user["subscription_status"])


def _days_left(user: dict) -> str:
    expires = user.get("subscription_expires_at")
    if user["subscription_status"] != "active" and user["subscription_status"] != "trial":
        return "—"
    if expires is None:
        return "∞"
    remaining = expires - int(time.time())
    if remaining <= 0:
        return "истекла"
    return str(remaining // 86400) if remaining >= 86400 else f"{remaining // 3600} ч"


@app.get(f"{PREFIX}/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_valid_session(request):
        return RedirectResponse(PREFIX, status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post(f"{PREFIX}/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    ok_user = hmac.compare_digest(username, config.admin_username)
    ok_pass = hmac.compare_digest(password, config.admin_password)
    if not (ok_user and ok_pass) or not config.admin_username:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Неверный логин или пароль"}
        )

    response = RedirectResponse(PREFIX, status_code=302)
    response.set_cookie(
        COOKIE_NAME, create_session_cookie(),
        max_age=SESSION_MAX_AGE, httponly=True, samesite="lax",
    )
    return response


@app.get(f"{PREFIX}/logout")
async def logout():
    response = RedirectResponse(f"{PREFIX}/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get(PREFIX, response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(require_admin)):
    users = await db.get_all_users_admin()
    rows = []
    for u in users:
        rows.append({
            "user_id": u["user_id"],
            "username": u["username"] or "—",
            "status": _status_label(u),
            "raw_status": u["subscription_status"],
            "days_left": _days_left(u),
            "balance": u["balance"],
            "free_trial_used": bool(u["free_trial_used"]),
        })

    total_users = len(users)
    paying_users = sum(1 for u in users if u["subscription_status"] == "active")

    return templates.TemplateResponse(request, "dashboard.html", {
        "rows": rows,
        "total_users": total_users,
        "paying_users": paying_users,
        "prefix": PREFIX,
    })


@app.post(f"{PREFIX}/users/{{user_id}}/add-days")
async def action_add_days(user_id: int, days: int = Form(...), _=Depends(require_admin)):
    await provisioning.add_days(user_id, days)
    return RedirectResponse(PREFIX, status_code=302)


@app.post(f"{PREFIX}/users/{{user_id}}/block")
async def action_block(user_id: int, _=Depends(require_admin)):
    await provisioning.block_user(user_id)
    return RedirectResponse(PREFIX, status_code=302)


@app.post(f"{PREFIX}/users/{{user_id}}/unblock")
async def action_unblock(user_id: int, _=Depends(require_admin)):
    await provisioning.unblock_user(user_id)
    return RedirectResponse(PREFIX, status_code=302)


@app.post(f"{PREFIX}/users/{{user_id}}/delete")
async def action_delete(user_id: int, _=Depends(require_admin)):
    await provisioning.delete_user_access(user_id)
    return RedirectResponse(PREFIX, status_code=302)


@app.post(f"{PREFIX}/users/{{user_id}}/trial")
async def action_trial(user_id: int, hours: int = Form(1), _=Depends(require_admin)):
    # админский override: выдаёт триал даже если free_trial_used уже стоит
    await provisioning.provision_trial(user_id, hours=hours)
    return RedirectResponse(PREFIX, status_code=302)
