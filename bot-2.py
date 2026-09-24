import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, OWNER_ID
import db
from keyboards import subscriber_menu, admin_menu, cancel_menu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("automatic628")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# ---------- Состояния (FSM) ----------
class WriteMessage(StatesGroup):
    waiting_text = State()


# ---------- Вспомогательное ----------
async def is_owner_or_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return await db.is_admin(user_id)


# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if await is_owner_or_admin(message.from_user.id):
        await message.answer(
            "Добро пожаловать в панель администратора Automatic628.",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            "Здравствуйте! Это бот <b>Automatic628</b>.\n"
            "Здесь вы можете отправить сообщение — оно будет передано администраторам.",
            reply_markup=subscriber_menu(),
        )


# ---------- Управление админами (только владелец) ----------
@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.answer("Эта команда доступна только владельцу бота.")
        return
    if not command.args:
        await message.answer("Использование: /add_admin <user_id>")
        return
    try:
        new_admin_id = int(command.args.strip())
    except ValueError:
        await message.answer("ID должен быть числом. Пример: /add_admin 123456789")
        return
    await db.add_admin(new_admin_id, None)
    await message.answer(f"Пользователь {new_admin_id} назначен администратором.")
    try:
        await bot.send_message(
            new_admin_id,
            "Вы назначены администратором бота Automatic628.",
            reply_markup=admin_menu(),
        )
    except Exception:
        pass  # пользователь ещё не писал боту — не страшно


@dp.message(Command("remove_admin"))
async def cmd_remove_admin(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.answer("Эта команда доступна только владельцу бота.")
        return
    if not command.args:
        await message.answer("Использование: /remove_admin <user_id>")
        return
    try:
        admin_id = int(command.args.strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    await db.remove_admin(admin_id)
    await message.answer(f"Пользователь {admin_id} удалён из администраторов.")


# ---------- Право видеть автора сообщений (только владелец назначает) ----------
@dp.message(Command("grant_reveal"))
async def cmd_grant_reveal(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.answer("Эта команда доступна только владельцу бота.")
        return
    if not command.args:
        await message.answer("Использование: /grant_reveal <user_id>\nЧеловек должен уже быть администратором.")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    if not await db.is_admin(target_id):
        await message.answer("Этот пользователь ещё не администратор. Сначала выполните /add_admin.")
        return
    await db.set_can_reveal(target_id, True)
    await message.answer(f"Пользователю {target_id} выдан доступ к просмотру авторов сообщений.")
    try:
        await bot.send_message(
            target_id,
            "Вам открыт доступ к просмотру авторов сообщений. Обратитесь к владельцу бота, "
            "чтобы узнать, как им пользоваться.",
        )
    except Exception:
        pass


@dp.message(Command("revoke_reveal"))
async def cmd_revoke_reveal(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.answer("Эта команда доступна только владельцу бота.")
        return
    if not command.args:
        await message.answer("Использование: /revoke_reveal <user_id>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    await db.set_can_reveal(target_id, False)
    await message.answer(f"У пользователя {target_id} отозван доступ к просмотру авторов.")


# ---------- /whois — узнать автора сообщения (владелец + те, кому дан доступ) ----------
@dp.message(Command("whois"))
async def cmd_whois(message: Message, command: CommandObject):
    if not await is_owner_or_admin(message.from_user.id):
        return
    if not await db.can_reveal_author(message.from_user.id, OWNER_ID):
        await message.answer("У вас нет доступа к просмотру авторов сообщений.")
        return
    if not command.args:
        await message.answer("Использование: /whois <номер сообщения>\nНомер указан в тексте сообщения как №...")
        return
    try:
        msg_id = int(command.args.strip())
    except ValueError:
        await message.answer("Номер должен быть числом.")
        return
    row = await db.get_message(msg_id)
    if row is None:
        await message.answer("Сообщение с таким номером не найдено.")
        return
    _, author_id, username, text, photo_file_id, status = row
    author_label = f"@{username}" if username else "без username"
    await message.answer(f"Сообщение №{msg_id} отправил: {author_label} (ID: {author_id})")


# ---------- Написать сообщение (подписчики, админы и владелец) ----------
@dp.message(F.text == "✍️ Написать сообщение")
async def start_write(message: Message, state: FSMContext):
    await state.set_state(WriteMessage.waiting_text)
    await message.answer(
        "Напишите ваше сообщение (можно с фото). Для отмены нажмите «❌ Отмена».",
        reply_markup=cancel_menu(),
    )


@dp.message(F.text == "❌ Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    if await is_owner_or_admin(message.from_user.id):
        await message.answer("Отменено.", reply_markup=admin_menu())
    else:
        await message.answer("Отменено.", reply_markup=subscriber_menu())


@dp.message(WriteMessage.waiting_text, F.photo)
async def receive_photo_message(message: Message, state: FSMContext):
    caption = message.caption or ""
    photo_id = message.photo[-1].file_id
    await _save_and_notify(message, text=caption, photo_file_id=photo_id)
    await state.clear()
    menu = admin_menu() if await is_owner_or_admin(message.from_user.id) else subscriber_menu()
    await message.answer("✅ Сообщение отправлено администраторам.", reply_markup=menu)


@dp.message(WriteMessage.waiting_text, F.text)
async def receive_text_message(message: Message, state: FSMContext):
    await _save_and_notify(message, text=message.text, photo_file_id=None)
    await state.clear()
    menu = admin_menu() if await is_owner_or_admin(message.from_user.id) else subscriber_menu()
    await message.answer("✅ Сообщение отправлено администраторам.", reply_markup=menu)


async def _save_and_notify(message: Message, text: str, photo_file_id: str | None):
    username = message.from_user.username
    msg_id = await db.save_message(message.from_user.id, username, text, photo_file_id)
    sender_id = message.from_user.id
    # Сообщение не рассылается автоматически — админы/владелец увидят его,
    # только когда сами нажмут «📥 Входящие сообщения».
    # Отправитель сразу считается просмотревшим своё же сообщение.
    await db.mark_messages_viewed(sender_id, [msg_id])


# ---------- Входящие сообщения: показывает только новые (непросмотренные) ----------
@dp.message(F.text == "📥 Входящие сообщения")
async def list_incoming(message: Message):
    if not await is_owner_or_admin(message.from_user.id):
        return

    viewer_id = message.from_user.id
    rows = await db.get_unseen_messages(viewer_id, limit=50)

    if not rows:
        await message.answer("Новых сообщений нет.")
        return

    seen_ids = []

    for msg_id, author_id, username, text, photo_file_id, status in rows:
        author_label = f"Аноним №{msg_id}"
        caption = f"№{msg_id} от {author_label}\n\n{text or ''}"
        try:
            if photo_file_id:
                await message.answer_photo(photo_file_id, caption=caption)
            else:
                await message.answer(caption)
            seen_ids.append(msg_id)
        except Exception as e:
            logger.warning(f"Не удалось показать сообщение {msg_id}: {e}")

    await db.mark_messages_viewed(viewer_id, seen_ids)
    await message.answer(
        "Показаны все новые сообщения ({} шт.). Чтобы переслать сообщение дальше — "
        "перешлите (forward) его прямо из этого чата в нужный канал или группу.".format(len(seen_ids))
    )


@dp.message(F.text == "👥 Список админов")
async def list_admins(message: Message):
    if not await is_owner_or_admin(message.from_user.id):
        return
    rows = await db.get_all_admins_detailed()
    lines = [f"• {OWNER_ID} (владелец)"]
    for user_id, username, can_reveal in rows:
        label = f"@{username}" if username else str(user_id)
        lines.append(f"• {label} (ID {user_id})")
    await message.answer("Администраторы:\n" + "\n".join(lines))


@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.answer(
            "Команды владельца:\n"
            "/add_admin <user_id> — назначить администратора\n"
            "/remove_admin <user_id> — снять администратора\n"
            "/grant_reveal <user_id> — разрешить этому админу видеть авторов сообщений\n"
            "/revoke_reveal <user_id> — забрать это право\n\n"
            "«📥 Входящие сообщения» — показывает только новые, ещё не просмотренные вами сообщения.\n"
            "«✍️ Написать сообщение» — отправить сообщение остальным администраторам.\n"
            "Чтобы переслать сообщение в канал — просто перешлите (forward) его из этого чата вручную.\n"
            "Все сообщения показываются как «Аноним»."
        )
    elif await is_owner_or_admin(message.from_user.id):
        await message.answer(
            "«📥 Входящие сообщения» — показывает только новые, ещё не просмотренные вами сообщения.\n"
            "«✍️ Написать сообщение» — отправить сообщение остальным администраторам.\n"
            "Чтобы переслать сообщение в канал — просто перешлите (forward) его из этого чата вручную.\n"
            "Все сообщения показываются как «Аноним»."
        )
    else:
        await message.answer("Нажмите «✍️ Написать сообщение», чтобы отправить сообщение администраторам.")


@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer(
        "<b>Команды владельца бота</b>\n\n"
        "/add_admin <code>user_id</code> — назначить администратора\n"
        "/remove_admin <code>user_id</code> — снять администратора\n"
        "/grant_reveal <code>user_id</code> — разрешить админу видеть авторов сообщений\n"
        "/revoke_reveal <code>user_id</code> — забрать это право\n"
        "/commands — показать этот список ещё раз\n\n"
        "Кнопки меню:\n"
        "«📥 Входящие сообщения» — только новые, ещё не просмотренные сообщения\n"
        "«✍️ Написать сообщение» — отправить сообщение остальным администраторам\n"
        "«👥 Список админов» — кто назначен администратором\n"
        "«ℹ️ Помощь» — краткая справка\n\n"
        "Чтобы переслать сообщение в канал/группу — просто перешлите (forward) его вручную из этого чата."
    )


# ---------- Запуск ----------
async def setup_owner_commands():
    """Настраивает всплывающую подсказку команд в Telegram только для владельца."""
    if not OWNER_ID:
        return
    from aiogram.types import BotCommand, BotCommandScopeChat

    owner_commands = [
        BotCommand(command="start", description="Открыть меню"),
        BotCommand(command="commands", description="Список всех команд владельца"),
        BotCommand(command="add_admin", description="Назначить администратора"),
        BotCommand(command="remove_admin", description="Снять администратора"),
        BotCommand(command="grant_reveal", description="Разрешить видеть авторов сообщений"),
        BotCommand(command="revoke_reveal", description="Забрать доступ к авторам"),
    ]
    try:
        await bot.set_my_commands(owner_commands, scope=BotCommandScopeChat(chat_id=OWNER_ID))
    except Exception as e:
        logger.warning(f"Не удалось настроить команды владельца: {e}")


async def main():
    await db.init_db()
    await setup_owner_commands()
    logger.info("Automatic628 запущен и слушает обновления...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.exception(f"Бот упал с ошибкой, перезапуск через 5 секунд: {e}")
            import time
            time.sleep(5)
