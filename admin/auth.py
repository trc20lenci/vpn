from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from bot.config import config

COOKIE_NAME = "aivpn_admin_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 часов

_serializer = URLSafeTimedSerializer(config.admin_secret_key, salt="admin-session")


def create_session_cookie() -> str:
    return _serializer.dumps({"admin": True})


def is_valid_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return bool(data.get("admin"))
    except (BadSignature, SignatureExpired):
        return False


def require_admin(request: Request):
    """FastAPI dependency — редиректит на страницу логина, если сессии нет."""
    if not is_valid_session(request):
        login_url = f"/{config.admin_url_path}/login"
        raise _RedirectException(login_url)


class _RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url
