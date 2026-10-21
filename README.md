# Olimpiada Telegram Bot (PostgreSQL + Railway)

## Imkoniyatlar
**O'quvchi**
- Ro'yxatdan o'tish: ism-familya → tug'ilgan sana (yil.oy.kun) → maktab raqami → sinf → fan → daraja. Keyin shaxsiy kabinet ochiladi.
- Fanlar: Ingliz tili (Starter, Beginner, Elementary, Intermediate, Advanced), Matematika (1–11-sinf), Mental arifmetika, IT (Frontend, Backend Python).
- Olimpiada vaqti kelganda bot xabar yuboradi; test tanlangan fan va daraja bo'yicha beriladi (30 ta tasodifiy savol).
- Test admin belgilagan davomiylik tugagach avtomatik to'xtaydi; javob berilmagan savollar noto'g'ri hisoblanadi.

**Admin** (login/parol bilan kiradi)
- 📊 Statistika; ✅ topshirganlar, 🔄 ishlayotganlar, ⏳ topshirmaganlar ro'yxati.
- 🕒 Boshlanish vaqti (Asia/Tashkent) va davomiylikni belgilash; ⏱ davomiylikni o'zgartirish (ishlayotgan testlar muddati ham yangilanadi).
- 📥 Excel: Natijalar (foiz, sarflangan vaqt, fan/daraja ichida o'rin), Barcha o'quvchilar, Ishlayotganlar, Topshirmaganlar.
- Ro'yxatdan o'tishni yoqish/o'chirish.

Test holati bazada saqlanadi, shuning uchun bot qayta ishga tushsa ham o'quvchining testi yo'qolmaydi.

## Railway'ga joylash
1. Loyihani GitHub'ga yuklang (`.env` yuklanmasin, `.gitignore` buni oldini oladi).
2. Railway → **New Project** → **Deploy from GitHub repo** → shu repozitoriyani tanlang.
3. Shu loyiha ichida **+ New** → **Database** → **Add PostgreSQL**.
4. Bot xizmatining **Variables** bo'limiga qo'shing:
   - `BOT_TOKEN` — BotFather tokeni
   - `ADMIN_LOGIN` — masalan `admin`
   - `ADMIN_PASSWORD` — kuchli parol (standart parol bilan bot ishga tushmaydi)
   - `DATABASE_URL` — qiymat: `${{Postgres.DATABASE_URL}}` (Postgres xizmati nomi boshqacha bo'lsa, shuni yozing)
   - `TIMEZONE` — `Asia/Tashkent` (ixtiyoriy)
5. Deploy tugagach **Deploy Logs** da «Olimpiada bot ishga tushdi.» chiqishi kerak. Jadvallar birinchi ishga tushganda o'zi yaratiladi.
6. **Muhim:** xizmat faqat **1 ta nusxada** ishlashi kerak (replicas = 1). Bot polling rejimida ishlaydi, ikkita nusxa bir-biriga xalaqit beradi. Bu xizmatga domen (Generate Domain) kerak emas.

## Kompyuterda sinash
1. Python 3.11+ o'rnating, `.env.example` dan `.env` yarating va to'ldiring.
2. `DATABASE_URL` uchun o'zingizdagi PostgreSQL manzilini yozing (yoki Railway Postgres xizmatidagi *public* manzilni).
3. `run_windows.bat` ni ishga tushiring yoki:
   ```
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

## Vaqt belgilash
Admin panel → «🕒 Olimpiada vaqtini belgilash»: avval boshlanish vaqti (`YYYY-MM-DD HH:MM`, masalan `2026-10-20 17:00`), keyin davomiylik (daqiqada). Testni faqat boshlanish vaqtidan «boshlanish + davomiylik» gacha boshlash mumkin (masalan, 08:00 va 60 daqiqa bo'lsa 08:00–09:00). Har bir o'quvchi boshlagan paytidan to'liq davomiylikni oladi: 08:40 da boshlagan o'quvchi 09:40 gacha ishlaydi. Soat 09:00 dan keyin testni boshlab bo'lmaydi. Mental arifmetikada har bir o'quvchiga boshlagan paytidan 10 daqiqa beriladi.

## Savollar
- `tests/questions.json` — ingliz tili: Starter (30 ta), Beginner, Elementary, Intermediate, Advanced (20 tadan). Izoh: `tests/INGLIZ_TILI_IZOH.txt`.
- `tests/matematika.json` — 1–11-sinf savollari (asl hujjatdan olingan, kalitlar qayta hisoblab tekshirilgan; tuzatishlar `tests/MATEMATIKA_TUZATISHLAR.txt` da).
- `tests/mental.json` — Mental arifmetika: 120 ta misol (`tests/mental_asl/megabrain_misollar 2.pdf`, 1 xonali oddiy ±). Misollar ketma-ket chiqadi, o'quvchi javobni raqam bilan yozadi. Test boshlangandan keyin 10 daqiqa beriladi, vaqt tugasa qaysi misolda bo'lsa ham test yakunlanadi. Natija foizda emas, ballda: har bir to'g'ri javob 1 ball (o'rin ball bo'yicha, teng bo'lsa kam vaqt sarflagan yuqorida).
- `tests/it.json` — IT: Frontend (HTML, CSS) va Backend Python, 20 tadan oson test.
Savollarni o'zgartirgach, ilovani qayta deploy qiling.

## Xavfsizlik
- `.env` va tokenlarni hech kimga yubormang.
- Admin parolini 5 marta noto'g'ri kiritgan foydalanuvchi 10 daqiqaga bloklanadi.
