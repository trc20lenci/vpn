import time
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import config
from bot.database import db
from bot.keyboards.main_menu import main_menu_kb, back_to_menu_kb
from bot.utils import texts

router = Router(name="start")

START_PHOTO = f"{config.assets_dir}/start_profile.jpg"
ABOUT_PHOTO = f"{config.assets_dir}/about.jpg"


def _subscription_line(user: dict) -> str:
    if user["subscription_status"] != "active":
        return texts.NO_ACTIVE_SUBSCRIPTION
    if user["subscription_expires_at"] is None:
        return texts.ACTIVE_SUBSCRIPTION_FOREVER
    date_str = time.strftime("%d.%m.%Y", time.localtime(user["subscription_expires_at"]))
    return texts.ACTIVE_SUBSCRIPTION_UNTIL.format(date=date_str)


def render_main_menu_text(user: dict, username_display: str) -> str:
    return texts.MAIN_MENU.format(
        username=username_display,
        subscription_line=_subscription_line(user),
    )


def discount_minutes_left(user: dict) -> int | None:
    """Сколько минут осталось действовать скидке 30%, либо None если не активна."""
    until = user.get("discount_active_until")
    if not until:
        return None
    now = int(time.time())
    if until <= now:
        return None
    return max(1, (until - now) // 60)


async def send_main_menu(message: Message, user: dict, username_display: str):
    text = render_main_menu_text(user, username_display)
    await message.answer_photo(
        photo=FSInputFile(START_PHOTO),
        caption=text,
        reply_markup=main_menu_kb(discount_minutes_left(user)),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """Обрабатывает /start и /start ref<ID> (реферальная ссылка)."""
    referrer_id = None
    payload = command.args
    if payload and payload.startswith("ref"):
        try:
            referrer_id = int(payload.removeprefix("ref"))
        except ValueError:
            referrer_id = None

    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id,
    )

    username_display = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    await send_main_menu(message, user, username_display)


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if user is None:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    username_display = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name

    # главное меню всегда с фото — проще прислать новое сообщение, чем редактировать text<->photo
    await callback.message.delete()
    await send_main_menu(callback.message, user, username_display)
    await callback.answer()


async def send_about(message: Message):
    await message.answer_photo(
        photo=FSInputFile(ABOUT_PHOTO),
        caption=texts.ABOUT_TEXT,
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.delete()
    await send_about(callback.message)
    await callback.answer()


@router.message(Command("about"))
async def cmd_about(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await send_about(message)
