from aiogram.dispatcher.filters.state import State, StatesGroup

class NewsletterText(StatesGroup):
    text = State()



class SearchUserState(StatesGroup):
    InputUsername = State()



class BonusDayState(StatesGroup):
    bonus = State()


class Form(StatesGroup):
    waiting_for_new_photo = State()