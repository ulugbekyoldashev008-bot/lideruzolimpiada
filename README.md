# Olimpiada Telegram boti

O‘quvchilarni ro‘yxatdan o‘tkazish, vaqtli olimpiada o‘tkazish, testlarni avtomatik baholash va Excel hisobot olish uchun tayyor Telegram bot.

## Imkoniyatlar

- Bitta Telegram akkauntdan bir marta ro‘yxatdan o‘tish
- Bitta Telegram akkaunt ichida bir nechta qatnashchini ro‘yxatdan o‘tkazish va kerakli profil nomidan test yechish
- Telegram kanalga majburiy obunani avtomatik tekshirish
- Instagram sahifasiga obuna bo‘lish uchun havola
- Ism-familiya, telefon, viloyat, tuman, tug‘ilgan sana va avtomatik yosh
- Fan va darajani tugmalar orqali tanlash
- Qatnashchi ID, login va xavfsiz tasodifiy parol
- Admin tomonidan fan, daraja va savol qo‘shish
- A/B/C/D, matn va rasm javob turlari
- A/B/C/D testlarda to‘g‘ri javob kaliti va avtomatik baholash
- To‘g‘ri, noto‘g‘ri, umumiy ball va foizni avtomatik hisoblash
- Toshkent vaqti bo‘yicha boshlanish sanasi va davomiylik
- Admin vaqtni bekor qilsa test barcha foydalanuvchilar uchun yopiladi va yangi vaqt belgilanguncha hech kim test yecha olmaydi
- Admin testni to‘xtatsa ishlayotgan qatnashchilar avtomatik yakunlanadi
- Har bir javobning darhol bazaga saqlanishi
- Bot yopilib qolsa qolgan savoldan davom etish
- Vaqt tugaganda avtomatik yakunlash
- Kalitli testlarni avtomatik, matn va rasmli javoblarni admin tomonidan baholash
- Natijani yashirish/e’lon qilish va TOP-20 reyting
- Avtomatik test tugagach o‘quvchi o‘z foizini darhol ko‘radi
- Qatnashchini bloklash/qayta ochish
- 24 soat va 1 soat oldin avtomatik eslatma
- Qatnashchilar va barcha javoblarni `.xlsx` shaklida yuklab olish
- Admin harakatlari tarixi
- SQLite (lokal) va PostgreSQL (Railway) qo‘llab-quvvatlanadi
- Birinchi ishga tushishda tayyor fan va darajalar avtomatik qo‘shiladi
- Ingliz tili Starter, Beginner, Elementary, Pre-Intermediate va Intermediate darajalariga 20 tadan tayyor test
- Rus tili A1, A2 va B1 darajalariga 20 tadan tayyor test
- IT fanidan HTML CSS uchun 40 ta, JavaScript, Vue va Python uchun 30 tadan tayyor test
- Kompyuter fanidan Word, Excel va PowerPoint uchun 30 tadan tayyor test; dastur bo‘limlari ruscha nomlangan
- Matematika fanidan 4-sinfdan 11-sinfgacha har bir sinf uchun 20 tadan mos test
- Arab tili A1 va A2 darajalariga 30 tadan tayyor test
- Mental arifmetika uchun 3 ta kategoriya, har birida 100 tadan yozma misol, 10 daqiqalik alohida rejim va avtomatik raqamli tekshiruv

## Avtomatik qo‘shiladigan fan va darajalar

- **Ingliz tili:** Starter, Beginner, Elementary, Pre-Intermediate, Intermediate, Upper-Intermediate, Advanced, IELTS
- **Rus tili:** A1, A2, B1
- **Koreys tili:** Boshlang‘ich, O‘rta
- **Arab tili:** A1, A2, B1
- **Matematika:** 4-sinf, 5-sinf, 6-sinf, 7-sinf, 8-sinf, 9-sinf, 10-sinf, 11-sinf
- **Mental arifmetika:** 1-xonali A, 2-xonali B, 2-xonali C
- **IT:** HTML, HTML CSS, HTML CSS JS, JavaScript, Vue, React, Python
- **Kompyuter:** Word, Excel, PowerPoint

Bot qayta ishga tushganda mavjud fanlar va tayyor testlar takrorlanmaydi; faqat yetishmayotgan ma’lumotlar qo‘shiladi. Tayyor Ingliz, Rus tili, IT, Kompyuter, Matematika, Arab tili va Mental arifmetika testlari javob kaliti bilan avtomatik biriktiriladi.

## 1. Telegram bot ochish

1. Telegram’da `@BotFather` ni oching.
2. `/newbot` yuboring, nom va username tanlang.
3. Berilgan tokenni nusxalang.
4. Telegram ID olish uchun `@userinfobot` ga kiring va o‘z raqamli ID’ingizni oling.

## 2. Windows’da ishga tushirish

1. Kompyuterga Python 3.11 yoki 3.12 o‘rnating. O‘rnatishda **Add Python to PATH** ni belgilang.
2. ZIP faylni oching.
3. `.env.example` faylidan nusxa olib, nomini `.env` qiling.
4. `.env` ichida quyidagilarni o‘zgartiring:

```env
BOT_TOKEN=BotFather_bergan_token
ADMIN_IDS=sizning_telegram_id
DATABASE_URL=sqlite+aiosqlite:///olympiad.db
TIMEZONE=Asia/Tashkent
TELEGRAM_CHANNEL=@kanal_username
TELEGRAM_CHANNEL_URL=https://t.me/kanal_username
INSTAGRAM_URL=https://instagram.com/sahifa_username
```

5. `run.bat` faylini ikki marta bosing.

Yoki PowerShell’da:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.main
```

## 3. Railway’ga joylash

1. Loyihani GitHub’ga yuklang.
2. Railway’da **New Project → Deploy from GitHub** ni tanlang.
3. Railway loyihasiga **PostgreSQL** qo‘shing. Railway `DATABASE_URL` ni avtomatik beradi.
4. Deploy qilingan bot servisining **Variables** bo‘limiga kiriting:

```env
BOT_TOKEN=BotFather_bergan_token
ADMIN_IDS=sizning_telegram_id
TIMEZONE=Asia/Tashkent
TELEGRAM_CHANNEL=@kanal_username
TELEGRAM_CHANNEL_URL=https://t.me/kanal_username
INSTAGRAM_URL=https://instagram.com/sahifa_username
```

5. Agar kanalingiz public bo‘lsa `TELEGRAM_CHANNEL=@kanal_username` yetadi. Agar kanal private bo‘lsa, bot obunani tekshirishi uchun kanal ID kerak bo‘ladi.
6. Botni Telegram kanalingizga **admin** qilib qo‘shing. Aks holda Telegram obunani tekshirish ishlamaydi.
7. Railway deploy tugagach, **Deploy Logs** ichida xato yo‘qligini tekshiring va Telegramda botga `/start` yuboring.

`railway.json` botni `python -m app.main` bilan ishga tushiradi. Railway sog‘lom ishlayotganini ko‘rishi uchun bot `/health` endpointini ham ochadi.

Majburiy Telegram obunasini tekshirish ishlashi uchun botni ko‘rsatilgan Telegram kanalga **admin** qilib qo‘shing. Botda Instagram va Telegram havolalari birga ko‘rinadi. Foydalanuvchi **Obuna bo‘ldim** tugmasini bosganda Telegram kanal obunasi avtomatik tekshiriladi. Telegramga obuna bo‘lmagan bo‘lsa, bot menyusi ochilmaydi. Instagram havolasi esa obuna bo‘lish uchun ko‘rsatiladi va alohida tekshirilmaydi.

## 4. Birinchi sozlash

1. Botga `/start` yuboring.
2. **Admin** tugmasini bosing.
3. Avval fanlarni, keyin har bir fan darajalarini qo‘shing.
4. Yangi A/B/C/D savol qo‘shsangiz, variantlardan to‘g‘ri javobni ham tanlang. Matn va rasm javoblari qo‘lda baholanadi.
5. Olimpiada boshlanish vaqti hamda davomiyligini belgilang.
6. Qatnashchilar uchun ro‘yxatdan o‘tishni ochiq qoldiring.
7. A/B/C/D testlar avtomatik tekshiriladi va o‘quvchiga foizi darhol ko‘rinadi. Matn va rasm javoblari bo‘lsa, **Javoblarni tekshirish** bo‘limida ball qo‘ying.
8. Mental arifmetika savollarini **Matn** turida qo‘shing. Bot to‘g‘ri sonli javobni ham so‘raydi; 100 ta misol to‘liq kiritilgach, o‘quvchiga 10 daqiqalik rejim ochiladi.
9. Vaqtni butunlay bekor qilish uchun **Vaqtni bekor qilish** tugmasini bosing. Bu eski urinishlarni tozalaydi va yangi vaqt belgilanguncha testni yopadi.
10. Test jarayonini majburiy to‘xtatish uchun **Testni to‘xtatish** tugmasini bosing. Ishlayotgan qatnashchilar yakunlanadi.
11. Tayyor natijalarni umumiy reytingda ko‘rsatish uchun **Natijani e’lon qilish** tugmasini bosing.
12. **Excel yuklash** hisobotida ism familya, fan, daraja/sinf, to‘g‘ri topgani, foizi va nechta daqiqada ishlagani chiqadi.

## Bir telefondan bir nechta qatnashchi

Foydalanuvchi birinchi ro‘yxatdan o‘tgandan keyin **Yangi qatnashchi qo‘shish** tugmasi orqali boshqa odamni ham ro‘yxatdan o‘tkazishi mumkin. **Qatnashchilarim** bo‘limida qaysi qatnashchi faol ekanini tanlaydi. Test, natija va profil ma’lumotlari aynan tanlangan qatnashchi nomidan ishlaydi.

## Muhim xavfsizlik

- `.env` faylini GitHub yoki boshqa joyga yubormang.
- `ADMIN_IDS` ga bir nechta admin qo‘shish mumkin: `123456789,987654321`.
- Admin tugmasi hammaga ko‘rinsa ham, faqat ro‘yxatdagi Telegram ID’lar panelga kira oladi.
- Railway’da PostgreSQL zaxira nusxalarini yoqib qo‘yish tavsiya etiladi.
