"""
═══════════════════════════════════════════════════════════════
  DATABASE QATLAMI — PostgreSQL (asyncpg)
  Railway'da PostgreSQL plugin qo'shilsa, u avtomatik DATABASE_URL
  environment o'zgaruvchisini beradi — shu URL shu yerda ishlatiladi.
═══════════════════════════════════════════════════════════════
"""

import os
import asyncpg
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None

# Cheksiz (umrbod) premium uchun "uzoq kelajak" sana ishlatamiz —
# NULL bilan chalkashmasligi uchun.
FOREVER = datetime(2099, 12, 31, 23, 59, 59)


async def init_pool():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError(
            "❌ DATABASE_URL topilmadi! Railway'da PostgreSQL plugin qo'shing "
            "yoki .env fayliga DATABASE_URL qo'shing."
        )
    _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    await _create_schema()
    await _seed_defaults()


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool hali ishga tushmagan — init_pool() chaqirilmagan.")
    return _pool


async def _create_schema():
    async with _pool.acquire() as con:
        await con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              BIGINT PRIMARY KEY,
            full_name       TEXT DEFAULT '',
            username        TEXT DEFAULT '',
            lang            TEXT DEFAULT 'uz',
            joined_at       TIMESTAMP DEFAULT NOW(),
            is_blocked      BOOLEAN DEFAULT FALSE,
            premium_until   TIMESTAMP NULL
        );

        CREATE TABLE IF NOT EXISTS admins (
            id BIGINT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS kino (
            kod           SERIAL PRIMARY KEY,
            nom           TEXT DEFAULT 'Nomsiz',
            tavsif        TEXT DEFAULT '',
            janr          TEXT DEFAULT '—',
            yil           TEXT DEFAULT '—',
            til           TEXT DEFAULT '—',
            duration_sec  INT DEFAULT 0,
            hajm_bytes    BIGINT DEFAULT 0,
            rasm_id       TEXT DEFAULT '',
            film_id       TEXT DEFAULT '',
            msg_id        TEXT DEFAULT '',
            downcount     INT DEFAULT 0,
            premium_only  BOOLEAN DEFAULT FALSE,
            added_at      TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS daily_views (
            uid       BIGINT,
            view_date DATE,
            cnt       INT DEFAULT 0,
            PRIMARY KEY (uid, view_date)
        );

        CREATE TABLE IF NOT EXISTS viewers (
            kod       INT REFERENCES kino(kod) ON DELETE CASCADE,
            uid       BIGINT,
            viewed_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (kod, uid)
        );

        CREATE TABLE IF NOT EXISTS favorites (
            uid BIGINT,
            kod INT REFERENCES kino(kod) ON DELETE CASCADE,
            PRIMARY KEY (uid, kod)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            kod      INT REFERENCES kino(kod) ON DELETE CASCADE,
            uid      BIGINT,
            stars    INT,
            rated_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (kod, uid)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id         SERIAL PRIMARY KEY,
            kod        INT REFERENCES kino(kod) ON DELETE CASCADE,
            uid        BIGINT,
            username   TEXT,
            text       TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS public_channels (
            channel TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS private_channels (
            link    TEXT,
            chat_id TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS private_joined (
            chat_id TEXT,
            uid     BIGINT,
            PRIMARY KEY (chat_id, uid)
        );

        CREATE TABLE IF NOT EXISTS premium_requests (
            id                 SERIAL PRIMARY KEY,
            uid                BIGINT,
            amount             BIGINT,
            screenshot_file_id TEXT,
            status             TEXT DEFAULT 'pending',
            created_at         TIMESTAMP DEFAULT NOW(),
            resolved_at        TIMESTAMP,
            resolved_by        BIGINT
        );

        CREATE TABLE IF NOT EXISTS blocked_by_bot (
            uid BIGINT PRIMARY KEY
        );
        """)
        # Eski (v4.0) bazalarda ustun mavjud bo'lmasligi mumkin — xavfsiz migratsiya:
        await con.execute(
            "ALTER TABLE kino ADD COLUMN IF NOT EXISTS premium_only BOOLEAN DEFAULT FALSE")


async def _seed_defaults():
    defaults = {
        "holat": "Yoqilgan",
        "kino_ch": "",
        "notify_enabled": "1",
        "premium_price": "0",
        "premium_card": "",
        "premium_card_owner": "",
        "free_daily_limit": "0",
        "early_access_minutes": "0",
        "premium_promo_text": (
            "🔥 Cheksiz kino olamiga xush kelibsiz!\n\n"
            "👑 Premium bilan siz:\n"
            "✅ Majburiy kanallarga obuna bo'lmasdan kino ko'rasiz\n"
            "✅ Kunlik limitlarsiz — xohlagancha kino tomosha qilasiz\n"
            "✅ 🔒 Faqat premium uchun chiqadigan eksklyuziv kinolarga kirasiz\n"
            "✅ Yangi kinolarni hammadan oldin ko'rasiz ⏱\n\n"
            "Hoziroq premium bo'ling! 🚀"
        ),
    }
    async with _pool.acquire() as con:
        for k, v in defaults.items():
            await con.execute(
                "INSERT INTO settings(key, value) VALUES($1,$2) ON CONFLICT (key) DO NOTHING",
                k, v,
            )


# ═══════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════

async def get_setting(key: str, default: str = "") -> str:
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT value FROM settings WHERE key=$1", key)
        return row["value"] if row and row["value"] is not None else default


async def set_setting(key: str, value: str):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO settings(key,value) VALUES($1,$2) "
            "ON CONFLICT (key) DO UPDATE SET value=$2", key, value,
        )


# ═══════════════════════════════════════════════════════════════
#  FOYDALANUVCHILAR
# ═══════════════════════════════════════════════════════════════

async def upsert_user(uid: int, full_name: str, username: str) -> bool:
    """Yangi user bo'lsa True qaytaradi (birinchi marta yozilgan bo'lsa)."""
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT id FROM users WHERE id=$1", uid)
        if row:
            await con.execute(
                "UPDATE users SET full_name=$2, username=$3 WHERE id=$1",
                uid, full_name, username,
            )
            return False
        await con.execute(
            "INSERT INTO users(id, full_name, username) VALUES($1,$2,$3)",
            uid, full_name, username,
        )
        return True


async def get_lang(uid: int) -> str:
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT lang FROM users WHERE id=$1", uid)
        return row["lang"] if row and row["lang"] else "uz"


async def set_lang(uid: int, lang: str):
    async with _pool.acquire() as con:
        await con.execute("UPDATE users SET lang=$2 WHERE id=$1", uid, lang)


async def is_blocked(uid: int) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT is_blocked FROM users WHERE id=$1", uid)
        return bool(row and row["is_blocked"])


async def set_blocked(uid: int, blocked: bool = True):
    async with _pool.acquire() as con:
        await con.execute("UPDATE users SET is_blocked=$2 WHERE id=$1", uid, blocked)


async def total_users() -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT COUNT(*) AS c FROM users")
        return row["c"]


async def all_user_ids() -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch("SELECT id FROM users WHERE is_blocked=FALSE")
        return [r["id"] for r in rows]


async def premium_user_ids() -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT id FROM users WHERE is_blocked=FALSE AND premium_until > NOW()")
        return [r["id"] for r in rows]


async def count_users_since(dt: datetime) -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT COUNT(*) AS c FROM users WHERE joined_at::date = $1::date", dt)
        return row["c"]


async def count_users_between(start: datetime, end: datetime) -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT COUNT(*) AS c FROM users WHERE joined_at >= $1 AND joined_at < $2",
            start, end)
        return row["c"]


# ═══════════════════════════════════════════════════════════════
#  ADMINLAR
# ═══════════════════════════════════════════════════════════════

async def get_admins(owner_id: int) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch("SELECT id FROM admins")
        ids = {r["id"] for r in rows}
        ids.add(owner_id)
        return list(ids)


async def add_admin(uid: int):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO admins(id) VALUES($1) ON CONFLICT DO NOTHING", uid)


async def remove_admin(uid: int):
    async with _pool.acquire() as con:
        await con.execute("DELETE FROM admins WHERE id=$1", uid)


# ═══════════════════════════════════════════════════════════════
#  PREMIUM
# ═══════════════════════════════════════════════════════════════

async def is_premium(uid: int) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT premium_until FROM users WHERE id=$1", uid)
        if not row or not row["premium_until"]:
            return False
        return row["premium_until"] > datetime.now()


async def premium_until(uid: int):
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT premium_until FROM users WHERE id=$1", uid)
        return row["premium_until"] if row else None


async def grant_premium(uid: int, days: int | None):
    """days=None -> cheksiz (umrbod)."""
    until = FOREVER if days is None else datetime.now() + timedelta(days=days)
    async with _pool.acquire() as con:
        await con.execute(
            "UPDATE users SET premium_until=$2 WHERE id=$1", uid, until)
    return until


async def revoke_premium(uid: int):
    async with _pool.acquire() as con:
        await con.execute("UPDATE users SET premium_until=NULL WHERE id=$1", uid)


async def create_premium_request(uid: int, amount: int, screenshot_file_id: str) -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "INSERT INTO premium_requests(uid, amount, screenshot_file_id) "
            "VALUES($1,$2,$3) RETURNING id", uid, amount, screenshot_file_id)
        return row["id"]


async def get_premium_request(req_id: int):
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT * FROM premium_requests WHERE id=$1", req_id)
        return dict(row) if row else None


async def resolve_premium_request(req_id: int, status: str, admin_id: int):
    async with _pool.acquire() as con:
        await con.execute(
            "UPDATE premium_requests SET status=$2, resolved_at=NOW(), resolved_by=$3 "
            "WHERE id=$1", req_id, status, admin_id)


# ═══════════════════════════════════════════════════════════════
#  KINO
# ═══════════════════════════════════════════════════════════════

async def next_kino_kod() -> int:
    """Postgres sequence orqali thread/async-safe id (bo'shliqlarni to'ldirmaydi,
    lekin SERIAL tabiiy ravishda parallel so'rovlarda xavfsiz)."""
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "INSERT INTO kino(nom) VALUES('') RETURNING kod")
        return row["kod"]


async def save_kino_meta(kod: int, meta: dict):
    fields = []
    values = []
    idx = 2
    for key, val in meta.items():
        fields.append(f"{key}=${idx}")
        values.append(val)
        idx += 1
    if not fields:
        return
    query = f"UPDATE kino SET {', '.join(fields)} WHERE kod=$1"
    async with _pool.acquire() as con:
        await con.execute(query, kod, *values)


async def delete_kino(kod: int):
    async with _pool.acquire() as con:
        await con.execute("DELETE FROM kino WHERE kod=$1", kod)


async def get_kino(kod) -> dict | None:
    try:
        kod_int = int(kod)
    except (ValueError, TypeError):
        return None
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT * FROM kino WHERE kod=$1", kod_int)
        if not row or not row["film_id"]:
            return None
        avg_row = await con.fetchrow(
            "SELECT COALESCE(AVG(stars),0) AS avg, COUNT(*) AS c FROM ratings WHERE kod=$1",
            kod_int)
        d = dict(row)
        d["kod"] = str(row["kod"])
        d["avg_rating"] = round(float(avg_row["avg"]), 1)
        d["rating_count"] = avg_row["c"]
        return d


async def get_all_kinolar() -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT * FROM kino WHERE film_id IS NOT NULL AND film_id != '' "
            "ORDER BY kod DESC")
        result = []
        for row in rows:
            d = dict(row)
            d["kod"] = str(row["kod"])
            result.append(d)
        return result


async def get_kinolar_by_janr(janr: str) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT * FROM kino WHERE film_id IS NOT NULL AND film_id != '' "
            "AND janr ILIKE $1 ORDER BY kod DESC", f"%{janr}%")
        result = []
        for row in rows:
            d = dict(row)
            d["kod"] = str(row["kod"])
            result.append(d)
        return result


async def search_kino_by_name(query: str) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT * FROM kino WHERE film_id IS NOT NULL AND film_id != '' "
            "AND nom ILIKE $1 ORDER BY kod DESC LIMIT 15", f"%{query}%")
        result = []
        for row in rows:
            d = dict(row)
            d["kod"] = str(row["kod"])
            result.append(d)
        return result


async def get_top_kinolar(limit: int = 10) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT * FROM kino WHERE film_id IS NOT NULL AND film_id != '' "
            "ORDER BY downcount DESC LIMIT $1", limit)
        result = []
        for row in rows:
            d = dict(row)
            d["kod"] = str(row["kod"])
            avg_row = await con.fetchrow(
                "SELECT COALESCE(AVG(stars),0) AS avg, COUNT(*) AS c FROM ratings WHERE kod=$1",
                row["kod"])
            d["avg_rating"] = round(float(avg_row["avg"]), 1)
            d["rating_count"] = avg_row["c"]
            result.append(d)
        return result


async def increment_down(kod, uid: int) -> int:
    kod_int = int(kod)
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "UPDATE kino SET downcount = downcount + 1 WHERE kod=$1 RETURNING downcount",
            kod_int)
        await con.execute(
            "INSERT INTO viewers(kod, uid) VALUES($1,$2) "
            "ON CONFLICT (kod, uid) DO UPDATE SET viewed_at=NOW()", kod_int, uid)
        return row["downcount"] if row else 0


async def get_today_view_count(uid: int) -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT cnt FROM daily_views WHERE uid=$1 AND view_date=CURRENT_DATE", uid)
        return row["cnt"] if row else 0


async def increment_today_view(uid: int) -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "INSERT INTO daily_views(uid, view_date, cnt) VALUES($1, CURRENT_DATE, 1) "
            "ON CONFLICT (uid, view_date) DO UPDATE SET cnt = daily_views.cnt + 1 "
            "RETURNING cnt", uid)
        return row["cnt"]


async def total_kinolar() -> int:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT COUNT(*) AS c FROM kino WHERE film_id IS NOT NULL AND film_id != ''")
        return row["c"]


# ═══════════════════════════════════════════════════════════════
#  REYTING / SHARH
# ═══════════════════════════════════════════════════════════════

async def save_rating(uid: int, kod: str, stars: int):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO ratings(kod, uid, stars) VALUES($1,$2,$3) "
            "ON CONFLICT (kod, uid) DO UPDATE SET stars=$3, rated_at=NOW()",
            int(kod), uid, stars)


async def user_rated(uid: int, kod: str) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT 1 FROM ratings WHERE kod=$1 AND uid=$2", int(kod), uid)
        return row is not None


async def save_review(uid: int, kod: str, text: str, username: str = ""):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO reviews(kod, uid, username, text) VALUES($1,$2,$3,$4)",
            int(kod), uid, username or str(uid), text[:300])


async def get_reviews(kod: str, limit: int = 20) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT * FROM reviews WHERE kod=$1 ORDER BY created_at DESC LIMIT $2",
            int(kod), limit)
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  SEVIMLILAR
# ═══════════════════════════════════════════════════════════════

async def get_favorites(uid: int) -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch(
            "SELECT kod FROM favorites WHERE uid=$1 ORDER BY kod DESC", uid)
        return [str(r["kod"]) for r in rows]


async def add_favorite(uid: int, kod: str) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT 1 FROM favorites WHERE uid=$1 AND kod=$2", uid, int(kod))
        if row:
            return False
        await con.execute(
            "INSERT INTO favorites(uid, kod) VALUES($1,$2)", uid, int(kod))
        return True


async def remove_favorite(uid: int, kod: str) -> bool:
    async with _pool.acquire() as con:
        result = await con.execute(
            "DELETE FROM favorites WHERE uid=$1 AND kod=$2", uid, int(kod))
        return result.endswith("1")


async def is_favorite(uid: int, kod: str) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT 1 FROM favorites WHERE uid=$1 AND kod=$2", uid, int(kod))
        return row is not None


# ═══════════════════════════════════════════════════════════════
#  KANALLAR
# ═══════════════════════════════════════════════════════════════

async def get_kino_ch() -> str:
    return await get_setting("kino_ch", "")


async def set_kino_ch(ch: str):
    await set_setting("kino_ch", ch)


async def get_public_channels() -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch("SELECT channel FROM public_channels ORDER BY channel")
        return [r["channel"] for r in rows]


async def add_public_channel(ch: str):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO public_channels(channel) VALUES($1) ON CONFLICT DO NOTHING", ch)


async def remove_public_channel(ch: str):
    async with _pool.acquire() as con:
        await con.execute("DELETE FROM public_channels WHERE channel=$1", ch)


async def get_private_channels() -> list:
    async with _pool.acquire() as con:
        rows = await con.fetch("SELECT link, chat_id FROM private_channels")
        return [{"link": r["link"], "id": r["chat_id"]} for r in rows]


async def add_private_channel(link: str, chat_id: str):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO private_channels(link, chat_id) VALUES($1,$2) "
            "ON CONFLICT (chat_id) DO UPDATE SET link=$1", link, chat_id)


async def remove_private_channel(chat_id: str):
    async with _pool.acquire() as con:
        await con.execute("DELETE FROM private_channels WHERE chat_id=$1", chat_id)
        await con.execute("DELETE FROM private_joined WHERE chat_id=$1", chat_id)


async def mark_private_joined(chat_id: str, uid: int):
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO private_joined(chat_id, uid) VALUES($1,$2) "
            "ON CONFLICT DO NOTHING", chat_id, uid)


async def is_private_joined(chat_id: str, uid: int) -> bool:
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT 1 FROM private_joined WHERE chat_id=$1 AND uid=$2", chat_id, uid)
        return row is not None


# ═══════════════════════════════════════════════════════════════
#  BOT HOLATI
# ═══════════════════════════════════════════════════════════════

async def bot_holat() -> str:
    return await get_setting("holat", "Yoqilgan")


async def set_holat(val: str):
    await set_setting("holat", val)


async def notify_enabled() -> bool:
    return await get_setting("notify_enabled", "1") == "1"


async def set_notify_enabled(val: bool):
    await set_setting("notify_enabled", "1" if val else "0")
