"""Job 1: create a new Short and send it to Telegram for approval.

Usage: python -m agent.generate [--count N]
"""
from __future__ import annotations

import argparse
import html
import os
import random
import re
import string
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import images, music, telegram, video
from .common import ROOT, load_config, load_history, log, save_history, save_pending
from .songwriter import write_song


def _new_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"{stamp}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"


def _youtube_description(cfg: dict, song: dict) -> str:
    lyrics = "\n\n".join("\n".join(s["lines"]) for s in song["sections"])
    tags = " ".join("#" + re.sub(r"\W", "", t) for t in song.get("tags", [])[:3] if re.sub(r"\W", "", t))
    return (
        f"{song.get('description', '').strip()}\n\n"
        f"🎵 {song['title']}\n\n{lyrics}\n\n"
        f"{cfg['channel'].get('series_name', '')}\n"
        f"Animation and music created with AI tools, written and reviewed by a human.\n\n"
        f"#Shorts #KidsSongs {tags}"
    ).strip()


def make_one(cfg: dict, history: list[dict]) -> dict:
    song = write_song(cfg, history)
    item_id = _new_id()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pics = images.draw_scenes(cfg, song, work)
        audio = music.compose(cfg, song, work / "song.mp3")
        mp4 = video.build(cfg, song, pics, audio, work / f"{item_id}.mp4", ROOT)

        lyrics_preview = "\n".join(song["sections"][0]["lines"][:2])
        caption = (
            f"🎵 <b>{html.escape(song['title'])}</b>\n"
            f"Тема: {html.escape(song['topic'])}\n\n"
            f"<i>{html.escape(lyrics_preview)}</i>\n\n"
            f"Проверьте ролик: публиковать?"
        )
        msg = telegram.send_for_approval(mp4, item_id, caption)

    item = {
        "id": item_id,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "topic": song["topic"],
        "title": song["title"],
        "tags": song.get("tags", []),
        "yt_description": _youtube_description(cfg, song),
        "sections": song["sections"],
        "telegram_file_id": msg["video"]["file_id"],
        "telegram_message_id": msg["message_id"],
    }
    save_pending(item)
    history.append({"id": item_id, "title": song["title"], "topic": song["topic"],
                    "status": "pending", "created": item["created"]})
    save_history(history)
    log(f"📨 Отправлено на одобрение в Telegram ({item_id})")
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        log("Секреты ещё не настроены — пропускаю.")
        return

    cfg = load_config()
    history = load_history()
    failures = 0
    for n in range(args.count):
        try:
            make_one(cfg, history)
        except Exception as e:  # noqa: BLE001 — report every failure to Telegram
            failures += 1
            traceback.print_exc()
            try:
                telegram.send_message(f"⚠️ Не удалось сделать ролик:\n<code>{html.escape(str(e))[:800]}</code>")
            except Exception:  # noqa: BLE001
                pass
    if failures == args.count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
