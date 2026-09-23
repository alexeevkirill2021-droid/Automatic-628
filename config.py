import os

# Токен бота — получите у @BotFather в Telegram.
# Лучше хранить в переменной окружения, а не в коде.
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_СЮДА_ВАШ_ТОКЕН")

# Ваш личный Telegram ID (владелец бота).
# Узнать свой ID можно у бота @userinfobot
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DB_PATH = os.getenv("DB_PATH", "automatic628.db")
