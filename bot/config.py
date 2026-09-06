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

    assets_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


config = Config()
