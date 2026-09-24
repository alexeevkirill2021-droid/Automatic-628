from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- Меню подписчика ---
def subscriber_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Написать сообщение")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


# --- Меню админа (и владельца) ---
def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Входящие сообщения")],
            [KeyboardButton(text="✍️ Написать сообщение")],
            [KeyboardButton(text="👥 Список админов"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
