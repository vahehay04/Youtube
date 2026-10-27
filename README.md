# 🎵 Агент для детского YouTube-канала (Shorts)

Агент сам делает 2 коротких детских песенки в день и присылает их вам в Telegram.
Вы нажимаете **✅ Опубликовать** — и через несколько секунд ролик уходит на YouTube
с пометкой «Для детей» (агент ждёт нажатия до 2 часов после отправки ролика;
позже — подхватит при следующей проверке).
Всё работает на серверах GitHub, компьютер можно выключить.

```
 08:47 и 16:47 (МСК)          каждый час
┌──────────────────────┐     ┌───────────────────────────┐
│ 1. ИИ пишет песню    │     │ 4. Проверка кнопок в TG    │
│ 2. Рисует 5 сцен     │ ──▶ │ 5. ✅ → загрузка на YouTube │
│ 3. Музыка + монтаж   │ TG  │    ❌ → ролик удаляется     │
└──────────────────────┘     └───────────────────────────┘
```

Каждая песня чему-то учит (счёт, цвета, животные, режим дня), персонажи
свои — лисёнок **Pip**, зайка **Lulu** и черепашка **Bo**. Это важно:
YouTube не монетизирует «бессмысленный» шаблонный детский контент.

---

## Настройка (один раз, ~30–40 минут)

### Шаг 1. Telegram-бот

1. В Telegram откройте **@BotFather** → `/newbot` → придумайте имя.
   Он пришлёт **токен** вида `123456:ABC...` — это `TELEGRAM_BOT_TOKEN`.
2. Найдите своего бота и отправьте ему `/start`.
3. Откройте в браузере `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`
   и найдите `"chat":{"id": 123456789` — это число и есть `TELEGRAM_CHAT_ID`.

### Шаг 2. Cloudflare Workers AI (тексты песен и картинки — бесплатно)

1. Зарегистрируйтесь на https://dash.cloudflare.com (бесплатный тариф).
2. **Account ID**: на главной странице панели справа (или в адресе страницы после `dash.cloudflare.com/`) —
   это `CLOUDFLARE_ACCOUNT_ID`.
3. **My Profile → API Tokens → Create Token → шаблон «Workers AI»** → Continue → Create Token —
   это `CLOUDFLARE_API_TOKEN`.
4. Бесплатно — 10 000 «нейронов» в день; 2 ролика в день тратят около 1 000.

### Шаг 2б. OpenAI (по желанию, платно)

Нужен, только если в `config.yaml` указано `provider: openai`, или чтобы перерисовать персонажей и их позы.


1. Зайдите на https://platform.openai.com → **Billing** → пополните на $10–20.
2. **API keys** → *Create new secret key* — это `OPENAI_API_KEY`.
3. Для генерации картинок OpenAI может попросить подтвердить организацию
   (**Settings → Organization → Verify**) — сделайте это, иначе картинки не нарисуются.

### Шаг 3. ElevenLabs (музыка с вокалом)

1. Зарегистрируйтесь на https://elevenlabs.io и оформите платный тариф —
   Music API на бесплатном тарифе не работает. Проверьте актуальные цены
   и лимиты минут музыки на странице тарифов.
2. Профиль → **API Keys** → создайте ключ — это `ELEVENLABS_API_KEY`.

### Шаг 4. Доступ к YouTube-каналу

1. Откройте https://console.cloud.google.com → создайте проект (например, `shorts-agent`).
2. **APIs & Services → Library** → найдите **YouTube Data API v3** → *Enable*.
3. **APIs & Services → OAuth consent screen**:
   тип *External*, заполните название и почту, добавьте scope
   `https://www.googleapis.com/auth/youtube.upload`, добавьте себя в *Test users*.
4. ⚠️ Нажмите **Publish app** (статус *In production*). Иначе доступ
   будет слетать каждые 7 дней. Проверка Google для личного использования не нужна —
   при входе просто нажмите «Дополнительно → Перейти в приложение».
5. **Credentials → Create credentials → OAuth client ID** → тип **Desktop app** →
   скачайте JSON-файл (`client_secret_....json`).
6. На своём компьютере (нужен Python):
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_youtube_token.py путь/к/client_secret.json
   ```
   Войдите в аккаунт **с вашим каналом**. Скрипт покажет три значения:
   `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.
7. **Подайте заявку на аудит API**: https://support.google.com/youtube/contact/yt_api_form
   (*YouTube API Services – Audit and Quota Extension Form*). Пока аудит не пройден,
   YouTube делает все загруженные через API видео **приватными** — их можно
   вручную сделать публичными в YouTube Studio.

### Шаг 5. Секреты в GitHub

В репозитории: **Settings → Secrets and variables → Actions → New repository secret**.
Добавьте 7 секретов:

| Имя | Откуда |
|---|---|
| `TELEGRAM_BOT_TOKEN` | шаг 1 |
| `TELEGRAM_CHAT_ID` | шаг 1 |
| `CLOUDFLARE_ACCOUNT_ID` | шаг 2 |
| `CLOUDFLARE_API_TOKEN` | шаг 2 |
| `OPENAI_API_KEY` | шаг 2б (необязательно) |
| `ELEVENLABS_API_KEY` | шаг 3 |
| `YOUTUBE_CLIENT_ID` | шаг 4 |
| `YOUTUBE_CLIENT_SECRET` | шаг 4 |
| `YOUTUBE_REFRESH_TOKEN` | шаг 4 |

Никому не отправляйте эти значения (в том числе в чат с ИИ).

### Шаг 6. Первый запуск

1. **Actions → Draw characters (run once) → Run workflow.**
   В Telegram придут картинки персонажей и их позы (стоит, машет, танцует, прыгает) —
   в роликах они двигаются в такт музыке. Не нравятся — поправьте описание
   в `config.yaml` и запустите снова с галочкой «Перерисовать».
2. **Actions → Make new Short → Run workflow** — через 5–10 минут
   в Telegram придёт первый ролик с кнопками.
3. Нажмите ✅ — в течение часа ролик появится на канале
   (можно ускорить: **Actions → Publish approved → Run workflow**).

Дальше всё идёт само: 2 ролика в день по расписанию.

---

## Как менять настройки

Всё в файле **`config.yaml`** (редактируется прямо на сайте GitHub, значок ✏️):

- `language: en` → `ru` — песни на русском;
- `characters` — внешность персонажей;
- `topics` — темы песен;
- `music_style` — стиль музыки;
- расписание — в `.github/workflows/generate.yml` (строки `cron`, время в UTC = МСК − 3).

## Сколько это стоит (примерно)

- **GitHub Actions** — бесплатно (≈1 200 из 2 000 бесплатных минут в месяц для приватного репозитория).
- **Cloudflare Workers AI** — бесплатно (тексты и картинки сцен).
- **ElevenLabs** — по вашему тарифу; ≈60 песен по ~50 секунд в месяц.

## Важно про правила YouTube

- Все ролики загружаются с пометками **«Для детей»** и **«Создано с помощью ИИ»** — это обязательно.
- Не включайте полный автопилот без проверки: ролики со странными картинками
  или текстом — главная причина отказа в монетизации детских каналов.
- Отклоняйте всё, что выглядит странно, — новый ролик придёт по расписанию.

## Структура

```
agent/songwriter.py   текст песни и сценарий сцен (OpenAI)
agent/images.py       картинки сцен и персонажей (OpenAI Images)
agent/music.py        песня с вокалом (ElevenLabs Music)
agent/video.py        монтаж 1080×1920 (ffmpeg)
agent/telegram.py     бот для одобрения
agent/youtube.py      загрузка на YouTube
agent/generate.py     задача «сделать ролик»
agent/poll.py         задача «опубликовать одобренные»
state/                очередь и история роликов (обновляется автоматически)
```
