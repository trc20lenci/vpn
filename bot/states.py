from aiogram.fsm.state import State, StatesGroup


class BalanceTopUp(StatesGroup):
    entering_amount = State()


class TicketCreation(StatesGroup):
    entering_subject = State()
    entering_message = State()


class GiftSubscription(StatesGroup):
    entering_target = State()
