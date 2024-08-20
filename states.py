from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    awaiting_full_name = State()
    awaiting_birth_date = State()
    awaiting_description = State()
    awaiting_main_username = State()
    awaiting_add_photo = State()
    awaiting_photo = State()
    awaiting_channel = State()
    awaiting_add_channel = State()