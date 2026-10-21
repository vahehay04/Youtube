"""Job 2: read button presses in Telegram; upload approved videos to YouTube.

Usage: python -m agent.poll
"""
from __future__ import annotations

import html
import os
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import telegram, youtube
from .common import (PENDING_DIR, delete_pending, load_config, load_history, load_pending, log,
                     save_history, write_offset)


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
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        log("Секреты ещё не настроены — пропускаю.")
        return
    cfg = load_config()
    history = load_history()
    log("Telegram: " + telegram.diagnostics())
    # Read WITHOUT an offset: this never discards anything. Updates are confirmed
    # (deleted on Telegram's side) only after they have been handled, below.
    updates = telegram.get_updates(None)
    pending = sorted(p.stem for p in PENDING_DIR.glob("*.json"))
    log(f"Новых событий в Telegram: {len(updates)}; роликов в очереди: {len(pending)} {pending}")
    for upd in updates:
        cq = upd.get("callback_query")
        if cq:
            log(f"   кнопка {cq.get('data')} из чата {cq.get('message', {}).get('chat', {}).get('id')}")

    for upd in updates:
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

    if updates:
        last = max(u["update_id"] for u in updates)
        telegram.get_updates(last + 1)  # confirm handled updates
        write_offset(last + 1)  # kept for reference only
    save_history(history)


if __name__ == "__main__":
    main()
