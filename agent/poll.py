"""Reads button presses in Telegram and uploads approved videos to YouTube.

Usage:
    python -m agent.poll                 # check once (scheduled backup)
    python -m agent.poll --listen 120    # wait up to 120 min, react within seconds
"""
from __future__ import annotations

import argparse
import html
import os
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import telegram, youtube
from .common import (PENDING_DIR, commit_state, delete_pending, load_config, load_history,
                     load_pending, log, migrate_history, save_item, sync_state)


def _entry(item_id: str, item: dict) -> dict:
    for h in load_history():
        if h.get("id") == item_id:
            return h
    return {"id": item_id, "title": item.get("title"), "topic": item.get("topic"),
            "created": item.get("created")}


def _pending_ids() -> list[str]:
    return sorted(p.stem for p in PENDING_DIR.glob("*.json"))


def handle(cfg: dict, cq: dict) -> None:
    allowed = str(telegram.chat_id())
    chat = str(cq.get("message", {}).get("chat", {}).get("id"))
    if chat != allowed:
        telegram.answer_callback(cq["id"], "Нет доступа")
        return

    action, _, item_id = cq.get("data", "").partition(":")
    sync_state()  # make sure another job hasn't handled it already
    item = load_pending(item_id)
    if not item:
        telegram.answer_callback(cq["id"], "Уже обработано")
        return
    title = html.escape(item["title"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = _entry(item_id, item)

    if action == "no":
        telegram.answer_callback(cq["id"], "Отклонено")
        telegram.update_caption(item["telegram_message_id"], f"❌ Отклонено: <b>{title}</b>")
        entry.update(status="rejected", decided=now)
        save_item(entry)
        delete_pending(item_id)
        commit_state(f"state: rejected {item_id}")
        log(f"❌ {item_id} отклонён")
        return

    if action == "ok":
        telegram.answer_callback(cq["id"], "Публикую… ⏳")
        telegram.update_caption(item["telegram_message_id"], f"⏳ Публикую: <b>{title}</b>")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mp4 = telegram.download_file(item["telegram_file_id"], Path(tmp) / f"{item_id}.mp4")
                video_id = youtube.upload(cfg, item, mp4)
        except Exception:
            # put the buttons back so the user can try again
            telegram.restore_buttons(item["telegram_message_id"], item_id,
                                     f"⚠️ Не удалось опубликовать: <b>{title}</b>\nНажмите ещё раз.")
            raise
        link = f"https://youtube.com/shorts/{video_id}"
        telegram.update_caption(item["telegram_message_id"],
                                f"✅ Опубликовано: <b>{title}</b>\n{link}")
        entry.update(status="published", video_id=video_id, decided=now)
        save_item(entry)
        delete_pending(item_id)
        commit_state(f"state: published {item_id}")
        log(f"✅ {item_id} опубликован: {link}")


def process(cfg: dict, updates: list[dict]) -> None:
    for upd in updates:
        cq = upd.get("callback_query")
        if not cq:
            continue
        log(f"   кнопка {cq.get('data')}")
        try:
            handle(cfg, cq)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            telegram.send_message(
                "⚠️ Не получилось опубликовать — нажмите «Опубликовать» ещё раз.\n"
                f"<code>{html.escape(str(e))[:800]}</code>")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=float, default=0,
                        help="minutes to keep waiting for presses while videos are pending")
    args = parser.parse_args()
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        log("Секреты ещё не настроены — пропускаю.")
        return

    cfg = load_config()
    migrate_history()
    commit_state("state: migrate history format")
    log("Telegram: " + telegram.diagnostics())

    deadline = time.time() + args.listen * 60
    offset = None  # only ever taken from updates received in this run
    while True:
        try:
            wait = 0 if not args.listen else int(min(50, max(1, deadline - time.time())))
            updates = telegram.get_updates(offset, timeout=wait)
        except telegram.Conflict:
            if not args.listen:
                log("Кнопки сейчас обрабатывает другой запуск агента — выхожу.")
                return
            time.sleep(15)
            continue
        if updates:
            log(f"Новых событий: {len(updates)}; в очереди: {_pending_ids()}")
            process(cfg, updates)
            offset = max(u["update_id"] for u in updates) + 1
            telegram.get_updates(offset)  # confirm what was handled
        if not args.listen or time.time() >= deadline:
            break
        sync_state()  # pick up videos added by other jobs
        if not _pending_ids():
            log("Очередь пуста — завершаю ожидание.")
            break
    log(f"Готово. В очереди: {_pending_ids()}")


if __name__ == "__main__":
    main()
