import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _split_ids(raw: str) -> list[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    bot_username: str = os.getenv("BOT_USERNAME", "MyAiVPNbot")
    admin_ids: list[int] = field(default_factory=lambda: _split_ids(os.getenv("ADMIN_IDS", "")))

    channel_id: str = os.getenv("CHANNEL_ID", "")
    channel_url: str = os.getenv("CHANNEL_URL", "")

    database_path: str = os.getenv("DATABASE_PATH", "bot.db")

    cryptobot_api_token: str = os.getenv("CRYPTOBOT_API_TOKEN", "")
    yookassa_shop_id: str = os.getenv("YOOKASSA_SHOP_ID", "")
    yookassa_secret_key: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    sberpay_terminal_key: str = os.getenv("SBERPAY_TERMINAL_KEY", "")
    sberpay_secret_key: str = os.getenv("SBERPAY_SECRET_KEY", "")

    referral_bonus_rub: int = int(os.getenv("REFERRAL_BONUS_RUB", "50"))
    referral_bonus_tickets: int = int(os.getenv("REFERRAL_BONUS_TICKETS", "2"))
    referral_mutual_tickets: int = int(os.getenv("REFERRAL_MUTUAL_TICKETS", "1"))

    # === Admin dashboard ===
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    admin_secret_key: str = os.getenv("ADMIN_SECRET_KEY", "change-me-please")
    # часть пути вместо /admin — держи в секрете, напр. "panel-9f3a1c"
    admin_url_path: str = os.getenv("ADMIN_URL_PATH", "admin")
    admin_host: str = os.getenv("ADMIN_HOST", "0.0.0.0")
    admin_port: int = int(os.getenv("ADMIN_PORT", "8000"))

    # === Subscription hub (агрегированная sub-ссылка) ===
    sub_hub_base_url: str = os.getenv("SUB_HUB_BASE_URL", "http://localhost:8000")

    # === Первый сервер 3X-UI (сидируется в БД при первом старте, если таблица servers пуста) ===
    xui_api_url: str = os.getenv("XUI_API_URL", "")
    xui_username: str = os.getenv("XUI_USERNAME", "")
    xui_password: str = os.getenv("XUI_PASSWORD", "")
    xui_inbound_id: int = int(os.getenv("XUI_INBOUND_ID", "1"))
    xui_connect_host: str = os.getenv("XUI_CONNECT_HOST", "")
    xui_connect_port: int = int(os.getenv("XUI_CONNECT_PORT", "443"))
    xui_public_key: str = os.getenv("XUI_PUBLIC_KEY", "")
    xui_short_id: str = os.getenv("XUI_SHORT_ID", "")
    xui_sni: str = os.getenv("XUI_SNI", "")
    xui_server_label: str = os.getenv("XUI_SERVER_LABEL", "🇩🇪 Germany Premium")

    assets_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


config = Config()
