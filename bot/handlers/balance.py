from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile

from bot.config import config
from bot.database import db
from bot.states import BalanceTopUp
from bot.keyboards.balance import balance_kb
from bot.keyboards.subscription import payment_method_kb
from bot.keyboards.main_menu import back_to_menu_kb
from bot.utils import texts

router = Router(name="balance")

BALANCE_PHOTO = f"{config.assets_dir}/balance.jpg"


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile(BALANCE_PHOTO),
        caption=texts.BALANCE_TEXT.format(balance=user["balance"]),
        reply_markup=balance_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "balance_topup")
async def cb_balance_topup(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceTopUp.entering_amount)
    await callback.message.answer("💵 Введите сумму пополнения в рублях (число):")
    await callback.answer()


@router.message(BalanceTopUp.entering_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Введите положительное целое число, например: 500")
        return

    amount = int(message.text)
    await state.clear()
    await message.answer(
        f"{texts.PAYMENT_METHOD_TEXT}\n\nСумма пополнения: <b>{amount}₽</b>",
        reply_markup=payment_method_kb(context=f"balance_topup:{amount}"),
    )


@router.callback_query(F.data == "balance_history")
async def cb_balance_history(callback: CallbackQuery):
    history = await db.get_payment_history(callback.from_user.id)
    if not history:
        await callback.answer("У вас пока нет операций.", show_alert=True)
        return

    lines = []
    for p in history:
        lines.append(f"• {p['amount']}₽ — {p['purpose']} — {p['method']} — {p['status']}")

    await callback.message.answer("📜 <b>История операций</b>\n\n" + "\n".join(lines),
                                   reply_markup=back_to_menu_kb())
    await callback.answer()
