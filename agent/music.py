"""Generates the sung song with the ElevenLabs Music API."""
from __future__ import annotations

from pathlib import Path

import requests

from .common import env, log

API_URL = "https://api.elevenlabs.io/v1/music"


def compose(cfg: dict, song: dict, out_path: Path) -> Path:
    style = [s.strip() for s in cfg["song"]["music_style"].split(",") if s.strip()]
    plan = {
        "positive_global_styles": style,
        "negative_global_styles": [
            "aggressive", "dark", "scary", "explicit", "heavy distortion", "screaming", "sad minor key",
        ],
        "sections": [
            {
                "section_name": s["name"][:100] or f"Part {i + 1}",
                "positive_local_styles": [],
                "negative_local_styles": [],
                "duration_ms": int(s["seconds"] * 1000),
                "lines": s["lines"][:30],
            }
            for i, s in enumerate(song["sections"])
        ],
    }
    log("🎶 Генерирую музыку (ElevenLabs)…")
    resp = requests.post(
        API_URL,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
        json={
            "composition_plan": plan,
            "model_id": cfg["models"]["music"],
            "respect_sections_durations": True,
        },
        timeout=600,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs вернул {resp.status_code}: {resp.text[:500]}")
    out_path.write_bytes(resp.content)
    log(f"   готово: {out_path.name} ({len(resp.content) // 1024} КБ)")
    return out_path
