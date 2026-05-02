# Telegram World Facts Bot

Автономний Python-агент для публікації 4–5 постів на день у Telegram-канал.

## Що робить система

1. Збирає сирі ідеї та факти з безкоштовних джерел:
   - Reddit (`r/todayilearned`, `r/showerthoughts`) через `praw`
   - Wikimedia random pages через `requests`
2. Обробляє факт через Google Gemini:
   - перевірка правдоподібності
   - короткий текст українською
   - емодзі та хештеги
   - англомовний image prompt
3. Генерує обкладинку через безкоштовний HTTP API:
   - Pollinations.ai
4. Публікує пост у Telegram як photo + caption
5. Публікує той самий медіа-файл в Instagram через Graph API
6. Логує публікацію в Google Sheets
7. Запобігає повторній публікації через `data/used_facts.txt`

---

## Структура проєкту

```text
app/
  __init__.py
  config.py
  fact_sources.py
  gemini_processor.py
  main.py
  media_generator.py
  models.py
  sheets_logger.py
  telegram_publisher.py
  utils.py
requirements.txt
.env.example
README.md
```

---

## Встановлення

### 1. Створіть віртуальне середовище

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Встановіть залежності

```bash
pip install -r requirements.txt
```

### 3. Скопіюйте змінні середовища

```bash
cp .env.example .env
```

Заповніть `.env`:

- `TELEGRAM_BOT_TOKEN` — токен бота від BotFather
- `TELEGRAM_CHANNEL_ID` — @username каналу або числовий ID
- `GEMINI_API_KEY` — ключ Google Gemini
- `GOOGLE_SHEETS_ID` — ID таблиці Google Sheets
- `GOOGLE_SERVICE_ACCOUNT_FILE` — шлях до JSON файлу сервісного акаунта
- `GOOGLE_SERVICE_ACCOUNT_JSON` — JSON ключ сервісного акаунта як один рядок
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — для Reddit API
- `INSTAGRAM_ACCESS_TOKEN` — access token для Instagram Graph API
- `INSTAGRAM_USER_ID` — Instagram Business/Creator user ID
- `INSTAGRAM_IMAGE_URL_BASE` — публічний base URL, де лежать зображення
- `POSTS_PER_DAY` — кількість постів на день
- `TIMEZONE` — часовий пояс

---

## Google Sheets service account

### 1. Створіть сервісний акаунт
У Google Cloud Console:
- створіть проєкт
- увімкніть Google Sheets API
- створіть service account
- згенеруйте JSON key

### 2. Надішліть файл у проєкт
Збережіть JSON як, наприклад:

```text
service_account.json
```

### 3. Поділіться таблицею з service account email
Відкрийте Google Sheet і додайте email сервісного акаунта як редактора.

### 4. Вкажіть ID таблиці
У URL таблиці:
`https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

Скопіюйте `<SHEET_ID>` в `GOOGLE_SHEETS_ID`.

---

## Запуск вручну

```bash
python -m app.main
```

Або:

```bash
python app/main.py
```

---

## Scheduling

### Варіант 1 — GitHub Actions
Рекомендовано, якщо потрібно запускати постинг без вашого ноутбука.

#### Як це працює
- GitHub Actions запускає workflow кожну годину.
- Скрипт `github_actions_publish.py` сам перевіряє, чи це одна з потрібних годин:
  - `23:00`
  - `03:00`
  - `07:00`
  - `11:00`
  - `15:00`
  - `19:00`
- Якщо час не підходить, публікація пропускається.
- Якщо час підходить, бот публікує пост.

#### Що потрібно налаштувати
Додайте Secrets у GitHub repository:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `GEMINI_API_KEY`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`
- `INSTAGRAM_IMAGE_URL_BASE`

Якщо GitHub Actions повертає `Telegram API error: ... 404 Not Found`, це майже завжди означає, що `TELEGRAM_BOT_TOKEN` у Secrets неправильний, застарілий або порожній. Оновіть саме Secret у GitHub, а не код у репозиторії.

#### Workflow
Файл:
```text
.github/workflows/worldfacts_schedule.yml
```

#### Запуск вручну
У GitHub Actions можна натиснути `Run workflow`.

---

### Варіант 2 — локальний launchd / cron
Підходить тільки якщо Mac постійно увімкнений.

#### launchd
- `launchd/com.worldfacts.bot.plist`
- `install_launchagent.command`

#### schedule всередині Python
`run_scheduler.py`

Ці варіанти не підходять, якщо ноутбук вимкнений або спить.

### Рекомендація
Для продакшну використовуйте GitHub Actions.

---

## GitHub Actions secrets

Щоб запуск без Mac працював, додайте в GitHub repository settings → Secrets and variables → Actions:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `GEMINI_API_KEY`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`
- `INSTAGRAM_IMAGE_URL_BASE`

`GOOGLE_SERVICE_ACCOUNT_JSON` має містити повний JSON ключ сервісного акаунта в одному секреті.

---

## Deduplication

Система зберігає хеші вже використаних фактів у:

```text
data/used_facts.txt
```

Це не дає опублікувати один і той самий факт двічі.

---

## Основні файли для налаштування

- `app/config.py` — читання env-змінних
- `app/main.py` — головна оркестрація
- `app/fact_sources.py` — збір фактів
- `app/gemini_processor.py` — генерація тексту через Gemini
- `app/media_generator.py` — генерація фото
- `app/telegram_publisher.py` — публікація в Telegram
- `app/instagram_publisher.py` — публікація в Instagram через Graph API
- `app/sheets_logger.py` — логування в Google Sheets

---

## Важливі примітки

- Генерація відео не реалізована, бо free-tier для цього занадто обмежений.
- Поточний фокус — якісні зображення + сильний текст.
- Якщо Reddit API недоступний, система все одно може працювати на Wikimedia-джерелах.
- Якщо Gemini або Telegram недоступні, відповідний пост не буде опублікований, але помилка буде залогована.
- Якщо Instagram недоступний або не налаштований, Telegram-пост все одно буде опубліковано, а Instagram-спроба залогована як warning.

---

## Рекомендація для продакшну

Додайте:
- systemd service або cron
- rotation логів
- резервне джерело контенту
- періодичну перевірку доступності API
- додаткову модерацію контенту перед постингом
