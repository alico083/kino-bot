"""
═══════════════════════════════════════════════════════════════
  TIL (UZ / RU) TIZIMI
═══════════════════════════════════════════════════════════════
"""

import db

STRINGS = {
    "uz": {
        "start_greet": (
            "🖐 Assalomu alaykum, {name}!\n\n"
            "<blockquote>📊 Buyruqlar:\n"
            "/start — Botni qayta ishga tushirish\n"
            "/favorites — Sevimli kinolarim\n"
            "/top — Top-10 kinolar\n"
            "/filter — Janr bo'yicha\n"
            "/premium — Premium obuna\n"
            "/help — Yordam</blockquote>\n\n"
            "🔎 Kino kodi yoki nom yuboring:"
        ),
        "not_subscribed": "⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!",
        "sub_check": "🔄 Tekshirish",
        "sub_ok": "✅ Obuna tasdiqlandi!",
        "sub_fail": "❌ Hali a'zo bo'lmadingiz!",
        "not_found": "❌ Kino topilmadi!\n<i>Kino kodi (raqam) yoki nom yuboring.</i>",
        "bot_off": "⛔️ Bot vaqtinchalik o'chirilgan!",
        "spam_warn": "⚠️ Juda tez so'rov yuboryapsiz! {sec} soniya kuting.",
        "send_code": "🔎 Kino kodini yuboring:",
        "fav_added": "❤️ Sevimlilarga qo'shildi!",
        "fav_removed": "💔 Sevimlilardan olib tashlandi!",
        "fav_empty": "❤️ Sevimlilar ro'yxatingiz bo'sh!\n\n<i>Kino yuklaganda '❤️ Sevimlilarga' tugmasini bosing.</i>",
        "fav_title": "❤️ Sevimli kinolaringiz ({n} ta):",
        "top_empty": "📊 Hali kinolar yuklanmagan.",
        "top_title": "⭐ Top-10 eng ko'p yuklab olingan kinolar:",
        "rate_ask": "⭐ Kino uchun baho bering (1-5 yulduz):",
        "rate_done": "✅ Bahoyingiz saqlandi! Rahmat! 🎉",
        "review_ask": "💬 Kino haqida fikringizni yozing (yoki /skip):",
        "review_done": "💬 Sharhingiz qabul qilindi! 🙌",
        "reviews_empty": "💬 Bu kino uchun hali sharh yo'q.",
        "filter_ask": "🎯 Janrni tanlang:",
        "filter_empty": "🎭 Bu janrda kino topilmadi.",
        "notify_new": "🔔 Yangi kino qo'shildi!\n\n🎬 <b>{nom}</b>\n🎭 {janr} | 📅 {yil} | 🌐 {til}\n\nKo'rish uchun tugmani bosing 👇",
        "lang_choose": "🌍 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Til o'rnatildi: O'zbekcha 🇺🇿",
        "panel_welcome": "🖥️ Admin paneliga xush kelibsiz! 👑",
        "kino_channels": "📢 Majburiy obunalarni sozlash:",
        "kino_manage": "🎬 Kino boshqaruvi:",
        "stat_title": "📊 <b>Statistika:</b>\n\n👥 Jami foydalanuvchilar: {users} ta\n🎬 Jami kinolar: {kinolar} ta\n👑 Premium userlar: {premium} ta",
        "bot_status": "📄 Hozirgi holat: {holat}",
        "kino_deleted": "🗑 <b>{nom}</b> o'chirildi!",
        "kino_confirm_del": "⚠️ Haqiqatan ham o'chirasizmi?\n\n🎬 <b>{nom}</b>\n🎭 {janr} | 📅 {yil}\n📥 {down} marta yuklab olingan",
        # ── PREMIUM ──────────────────────────────────────────
        "premium_menu": (
            "👑 <b>Premium obuna</b>\n\n"
            "✨ Premium foydalanuvchilar majburiy kanallarga obuna bo'lmasdan "
            "istalgan kinoni bemalol tomosha qilishlari mumkin!\n\n"
            "💎 Narxi: <b>{price} so'm</b>\n"
            "📆 Sizning holatingiz: {status}"
        ),
        "premium_status_active": "👑 Premium faol ({until} gacha)",
        "premium_status_forever": "👑 Premium faol (umrbod ♾)",
        "premium_status_none": "🔓 Premium yo'q",
        "premium_buy_btn": "🛒 Premium sotib olish",
        "premium_already_active": "✅ Sizda allaqachon premium obuna faol!\n📆 Muddati: {until}",
        "premium_pay_instructions": (
            "💳 <b>To'lov qilish</b>\n\n"
            "⚠️ <i>To'lovdan oldin summaga diqqat bilan qarang, xato tashlangan pul qaytarilmaydi!</i>\n\n"
            "💰 Narxi: <b>{price} so'm</b>\n"
            "💳 Karta raqami: <code>{card}</code>\n"
            "👤 Karta egasi: <b>{owner}</b>\n\n"
            "📸 To'lovni amalga oshirgach, chekingiz (skrinshot) shu yerga rasm qilib yuboring."
        ),
        "premium_no_price": "⏳ Premium narxi hali admin tomonidan belgilanmagan. Birozdan so'ng qayta urinib ko'ring.",
        "premium_screenshot_received": "✅ Skrinshotingiz qabul qilindi va adminга yuborildi!\n⏳ Tez orada tasdiqlanadi, iltimos kuting...",
        "premium_admin_new_request": (
            "💎 <b>Yangi premium so'rov!</b>\n\n"
            "👤 {name} (<code>{uid}</code>)\n"
            "🔗 @{username}\n"
            "💰 Taxminiy summa: {price} so'm\n\n"
            "Tasdiqlaysizmi?"
        ),
        "premium_approve_btn": "✅ Tasdiqlash",
        "premium_reject_btn": "❌ Rad etish",
        "premium_choose_duration": "📆 Premium necha kunga beriladi?",
        "premium_approved_user": "🎉 Tabriklaymiz! Premium obunangiz faollashtirildi!\n👑 Muddati: {until}",
        "premium_rejected_user": "❌ Kechirasiz, to'lovingiz tasdiqlanmadi. Qo'llab-quvvatlash xizmatiga murojaat qiling.",
        "premium_approved_admin": "✅ Premium tasdiqlandi va foydalanuvchiga berildi!",
        "premium_rejected_admin": "❌ So'rov rad etildi.",
        "premium_grant_ask_uid": "🆔 Kimga premium bermoqchisiz? Foydalanuvchi IDsini yuboring:",
        "premium_grant_user_not_found": "❌ Bunday foydalanuvchi topilmadi (u botga /start bosmagan bo'lishi mumkin).",
        "premium_granted_manual": "🎁 Sizga admin tomonidan premium obuna berildi!\n👑 Muddati: {until}",
        "premium_ask_price": "💰 Premium narxini kiriting (faqat son, so'mda):",
        "premium_ask_card": "💳 Karta raqamini kiriting:",
        "premium_ask_card_owner": "👤 Karta egasining F.I.Sh. kiriting:",
        "premium_settings_saved": "✅ Premium sozlamalari saqlandi!",
        "premium_settings_menu": "👑 <b>Premium sozlamalari</b>\n\n💰 Narx: {price} so'm\n💳 Karta: {card}\n👤 Egasi: {owner}",
        "premium_revoked": "🔻 Premium obuna bekor qilindi.",
        # ── FILM SAQLASH ─────────────────────────────────────
        "kino_preview_title": "👀 <b>Kino ma'lumotlari — tekshirib ko'ring:</b>",
        "kino_save_btn": "💾 Saqlash",
        "kino_cancel_btn": "❌ Bekor qilish",
        "kino_saved": "✅ Kino muvaffaqiyatli saqlandi va bazaga qo'shildi! 🎉\n🔢 Kod: <code>{kod}</code>",
        "kino_save_cancelled": "🚫 Kino saqlash bekor qilindi.",
    },
    "ru": {
        "start_greet": (
            "🖐 Привет, {name}!\n\n"
            "<blockquote>📊 Команды:\n"
            "/start — Перезапустить бота\n"
            "/favorites — Избранное\n"
            "/top — Топ-10 фильмов\n"
            "/filter — По жанру\n"
            "/premium — Премиум подписка\n"
            "/help — Помощь</blockquote>\n\n"
            "🔎 Отправьте код или название фильма:"
        ),
        "not_subscribed": "⚠️ Для полного доступа подпишитесь на каналы ниже!",
        "sub_check": "🔄 Проверить",
        "sub_ok": "✅ Подписка подтверждена!",
        "sub_fail": "❌ Вы ещё не подписались!",
        "not_found": "❌ Фильм не найден!\n<i>Введите код (число) или название.</i>",
        "bot_off": "⛔️ Бот временно отключён!",
        "spam_warn": "⚠️ Слишком быстро! Подождите {sec} секунд.",
        "send_code": "🔎 Введите код фильма:",
        "fav_added": "❤️ Добавлено в избранное!",
        "fav_removed": "💔 Удалено из избранного!",
        "fav_empty": "❤️ Список избранного пуст!\n\n<i>Нажмите '❤️ В избранное' при просмотре фильма.</i>",
        "fav_title": "❤️ Ваши избранные фильмы ({n} шт.):",
        "top_empty": "📊 Фильмы ещё не загружены.",
        "top_title": "⭐ Топ-10 самых скачиваемых фильмов:",
        "rate_ask": "⭐ Оцените фильм (1-5 звёзд):",
        "rate_done": "✅ Ваша оценка сохранена! Спасибо! 🎉",
        "review_ask": "💬 Напишите отзыв о фильме (или /skip):",
        "review_done": "💬 Ваш отзыв принят! 🙌",
        "reviews_empty": "💬 Отзывов для этого фильма пока нет.",
        "filter_ask": "🎯 Выберите жанр:",
        "filter_empty": "🎭 Фильмы этого жанра не найдены.",
        "notify_new": "🔔 Новый фильм добавлен!\n\n🎬 <b>{nom}</b>\n🎭 {janr} | 📅 {yil} | 🌐 {til}\n\nНажмите кнопку для просмотра 👇",
        "lang_choose": "🌍 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Язык установлен: Русский 🇷🇺",
        "panel_welcome": "🖥️ Добро пожаловать в панель администратора! 👑",
        "kino_channels": "📢 Настройка обязательных подписок:",
        "kino_manage": "🎬 Управление фильмами:",
        "stat_title": "📊 <b>Статистика:</b>\n\n👥 Всего пользователей: {users}\n🎬 Всего фильмов: {kinolar}\n👑 Премиум пользователей: {premium}",
        "bot_status": "📄 Текущий статус: {holat}",
        "kino_deleted": "🗑 <b>{nom}</b> удалён!",
        "kino_confirm_del": "⚠️ Действительно удалить?\n\n🎬 <b>{nom}</b>\n🎭 {janr} | 📅 {yil}\n📥 Скачано {down} раз",
        # ── PREMIUM ──────────────────────────────────────────
        "premium_menu": (
            "👑 <b>Премиум подписка</b>\n\n"
            "✨ Премиум пользователи могут смотреть любые фильмы без "
            "обязательной подписки на каналы!\n\n"
            "💎 Цена: <b>{price} сум</b>\n"
            "📆 Ваш статус: {status}"
        ),
        "premium_status_active": "👑 Премиум активен (до {until})",
        "premium_status_forever": "👑 Премиум активен (навсегда ♾)",
        "premium_status_none": "🔓 Премиум не активен",
        "premium_buy_btn": "🛒 Купить премиум",
        "premium_already_active": "✅ У вас уже есть активный премиум!\n📆 Срок: {until}",
        "premium_pay_instructions": (
            "💳 <b>Оплата</b>\n\n"
            "⚠️ <i>Перед оплатой внимательно проверьте сумму, ошибочные платежи не возвращаются!</i>\n\n"
            "💰 Цена: <b>{price} сум</b>\n"
            "💳 Номер карты: <code>{card}</code>\n"
            "👤 Владелец карты: <b>{owner}</b>\n\n"
            "📸 После оплаты отправьте сюда скриншот чека."
        ),
        "premium_no_price": "⏳ Цена премиума ещё не установлена админом. Попробуйте позже.",
        "premium_screenshot_received": "✅ Ваш скриншот получен и отправлен админу!\n⏳ Пожалуйста, подождите подтверждения...",
        "premium_admin_new_request": (
            "💎 <b>Новый запрос на премиум!</b>\n\n"
            "👤 {name} (<code>{uid}</code>)\n"
            "🔗 @{username}\n"
            "💰 Ожидаемая сумма: {price} сум\n\n"
            "Подтвердить?"
        ),
        "premium_approve_btn": "✅ Подтвердить",
        "premium_reject_btn": "❌ Отклонить",
        "premium_choose_duration": "📆 На сколько дней выдать премиум?",
        "premium_approved_user": "🎉 Поздравляем! Ваша премиум подписка активирована!\n👑 Срок: {until}",
        "premium_rejected_user": "❌ К сожалению, ваш платёж не подтверждён. Обратитесь в поддержку.",
        "premium_approved_admin": "✅ Премиум подтверждён и выдан пользователю!",
        "premium_rejected_admin": "❌ Запрос отклонён.",
        "premium_grant_ask_uid": "🆔 Кому выдать премиум? Отправьте ID пользователя:",
        "premium_grant_user_not_found": "❌ Пользователь не найден (возможно, он не нажимал /start).",
        "premium_granted_manual": "🎁 Администратор выдал вам премиум подписку!\n👑 Срок: {until}",
        "premium_ask_price": "💰 Введите цену премиума (только число, в сумах):",
        "premium_ask_card": "💳 Введите номер карты:",
        "premium_ask_card_owner": "👤 Введите Ф.И.О. владельца карты:",
        "premium_settings_saved": "✅ Настройки премиума сохранены!",
        "premium_settings_menu": "👑 <b>Настройки премиума</b>\n\n💰 Цена: {price} сум\n💳 Карта: {card}\n👤 Владелец: {owner}",
        "premium_revoked": "🔻 Премиум подписка отменена.",
        # ── СОХРАНЕНИЕ ФИЛЬМА ────────────────────────────────
        "kino_preview_title": "👀 <b>Данные фильма — проверьте:</b>",
        "kino_save_btn": "💾 Сохранить",
        "kino_cancel_btn": "❌ Отмена",
        "kino_saved": "✅ Фильм успешно сохранён и добавлен в базу! 🎉\n🔢 Код: <code>{kod}</code>",
        "kino_save_cancelled": "🚫 Сохранение фильма отменено.",
    },
}


async def s(uid: int, key: str, **kwargs) -> str:
    """Foydalanuvchi tiliga mos matnni qaytaradi (async, DB'dan tilni oladi)."""
    lang = await db.get_lang(uid)
    if lang not in STRINGS:
        lang = "uz"
    text = STRINGS[lang].get(key, STRINGS["uz"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
