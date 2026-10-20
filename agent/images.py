"""Draws pictures with the OpenAI Images API.

* character reference sheets (one per character, assets/characters/<name>.png)
* character poses on a transparent background (assets/characters/poses/<name>_<pose>.png),
  used as animated layers in the video
* scene pictures for every song section
"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

from .common import CHAR_REF_DIR, env, log

SIZE = "1024x1536"  # portrait, cropped to 9:16 later
POSE_DIR = CHAR_REF_DIR / "poses"

POSE_TEXT = {
    "standing": "standing happily, facing the viewer, arms relaxed, big smile",
    "waving": "waving hello with one raised paw/hand, big open smile",
    "dancing": "dancing joyfully, arms up and to the side, one foot lifted, singing",
    "jumping": "jumping in the air with both arms up, very excited, feet off the ground",
}


# ── helpers ──

def _headers() -> dict:
    return {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"}


def _save(resp: requests.Response, out_path: Path) -> Path:
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI Images вернул {resp.status_code}: {resp.text[:500]}")
    b64 = resp.json()["data"][0]["b64_json"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(b64))
    return out_path


def _character(cfg: dict, name: str) -> dict | None:
    return next((c for c in cfg["characters"] if c["name"].lower() == name.lower()), None)


def ref_path(name: str) -> Path:
    return CHAR_REF_DIR / f"{name.lower()}.png"


def pose_path(name: str, pose: str) -> Path:
    return POSE_DIR / f"{name.lower()}_{pose}.png"


def poses_ready(cfg: dict) -> bool:
    anim = cfg.get("animation", {})
    if not anim.get("enabled"):
        return False
    return all(pose_path(c["name"], p).exists()
               for c in cfg["characters"] for p in anim.get("poses", []))


# ── one-time character art ──

def draw_character_sheet(cfg: dict, character: dict, out_path: Path) -> Path:
    prompt = (
        f"{cfg['visual_style']}. Character reference sheet of ONE character, full body, "
        f"standing, front three-quarter view, plain light background, centered. "
        f"The character: {character['name']} is {character['look']}. No text."
    )
    resp = requests.post(
        "https://api.openai.com/v1/images/generations", headers=_headers(), timeout=300,
        json={"model": cfg["models"]["image"], "prompt": prompt, "size": "1024x1024",
              "quality": "high", "n": 1},
    )
    return _save(resp, out_path)


def draw_pose(cfg: dict, character: dict, pose: str, out_path: Path) -> Path:
    prompt = (
        f"{cfg['visual_style']}. The same character as in the reference image: "
        f"{character['name']} is {character['look']}. Full body, {POSE_TEXT.get(pose, pose)}. "
        "Exactly the same design, colors, proportions and outfit as the reference. "
        "Only the character, fully visible from head to feet, centered, "
        "on a fully transparent background. No shadow, no ground, no text."
    )
    ref = ref_path(character["name"])
    resp = requests.post(
        "https://api.openai.com/v1/images/edits", headers=_headers(), timeout=300,
        data={"model": cfg["models"]["image"], "prompt": prompt, "size": "1024x1536",
              "quality": "high", "background": "transparent", "output_format": "png", "n": "1"},
        files=[("image[]", (ref.name, ref.read_bytes(), "image/png"))],
    )
    return _save(resp, out_path)


# ── scenes ──

def draw(cfg: dict, section: dict, out_path: Path, layered: bool) -> Path:
    if layered:
        # Background only: characters are added later as animated layers
        names = ", ".join(c["name"] for c in cfg["characters"])
        prompt = (
            f"{cfg['visual_style']}. Vertical children's illustration, background scene: "
            f"{section['scene']}. Do NOT draw the main characters ({names}) and no other "
            "main heroes: they will be added later. Background and props only. "
            "Keep the lower half of the picture open and uncluttered (soft ground, grass, floor "
            "or sand) so characters can stand there. Calm space in the upper third. "
            "No text or letters anywhere."
        )
        resp = requests.post(
            "https://api.openai.com/v1/images/generations", headers=_headers(), timeout=300,
            json={"model": cfg["models"]["image"], "prompt": prompt, "size": SIZE,
                  "quality": cfg["models"]["image_quality"], "n": 1},
        )
        return _save(resp, out_path)

    # Characters drawn into the picture (used when poses are not ready)
    cast = [_character(cfg, c["name"]) for c in section.get("cast", [])]
    cast = [c for c in cast if c] or cfg["characters"][:2]
    who = " ".join(f"{c['name']} is {c['look']}." for c in cast)
    prompt = (
        f"{cfg['visual_style']}. Vertical children's illustration. Scene: {section['scene']}. "
        f"Characters in the scene: {who} Keep the characters exactly as in the reference images. "
        "Leave some calm space in the upper third of the picture. No text or letters anywhere."
    )
    refs = [ref_path(c["name"]) for c in cast if ref_path(c["name"]).exists()]
    if refs:
        resp = requests.post(
            "https://api.openai.com/v1/images/edits", headers=_headers(), timeout=300,
            data={"model": cfg["models"]["image"], "prompt": prompt, "size": SIZE,
                  "quality": cfg["models"]["image_quality"], "n": "1"},
            files=[("image[]", (p.name, p.read_bytes(), "image/png")) for p in refs],
        )
    else:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations", headers=_headers(), timeout=300,
            json={"model": cfg["models"]["image"], "prompt": prompt, "size": SIZE,
                  "quality": cfg["models"]["image_quality"], "n": 1},
        )
    return _save(resp, out_path)


def draw_scenes(cfg: dict, song: dict, work_dir: Path, layered: bool) -> list[Path]:
    paths = []
    for i, section in enumerate(song["sections"]):
        log(f"🖼  Рисую сцену {i + 1}/{len(song['sections'])}" + (" (фон)" if layered else ""))
        paths.append(draw(cfg, section, work_dir / f"scene_{i:02d}.png", layered))
    return paths
