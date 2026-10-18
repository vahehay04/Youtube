"""One-time job: draw reference pictures of the characters and send them to Telegram.

Usage: python -m agent.make_characters [--force]
The pictures are saved to assets/characters/ and committed by the workflow.
Delete a picture (or run with --force) to redraw it.
"""
from __future__ import annotations

import argparse
import json

import requests

from . import images, telegram
from .common import CHAR_REF_DIR, env, load_config, log


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    CHAR_REF_DIR.mkdir(parents=True, exist_ok=True)
    for ch in cfg["characters"]:
        path = CHAR_REF_DIR / f"{ch['name'].lower()}.png"
        if path.exists() and not args.force:
            log(f"{ch['name']}: уже есть")
            continue
        log(f"🖼  Рисую персонажа {ch['name']}")
        images.draw_character_sheet(cfg, ch, path)
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendPhoto",
                data={"chat_id": telegram.chat_id(),
                      "caption": f"Персонаж канала: {ch['name']}"},
                files={"photo": (path.name, f, "image/png")},
                timeout=120,
            )
    log(json.dumps(sorted(p.name for p in CHAR_REF_DIR.glob("*.png"))))


if __name__ == "__main__":
    main()
