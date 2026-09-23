import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, OWNER_ID
import db
from keyboards import subscriber_menu, admin_menu, message_actions, cancel_menu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("automatic628")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# ---------- Состояния (FSM) ----------
class WriteMessage(StatesGroup):
    waiting_text = State()


class ForwardMessage(StatesGroup):
    waiting_target = State()


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


# ---------- Меню подписчика: написать сообщение ----------
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
    await message.answer("✅ Сообщение отправлено администраторам.", reply_markup=subscriber_menu())


@dp.message(WriteMessage.waiting_text, F.text)
async def receive_text_message(message: Message, state: FSMContext):
    await _save_and_notify(message, text=message.text, photo_file_id=None)
    await state.clear()
    await message.answer("✅ Сообщение отправлено администраторам.", reply_markup=subscriber_menu())


async def _save_and_notify(message: Message, text: str, photo_file_id: str | None):
    username = message.from_user.username
    msg_id = await db.save_message(message.from_user.id, username, text, photo_file_id)

    admins = await db.get_all_admins()
    if OWNER_ID and OWNER_ID not in admins:
        admins.append(OWNER_ID)

    author_label = f"@{username}" if username else f"ID {message.from_user.id}"
    caption = f"📨 Новое сообщение от {author_label} (№{msg_id})\n\n{text or ''}"

    for admin_id in admins:
        try:
            if photo_file_id:
                await bot.send_photo(
                    admin_id, photo_file_id, caption=caption, reply_markup=message_actions(msg_id)
                )
            else:
                await bot.send_message(admin_id, caption, reply_markup=message_actions(msg_id))
        except Exception as e:
            logger.warning(f"Не удалось отправить админу {admin_id}: {e}")


# ---------- Меню админа: входящие сообщения ----------
@dp.message(F.text == "📥 Входящие сообщения")
async def list_incoming(message: Message):
    if not await is_owner_or_admin(message.from_user.id):
        return
    rows = await db.get_recent_messages(10)
    if not rows:
        await message.answer("Сообщений пока нет.")
        return
    for msg_id, author_id, username, text, photo_file_id, status in rows:
        author_label = f"@{username}" if username else f"ID {author_id}"
        caption = f"№{msg_id} от {author_label} [{status}]\n\n{text or ''}"
        if photo_file_id:
            await message.answer_photo(photo_file_id, caption=caption, reply_markup=message_actions(msg_id))
        else:
            await message.answer(caption, reply_markup=message_actions(msg_id))


@dp.message(F.text == "👥 Список админов")
async def list_admins(message: Message):
    if not await is_owner_or_admin(message.from_user.id):
        return
    admins = await db.get_all_admins()
    if OWNER_ID:
        admins = list(set(admins + [OWNER_ID]))
    text = "Администраторы:\n" + "\n".join(f"• {a}" + (" (владелец)" if a == OWNER_ID else "") for a in admins)
    await message.answer(text)


@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    if await is_owner_or_admin(message.from_user.id):
        await message.answer(
            "Команды владельца:\n"
            "/add_admin <user_id> — назначить администратора\n"
            "/remove_admin <user_id> — снять администратора\n\n"
            "«📥 Входящие сообщения» — посмотреть и переслать сообщения от подписчиков."
        )
    else:
        await message.answer("Нажмите «✍️ Написать сообщение», чтобы отправить сообщение администраторам.")


# ---------- Пересылка (инлайн-кнопка) ----------
@dp.callback_query(F.data.startswith("fwd:"))
async def start_forward(callback: CallbackQuery, state: FSMContext):
    if not await is_owner_or_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    msg_id = int(callback.data.split(":")[1])
    await state.set_state(ForwardMessage.waiting_target)
    await state.update_data(msg_id=msg_id)
    await callback.answer()
    await callback.message.answer(
        "Перешлите (forward) любое сообщение ИЗ ЦЕЛЕВОГО ЧАТА сюда, "
        "или отправьте ID чата (например -1001234567890), куда переслать сообщение №{}.\n\n"
        "Бот должен быть участником этого чата/канала.".format(msg_id),
        reply_markup=cancel_menu(),
    )


@dp.message(ForwardMessage.waiting_target)
async def do_forward(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get("msg_id")
    if msg_id is None:
        await state.clear()
        return

    target_chat_id = None
    if message.forward_from_chat:
        target_chat_id = message.forward_from_chat.id
    elif message.text and message.text.lstrip("-").isdigit():
        target_chat_id = int(message.text.strip())

    if target_chat_id is None:
        await message.answer(
            "Не удалось определить целевой чат. Перешлите сообщение из чата или отправьте его числовой ID."
        )
        return

    row = await db.get_message(msg_id)
    if row is None:
        await message.answer("Сообщение не найдено.")
        await state.clear()
        return

    _, author_id, username, text, photo_file_id, status = row
    author_label = f"@{username}" if username else f"ID {author_id}"
    caption = f"{text or ''}\n\n— переслано от {author_label}"

    try:
        if photo_file_id:
            await bot.send_photo(target_chat_id, photo_file_id, caption=caption)
        else:
            await bot.send_message(target_chat_id, caption)
        await db.mark_forwarded(msg_id)
        await message.answer("✅ Сообщение переслано.", reply_markup=admin_menu())
    except Exception as e:
        await message.answer(
            f"❌ Не удалось переслать: {e}\n\n"
            "Убедитесь, что бот добавлен в целевой чат/канал и имеет права отправки сообщений."
        )

    await state.clear()


# ---------- Запуск ----------
async def main():
    await db.init_db()
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
