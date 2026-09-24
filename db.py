import aiosqlite
from config import DB_PATH

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    can_reveal INTEGER DEFAULT 0,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER,
    author_username TEXT,
    text TEXT,
    photo_file_id TEXT,
    status TEXT DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS message_views (
    message_id INTEGER,
    viewer_id INTEGER,
    viewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, viewer_id)
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()
        # Миграция: если база создана до появления can_reveal, добавим колонку.
        cur = await db.execute("PRAGMA table_info(admins)")
        columns = [row[1] for row in await cur.fetchall()]
        if "can_reveal" not in columns:
            await db.execute("ALTER TABLE admins ADD COLUMN can_reveal INTEGER DEFAULT 0")
            await db.commit()


async def add_admin(user_id: int, username: str | None, can_reveal: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        # Сохраняем существующий can_reveal, если админ уже был, и явно не меняем его,
        # если add_admin вызван без указания прав.
        cur = await db.execute("SELECT can_reveal FROM admins WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        existing_can_reveal = row[0] if row else 0
        final_can_reveal = 1 if can_reveal else existing_can_reveal
        await db.execute(
            "INSERT OR REPLACE INTO admins (user_id, username, can_reveal) VALUES (?, ?, ?)",
            (user_id, username, final_can_reveal),
        )
        await db.commit()


async def set_can_reveal(user_id: int, can_reveal: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE admins SET can_reveal = ? WHERE user_id = ?",
            (1 if can_reveal else 0, user_id),
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row is not None


async def can_reveal_author(user_id: int, owner_id: int) -> bool:
    if user_id == owner_id:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT can_reveal FROM admins WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0] == 1)


async def get_all_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_all_admins_detailed() -> list[tuple[int, str | None, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, username, can_reveal FROM admins")
        return await cur.fetchall()


async def save_message(author_id: int, username: str | None, text: str | None, photo_file_id: str | None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO messages (author_id, author_username, text, photo_file_id) VALUES (?, ?, ?, ?)",
            (author_id, username, text, photo_file_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_message(msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, author_id, author_username, text, photo_file_id, status FROM messages WHERE id = ?",
            (msg_id,),
        )
        return await cur.fetchone()


async def get_recent_messages(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, author_id, author_username, text, photo_file_id, status FROM messages "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_unseen_messages(viewer_id: int, limit: int = 50):
    """Сообщения, которые viewer_id ещё не просматривал (в хронологическом порядке)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT m.id, m.author_id, m.author_username, m.text, m.photo_file_id, m.status
            FROM messages m
            WHERE NOT EXISTS (
                SELECT 1 FROM message_views v
                WHERE v.message_id = m.id AND v.viewer_id = ?
            )
            ORDER BY m.id ASC
            LIMIT ?
            """,
            (viewer_id, limit),
        )
        return await cur.fetchall()


async def mark_messages_viewed(viewer_id: int, message_ids: list[int]):
    if not message_ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO message_views (message_id, viewer_id) VALUES (?, ?)",
            [(msg_id, viewer_id) for msg_id in message_ids],
        )
        await db.commit()


async def mark_forwarded(msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE messages SET status = 'forwarded' WHERE id = ?", (msg_id,))
        await db.commit()
