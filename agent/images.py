"""Draws scene pictures with the OpenAI Images API.

If reference pictures of the characters exist in assets/characters/,
they are passed to the model so the characters look the same in every video.
"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

from .common import CHAR_REF_DIR, env, log

SIZE = "1024x1536"  # portrait, cropped to 9:16 later


def _character_block(cfg: dict, names: list[str]) -> str:
    chars = [c for c in cfg["characters"] if c["name"] in names] or cfg["characters"]
    return " ".join(f"{c['name']} is {c['look']}." for c in chars)


def _mentioned(cfg: dict, text: str) -> list[str]:
    low = text.lower()
    return [c["name"] for c in cfg["characters"] if c["name"].lower() in low]


def _ref_paths(names: list[str]) -> list[Path]:
    paths = []
    for name in names:
        p = CHAR_REF_DIR / f"{name.lower()}.png"
        if p.exists():
            paths.append(p)
    return paths


def _save(resp: requests.Response, out_path: Path) -> Path:
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI Images вернул {resp.status_code}: {resp.text[:500]}")
    b64 = resp.json()["data"][0]["b64_json"]
    out_path.write_bytes(base64.b64decode(b64))
    return out_path


def draw(cfg: dict, scene_text: str, out_path: Path, use_refs: bool = True) -> Path:
    names = _mentioned(cfg, scene_text)
    prompt = (
        f"{cfg['visual_style']}. Vertical children's illustration. Scene: {scene_text}. "
        f"Characters: {_character_block(cfg, names)} "
        "Keep the characters exactly as described and as in the reference images. "
        "Leave some calm space in the upper third of the picture. No text or letters anywhere."
    )
    headers = {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"}
    model = cfg["models"]["image"]
    quality = cfg["models"]["image_quality"]
    refs = _ref_paths(names) if use_refs else []

    if refs:
        files = [("image[]", (p.name, p.read_bytes(), "image/png")) for p in refs]
        resp = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            data={"model": model, "prompt": prompt, "size": SIZE, "quality": quality, "n": "1"},
            files=files,
            timeout=300,
        )
    else:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json={"model": model, "prompt": prompt, "size": SIZE, "quality": quality, "n": 1},
            timeout=300,
        )
    return _save(resp, out_path)


def draw_scenes(cfg: dict, song: dict, work_dir: Path) -> list[Path]:
    paths = []
    for i, section in enumerate(song["sections"]):
        log(f"🖼  Рисую сцену {i + 1}/{len(song['sections'])}")
        paths.append(draw(cfg, section["scene"], work_dir / f"scene_{i:02d}.png"))
    return paths


def draw_character_sheet(cfg: dict, character: dict, out_path: Path) -> Path:
    """One-time reference picture of a character (used for consistency)."""
    prompt = (
        f"{cfg['visual_style']}. Character reference sheet of ONE character, full body, "
        f"standing, front three-quarter view, plain light background, centered. "
        f"The character: {character['name']} is {character['look']}. No text."
    )
    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json={"model": cfg["models"]["image"], "prompt": prompt, "size": "1024x1024",
              "quality": "high", "n": 1},
        timeout=300,
    )
    return _save(resp, out_path)
