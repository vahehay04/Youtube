"""Shared helpers: config, secrets, repo state."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
PENDING_DIR = STATE_DIR / "pending"
HISTORY_FILE = STATE_DIR / "history.json"
OFFSET_FILE = STATE_DIR / "telegram_offset.txt"
CHAR_REF_DIR = ROOT / "assets" / "characters"


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        sys.exit(f"Не задан секрет {name}. Добавьте его в GitHub → Settings → Secrets and variables → Actions.")
    return value


def log(msg: str) -> None:
    print(msg, flush=True)


# ── History of published / generated songs (to avoid repeats) ──

def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def save_history(items: list[dict]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Pending videos waiting for approval ──

def save_pending(item: dict) -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    (PENDING_DIR / f"{item['id']}.json").write_text(
        json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_pending(item_id: str) -> dict | None:
    path = PENDING_DIR / f"{item_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_pending(item_id: str) -> None:
    path = PENDING_DIR / f"{item_id}.json"
    if path.exists():
        path.unlink()


def read_offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except ValueError:
            return 0
    return 0


def write_offset(offset: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))


# ── HTTP with retries (servers of AI services are sometimes overloaded) ──

RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
RETRY_WAITS = [20, 45, 90, 180, 300]  # ~10 minutes in total


def post_retry(url: str, **kwargs):
    """requests.post that waits and retries on overload / network errors."""
    import time

    import requests

    last = None
    for attempt, wait in enumerate([0] + RETRY_WAITS):
        if wait:
            log(f"   сервис занят, повтор через {wait} с (попытка {attempt + 1})")
            time.sleep(wait)
        try:
            last = requests.post(url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            continue
        if last.status_code not in RETRY_STATUS:
            return last
        # A 429 caused by an empty balance will not fix itself
        body = last.text.lower()
        if ("quota" in body and "exceeded" in body) or "insufficient" in body:
            return last
    if isinstance(last, Exception):
        raise last
    return last
