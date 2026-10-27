"""Checks that every secret is set and works. Publishes nothing.

Usage: python -m agent.check
"""
from __future__ import annotations

import os

import requests

from .common import load_config

OK, BAD = "✅", "❌"
results: list[str] = []


def add(ok: bool, name: str, detail: str = "") -> None:
    results.append(f"{OK if ok else BAD} {name}" + (f" — {detail}" if detail else ""))


def get(name: str) -> str:
    return os.environ.get(name, "").strip()


def check_telegram() -> None:
    token, chat = get("TELEGRAM_BOT_TOKEN"), get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        add(False, "Telegram", "не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=30).json()
    if not r.get("ok"):
        add(False, "Telegram", "неверный TELEGRAM_BOT_TOKEN")
        return
    add(True, "Telegram-бот", "@" + r["result"]["username"])


def check_openai(cfg: dict) -> None:
    key = get("OPENAI_API_KEY")
    if not key:
        add(False, "OpenAI", "не задан OPENAI_API_KEY")
        return
    h = {"Authorization": f"Bearer {key}"}
    r = requests.get("https://api.openai.com/v1/models", headers=h, timeout=30)
    if r.status_code == 401:
        add(False, "OpenAI", "неверный ключ")
        return
    if r.status_code != 200:
        add(False, "OpenAI", f"ошибка {r.status_code}: {r.text[:200]}")
        return
    ids = {m["id"] for m in r.json().get("data", [])}
    for model in (cfg["models"]["text"], cfg["models"]["image"]):
        add(model in ids, f"OpenAI модель {model}",
            "доступна" if model in ids else "нет доступа (для картинок нужна верификация организации)")
    # Tiny paid request to make sure billing works (~$0.0001)
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=h, timeout=60, json={
        "model": cfg["models"]["text"], "max_tokens": 5,
        "messages": [{"role": "user", "content": "Say OK"}]})
    if r.status_code == 200:
        add(True, "OpenAI баланс", "запрос прошёл")
    elif r.status_code == 429:
        add(False, "OpenAI баланс", "нет средств — пополните Billing")
    else:
        add(False, "OpenAI баланс", f"ошибка {r.status_code}: {r.text[:200]}")


def check_cloudflare(cfg: dict) -> None:
    acc, tok = get("CLOUDFLARE_ACCOUNT_ID"), get("CLOUDFLARE_API_TOKEN")
    if not acc or not tok:
        add(False, "Cloudflare", "не заданы CLOUDFLARE_ACCOUNT_ID или CLOUDFLARE_API_TOKEN")
        return
    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/"
    h = {"Authorization": f"Bearer {tok}"}
    r = requests.post(base + cfg["models"]["text"], headers=h, timeout=60,
                      json={"messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5})
    if r.status_code == 200 and r.json().get("success"):
        add(True, "Cloudflare тексты", cfg["models"]["text"].split("/")[-1])
    else:
        hint = {401: "неверный API-токен", 403: "у токена нет права Workers AI",
                404: "неверный Account ID"}.get(r.status_code, "")
        add(False, "Cloudflare тексты", f"ошибка {r.status_code} {hint}: {r.text[:200]}")
        return
    from . import ai
    try:
        img = ai.image(cfg, "a cute small cartoon sun, simple, soft colors", 1024, 1024)
        add(len(img) > 1000, "Cloudflare картинки", cfg["models"]["image"].split("/")[-1])
    except Exception as e:  # noqa: BLE001
        add(False, "Cloudflare картинки", str(e)[:250])


def check_elevenlabs() -> None:
    key = get("ELEVENLABS_API_KEY")
    if not key:
        add(False, "ElevenLabs", "не задан ELEVENLABS_API_KEY")
        return
    r = requests.get("https://api.elevenlabs.io/v1/user/subscription",
                     headers={"xi-api-key": key}, timeout=30)
    if r.status_code == 401:
        add(False, "ElevenLabs", "неверный ключ (или у ключа нет права user_read)")
        return
    if r.status_code != 200:
        add(False, "ElevenLabs", f"ошибка {r.status_code}: {r.text[:200]}")
        return
    sub = r.json()
    tier = sub.get("tier", "?")
    left = sub.get("character_limit", 0) - sub.get("character_count", 0)
    add(tier != "free", "ElevenLabs тариф",
        f"{tier}, осталось кредитов: {left}" + (" — для музыки нужен платный тариф" if tier == "free" else ""))


def check_youtube() -> None:
    names = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [n for n in names if not get(n)]
    if missing:
        add(False, "YouTube", "не заданы: " + ", ".join(missing))
        return
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": get("YOUTUBE_CLIENT_ID"), "client_secret": get("YOUTUBE_CLIENT_SECRET"),
        "refresh_token": get("YOUTUBE_REFRESH_TOKEN"), "grant_type": "refresh_token"})
    if r.status_code == 200:
        scope = r.json().get("scope", "")
        add("youtube.upload" in scope, "YouTube доступ",
            "токен рабочий" if "youtube.upload" in scope else f"нет права youtube.upload ({scope})")
    else:
        err = r.json().get("error", r.text[:200])
        hint = {"invalid_client": "неверный CLIENT_ID или CLIENT_SECRET",
                "invalid_grant": "refresh token недействителен — получите новый в OAuth Playground",
                "unauthorized_client": "токен получен с другим Client ID"}.get(err, err)
        add(False, "YouTube доступ", hint)


def main() -> None:
    cfg = load_config()
    from . import ai
    text_check = (lambda: check_cloudflare(cfg)) if ai.provider(cfg) == "cloudflare" else (lambda: check_openai(cfg))
    for fn in (check_telegram, text_check, check_elevenlabs, check_youtube):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            add(False, getattr(fn, "__name__", "check"), str(e)[:200])
    report = "🔧 Проверка настроек агента\n\n" + "\n".join(results)
    print(report)
    token, chat = get("TELEGRAM_BOT_TOKEN"), get("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=30,
                              json={"chat_id": chat, "text": report}).json()
            print("Отчёт отправлен в Telegram" if r.get("ok")
                  else f"❌ Не удалось написать в Telegram: проверьте TELEGRAM_CHAT_ID и что вы нажали /start у бота ({r.get('description')})")
        except Exception as e:  # noqa: BLE001
            print(f"Telegram: {e}")
    if any(line.startswith(BAD) for line in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
