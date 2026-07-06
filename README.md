# 🎬 Kino Bot v4.0 (PostgreSQL + Premium)

## Nima o'zgardi (v3.0 → v4.0)

| # | O'zgarish |
|---|-----------|
| 1 | 🐘 Barcha fayl-asosli "baza" (`kino/`, `azo.dat`, `favorites/` va h.k.) **PostgreSQL**'ga ko'chirildi — Railway'da konteyner qayta ishga tushganda ma'lumot yo'qolmaydi. |
| 2 | 👑 **Premium obuna tizimi** qo'shildi: premium userlar majburiy kanal obunasisiz kino ko'radi. |
| 3 | 💳 Admin premium **narxini** va **karta raqamini** o'zi belgilaydi. |
| 4 | 📸 User to'lov chekini (skrinshot) yuboradi → barcha adminlarga yuboriladi → admin ✅/❌ tugmasi bilan tasdiqlaydi. |
| 5 | 📆 Admin tasdiqlaganda **muddatni o'zi tanlaydi** (7 / 30 / 90 / 365 kun yoki ♾ cheksiz). |
| 6 | 🎁 Admin xohlagan foydalanuvchiga **qo'lda** ham premium bera oladi (to'lovsiz). |
| 7 | 💾 Yangi kino qo'shishda endi **"Saqlash / Bekor qilish"** preview bosqichi bor — metadata avval ko'rsatiladi, keyin admin tasdiqlagach bazaga yoziladi va foydalanuvchilarga bildirishnoma ketadi. |
| 8 | 🌍 UZ/RU ikkala tilda ham barcha yangi matnlar (premium, saqlash) tarjima qilingan, stikerli (emoji) qilib yozilgan. |

## Fayllar

```
kinobot/
├── main.py           # Botning asosiy logikasi (handlerlar)
├── db.py             # PostgreSQL bilan ishlaydigan barcha so'rovlar (asyncpg)
├── lang.py           # UZ/RU matnlar lug'ati
├── requirements.txt  # Python kutubxonalari
├── .env.example      # Muhit o'zgaruvchilari namunasi
└── Procfile          # Railway/Heroku uchun ishga tushirish buyrug'i
```

## Railway'da deploy qilish

1. **Yangi loyiha yarating** → GitHub repo'ni ulang (yoki fayllarni to'g'ridan-to'g'ri yuklang).
2. **PostgreSQL plugin qo'shing**: loyiha ichida "+ New" → "Database" → "Add PostgreSQL".
   - Railway avtomatik ravishda `DATABASE_URL` degan environment variable yaratadi va uni botga bog'laydi (agar bitta loyiha ichida bo'lsa, "Variable reference" orqali ulang: `${{Postgres.DATABASE_URL}}`).
3. **Environment Variables** bo'limiga qo'shing:
   - `BOT_TOKEN` — @BotFather'dan olingan token
   - `OWNER_ID` — sizning Telegram ID raqamingiz
4. **Deploy** tugmasini bosing. Bot birinchi ishga tushganda barcha jadvallarni (`users`, `kino`, `premium_requests` va h.k.) o'zi avtomatik yaratadi — qo'shimcha SQL skript ishga tushirish shart emas.
5. Bot loglarida `✅ Bot tayyor! Polling boshlandi...` yozuvini ko'rsangiz — hammasi ishlayapti.

## Lokal (o'z kompyuteringizda) ishga tushirish

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env faylini oching va BOT_TOKEN, OWNER_ID, DATABASE_URL qiymatlarini kiriting
# (lokal PostgreSQL kerak bo'ladi — masalan Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pass postgres)

python main.py
```

## Premium tizimi qanday ishlaydi

**Admin tomonidan sozlash** (Admin panel → 👑 Premium):
1. 💰 Narxni belgilash (so'mda)
2. 💳 Karta raqami va egasining F.I.Sh. kiritish

**Foydalanuvchi tomonidan sotib olish**:
1. Bosh menyudan **👑 Premium** tugmasini bosadi
2. **🛒 Premium sotib olish** tugmasini bosadi → karta raqami va narx ko'rsatiladi
3. To'lovni amalga oshirib, chek skrinshotini botga yuboradi
4. Skrinshot barcha adminlarga ✅/❌ tugmalari bilan yuboriladi
5. Admin ✅ bossa — muddatni tanlaydi (7/30/90/365/♾ kun) → foydalanuvchiga premium avtomatik beriladi va u xabar oladi

**Admin qo'lda premium berish**:
- Admin panel → 👑 Premium → 🎁 Foydalanuvchiga premium berish → ID kiritiladi → muddat tanlanadi

Premium faol bo'lgan foydalanuvchilar `joinchat()` funksiyasida avtomatik ravishda majburiy obuna tekshiruvidan o'tkazib yuboriladi.

## Muhim eslatmalar

- `python-telegram-bot==21.4` versiyasi ishlatilgan — kelajakda yangilashda API o'zgarishlarini tekshiring.
- Bot to'liq **async** (asyncpg) ishlaydi, shuning uchun ma'lumotlar bazasi so'rovlari bot javobini bloklamaydi.
- `OWNER_ID` doim avtomatik admin hisoblanadi, uni adminlar ro'yxatidan o'chirib bo'lmaydi.
- Fayl-asosli eski ma'lumotlaringiz (agar mavjud bo'lsa: `kino/`, `azo.dat`, `favorites/` va h.k.) avtomatik import qilinmaydi — agar eski ma'lumotlarni ko'chirish kerak bo'lsa, alohida migratsiya skripti kerak bo'ladi (buyurtma qilsangiz tayyorlab beraman).
