from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import config
from bot.database import db
from bot.states import TicketCreation
from bot.keyboards.support import support_kb
from bot.keyboards.main_menu import back_to_menu_kb
from bot.utils import texts

router = Router(name="support")

SUPPORT_PHOTO = f"{config.assets_dir}/support.jpg"


async def _send_support_menu(message: Message):
    await message.answer_photo(
        photo=FSInputFile(SUPPORT_PHOTO),
        caption=texts.SUPPORT_TEXT,
        reply_markup=support_kb(),
    )


@router.message(Command("support"))
async def cmd_support(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await _send_support_menu(message)


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.message.delete()
    await _send_support_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "ticket_create")
async def cb_ticket_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TicketCreation.entering_subject)
    await callback.message.answer(texts.TICKET_ASK_SUBJECT)
    await callback.answer()


@router.message(TicketCreation.entering_subject)
async def process_ticket_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await state.set_state(TicketCreation.entering_message)
    await message.answer(texts.TICKET_ASK_MESSAGE)


@router.message(TicketCreation.entering_message)
async def process_ticket_message(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        subject=data.get("subject", "Без темы"),
        message=message.text,
    )
    await state.clear()
    await message.answer(texts.TICKET_CREATED.format(ticket_id=ticket_id), reply_markup=back_to_menu_kb())

    for admin_id in config.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"🎫 Новый тикет #{ticket_id}\n"
                f"От: @{message.from_user.username or message.from_user.id}\n"
                f"Тема: {data.get('subject', 'Без темы')}\n\n"
                f"{message.text}",
            )
        except Exception:
            pass  # админ мог не запускать бота лично — не блокируем основной поток


@router.callback_query(F.data == "ticket_list")
async def cb_ticket_list(callback: CallbackQuery):
    tickets = await db.get_user_tickets(callback.from_user.id)
    if not tickets:
        await callback.answer(texts.NO_TICKETS, show_alert=True)
        return

    lines = [f"#{t['ticket_id']} — {t['subject']} — статус: {t['status']}" for t in tickets]
    await callback.message.answer("📋 <b>Ваши тикеты</b>\n\n" + "\n".join(lines),
                                   reply_markup=back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "ticket_contact")
async def cb_ticket_contact(callback: CallbackQuery):
    await callback.message.answer(
        "💬 Напишите ваш вопрос прямо сюда — оператор ответит в этом чате, "
        "либо создайте тикет для более быстрой и структурированной обработки.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
