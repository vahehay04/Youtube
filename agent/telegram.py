"""Minimal Telegram Bot API client for the approval flow."""
from __future__ import annotations

import json
from pathlib import Path

import requests

from .common import env


def _url(method: str) -> str:
    return f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}"


class Conflict(RuntimeError):
    """Another process is reading this bot's updates at the same moment."""


def _call(method: str, **kwargs) -> dict:
    resp = requests.post(_url(method), timeout=120, **kwargs)
    data = resp.json()
    if not data.get("ok"):
        if data.get("error_code") == 409:
            raise Conflict(data.get("description", "conflict"))
        raise RuntimeError(f"Telegram {method}: {data}")
    return data["result"]


def chat_id() -> str:
    return env("TELEGRAM_CHAT_ID")


def send_message(text: str) -> dict:
    return _call("sendMessage", json={"chat_id": chat_id(), "text": text, "parse_mode": "HTML"})


def _keyboard(item_id: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Опубликовать", "callback_data": f"ok:{item_id}"},
        {"text": "❌ Отклонить", "callback_data": f"no:{item_id}"},
    ]]}


def restore_buttons(message_id: int, item_id: str, caption: str) -> None:
    try:
        _call("editMessageCaption", json={
            "chat_id": chat_id(), "message_id": message_id, "caption": caption[:1024],
            "parse_mode": "HTML", "reply_markup": _keyboard(item_id)})
    except RuntimeError:
        pass


def send_for_approval(video: Path, item_id: str, caption: str) -> dict:
    keyboard = _keyboard(item_id)
    with open(video, "rb") as f:
        return _call(
            "sendVideo",
            data={
                "chat_id": chat_id(),
                "caption": caption[:1024],
                "parse_mode": "HTML",
                "supports_streaming": "true",
                "reply_markup": json.dumps(keyboard),
            },
            files={"video": (video.name, f, "video/mp4")},
        )


def get_updates(offset: int | None, timeout: int = 0) -> list[dict]:
    """Never pass an offset that did not come from updates received in THIS run:
    Telegram deletes every update with a smaller id."""
    body = {"timeout": timeout, "allowed_updates": ["callback_query", "message"]}
    if offset:
        body["offset"] = offset
    return _call("getUpdates", json=body)


def diagnostics() -> str:
    me = _call("getMe", json={})
    hook = _call("getWebhookInfo", json={})
    return (f"бот @{me.get('username')}, webhook: {hook.get('url') or 'нет'}, "
            f"ожидающих обновлений по данным Telegram: {hook.get('pending_update_count')}")


def answer_callback(callback_id: str, text: str) -> None:
    try:
        _call("answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})
    except RuntimeError:
        pass  # callbacks older than ~15 min can no longer be answered; that's fine


def update_caption(message_id: int, caption: str) -> None:
    try:
        _call("editMessageCaption", json={
            "chat_id": chat_id(), "message_id": message_id, "caption": caption[:1024],
            "parse_mode": "HTML", "reply_markup": {"inline_keyboard": []},
        })
    except RuntimeError:
        pass


def download_file(file_id: str, out_path: Path) -> Path:
    info = _call("getFile", json={"file_id": file_id})
    url = f"https://api.telegram.org/file/bot{env('TELEGRAM_BOT_TOKEN')}/{info['file_path']}"
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return out_path
