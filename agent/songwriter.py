"""Writes the song: lyrics split into sections, one illustrated scene per section."""
from __future__ import annotations

import json
import random

import requests

from .common import env, log

LANG_NAMES = {"en": "English", "ru": "Russian"}

SYSTEM = """You are a children's songwriter and early-education expert creating
YouTube Shorts for toddlers. Songs must be gentle, positive, simple,
repetitive in a catchy way, and teach ONE small concrete thing. Never include
anything scary, violent, commercial, brand names, real people or existing
copyrighted characters. Only use the channel's own characters described by the user.
Answer with JSON only."""

USER_TEMPLATE = """Write a new song for our channel.

Language of lyrics, title, description and captions: {lang}
Audience age: {age}
Topic of this song: {topic}
Song length: about {seconds} seconds, split into exactly {scenes} sections.
Our characters (use 1-3 of them):
{characters}

Do NOT repeat these previous titles or their main idea:
{history}

Return JSON with this exact shape:
{{
  "title": "catchy title, max 60 characters, no hashtags, no emoji",
  "description": "2-3 friendly sentences for parents about what the child learns",
  "tags": ["8-12 short search tags in the same language"],
  "sections": [
    {{
      "name": "Intro | Verse 1 | Chorus | Verse 2 | Outro ...",
      "seconds": 10,
      "lines": ["2-4 short sung lines, max 8 words each"],
      "caption": "1-3 BIG words shown on screen that reinforce the lesson, e.g. a number, color or animal sound",
      "cast": [{{"name": "one of our characters", "pose": "one of: {poses}"}}],
      "scene": "the place and the objects that teach the lesson (e.g. 'a sunny farm with a red barn, a cow and three yellow chicks'), concrete and visual, in English; do NOT describe our characters here"
    }}
  ]
}}
"cast" has 1-3 of our characters for that section, with a pose that fits the lyrics
(use "dancing" or "jumping" in the chorus, "waving" in the intro/outro).
The sum of "seconds" must be about {seconds}. Each section at least 6 seconds.
Repeat the chorus at least twice so kids can sing along."""


def pick_topic(cfg: dict, history: list[dict]) -> str:
    topics = cfg["topics"]
    recent = [h.get("topic") for h in history[-len(topics) // 2 :]]
    fresh = [t for t in topics if t not in recent] or topics
    return random.choice(fresh)


def write_song(cfg: dict, history: list[dict]) -> dict:
    ch = cfg["channel"]
    song_cfg = cfg["song"]
    topic = pick_topic(cfg, history)
    chars = "\n".join(f"- {c['name']}: {c['look']}" for c in cfg["characters"])
    prev = "\n".join(f"- {h['title']}" for h in history[-40:]) or "- (none yet)"

    prompt = USER_TEMPLATE.format(
        lang=LANG_NAMES.get(ch["language"], ch["language"]),
        age=ch["audience_age"],
        topic=topic,
        seconds=song_cfg["target_seconds"],
        scenes=song_cfg["scenes"],
        characters=chars,
        history=prev,
        poses=", ".join(cfg.get("animation", {}).get("poses", ["standing"])),
    )

    log(f"✍️  Пишу песню на тему: {topic}")
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json={
            "model": cfg["models"]["text"],
            "response_format": {"type": "json_object"},
            "temperature": 0.9,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    song = json.loads(resp.json()["choices"][0]["message"]["content"])
    song["topic"] = topic
    normalize(song, song_cfg["target_seconds"], cfg)
    log(f"🎵 «{song['title']}» — {len(song['sections'])} частей")
    return song


def _clean_cast(cast, cfg: dict, idx: int) -> list[dict]:
    names = {c["name"].lower(): c["name"] for c in cfg["characters"]}
    poses = cfg.get("animation", {}).get("poses", ["standing"])
    out, seen = [], set()
    for item in cast if isinstance(cast, list) else []:
        if not isinstance(item, dict):
            continue
        name = names.get(str(item.get("name", "")).strip().lower())
        if not name or name in seen:
            continue
        pose = str(item.get("pose", "")).strip().lower()
        out.append({"name": name, "pose": pose if pose in poses else poses[0]})
        seen.add(name)
    if not out:  # fallback: rotate through characters
        c = cfg["characters"][idx % len(cfg["characters"])]["name"]
        out = [{"name": c, "pose": poses[idx % len(poses)]}]
    return out[:3]


def normalize(song: dict, target_seconds: int, cfg: dict | None = None) -> None:
    """Make section durations sane and add up to the target length."""
    sections = [s for s in song.get("sections", []) if s.get("lines")]
    if not sections:
        raise ValueError("Модель не вернула ни одной части песни")
    total = sum(max(float(s.get("seconds", 8)), 1.0) for s in sections)
    for s in sections:
        sec = max(float(s.get("seconds", 8)), 1.0) * target_seconds / total
        s["seconds"] = round(max(6.0, min(sec, 30.0)), 1)
        s["lines"] = [str(line)[:200] for line in s["lines"]][:8]
        s["caption"] = str(s.get("caption", ""))[:24]
    if cfg:
        for i, s in enumerate(sections):
            s["cast"] = _clean_cast(s.get("cast"), cfg, i)
    song["sections"] = sections
    song["title"] = str(song.get("title", "Song"))[:60].strip()
    song["tags"] = [str(t)[:30] for t in song.get("tags", [])][:12]
