"""One-time job: draw character reference pictures and their poses, send them to Telegram.

Usage: python -m agent.make_characters [--force]
Pictures are saved to assets/characters/ and committed by the workflow.
Existing pictures are kept unless --force is given.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import requests

from . import images, telegram
from .common import env, load_config, log


def _send_photo(path: Path, caption: str, as_document: bool = False) -> None:
    method = "sendDocument" if as_document else "sendPhoto"
    field = "document" if as_document else "photo"
    with open(path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}",
            data={"chat_id": telegram.chat_id(), "caption": caption},
            files={field: (path.name, f, "image/png")}, timeout=120,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    poses = cfg.get("animation", {}).get("poses", [])
    for ch in cfg["characters"]:
        ref = images.ref_path(ch["name"])
        if args.force or not ref.exists():
            log(f"🖼  Рисую персонажа {ch['name']}")
            images.draw_character_sheet(cfg, ch, ref)
            _send_photo(ref, f"Персонаж канала: {ch['name']}")
        else:
            log(f"{ch['name']}: образец уже есть")

        for pose in poses:
            out = images.pose_path(ch["name"], pose)
            if out.exists() and not args.force:
                continue
            log(f"   поза {pose}")
            images.draw_pose(cfg, ch, pose, out)
            _send_photo(out, f"{ch['name']} — {pose}")


if __name__ == "__main__":
    main()
