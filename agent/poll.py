"""Job 2: read button presses in Telegram; upload approved videos to YouTube.

Usage: python -m agent.poll
"""
from __future__ import annotations

import html
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import telegram, youtube
from .common import (delete_pending, load_config, load_history, load_pending, log,
                     read_offset, save_history, write_offset)


def _set_status(history: list[dict], item_id: str, **fields) -> None:
    for h in history:
        if h.get("id") == item_id:
            h.update(fields)
            return


def _handle(cfg: dict, history: list[dict], cq: dict) -> None:
    allowed = str(telegram.chat_id())
    chat = str(cq.get("message", {}).get("chat", {}).get("id"))
    if chat != allowed:
        telegram.answer_callback(cq["id"], "Нет доступа")
        return

    action, _, item_id = cq.get("data", "").partition(":")
    item = load_pending(item_id)
    if not item:
        telegram.answer_callback(cq["id"], "Уже обработано")
        return
    title = html.escape(item["title"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if action == "no":
        telegram.answer_callback(cq["id"], "Отклонено")
        telegram.update_caption(item["telegram_message_id"], f"❌ Отклонено: <b>{title}</b>")
        _set_status(history, item_id, status="rejected", decided=now)
        delete_pending(item_id)
        log(f"❌ {item_id} отклонён")
        return

    if action == "ok":
        telegram.answer_callback(cq["id"], "Публикую…")
        with tempfile.TemporaryDirectory() as tmp:
            mp4 = telegram.download_file(item["telegram_file_id"], Path(tmp) / f"{item_id}.mp4")
            video_id = youtube.upload(cfg, item, mp4)
        link = f"https://youtube.com/shorts/{video_id}"
        telegram.update_caption(item["telegram_message_id"],
                                f"✅ Опубликовано: <b>{title}</b>\n{link}")
        _set_status(history, item_id, status="published", video_id=video_id, decided=now)
        delete_pending(item_id)
        log(f"✅ {item_id} опубликован: {link}")


def main() -> None:
    cfg = load_config()
    history = load_history()
    offset = read_offset()
    updates = telegram.get_updates(offset)
    log(f"Новых событий в Telegram: {len(updates)}")

    for upd in updates:
        offset = max(offset, upd["update_id"] + 1)
        cq = upd.get("callback_query")
        if cq:
            try:
                _handle(cfg, history, cq)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                telegram.send_message(
                    "⚠️ Не получилось опубликовать. Ролик остался в очереди — "
                    "нажмите «Опубликовать» ещё раз позже.\n"
                    f"<code>{html.escape(str(e))[:800]}</code>"
                )
        elif upd.get("message", {}).get("text", "").startswith("/start"):
            chat_id = upd["message"]["chat"]["id"]
            log(f"Получен /start из чата {chat_id}")

    write_offset(offset)
    save_history(history)


if __name__ == "__main__":
    main()
