from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def home(is_registered=False):
    rows = [[KeyboardButton(text="🏆 Olimpiadaga qatnashish")], [KeyboardButton(text="🔐 Admin")]]
    if is_registered:
        rows = [
            [KeyboardButton(text="👤 Mening kabinetim")],
            [KeyboardButton(text="➕ Yangi qatnashchi qo‘shish")],
            [KeyboardButton(text="🔐 Admin")],
        ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cabinet():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🏆 Olimpiadani boshlash")],
        [KeyboardButton(text="📅 Boshlanish vaqti"), KeyboardButton(text="📊 Natijam")],
        [KeyboardButton(text="🏅 Reyting"), KeyboardButton(text="👤 Ma’lumotlarim")],
        [KeyboardButton(text="👥 Qatnashchilarim"), KeyboardButton(text="➕ Yangi qatnashchi qo‘shish")],
        [KeyboardButton(text="🏠 Bosh menyu")],
    ], resize_keyboard=True)


def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Fan"), KeyboardButton(text="➕ Daraja")],
        [KeyboardButton(text="❓ Savol qo‘shish"), KeyboardButton(text="🗓 Vaqt belgilash")],
        [KeyboardButton(text="🧹 Vaqtni bekor qilish"), KeyboardButton(text="⛔ Testni to‘xtatish")],
        [KeyboardButton(text="👥 Qatnashchilar"), KeyboardButton(text="📥 Excel yuklash")],
        [KeyboardButton(text="📝 Javoblarni tekshirish")],
        [KeyboardButton(text="🔓 Ro‘yxatni yoqish/o‘chirish"), KeyboardButton(text="📣 Natijani e’lon qilish")],
        [KeyboardButton(text="🏠 Bosh menyu")],
    ], resize_keyboard=True)


def inline_items(items, prefix, cols=2):
    b = InlineKeyboardBuilder()
    for item_id, label in items:
        b.button(text=str(label), callback_data=f"{prefix}:{item_id}")
    b.adjust(cols)
    return b.as_markup()


def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="reg:confirm"), InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reg:cancel")]])


def subscription_kb(telegram_url: str, instagram_url: str, instagram_confirmed=False):
    rows = []
    if telegram_url:
        rows.append([InlineKeyboardButton(text="📢 Telegram kanalga obuna bo‘lish", url=telegram_url)])
    if instagram_url:
        rows.append([InlineKeyboardButton(text="📸 Instagram sahifaga obuna bo‘lish", url=instagram_url)])
    rows.append([InlineKeyboardButton(text="✅ Obuna bo‘ldim", callback_data="social:check")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
