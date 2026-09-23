import aiosqlite
from config import DB_PATH

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
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
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


async def add_admin(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username),
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


async def get_all_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


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


async def mark_forwarded(msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE messages SET status = 'forwarded' WHERE id = ?", (msg_id,))
        await db.commit()
