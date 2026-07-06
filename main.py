"""
╔══════════════════════════════════════════════════════════════════╗
║         TELEGRAM KINO BOT — v4.0  (PostgreSQL + Premium)          ║
╠══════════════════════════════════════════════════════════════════╣
║  Yangi (v4.0):                                                    ║
║  🐘 Butun baza PostgreSQL'ga ko'chirildi (Railway uchun)          ║
║  👑 Premium obuna tizimi — majburiy obunasiz kino ko'rish         ║
║     • Admin narxni va karta raqamini o'zi belgilaydi              ║
║     • User chek(skrinshot) yuboradi -> admin tasdiqlaydi          ║
║     • Admin muddatni har safar o'zi tanlaydi                      ║
║     • Admin xohlagan userga qo'lda premium bera oladi             ║
║  💾 "Kinoni saqlash" — yangi kino qo'shishda preview + tasdiqlash ║
║  🌍 UZ/RU ikki tilli interfeys, barcha xabarlar stikerli          ║
╚══════════════════════════════════════════════════════════════════╝

Ishga tushirish:
    pip install -r requirements.txt
    python main.py

Railway'da:
    1. PostgreSQL plugin qo'shing (DATABASE_URL avtomatik yaratiladi)
    2. BOT_TOKEN va OWNER_ID environment o'zgaruvchilarini qo'shing
    3. Deploy qiling — jadvallar avtomatik yaratiladi
"""

import os
import logging
import time
import asyncio
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)
from telegram.error import Forbidden, TelegramError

import db
from lang import s

# ═══════════════════════════════════════════════════════════════
#  SOZLAMALAR
# ═══════════════════════════════════════════════════════════════
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID  = int(os.getenv("OWNER_ID", "0"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("KinoBot")

# ── Anti-spam: {user_id: [timestamp, ...]} — xotirada, DB kerak emas ──
_spam_tracker: dict[int, list] = {}
SPAM_WINDOW   = 30   # sekund
SPAM_MAX_REQS = 5    # max so'rovlar

JANRLAR = ["🎬 Action", "😂 Komediya", "😢 Drama", "👻 Horror",
           "💕 Melodrama", "🚀 Fantastika", "🔍 Detektiv",
           "🧸 Multfilm", "📽 Hujjatli", "🎭 Boshqa"]

TILLAR  = ["🇺🇿 O'zbekcha", "🇷🇺 Ruscha", "🇺🇸 Inglizcha",
           "🇰🇷 Koreycha", "🇹🇷 Turk", "🌐 Aralash"]

PREMIUM_DURATIONS = [
    (7, "7️⃣ 7 kun"), (30, "3️⃣0️⃣ 30 kun"), (90, "📆 90 kun"),
    (365, "🗓 365 kun"), (None, "♾ Cheksiz"),
]

# ═══════════════════════════════════════════════════════════════
#  YORDAMCHI FORMATLAR
# ═══════════════════════════════════════════════════════════════

def format_size(size_bytes: int) -> str:
    if not size_bytes or size_bytes <= 0:
        return "Noma'lum"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb/1024:.2f} GB"
    return f"{mb:.1f} MB"

def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "Noma'lum"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s_rem = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s_rem:02d}"
    return f"{m}:{s_rem:02d}"

def format_dt(dt) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

def stars_bar(avg: float, count: int) -> str:
    if not avg:
        return "☆☆☆☆☆ (0)"
    full  = int(avg)
    half  = 1 if avg - full >= 0.5 else 0
    empty = 5 - full - half
    bar   = "⭐" * full + ("✨" if half else "") + "☆" * empty
    return f"{bar} {avg}/5 ({count} baho)"

# ═══════════════════════════════════════════════════════════════
#  ANTI-SPAM
# ═══════════════════════════════════════════════════════════════

def check_spam(uid: int) -> tuple[bool, int]:
    now  = time.time()
    reqs = _spam_tracker.get(uid, [])
    reqs = [t for t in reqs if now - t < SPAM_WINDOW]
    if len(reqs) >= SPAM_MAX_REQS:
        wait = int(SPAM_WINDOW - (now - reqs[0])) + 1
        _spam_tracker[uid] = reqs
        return True, wait
    reqs.append(now)
    _spam_tracker[uid] = reqs
    return False, 0

# ═══════════════════════════════════════════════════════════════
#  KLAVIATURALAR
# ═══════════════════════════════════════════════════════════════

def panel_keyboard():
    return ReplyKeyboardMarkup([
        ["📢 Kanallar",       "📥 Kino Yuklash"],
        ["✉ Xabarnoma",      "📊 Statistika"],
        ["👑 Premium",        "🤖 Bot holati"],
        ["👥 Adminlar",       "🎬 Kino boshqaruv"],
        ["◀️ Orqaga"],
    ], resize_keyboard=True)

def bosh_keyboard():
    return ReplyKeyboardMarkup([["◀️ Orqaga"]], resize_keyboard=True)

def skip_keyboard():
    return ReplyKeyboardMarkup([[".  (o'tkazib yuborish)"], ["◀️ Orqaga"]], resize_keyboard=True)

def janr_keyboard(prefix="nk_janr_"):
    rows = []
    for i in range(0, len(JANRLAR), 2):
        row = [InlineKeyboardButton(JANRLAR[i], callback_data=f"{prefix}{i}")]
        if i + 1 < len(JANRLAR):
            row.append(InlineKeyboardButton(JANRLAR[i+1], callback_data=f"{prefix}{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def til_keyboard(prefix="nk_til_"):
    rows = []
    for i in range(0, len(TILLAR), 2):
        row = [InlineKeyboardButton(TILLAR[i], callback_data=f"{prefix}{i}")]
        if i + 1 < len(TILLAR):
            row.append(InlineKeyboardButton(TILLAR[i+1], callback_data=f"{prefix}{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def filter_janr_keyboard():
    rows = []
    for i in range(0, len(JANRLAR), 2):
        row = [InlineKeyboardButton(JANRLAR[i], callback_data=f"filter_{i}")]
        if i + 1 < len(JANRLAR):
            row.append(InlineKeyboardButton(JANRLAR[i+1], callback_data=f"filter_{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def rating_keyboard(kod: str):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐1", callback_data=f"rate_{kod}_1"),
        InlineKeyboardButton("⭐2", callback_data=f"rate_{kod}_2"),
        InlineKeyboardButton("⭐3", callback_data=f"rate_{kod}_3"),
        InlineKeyboardButton("⭐4", callback_data=f"rate_{kod}_4"),
        InlineKeyboardButton("⭐5", callback_data=f"rate_{kod}_5"),
    ], [
        InlineKeyboardButton("🚫 O'tkazib yuborish", callback_data=f"rate_{kod}_skip"),
    ]])

def premium_duration_keyboard(action: str, ref_id):
    rows = []
    row = []
    for days, label in PREMIUM_DURATIONS:
        d = "forever" if days is None else str(days)
        row.append(InlineKeyboardButton(label, callback_data=f"{action}_{ref_id}_{d}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════════════════════════════
#  OBUNA TEKSHIRISH (Premium bo'lsa — o'tkazib yuboriladi!)
# ═══════════════════════════════════════════════════════════════

async def check_public_sub(bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status not in (ChatMember.BANNED, ChatMember.LEFT)
    except TelegramError:
        return True

async def joinchat(bot, user_id: int) -> tuple[bool, list]:
    # 👑 Premium foydalanuvchilar majburiy obunadan ozod!
    if await db.is_premium(user_id):
        return True, []

    buttons = []
    for ch in await db.get_public_channels():
        if not ch:
            continue
        ch_clean = ch.lstrip("@")
        if not await check_public_sub(bot, user_id, f"@{ch_clean}"):
            try:
                chat = await bot.get_chat(f"@{ch_clean}")
                name = chat.title or ch
            except Exception:
                name = ch
            buttons.append([InlineKeyboardButton(f"❌ {name}", url=f"https://t.me/{ch_clean}")])
    for priv in await db.get_private_channels():
        if not await db.is_private_joined(priv["id"], user_id):
            buttons.append([InlineKeyboardButton("❌ Maxfiy kanal", url=priv["link"])])
    if buttons:
        buttons.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="checksuv")])
        return False, buttons
    return True, []

async def send_not_subscribed(message, uid: int, buttons: list):
    await message.reply_text(
        f"<b>⚠️ {await s(uid, 'not_subscribed')}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ═══════════════════════════════════════════════════════════════
#  KINONI YUBORISH
# ═══════════════════════════════════════════════════════════════

async def send_premium_promo(bot, chat_id: int, uid: int, reason: str = "generic", limit: int = 0):
    """Premium sotib olishga undovchi jozibali xabar."""
    price = await db.get_setting("premium_price", "0")
    promo_text = await db.get_setting("premium_promo_text", "")
    if reason == "premium_movie":
        header = "🔒 <b>Ushbu kino faqat Premium foydalanuvchilar uchun!</b> 👑"
    elif reason == "daily_limit":
        header = f"⏳ <b>Bugungi bepul ko'rish limitingiz tugadi!</b> ({limit} ta kino)"
    else:
        header = "👑 <b>Premium imkoniyatlarni kashf eting!</b>"
    text = f"{header}\n\n{promo_text}"
    if price and price != "0":
        text += f"\n\n💎 Narxi: <b>{price} so'm</b>"
    await bot.send_message(
        chat_id, text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🛒 Premium sotib olish", callback_data="premium_buy")
        ]]))


async def send_kino_to_user(bot, chat_id: int, kod, uid: int = None):
    if uid is None:
        uid = chat_id
    kino = await db.get_kino(kod)
    if not kino:
        await bot.send_message(chat_id,
            f"❌ <b>{await s(uid, 'not_found')}</b>", parse_mode="HTML")
        return

    premium = await db.is_premium(uid)
    admin_user = await is_admin(uid)

    # 🔒 Faqat premium uchun mo'ljallangan kino
    if kino.get("premium_only") and not premium and not admin_user:
        await send_premium_promo(bot, chat_id, uid, reason="premium_movie")
        return

    # ⏳ Kunlik bepul limit (0 = cheksiz)
    if not premium and not admin_user:
        limit = int(await db.get_setting("free_daily_limit", "0") or 0)
        if limit > 0:
            today_count = await db.get_today_view_count(uid)
            if today_count >= limit:
                await send_premium_promo(bot, chat_id, uid, reason="daily_limit", limit=limit)
                return
            await db.increment_today_view(uid)

    down     = await db.increment_down(kod, uid)
    kino_ch  = await db.get_kino_ch()
    bot_info = await bot.get_me()
    fav_lbl  = "💔 Sevimlilardan olib tashlash" if await db.is_favorite(uid, str(kod)) else "❤️ Sevimlilarga"
    rated    = await db.user_rated(uid, str(kod))
    rating_bar = stars_bar(kino["avg_rating"], kino["rating_count"])

    badge_line = "👑 <b>Premium kino</b>\n\n" if kino.get("premium_only") else ""
    limit_line = ""
    if not premium and not admin_user:
        limit = int(await db.get_setting("free_daily_limit", "0") or 0)
        if limit > 0:
            left = max(0, limit - await db.get_today_view_count(uid))
            limit_line = f"\n\n🎟 Bugun qolgan bepul ko'rishlar: <b>{left}/{limit}</b> — 👑 Premium bilan cheksiz!"

    caption = (
        f"{badge_line}<b>🎬 {kino['nom']}</b>\n\n"
        f"<blockquote>"
        f"📝 {kino['tavsif'] or '—'}\n\n"
        f"🎭 Janr: {kino['janr']}\n"
        f"📅 Yil: {kino['yil']}\n"
        f"🌐 Til: {kino['til']}\n"
        f"⏱ Davomiylik: {format_duration(kino['duration_sec'])}\n"
        f"💾 Hajm: {format_size(kino['hajm_bytes'])}\n"
        f"📥 Yuklab olindi: {down} marta\n"
        f"⭐ Reyting: {rating_bar}\n"
        f"📆 Qo'shilgan: {format_dt(kino['added_at'])}"
        f"</blockquote>\n\n"
        f"🔰 Kanal: {kino_ch or '—'}\n"
        f"🤖 Bot: @{bot_info.username}"
        f"{limit_line}"
    )

    inline = [
        [InlineKeyboardButton("🔎 Kino kodlari",
             url=f"https://t.me/{kino_ch.lstrip('@')}" if kino_ch else "https://t.me/")],
        [InlineKeyboardButton("📋 Ulashish",
             url=f"https://t.me/share/url?url=https://t.me/{bot_info.username}?start={kod}"),
         InlineKeyboardButton(fav_lbl, callback_data=f"fav_{kod}")],
        [InlineKeyboardButton("💬 Sharhlar", callback_data=f"reviews_{kod}"),
         InlineKeyboardButton("📊 Stat", callback_data=f"kinostat_{kod}")],
    ]
    if not rated:
        inline.append([InlineKeyboardButton("⭐ Baho berish", callback_data=f"askrate_{kod}")])

    try:
        await bot.send_video(
            chat_id=chat_id,
            video=kino["film_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline),
        )
    except TelegramError as e:
        logger.error("Kino yuborishda xato [%s]: %s", kod, e)
        await bot.send_message(chat_id, "❌ Kino yuborishda xato yuz berdi.")

def kino_card_text(k: dict) -> str:
    rating_bar = stars_bar(k.get("avg_rating", 0), k.get("rating_count", 0))
    badge = "👑 Premium" if k.get("premium_only") else "🆓 Oddiy"
    return (
        f"🎬 <b>{k['nom']}</b> — <code>{k['kod']}</code> [{badge}]\n"
        f"🎭 {k['janr']} | 📅 {k['yil']} | 🌐 {k['til']}\n"
        f"💾 {format_size(k['hajm_bytes'])} | 📥 {k['downcount']} marta\n"
        f"⭐ {rating_bar}\n"
        f"📆 {format_dt(k.get('added_at'))}"
    )

# ═══════════════════════════════════════════════════════════════
#  BILDIRISHNOMA
# ═══════════════════════════════════════════════════════════════

async def _send_bulk(bot, user_ids: list, text: str, markup) -> tuple:
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="HTML", reply_markup=markup)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    return sent, failed


async def broadcast_new_kino(bot, kod: str, meta: dict, bot_username: str):
    if not await db.notify_enabled():
        return

    premium_ids = await db.premium_user_ids()
    all_ids     = await db.all_user_ids()
    regular_ids = [u for u in all_ids if u not in set(premium_ids)]
    is_premium_only = bool(meta.get("premium_only"))

    watch_text = (
        f"🔔 <b>Yangi kino qo'shildi!</b>\n\n"
        f"🎬 <b>{meta['nom']}</b>\n"
        f"🎭 {meta['janr']} | 📅 {meta['yil']} | 🌐 {meta['til']}\n"
        f"💾 {format_size(int(meta.get('hajm_bytes', 0)))}\n\n"
        f"Tomosha qilish uchun tugmani bosing 👇"
    )
    watch_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Ko'rish", url=f"https://t.me/{bot_username}?start={kod}")
    ]])

    # 👑 Premium userlarga — har doim darrov, "Ko'rish" tugmasi bilan
    premium_notify_text = ("🔒 <b>Eksklyuziv Premium kino!</b>\n\n" + watch_text) if is_premium_only else watch_text

    async def _send_all():
        s1, f1 = await _send_bulk(bot, premium_ids, premium_notify_text, watch_markup)
        logger.info("👑 Premium bildirishnoma: %d yuborildi, %d xato", s1, f1)

        if is_premium_only:
            # 🆓 Oddiy userlarga kino ko'rsatilmaydi — o'rniga premium sotib olishga undash
            promo_price = await db.get_setting("premium_price", "0")
            promo_text = (
                f"🔒 <b>Yangi eksklyuziv Premium kino qo'shildi!</b>\n\n"
                f"🎬 <b>{meta['nom']}</b>\n"
                f"🎭 {meta['janr']} | 📅 {meta['yil']}\n\n"
                f"Bu kinoni faqat 👑 <b>Premium</b> obunachilar tomosha qila oladi.\n"
                f"💎 Narxi: <b>{promo_price} so'm</b> — hoziroq obuna bo'ling! 🚀"
            )
            promo_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Premium sotib olish", callback_data="premium_buy")
            ]])
            s2, f2 = await _send_bulk(bot, regular_ids, promo_text, promo_markup)
            logger.info("🔒 Premium-reklama: %d yuborildi, %d xato", s2, f2)
            return

        # 🆓 Oddiy kino: erta kirish muddati bo'lsa — kutib, keyin oddiy userlarga yuborish
        early_minutes = int(await db.get_setting("early_access_minutes", "0") or 0)
        if early_minutes > 0:
            await asyncio.sleep(early_minutes * 60)
        s2, f2 = await _send_bulk(bot, regular_ids, watch_text, watch_markup)
        logger.info("🆓 Oddiy bildirishnoma: %d yuborildi, %d xato", s2, f2)

    asyncio.create_task(_send_all())

# ═══════════════════════════════════════════════════════════════
#  MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

async def common_checks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False

    if await db.is_blocked(user.id):
        return False

    is_new = await db.upsert_user(user.id, user.full_name or "", user.username or "")
    if is_new and update.message:
        try:
            await ctx.bot.send_message(
                OWNER_ID,
                f"<b>👤 Yangi obunachi! 🎉\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"🔗 @{user.username or '—'}\n"
                f"🕒 {datetime.now().strftime('%d.%m.%Y | %H:%M')}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👀 Ko'rish", url=f"tg://user?id={user.id}")
                ]]),
            )
        except TelegramError:
            pass

    if await db.bot_holat() == "O'chirilgan" and not await is_admin(user.id):
        if update.message:
            await update.message.reply_text(
                f"⛔️ <b>{await s(user.id, 'bot_off')}</b>", parse_mode="HTML")
        return False
    return True

async def is_admin(uid: int) -> bool:
    admins = await db.get_admins(OWNER_ID)
    return uid in admins

async def send_start_message(message, user, ctx):
    kino_ch = await db.get_kino_ch()
    uid     = user.id
    inline  = [
        [InlineKeyboardButton("🔎 Kino kodlari",
             url=f"https://t.me/{kino_ch.lstrip('@')}" if kino_ch else "https://t.me/")],
        [InlineKeyboardButton("🔍 Kino qidirish", callback_data="search_kino"),
         InlineKeyboardButton("⭐ Top kinolar",   callback_data="top_kinolar")],
        [InlineKeyboardButton("❤️ Sevimlilarim",  callback_data="my_favorites"),
         InlineKeyboardButton("🎯 Janr filtri",   callback_data="janr_filter")],
        [InlineKeyboardButton("👑 Premium",       callback_data="premium_menu"),
         InlineKeyboardButton("🌍 Til / Lang",    callback_data="choose_lang")],
    ]
    if await is_admin(uid):
        inline.append([InlineKeyboardButton("🗄 Boshqaruv paneli", callback_data="boshqar")])

    teaser = ""
    if not await db.is_premium(uid):
        price = await db.get_setting("premium_price", "0")
        if price and price != "0":
            teaser = f"\n\n👑 <i>Majburiy obunasiz va limitlarsiz kino ko'rishni xohlaysizmi? Premium — atigi {price} so'm!</i>"

    await message.reply_text(
        f"🖐 <b>Assalomu alaykum, <a href='tg://user?id={uid}'>{user.first_name}</a>\n\n"
        f"{await s(uid, 'start_greet', name=user.first_name)}</b>{teaser}",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(inline),
    )

# ═══════════════════════════════════════════════════════════════
#  KOMANDALAR
# ═══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await common_checks(update, ctx):
        return
    ctx.user_data.clear()
    ok, buttons = await joinchat(ctx.bot, user.id)
    if not ok:
        await send_not_subscribed(update.message, user.id, buttons)
        if ctx.args:
            ctx.user_data["pending_kod"] = ctx.args[0]
        return
    if ctx.args:
        await send_kino_to_user(ctx.bot, user.id, ctx.args[0], user.id)
        return
    await send_start_message(update.message, user, ctx)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    uid = update.effective_user.id
    ok, buttons = await joinchat(ctx.bot, uid)
    if not ok:
        await send_not_subscribed(update.message, uid, buttons)
        return
    await update.message.reply_text(
        "💻 <b>Savol va takliflar uchun murojaat qiling:</b> 🙋",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("☎️ Qo'llab-quvvatlash", url=f"tg://user?id={OWNER_ID}")
        ]]),
    )

async def cmd_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    if await is_admin(update.effective_user.id):
        await update.message.reply_text(
            f"<b>{await s(update.effective_user.id, 'panel_welcome')}</b>",
            parse_mode="HTML",
            reply_markup=panel_keyboard())

async def cmd_favorites(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    user = update.effective_user
    ok, buttons = await joinchat(ctx.bot, user.id)
    if not ok:
        await send_not_subscribed(update.message, user.id, buttons)
        return
    await show_favorites(update.message, user.id)

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    uid = update.effective_user.id
    ok, buttons = await joinchat(ctx.bot, uid)
    if not ok:
        await send_not_subscribed(update.message, uid, buttons)
        return
    await show_top_kinolar(update.message, uid)

async def cmd_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    uid = update.effective_user.id
    ok, buttons = await joinchat(ctx.bot, uid)
    if not ok:
        await send_not_subscribed(update.message, uid, buttons)
        return
    await update.message.reply_text(
        f"<b>🎯 {await s(uid, 'filter_ask')}</b>",
        parse_mode="HTML",
        reply_markup=filter_janr_keyboard())

async def cmd_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await common_checks(update, ctx):
        return
    await show_premium_menu(update.message, update.effective_user.id)

# ═══════════════════════════════════════════════════════════════
#  PREMIUM — MENU
# ═══════════════════════════════════════════════════════════════

async def show_premium_menu(message, uid: int, edit=False):
    price = await db.get_setting("premium_price", "0")
    if await db.is_premium(uid):
        until = await db.premium_until(uid)
        if until and until.year >= 2099:
            status = await s(uid, "premium_status_forever")
        else:
            status = await s(uid, "premium_status_active", until=format_dt(until))
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_start")]])
    else:
        status = await s(uid, "premium_status_none")
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(await s(uid, "premium_buy_btn"), callback_data="premium_buy")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_start")],
        ])
    text = await s(uid, "premium_menu", price=price, status=status)

    if not await db.is_premium(uid):
        limit = int(await db.get_setting("free_daily_limit", "0") or 0)
        if limit > 0:
            left = max(0, limit - await db.get_today_view_count(uid))
            text += f"\n\n🎟 Bugungi qolgan bepul ko'rishlar: <b>{left}/{limit}</b>"
        text += (
            "\n\n✨ <b>Premium bilan siz:</b>\n"
            "✅ Majburiy obunasiz kino ko'rasiz\n"
            "✅ Kunlik limitlarsiz — cheksiz tomosha qilasiz\n"
            "✅ 🔒 Eksklyuziv premium-kinolarga kirasiz\n"
            "✅ Yangi kinolarni hammadan oldin ko'rasiz ⏱"
        )
    if edit:
        await message.edit_text(f"👑 {text}", parse_mode="HTML", reply_markup=buttons)
    else:
        await message.reply_text(f"👑 {text}", parse_mode="HTML", reply_markup=buttons)

# ═══════════════════════════════════════════════════════════════
#  SEVIMLILAR / TOP
# ═══════════════════════════════════════════════════════════════

async def show_favorites(message, uid: int):
    favs = await db.get_favorites(uid)
    if not favs:
        await message.reply_text(f"<b>{await s(uid, 'fav_empty')}</b>", parse_mode="HTML")
        return
    lines, buttons = [], []
    for kod in favs:
        k = await db.get_kino(kod)
        if k:
            lines.append(f"🎬 <b>{k['nom']}</b> — <code>{kod}</code>")
            buttons.append([
                InlineKeyboardButton(f"▶️ {k['nom'][:25]}", callback_data=f"play_{kod}"),
                InlineKeyboardButton("🗑", callback_data=f"delfav_{kod}"),
            ])
    if not lines:
        await message.reply_text(f"<b>{await s(uid, 'fav_empty')}</b>", parse_mode="HTML")
        return
    text = f"<b>{await s(uid, 'fav_title', n=len(lines))}</b>\n\n" + "\n".join(lines)
    await message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def show_top_kinolar(message, uid: int = 0):
    top = await db.get_top_kinolar(10)
    if not top:
        await message.reply_text(f"<b>📊 {await s(uid, 'top_empty')}</b>", parse_mode="HTML")
        return
    lines, buttons = [], []
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
    for i, k in enumerate(top):
        rating_bar = stars_bar(k.get("avg_rating", 0), k.get("rating_count", 0))
        lines.append(f"{medals[i]} <b>{k['nom']}</b> — {k['downcount']} marta | {rating_bar}")
        buttons.append([InlineKeyboardButton(
            f"{medals[i]} {k['nom'][:30]}", callback_data=f"play_{k['kod']}")])
    text = f"<b>⭐ {await s(uid, 'top_title')}</b>\n\n" + "\n".join(lines)
    await message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

# ═══════════════════════════════════════════════════════════════
#  ASOSIY MATN HANDLERI (STATE MACHINE)
# ═══════════════════════════════════════════════════════════════

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return
    text = update.message.text.strip() if update.message.text else ""
    if not await common_checks(update, ctx):
        return

    uid = user.id
    state = ctx.user_data.get("state")

    # ── Orqaga ────────────────────────────────────────────────
    if text == "◀️ Orqaga":
        ctx.user_data.clear()
        if await is_admin(uid):
            await update.message.reply_text("🔙 Bosh menyu", reply_markup=panel_keyboard() if False else bosh_keyboard())
        await send_start_message(update.message, user, ctx)
        return

    # ── ADMIN PANEL TUGMALARI ────────────────────────────────
    if text == "🗄 Boshqaruv paneli" and await is_admin(uid):
        await update.message.reply_text(
            f"<b>{await s(uid, 'panel_welcome')}</b>", parse_mode="HTML",
            reply_markup=panel_keyboard())
        return

    if text == "📢 Kanallar" and await is_admin(uid):
        await update.message.reply_text(
            f"<b>{await s(uid, 'kino_channels')}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ochiq kanal qo'shish", callback_data="qoshish"),
                 InlineKeyboardButton("➖ Ochiq kanal o'chirish", callback_data="ochirish")],
                [InlineKeyboardButton("➕ Maxfiy kanal qo'shish", callback_data="qosh"),
                 InlineKeyboardButton("➖ Maxfiy kanal o'chirish", callback_data="ochir")],
                [InlineKeyboardButton("🎬 Kino kanalini sozlash", callback_data="kinokanal")],
            ]))
        return

    if text == "📥 Kino Yuklash" and await is_admin(uid):
        ctx.user_data.clear()
        ctx.user_data["state"] = "nk_photo"
        ctx.user_data["new_kino"] = {}
        await update.message.reply_text(
            "🖼 <b>Kino uchun rasm (poster) yuboring.</b>\n"
            "<i>Agar rasm kerak bo'lmasa, \".\" yuboring.</i>",
            parse_mode="HTML", reply_markup=skip_keyboard())
        return

    if text == "✉ Xabarnoma" and await is_admin(uid):
        await update.message.reply_text(
            "✉️ <b>Xabarnoma turi:</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Oddiy xabar", callback_data="send")],
                [InlineKeyboardButton("↪️ Forward xabar", callback_data="send2")],
                [InlineKeyboardButton("👤 Foydalanuvchiga xabar", callback_data="user_msg")],
                [InlineKeyboardButton("🔔 Bildirishnoma yoqish/o'chirish", callback_data="toggle_notify")],
            ]))
        return

    if text == "📊 Statistika" and await is_admin(uid):
        await show_stat(update.message, uid)
        return

    if text == "👑 Premium" and await is_admin(uid):
        await show_premium_admin_menu(update.message, uid)
        return

    if text == "🤖 Bot holati" and await is_admin(uid):
        holat = await db.bot_holat()
        await update.message.reply_text(
            f"<b>{await s(uid, 'bot_status', holat=holat)}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🔴 O'chirish" if holat == "Yoqilgan" else "🟢 Yoqish",
                    callback_data="toggle_holat")
            ]]))
        return

    if text == "👥 Adminlar" and await is_admin(uid):
        admins = await db.get_admins(OWNER_ID)
        lines = "\n".join(f"👤 <code>{a}</code>" + (" 👑" if a == OWNER_ID else "") for a in admins)
        await update.message.reply_text(
            f"<b>👥 Adminlar ro'yxati:</b>\n\n{lines}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin"),
                 InlineKeyboardButton("➖ Admin o'chirish", callback_data="del_admin")],
            ]))
        return

    if text == "🎬 Kino boshqaruv" and await is_admin(uid):
        await update.message.reply_text(
            f"<b>{await s(uid, 'kino_manage')}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="kino_list_0")],
                [InlineKeyboardButton("🔍 Kino qidirish (nomi bo'yicha)", callback_data="kino_search")],
            ]))
        return

    # ── STATE-BASED KIRISH ────────────────────────────────────
    if state and await handle_state_text(update, ctx, state, text, uid):
        return

    # ── ODDIY FOYDALANUVCHI: KINO KODI YOKI NOM QIDIRUV ───────
    ok, buttons = await joinchat(ctx.bot, uid)
    if not ok:
        await send_not_subscribed(update.message, uid, buttons)
        return

    if not await db.is_premium(uid):
        is_spam, wait = check_spam(uid)
        if is_spam:
            await update.message.reply_text(
                f"⚠️ <b>{await s(uid, 'spam_warn', sec=wait)}</b>", parse_mode="HTML")
            return

    if text.isdigit():
        await send_kino_to_user(ctx.bot, uid, text, uid)
        return

    # Nomi bo'yicha qidiruv
    results = await db.search_kino_by_name(text)
    if not results:
        await update.message.reply_text(
            f"<b>{await s(uid, 'not_found')}</b>", parse_mode="HTML")
        return
    buttons = [[InlineKeyboardButton(f"🎬 {k['nom'][:35]} ({k['kod']})", callback_data=f"play_{k['kod']}")]
               for k in results]
    await update.message.reply_text(
        f"🔎 <b>{len(results)} ta natija topildi:</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons))


async def handle_state_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE, state: str, text: str, uid: int) -> bool:
    """Turli holatlardagi matnli kiritishlarni boshqaradi. True qaytarsa — handle_text davom etmaydi."""
    skip = text in (".", ".  (o'tkazib yuborish)")

    # ── YANGI KINO YUKLASH OQIMI ───────────────────────────────
    if state == "nk_nom":
        ctx.user_data["new_kino"]["nom"] = text
        ctx.user_data["state"] = "nk_tavsif"
        await update.message.reply_text(
            "📝 <b>Kino tavsifini yuboring.</b>\n<i>Kerak bo'lmasa \".\" yuboring.</i>",
            parse_mode="HTML", reply_markup=skip_keyboard())
        return True

    if state == "nk_tavsif":
        ctx.user_data["new_kino"]["tavsif"] = "" if skip else text
        ctx.user_data["state"] = "nk_janr"
        await update.message.reply_text(
            "🎭 <b>Janrni tanlang:</b>", parse_mode="HTML",
            reply_markup=janr_keyboard())
        return True

    if state == "nk_yil":
        if not re.match(r"^\d{4}$", text):
            await update.message.reply_text("⚠️ Yilni 4 xonali son ko'rinishida kiriting (masalan 2024).")
            return True
        ctx.user_data["new_kino"]["yil"] = text
        ctx.user_data["state"] = "nk_til"
        await update.message.reply_text(
            "🌐 <b>Tilni tanlang:</b>", parse_mode="HTML",
            reply_markup=til_keyboard())
        return True

    # ── KANAL BOSHQARUVI ───────────────────────────────────────
    if state == "add_public_ch":
        ch = text.lstrip("@").strip()
        await db.add_public_channel(ch)
        ctx.user_data.clear()
        await update.message.reply_text(f"✅ <b>@{ch}</b> kanali qo'shildi!", parse_mode="HTML",
                                         reply_markup=panel_keyboard())
        return True

    if state == "remove_public_ch":
        ch = text.lstrip("@").strip()
        await db.remove_public_channel(ch)
        ctx.user_data.clear()
        await update.message.reply_text(f"🗑 <b>@{ch}</b> kanali o'chirildi!", parse_mode="HTML",
                                         reply_markup=panel_keyboard())
        return True

    if state == "add_private_ch":
        parts = text.strip().splitlines()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ 2 qatorda yuboring: havola va chat_id.")
            return True
        await db.add_private_channel(parts[0].strip(), parts[1].strip())
        ctx.user_data.clear()
        await update.message.reply_text("✅ Maxfiy kanal qo'shildi!", reply_markup=panel_keyboard())
        return True

    if state == "remove_private_ch":
        parts = text.strip().splitlines()
        chat_id = parts[1].strip() if len(parts) > 1 else parts[0].strip()
        await db.remove_private_channel(chat_id)
        ctx.user_data.clear()
        await update.message.reply_text("🗑 Maxfiy kanal o'chirildi!", reply_markup=panel_keyboard())
        return True

    if state == "set_kino_ch":
        await db.set_kino_ch(text.strip())
        ctx.user_data.clear()
        await update.message.reply_text("✅ Kino kanali sozlandi!", reply_markup=panel_keyboard())
        return True

    # ── XABARNOMA ──────────────────────────────────────────────
    if state == "broadcast_msg":
        await do_broadcast(ctx.bot, text=update.message.text, entities=update.message.entities)
        ctx.user_data.clear()
        await update.message.reply_text("✅ Xabar barcha userlarga yuborildi!", reply_markup=panel_keyboard())
        return True

    if state == "get_user_id":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Faqat raqamli ID kiriting.")
            return True
        ctx.user_data["target_uid"] = int(text)
        ctx.user_data["state"] = "send_user_text"
        await update.message.reply_text("📝 <b>Yuboriladigan xabar matnini kiriting:</b>", parse_mode="HTML")
        return True

    if state == "send_user_text":
        target = ctx.user_data.get("target_uid")
        try:
            await ctx.bot.send_message(target, update.message.text)
            await update.message.reply_text("✅ Xabar yuborildi!", reply_markup=panel_keyboard())
        except TelegramError:
            await update.message.reply_text("❌ Xabar yuborilmadi (user botni bloklagan bo'lishi mumkin).",
                                             reply_markup=panel_keyboard())
        ctx.user_data.clear()
        return True

    # ── ADMIN QO'SHISH / O'CHIRISH ─────────────────────────────
    if state == "add_admin":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Faqat raqamli ID kiriting.")
            return True
        await db.add_admin(int(text))
        ctx.user_data.clear()
        await update.message.reply_text(f"✅ <code>{text}</code> admin qilib qo'shildi!", parse_mode="HTML",
                                         reply_markup=panel_keyboard())
        return True

    if state == "del_admin":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Faqat raqamli ID kiriting.")
            return True
        await db.remove_admin(int(text))
        ctx.user_data.clear()
        await update.message.reply_text(f"🗑 <code>{text}</code> adminlikdan olindi!", parse_mode="HTML",
                                         reply_markup=panel_keyboard())
        return True

    # ── KINO QIDIRUV (admin panel) ──────────────────────────────
    if state == "kino_search_input":
        results = await db.search_kino_by_name(text)
        ctx.user_data.clear()
        if not results:
            await update.message.reply_text("❌ Hech narsa topilmadi.", reply_markup=panel_keyboard())
            return True
        buttons = [[InlineKeyboardButton(f"🎬 {k['nom'][:30]} ({k['kod']})", callback_data=f"kino_view_{k['kod']}")]
                   for k in results]
        await update.message.reply_text(f"🔎 {len(results)} ta natija:",
                                         reply_markup=InlineKeyboardMarkup(buttons))
        return True

    # ── PREMIUM SOZLAMALARI ─────────────────────────────────────
    if state == "premium_price_input":
        cleaned = re.sub(r"[^\d]", "", text)
        if not cleaned:
            await update.message.reply_text("⚠️ Faqat son kiriting.")
            return True
        await db.set_setting("premium_price", cleaned)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ {await s(uid, 'premium_settings_saved')}", reply_markup=panel_keyboard())
        return True

    if state == "premium_card_input":
        ctx.user_data["premium_card_tmp"] = text.strip()
        ctx.user_data["state"] = "premium_card_owner_input"
        await update.message.reply_text(f"👤 {await s(uid, 'premium_ask_card_owner')}")
        return True

    if state == "premium_card_owner_input":
        await db.set_setting("premium_card", ctx.user_data.get("premium_card_tmp", ""))
        await db.set_setting("premium_card_owner", text.strip())
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ {await s(uid, 'premium_settings_saved')}", reply_markup=panel_keyboard())
        return True

    if state == "premium_limit_input":
        cleaned = re.sub(r"[^\d]", "", text)
        if cleaned == "":
            await update.message.reply_text("⚠️ Faqat son kiriting (0 = cheksiz).")
            return True
        await db.set_setting("free_daily_limit", cleaned)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ Kunlik bepul limit: <b>{'Cheksiz' if cleaned == '0' else cleaned + ' ta'}</b>",
            parse_mode="HTML", reply_markup=panel_keyboard())
        return True

    if state == "premium_early_input":
        cleaned = re.sub(r"[^\d]", "", text)
        if cleaned == "":
            await update.message.reply_text("⚠️ Faqat son kiriting (0 = darrov hammaga yuboriladi).")
            return True
        await db.set_setting("early_access_minutes", cleaned)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ Erta kirish vaqti: <b>{'Yo\u02bbq' if cleaned == '0' else cleaned + ' daqiqa'}</b>",
            parse_mode="HTML", reply_markup=panel_keyboard())
        return True

    if state == "premium_promo_input":
        await db.set_setting("premium_promo_text", update.message.text)
        ctx.user_data.clear()
        await update.message.reply_text("✅ Reklama matni yangilandi!", reply_markup=panel_keyboard())
        return True

    if state == "premium_grant_uid":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Faqat raqamli ID kiriting.")
            return True
        target_uid = int(text)
        row_exists = await db.get_lang(target_uid)  # user mavjudligini tekshirish uchun soddalashtirilgan
        all_ids = await db.all_user_ids()
        if target_uid not in all_ids:
            await update.message.reply_text(
                f"❌ {await s(uid, 'premium_grant_user_not_found')}", reply_markup=panel_keyboard())
            ctx.user_data.clear()
            return True
        ctx.user_data["premium_grant_target"] = target_uid
        ctx.user_data["state"] = None
        await update.message.reply_text(
            f"📆 {await s(uid, 'premium_choose_duration')}",
            reply_markup=premium_duration_keyboard("grant", target_uid))
        return True

    # ── SHARH YOZISH ────────────────────────────────────────────
    if state and state.startswith("review_"):
        kod = state.split("_", 1)[1]
        if text != "/skip":
            await db.save_review(uid, kod, text, update.effective_user.username or "")
            await update.message.reply_text(f"<b>{await s(uid, 'review_done')}</b>", parse_mode="HTML")
        ctx.user_data.clear()
        return True

    return False


# ═══════════════════════════════════════════════════════════════
#  MEDIA (RASM / VIDEO) HANDLERI
# ═══════════════════════════════════════════════════════════════

async def handle_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return
    if not await common_checks(update, ctx):
        return
    uid = user.id
    state = ctx.user_data.get("state")

    # ── Yangi kino: poster rasm ─────────────────────────────────
    if state == "nk_photo":
        if update.message.photo:
            ctx.user_data["new_kino"]["rasm_id"] = update.message.photo[-1].file_id
        ctx.user_data["state"] = "nk_video"
        await update.message.reply_text(
            "🎥 <b>Endi kino videosini yuboring.</b>", parse_mode="HTML",
            reply_markup=bosh_keyboard())
        return

    # ── Yangi kino: video fayl ───────────────────────────────────
    if state == "nk_video":
        video = update.message.video
        if not video:
            await update.message.reply_text("⚠️ Iltimos, video fayl yuboring.")
            return
        nk = ctx.user_data["new_kino"]
        nk["film_id"] = video.file_id
        nk["duration_sec"] = video.duration or 0
        nk["hajm_bytes"] = video.file_size or 0
        ctx.user_data["state"] = "nk_nom"
        await update.message.reply_text(
            "📛 <b>Kino nomini kiriting:</b>", parse_mode="HTML",
            reply_markup=bosh_keyboard())
        return

    # ── Premium to'lov skrinshoti ────────────────────────────────
    if state == "premium_payment":
        if not update.message.photo:
            await update.message.reply_text("⚠️ Iltimos, to'lov chekining skrinshotini rasm qilib yuboring.")
            return
        photo_id = update.message.photo[-1].file_id
        price = await db.get_setting("premium_price", "0")
        req_id = await db.create_premium_request(uid, int(price or 0), photo_id)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"<b>{await s(uid, 'premium_screenshot_received')}</b>", parse_mode="HTML",
            reply_markup=bosh_keyboard())

        admin_text = await s(
            OWNER_ID, "premium_admin_new_request",
            name=user.full_name, uid=uid, username=user.username or "—", price=price)
        admin_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(await s(OWNER_ID, "premium_approve_btn"), callback_data=f"premium_approve_{req_id}"),
            InlineKeyboardButton(await s(OWNER_ID, "premium_reject_btn"), callback_data=f"premium_reject_{req_id}"),
        ]])
        for admin_id in await db.get_admins(OWNER_ID):
            try:
                await ctx.bot.send_photo(
                    admin_id, photo_id, caption=f"💎 {admin_text}",
                    parse_mode="HTML", reply_markup=admin_markup)
            except TelegramError:
                pass
        return

    # ── Broadcast forward xabar ───────────────────────────────────
    if state == "broadcast_fwd":
        await do_broadcast(ctx.bot, forward_from_chat=update.message.chat_id,
                            forward_message_id=update.message.message_id)
        ctx.user_data.clear()
        await update.message.reply_text("✅ Xabar barcha userlarga forward qilindi!", reply_markup=panel_keyboard())
        return


async def do_broadcast(bot, text=None, entities=None, forward_from_chat=None, forward_message_id=None):
    user_ids = await db.all_user_ids()

    async def _send():
        sent = failed = 0
        for uid in user_ids:
            try:
                if forward_from_chat:
                    await bot.forward_message(uid, forward_from_chat, forward_message_id)
                else:
                    await bot.send_message(uid, text, entities=entities)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        logger.info("Broadcast: %d yuborildi, %d xato", sent, failed)

    asyncio.create_task(_send())


# ═══════════════════════════════════════════════════════════════
#  STATISTIKA
# ═══════════════════════════════════════════════════════════════

async def show_stat(message, uid: int):
    users_count = await db.total_users()
    kino_count  = await db.total_kinolar()
    async with db.pool().acquire() as con:
        premium_count = await con.fetchrow(
            "SELECT COUNT(*) AS c FROM users WHERE premium_until > NOW()")
    text = await s(uid, "stat_title", users=users_count, kinolar=kino_count,
                   premium=premium_count["c"])
    await message.reply_text(
        f"<b>{text}</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📅 Kunlik", callback_data="kunlik"),
            InlineKeyboardButton("📆 Haftalik", callback_data="haftalik"),
            InlineKeyboardButton("📊 Oylik", callback_data="oylik"),
        ]]))

async def show_premium_admin_menu(message, uid: int):
    price = await db.get_setting("premium_price", "0")
    card  = await db.get_setting("premium_card", "—")
    owner = await db.get_setting("premium_card_owner", "—")
    limit = await db.get_setting("free_daily_limit", "0")
    early = await db.get_setting("early_access_minutes", "0")
    text = await s(uid, "premium_settings_menu", price=price, card=card or "—", owner=owner or "—")
    text += (
        f"\n🎟 Kunlik bepul limit: <b>{'Cheksiz' if limit == '0' else limit + ' ta'}</b>\n"
        f"⏱ Erta kirish (oddiy userlarga kechikish): <b>{'Yo\u02bbq' if early == '0' else early + ' daqiqa'}</b>"
    )
    await message.reply_text(
        f"<b>{text}</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Narxni o'zgartirish", callback_data="premium_set_price")],
            [InlineKeyboardButton("💳 Kartani o'zgartirish", callback_data="premium_set_card")],
            [InlineKeyboardButton("🎟 Kunlik bepul limit", callback_data="premium_set_limit"),
             InlineKeyboardButton("⏱ Erta kirish vaqti", callback_data="premium_set_early")],
            [InlineKeyboardButton("📝 Reklama matnini tahrirlash", callback_data="premium_set_promo")],
            [InlineKeyboardButton("📢 Reklamani hammaga yuborish", callback_data="premium_send_promo")],
            [InlineKeyboardButton("🎁 Foydalanuvchiga premium berish", callback_data="premium_grant_start")],
        ]))

# ═══════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    uid   = query.from_user.id
    cid   = query.message.chat_id if query.message else uid

    if await db.is_blocked(uid):
        await query.answer()
        return

    await query.answer()

    # ── OBUNA TEKSHIRISH ─────────────────────────────────────────
    if data == "checksuv":
        ok, buttons = await joinchat(ctx.bot, uid)
        if ok:
            await query.message.delete()
            pending = ctx.user_data.pop("pending_kod", None)
            if pending:
                await send_kino_to_user(ctx.bot, cid, pending, uid)
            else:
                await send_start_message(query.message, query.from_user, ctx)
        else:
            await query.answer(await s(uid, "sub_fail"), show_alert=True)
        return

    if data == "back_to_start":
        await query.message.delete()
        await send_start_message(query.message, query.from_user, ctx)
        return

    # ── ASOSIY MENYU TUGMALARI ────────────────────────────────────
    if data == "search_kino":
        await query.message.edit_text(f"<b>{await s(uid, 'send_code')}</b>", parse_mode="HTML")
        return

    if data == "top_kinolar":
        await show_top_kinolar(query.message, uid)
        return

    if data == "my_favorites":
        await show_favorites(query.message, uid)
        return

    if data == "janr_filter":
        await query.message.edit_text(
            f"<b>🎯 {await s(uid, 'filter_ask')}</b>", parse_mode="HTML",
            reply_markup=filter_janr_keyboard())
        return

    if data == "choose_lang":
        await query.message.edit_text(
            f"<b>{await s(uid, 'lang_choose')}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            ]]))
        return

    if data == "lang_uz":
        await db.set_lang(uid, "uz")
        await query.message.edit_text(f"<b>{await s(uid, 'lang_set')}</b> ✅", parse_mode="HTML")
        return

    if data == "lang_ru":
        await db.set_lang(uid, "ru")
        await query.message.edit_text(f"<b>{await s(uid, 'lang_set')}</b> ✅", parse_mode="HTML")
        return

    if data == "boshqar" and await is_admin(uid):
        await query.message.delete()
        await ctx.bot.send_message(cid, f"<b>{await s(uid, 'panel_welcome')}</b>",
                                    parse_mode="HTML", reply_markup=panel_keyboard())
        return

    # ── JANR / FILTER (index orqali, emoji muammosidan qochish) ──
    if data.startswith("filter_"):
        idx = int(data.split("_", 1)[1])
        janr = JANRLAR[idx]
        kinolar = await db.get_kinolar_by_janr(janr.split(" ", 1)[1])
        if not kinolar:
            await query.message.edit_text(f"<b>{await s(uid, 'filter_empty')}</b>", parse_mode="HTML")
            return
        buttons = [[InlineKeyboardButton(f"🎬 {k['nom'][:35]}", callback_data=f"play_{k['kod']}")]
                   for k in kinolar[:20]]
        await query.message.edit_text(
            f"<b>{janr}</b> — {len(kinolar)} ta kino:", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons))
        return

    # ── KINONI KO'RISH ──────────────────────────────────────────
    if data.startswith("play_"):
        kod = data.split("_", 1)[1]
        ok, buttons = await joinchat(ctx.bot, uid)
        if not ok:
            await send_not_subscribed(query.message, uid, buttons)
            return
        await send_kino_to_user(ctx.bot, cid, kod, uid)
        return

    # ── SEVIMLILAR ───────────────────────────────────────────────
    if data.startswith("fav_"):
        kod = data.split("_", 1)[1]
        if await db.is_favorite(uid, kod):
            await db.remove_favorite(uid, kod)
            await query.answer(await s(uid, "fav_removed"), show_alert=True)
        else:
            await db.add_favorite(uid, kod)
            await query.answer(await s(uid, "fav_added"), show_alert=True)
        return

    if data.startswith("delfav_"):
        kod = data.split("_", 1)[1]
        await db.remove_favorite(uid, kod)
        await query.answer(await s(uid, "fav_removed"), show_alert=True)
        await query.message.delete()
        await show_favorites(query.message, uid)
        return

    # ── REYTING ───────────────────────────────────────────────────
    if data.startswith("askrate_"):
        kod = data.split("_", 1)[1]
        await ctx.bot.send_message(cid, f"<b>{await s(uid, 'rate_ask')}</b>", parse_mode="HTML",
                                    reply_markup=rating_keyboard(kod))
        return

    if data.startswith("rate_"):
        parts = data.split("_")
        kod, val = parts[1], parts[2]
        if val == "skip":
            await query.message.delete()
            return
        await db.save_rating(uid, kod, int(val))
        await query.message.edit_text(f"<b>{await s(uid, 'rate_done')}</b> ⭐", parse_mode="HTML")
        ctx.user_data["state"] = f"review_{kod}"
        await ctx.bot.send_message(cid, f"<b>{await s(uid, 'review_ask')}</b>", parse_mode="HTML")
        return

    # ── SHARHLAR ──────────────────────────────────────────────────
    if data.startswith("reviews_"):
        kod = data.split("_", 1)[1]
        reviews = await db.get_reviews(kod, 10)
        if not reviews:
            await query.answer(await s(uid, "reviews_empty"), show_alert=True)
            return
        lines = []
        for r in reviews:
            badge = "👑 " if await db.is_premium(r["uid"]) else ""
            lines.append(f"{badge}👤 <b>{r['username']}</b>: {r['text']}")
        await ctx.bot.send_message(cid, "💬 <b>Sharhlar:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")
        return

    if data.startswith("kinostat_"):
        kod = data.split("_", 1)[1]
        k = await db.get_kino(kod)
        if not k:
            return
        text = (
            f"📊 <b>{k['nom']} statistikasi</b>\n\n"
            f"📥 Yuklab olindi: {k['downcount']} marta\n"
            f"⭐ Reyting: {stars_bar(k['avg_rating'], k['rating_count'])}\n"
            f"📆 Qo'shilgan: {format_dt(k['added_at'])}"
        )
        await ctx.bot.send_message(cid, text, parse_mode="HTML")
        return

    # ── PREMIUM — FOYDALANUVCHI TOMONI ────────────────────────────
    if data == "premium_menu":
        await show_premium_menu(query.message, uid, edit=True)
        return

    if data == "premium_buy":
        if await db.is_premium(uid):
            until = await db.premium_until(uid)
            await query.answer(await s(uid, "premium_already_active", until=format_dt(until)), show_alert=True)
            return
        price = await db.get_setting("premium_price", "0")
        if price == "0" or not price:
            await query.answer(await s(uid, "premium_no_price"), show_alert=True)
            return
        card  = await db.get_setting("premium_card", "—")
        owner = await db.get_setting("premium_card_owner", "—")
        text = await s(uid, "premium_pay_instructions", price=price, card=card, owner=owner)
        ctx.user_data["state"] = "premium_payment"
        await query.message.delete()
        await ctx.bot.send_message(cid, f"{text}", parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    # ── PREMIUM — ADMIN TASDIQLASH ────────────────────────────────
    if data.startswith("premium_approve_") and await is_admin(uid):
        req_id = int(data.rsplit("_", 1)[1])
        req = await db.get_premium_request(req_id)
        if not req or req["status"] != "pending":
            await query.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
            return
        await query.message.edit_caption(
            caption=f"{query.message.caption}\n\n⏳ Muddat tanlanmoqda...",
            reply_markup=premium_duration_keyboard("premium_dur", req_id))
        return

    if data.startswith("premium_dur_") and await is_admin(uid):
        _, _, req_id, days_str = data.split("_")
        req_id = int(req_id)
        req = await db.get_premium_request(req_id)
        if not req:
            return
        days = None if days_str == "forever" else int(days_str)
        until = await db.grant_premium(req["uid"], days)
        await db.resolve_premium_request(req_id, "approved", uid)
        await query.message.edit_caption(caption=f"✅ {await s(uid, 'premium_approved_admin')}")
        try:
            until_txt = "♾ Cheksiz" if until.year >= 2099 else format_dt(until)
            await ctx.bot.send_message(
                req["uid"],
                f"<b>{await s(req['uid'], 'premium_approved_user', until=until_txt)}</b>",
                parse_mode="HTML")
        except TelegramError:
            pass
        return

    if data.startswith("premium_reject_") and await is_admin(uid):
        req_id = int(data.rsplit("_", 1)[1])
        req = await db.get_premium_request(req_id)
        if not req or req["status"] != "pending":
            await query.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
            return
        await db.resolve_premium_request(req_id, "rejected", uid)
        await query.message.edit_caption(caption=f"❌ {await s(uid, 'premium_rejected_admin')}")
        try:
            await ctx.bot.send_message(
                req["uid"], f"<b>{await s(req['uid'], 'premium_rejected_user')}</b>", parse_mode="HTML")
        except TelegramError:
            pass
        return

    # ── PREMIUM — ADMIN SOZLAMALARI ───────────────────────────────
    if data == "premium_set_price" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "premium_price_input"
        await ctx.bot.send_message(cid, f"💰 {await s(uid, 'premium_ask_price')}", reply_markup=bosh_keyboard())
        return

    if data == "premium_set_card" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "premium_card_input"
        await ctx.bot.send_message(cid, f"💳 {await s(uid, 'premium_ask_card')}", reply_markup=bosh_keyboard())
        return

    if data == "premium_set_limit" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "premium_limit_input"
        await ctx.bot.send_message(
            cid, "🎟 <b>Kunlik bepul ko'rish limitini kiriting (0 = cheksiz):</b>",
            parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "premium_set_early" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "premium_early_input"
        await ctx.bot.send_message(
            cid,
            "⏱ <b>Oddiy kino qo'shilganda, oddiy foydalanuvchilarga necha daqiqa "
            "kechikib yuborilsin (premium userlar darrov oladi)?</b>\n<i>0 = kechikishsiz</i>",
            parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "premium_set_promo" and await is_admin(uid):
        await query.message.delete()
        cur = await db.get_setting("premium_promo_text", "")
        ctx.user_data["state"] = "premium_promo_input"
        await ctx.bot.send_message(
            cid, f"📝 <b>Joriy reklama matni:</b>\n\n{cur}\n\n<b>Yangisini yuboring:</b>",
            parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "premium_send_promo" and await is_admin(uid):
        await query.answer("📢 Reklama yuborilmoqda...", show_alert=True)
        regular_ids = [u for u in await db.all_user_ids() if u not in set(await db.premium_user_ids())]
        price = await db.get_setting("premium_price", "0")
        promo_text = await db.get_setting("premium_promo_text", "")
        text = f"👑 <b>Premium bo'lishning vaqti keldi!</b>\n\n{promo_text}"
        if price and price != "0":
            text += f"\n\n💎 Narxi: <b>{price} so'm</b>"
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🛒 Premium sotib olish", callback_data="premium_buy")
        ]])

        async def _send_promo():
            s1, f1 = await _send_bulk(ctx.bot, regular_ids, text, markup)
            logger.info("📢 Premium reklama: %d yuborildi, %d xato", s1, f1)
            try:
                await ctx.bot.send_message(
                    uid, f"✅ Reklama {s1} foydalanuvchiga yuborildi ({f1} xato).")
            except TelegramError:
                pass

        asyncio.create_task(_send_promo())
        return

    if data == "premium_grant_start" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "premium_grant_uid"
        await ctx.bot.send_message(cid, f"🆔 {await s(uid, 'premium_grant_ask_uid')}", reply_markup=bosh_keyboard())
        return

    if data.startswith("grant_") and await is_admin(uid):
        _, target_uid, days_str = data.split("_")
        target_uid = int(target_uid)
        days = None if days_str == "forever" else int(days_str)
        until = await db.grant_premium(target_uid, days)
        until_txt = "♾ Cheksiz" if until.year >= 2099 else format_dt(until)
        await query.message.edit_text(f"✅ Premium berildi! ({until_txt})")
        try:
            await ctx.bot.send_message(
                target_uid,
                f"<b>{await s(target_uid, 'premium_granted_manual', until=until_txt)}</b>",
                parse_mode="HTML")
        except TelegramError:
            pass
        return

    # ── YANGI KINO: JANR / TIL TANLASH ────────────────────────────
    if data.startswith("nk_janr_"):
        idx = int(data.rsplit("_", 1)[1])
        ctx.user_data["new_kino"]["janr"] = JANRLAR[idx]
        ctx.user_data["state"] = "nk_yil"
        await query.message.edit_text(f"🎭 Janr: <b>{JANRLAR[idx]}</b> ✅", parse_mode="HTML")
        await ctx.bot.send_message(cid, "📅 <b>Chiqarilgan yilini kiriting (masalan 2024):</b>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data.startswith("nk_til_"):
        idx = int(data.rsplit("_", 1)[1])
        ctx.user_data["new_kino"]["til"] = TILLAR[idx]
        await query.message.edit_text(f"🌐 Til: <b>{TILLAR[idx]}</b> ✅", parse_mode="HTML")
        await ctx.bot.send_message(
            cid,
            "🔖 <b>Bu kino qaysi toifada joylansin?</b>\n\n"
            "🆓 <b>Oddiy</b> — barcha foydalanuvchilar ko'ra oladi\n"
            "👑 <b>Premium</b> — faqat premium obunachilar ko'ra oladi "
            "(oddiy userlarga premium sotib olishni taklif qiluvchi reklama chiqadi)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🆓 Oddiy", callback_data="nk_type_0"),
                InlineKeyboardButton("👑 Premium", callback_data="nk_type_1"),
            ]]),
        )
        return

    if data.startswith("nk_type_"):
        ctx.user_data["new_kino"]["premium_only"] = (data == "nk_type_1")
        await query.message.edit_text(
            "👑 Toifa: <b>Premium</b> ✅" if data == "nk_type_1" else "🆓 Toifa: <b>Oddiy</b> ✅",
            parse_mode="HTML")
        await show_kino_preview(ctx.bot, cid, uid, ctx)
        return

    # ── KINO SAQLASH / BEKOR QILISH ───────────────────────────────
    if data == "nk_save" and await is_admin(uid):
        nk = ctx.user_data.get("new_kino", {})
        kod = await db.next_kino_kod()
        await db.save_kino_meta(kod, {
            "nom": nk.get("nom", "Nomsiz"),
            "tavsif": nk.get("tavsif", ""),
            "janr": nk.get("janr", "—"),
            "yil": nk.get("yil", "—"),
            "til": nk.get("til", "—"),
            "duration_sec": nk.get("duration_sec", 0),
            "hajm_bytes": nk.get("hajm_bytes", 0),
            "rasm_id": nk.get("rasm_id", ""),
            "film_id": nk.get("film_id", ""),
            "premium_only": nk.get("premium_only", False),
        })
        bot_info = await ctx.bot.get_me()
        await broadcast_new_kino(ctx.bot, str(kod), nk, bot_info.username)
        await query.message.edit_text(f"<b>{await s(uid, 'kino_saved', kod=kod)}</b>", parse_mode="HTML")
        ctx.user_data.clear()
        await ctx.bot.send_message(cid, "🗄 Admin panel:", reply_markup=panel_keyboard())
        return

    if data == "nk_cancel" and await is_admin(uid):
        ctx.user_data.clear()
        await query.message.edit_text(f"<b>{await s(uid, 'kino_save_cancelled')}</b>", parse_mode="HTML")
        await ctx.bot.send_message(cid, "🗄 Admin panel:", reply_markup=panel_keyboard())
        return

    # ── KINO RO'YXATI / O'CHIRISH (admin) ─────────────────────────
    if data.startswith("kino_list_") and await is_admin(uid):
        page = int(data.rsplit("_", 1)[1])
        await show_kino_list(query.message, page, edit=True)
        return

    if data == "kino_search" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "kino_search_input"
        await ctx.bot.send_message(cid, "🔍 <b>Kino nomini kiriting:</b>", parse_mode="HTML",
                                    reply_markup=bosh_keyboard())
        return

    if data.startswith("kino_view_") and await is_admin(uid):
        kod = data.rsplit("_", 1)[1]
        k = await db.get_kino(kod)
        if not k:
            await query.answer("❌ Topilmadi.", show_alert=True)
            return
        await query.message.edit_text(
            kino_card_text(k), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑 O'chirish", callback_data=f"kino_del_{kod}"),
                InlineKeyboardButton("▶️ Ko'rish", callback_data=f"play_{kod}"),
            ]]))
        return

    if data.startswith("kino_del_") and not data.startswith("kino_del_yes_") and await is_admin(uid):
        kod = data.rsplit("_", 1)[1]
        k = await db.get_kino(kod)
        if not k:
            return
        await query.message.edit_text(
            await s(uid, "kino_confirm_del", nom=k["nom"], janr=k["janr"], yil=k["yil"], down=k["downcount"]),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"kino_del_yes_{kod}"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data=f"kino_view_{kod}"),
            ]]))
        return

    if data.startswith("kino_del_yes_") and await is_admin(uid):
        kod = data.rsplit("_", 1)[1]
        k = await db.get_kino(kod)
        nom = k["nom"] if k else kod
        await db.delete_kino(int(kod))
        await query.message.edit_text(
            await s(uid, "kino_deleted", nom=nom), parse_mode="HTML")
        return

    # ── XABARNOMA / KANAL / BOT HOLATI ────────────────────────────
    if data == "toggle_notify" and await is_admin(uid):
        cur = await db.notify_enabled()
        await db.set_notify_enabled(not cur)
        await query.message.edit_text(f"🔔 Bildirishnoma: {'✅ Yoqilgan' if not cur else '🔕 O\u02bbchirilgan'}")
        return

    if data == "toggle_holat" and await is_admin(uid):
        cur = await db.bot_holat()
        new_val = "O'chirilgan" if cur == "Yoqilgan" else "Yoqilgan"
        await db.set_holat(new_val)
        await query.message.edit_text(
            f"<b>{await s(uid, 'bot_status', holat=new_val)}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔴 O'chirish" if new_val == "Yoqilgan" else "🟢 Yoqish",
                                      callback_data="toggle_holat")
            ]]))
        return

    if data == "add_admin" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "add_admin"
        await ctx.bot.send_message(cid, "🆔 <b>Yangi admin IDsini kiriting:</b>", parse_mode="HTML",
                                    reply_markup=bosh_keyboard())
        return

    if data == "del_admin" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "del_admin"
        await ctx.bot.send_message(cid, "🆔 <b>O'chiriladigan admin IDsini kiriting:</b>", parse_mode="HTML",
                                    reply_markup=bosh_keyboard())
        return

    # ── STATISTIKA ──────────────────────────────────────────────
    if data == "stat" and await is_admin(uid):
        await show_stat(query.message, uid)
        return

    if data == "kunlik" and await is_admin(uid):
        today  = datetime.now()
        labels = ["Bugun", "Kecha", "2 kun", "3 kun", "4 kun", "5 kun"]
        lines = []
        for i in range(6):
            day_start = (today - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            c = await db.count_users_between(day_start, day_end)
            lines.append(f"🔹 {labels[i]}: {c} ta")
        await query.message.edit_text(
            "<b>📅 Kunlik:</b>\n<blockquote>" + "\n".join(lines) + "</blockquote>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="stat")]]))
        return

    if data == "haftalik" and await is_admin(uid):
        today = datetime.now()
        labels = ["Shu hafta", "O'tgan hafta", "2 hafta oldin"]
        lines = []
        for i in range(3):
            start = today - timedelta(weeks=i, days=today.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(weeks=1)
            c = await db.count_users_between(start, end)
            lines.append(f"🔹 {labels[i]}: {c} ta")
        await query.message.edit_text(
            "<b>📆 Haftalik:</b>\n<blockquote>" + "\n".join(lines) + "</blockquote>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="stat")]]))
        return

    if data == "oylik" and await is_admin(uid):
        today = datetime.now()
        labels = ["Shu oy", "O'tgan oy", "2 oy oldin"]
        lines = []
        for i in range(3):
            month_ref = (today.replace(day=1) - timedelta(days=1)) if i else today
            for _ in range(max(i - 1, 0)):
                month_ref = (month_ref.replace(day=1) - timedelta(days=1))
            start = month_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            c = await db.count_users_between(start, end)
            lines.append(f"🔹 {labels[i]}: {c} ta")
        await query.message.edit_text(
            "<b>📊 Oylik:</b>\n<blockquote>" + "\n".join(lines) + "</blockquote>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="stat")]]))
        return

    # ── XABARNOMA YUBORISH ────────────────────────────────────────
    if data == "send" and await is_admin(uid):
        users = await db.all_user_ids()
        await query.message.delete()
        await ctx.bot.send_message(cid, f"<b>📝 {len(users)} ta userga oddiy xabar yuboring:</b>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        ctx.user_data["state"] = "broadcast_msg"
        return

    if data == "send2" and await is_admin(uid):
        users = await db.all_user_ids()
        await query.message.delete()
        await ctx.bot.send_message(cid, f"<b>📝 {len(users)} ta userga forward xabar yuboring:</b>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        ctx.user_data["state"] = "broadcast_fwd"
        return

    if data == "user_msg" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "get_user_id"
        await ctx.bot.send_message(cid, "<b>📝 Foydalanuvchi IDsi:</b>", parse_mode="HTML",
                                    reply_markup=bosh_keyboard())
        return

    # ── KANAL ADD/REMOVE ───────────────────────────────────────────
    if data == "qoshish" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "add_public_ch"
        await ctx.bot.send_message(cid, "<i>⚠️ Botni kanalga admin qiling!</i>\n\n📢 <b>Kanal manzili:</b> <code>@nom</code>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "ochirish" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "remove_public_ch"
        await ctx.bot.send_message(cid, "<b>O'chiriladigan kanal:</b> <code>@nom</code>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "qosh" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "add_private_ch"
        await ctx.bot.send_message(cid, "<b>Maxfiy kanal (2 qator):</b>\n<code>https://t.me/+XXXX\n-100XXXXXXXXX</code>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "ochir" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "remove_private_ch"
        await ctx.bot.send_message(cid, "<b>O'chiriladigan maxfiy kanal (2 qator):</b>\n<code>https://t.me/+XXXX\n-100XXXXXXXXX</code>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return

    if data == "kinokanal" and await is_admin(uid):
        await query.message.delete()
        ctx.user_data["state"] = "set_kino_ch"
        await ctx.bot.send_message(cid, "<b>Kino kanal manzili:</b> <code>@nom</code>",
                                    parse_mode="HTML", reply_markup=bosh_keyboard())
        return


async def show_kino_preview(bot, cid, uid, ctx):
    nk = ctx.user_data.get("new_kino", {})
    text = (
        f"{await s(uid, 'kino_preview_title')}\n\n"
        f"🎬 <b>{nk.get('nom', '—')}</b>\n"
        f"📝 {nk.get('tavsif') or '—'}\n"
        f"🎭 {nk.get('janr', '—')}\n"
        f"📅 {nk.get('yil', '—')}\n"
        f"🌐 {nk.get('til', '—')}\n"
        f"⏱ {format_duration(nk.get('duration_sec', 0))}\n"
        f"💾 {format_size(nk.get('hajm_bytes', 0))}\n"
        f"🔖 Toifa: {'👑 Premium (faqat premium userlar)' if nk.get('premium_only') else '🆓 Oddiy (hammaga ochiq)'}"
    )
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton(await s(uid, "kino_save_btn"), callback_data="nk_save"),
        InlineKeyboardButton(await s(uid, "kino_cancel_btn"), callback_data="nk_cancel"),
    ]])
    if nk.get("rasm_id"):
        await bot.send_photo(cid, nk["rasm_id"], caption=text, parse_mode="HTML", reply_markup=buttons)
    else:
        await bot.send_message(cid, text, parse_mode="HTML", reply_markup=buttons)


async def show_kino_list(message, page: int, edit=False):
    all_kino = await db.get_all_kinolar()
    per_page = 10
    start = page * per_page
    chunk = all_kino[start:start + per_page]
    if not chunk:
        text = "📭 Kinolar topilmadi."
        markup = None
    else:
        buttons = [[InlineKeyboardButton(
                        f"{'👑' if k.get('premium_only') else '🎬'} {k['nom'][:28]} ({k['kod']})",
                        callback_data=f"kino_view_{k['kod']}")]
                   for k in chunk]
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"kino_list_{page-1}"))
        if start + per_page < len(all_kino):
            nav.append(InlineKeyboardButton("➡️", callback_data=f"kino_list_{page+1}"))
        if nav:
            buttons.append(nav)
        text = f"📋 <b>Kinolar ({len(all_kino)} ta):</b>"
        markup = InlineKeyboardMarkup(buttons)
    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ═══════════════════════════════════════════════════════════════
#  CHAT JOIN REQUEST / MY CHAT MEMBER
# ═══════════════════════════════════════════════════════════════

async def handle_join_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    req     = update.chat_join_request
    chat_id = str(req.chat.id)
    user_id = req.from_user.id
    await db.mark_private_joined(chat_id, user_id)
    try:
        await ctx.bot.send_message(user_id, "<b>/start bosing va kino kodini yuboring!</b> 🎬", parse_mode="HTML")
    except TelegramError:
        pass

async def handle_my_chat_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    member = update.my_chat_member
    if member and member.new_chat_member.status == "kicked":
        await db.set_blocked(member.from_user.id, True)

# ═══════════════════════════════════════════════════════════════
#  XATO HANDLERI
# ═══════════════════════════════════════════════════════════════

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Xato: %s", ctx.error)

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

async def _post_init(app: Application):
    await db.init_pool()
    logger.info("🐘 PostgreSQL bazasi ulandi va jadvallar tayyorlandi!")

def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN topilmadi! .env faylini yarating.")
        return
    if not OWNER_ID:
        logger.error("❌ OWNER_ID topilmadi!")
        return
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ DATABASE_URL topilmadi! Railway'da PostgreSQL plugin qo'shing.")
        return

    logger.info("🤖 Kino bot v4.0 ishga tushmoqda...")
    logger.info("👑 Egasi ID: %s", OWNER_ID)

    app = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("panel",     cmd_panel))
    app.add_handler(CommandHandler("favorites", cmd_favorites))
    app.add_handler(CommandHandler("top",       cmd_top))
    app.add_handler(CommandHandler("filter",    cmd_filter))
    app.add_handler(CommandHandler("premium",   cmd_premium))

    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_error_handler(error_handler)

    logger.info("✅ Bot tayyor! Polling boshlandi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
