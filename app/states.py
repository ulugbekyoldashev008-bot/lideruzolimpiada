from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State(); region = State(); district = State(); birth_date = State()
    phone = State(); subject = State(); level = State(); confirm = State()


class AddSubject(StatesGroup):
    name = State()


class AddLevel(StatesGroup):
    subject = State(); name = State()


class AddQuestion(StatesGroup):
    subject = State(); level = State(); text = State(); answer_type = State()
    options = State(); correct_option = State(); correct_text = State(); max_score = State()


class Schedule(StatesGroup):
    start_at = State(); duration = State()


class Exam(StatesGroup):
    answering = State()


class Review(StatesGroup):
    selecting = State(); scoring = State(); comment = State()
