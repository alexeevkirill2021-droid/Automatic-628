from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# --- Меню подписчика ---
def subscriber_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Написать сообщение")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


# --- Меню админа ---
def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Входящие сообщения")],
            [KeyboardButton(text="👥 Список админов"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


# --- Кнопка под конкретным сообщением: переслать ---
def message_actions(msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↗️ Переслать в чат", callback_data=f"fwd:{msg_id}")],
        ]
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
