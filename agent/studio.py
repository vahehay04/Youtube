"""Builds and renders a Short with the 2D studio engine (private repo checked out at ./studio).

build(cfg, song, audio, work) -> path to the final MP4 (<= ~19 MB for Telegram).
The storyboard is generated from the song: sections, cast poses, props and set variants.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .common import ROOT, log

STUDIO = Path(os.environ.get("STUDIO_DIR", ROOT / "studio"))
SCENES = ROOT / "studio_scenes"
POSES = ROOT / "assets" / "characters" / "poses"
MAX_BYTES = 19 * 1024 * 1024

PROP_KINDS = ["ball", "car", "bus", "boat", "train", "duck", "chick", "cow", "pig", "sheep", "fish", "crab", "octopus",
              "kite", "balloon", "blocks", "teddy", "apple", "banana", "carrot", "strawberry", "star", "heart", "circle",
              "square", "triangle", "number", "letter", "toothbrush", "soap", "umbrella", "flower", "cake", "moon", "sun",
              "snowflake", "cloud", "bed"]
SETS = ["playground", "sandbox", "picnic", "hill", "farm", "beach", "night", "rain", "snow", "home"]
COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "white"]

# keyword → prop
PROP_WORDS = {
    "ball": ["ball"], "car": ["car", "vroom"], "bus": ["bus"], "boat": ["boat", "ship", "sail"], "train": ["train", "choo"],
    "duck": ["duck", "quack"], "chick": ["chick", "chicken", "hen", "cheep", "peep"], "cow": ["cow", "moo"], "pig": ["pig", "oink"],
    "sheep": ["sheep", "baa", "lamb"], "fish": ["fish"], "crab": ["crab"], "octopus": ["octopus"], "kite": ["kite"],
    "balloon": ["balloon"], "blocks": ["block", "blocks"], "teddy": ["teddy", "bear"], "apple": ["apple"],
    "banana": ["banana"], "carrot": ["carrot", "vegetable", "veggie"], "strawberry": ["strawberry", "berry", "fruit"],
    "star": ["star", "twinkle"], "heart": ["kind", "love", "hug", "heart"], "circle": ["circle", "round"],
    "square": ["square"], "triangle": ["triangle"], "toothbrush": ["brush", "teeth", "tooth"], "soap": ["soap", "wash", "bubbles", "hands"],
    "umbrella": ["umbrella", "rain"], "flower": ["flower", "garden"], "cake": ["cake", "birthday"], "moon": ["moon", "night", "goodnight"],
    "sun": ["sun"], "snowflake": ["snow", "snowflake"], "cloud": ["cloud"], "bed": ["bed", "sleep", "sleepy", "bedtime"],
}
SET_WORDS = {
    "farm": ["farm", "barn", "moo", "oink", "cow", "pig", "sheep"], "beach": ["sea", "ocean", "beach", "fish", "crab", "octopus", "wave"],
    "night": ["night", "moon", "goodnight", "bedtime", "sleep", "star"], "rain": ["rain", "puddle", "umbrella"],
    "snow": ["snow", "snowflake", "winter", "cold"], "home": ["brush", "teeth", "wash", "soap", "bath", "clean", "room", "tidy", "morning routine"],
    "picnic": ["picnic", "eat", "fruit", "apple", "banana", "lunch", "snack", "vegetable"], "sandbox": ["sand", "sandbox", "car", "truck"],
    "hill": ["kite", "hill", "wind"], "playground": ["play", "playground", "swing", "slide", "park"],
}
ALL_KEYS = {k for ks in PROP_WORDS.values() for k in ks}
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def available() -> bool:
    return (STUDIO / "render.mjs").exists() and (STUDIO / "node_modules").exists()


# ---------- analysis ----------

def _words(text: str) -> list[str]:
    ws = re.findall(r"[a-z]+|\d+", text.lower())
    # singular forms too: apples -> apple, berries -> berry, fishes -> fish
    return ws + [w[:-3] + "y" if w.endswith("ies") else w[:-2] if w.endswith("es") and w[:-2] in ALL_KEYS else w[:-1]
                 for w in ws if len(w) > 3 and w.endswith("s")]


def _detect_props(text: str, limit: int = 3) -> list[dict]:
    ws = _words(text); found = []
    for kind, keys in PROP_WORDS.items():
        pos = min((ws.index(k) for k in keys if k in ws), default=None)
        if pos is not None:
            found.append((pos, kind))
    out, colors = [], [w for w in ws if w in COLORS]
    for i, (_, kind) in enumerate(sorted(found)[:limit]):
        q = {"kind": kind}
        if colors:
            q["color"] = colors[i % len(colors)]
        out.append(q)
    return out


def _detect_set(text: str) -> str | None:
    ws = " " + " ".join(_words(text)) + " "
    best, score = None, 0
    for name, keys in SET_WORDS.items():
        s = sum(ws.count(f" {k} ") for k in keys)
        if s > score:
            best, score = name, s
    return best


def _number(text: str) -> int | None:
    nums = [int(w) for w in _words(text) if w.isdigit() and 1 <= int(w) <= 5] + [NUM_WORDS[w] for w in _words(text) if w in NUM_WORDS]
    return max(nums) if nums else None


def _clean_props(props, fallback_text: str) -> list[dict]:
    out = []
    for q in props if isinstance(props, list) else []:
        if isinstance(q, str):
            q = {"kind": q}
        if not isinstance(q, dict):
            continue
        k = str(q.get("kind", "")).lower().strip()
        if k not in PROP_KINDS:
            continue
        c = {"kind": k}
        if str(q.get("color", "")).lower() in COLORS:
            c["color"] = str(q["color"]).lower()
        if isinstance(q.get("n"), int) and 1 <= q["n"] <= 5:
            c["n"] = q["n"]
        if k == "letter" and str(q.get("letter", "")).strip():
            c["letter"] = str(q["letter"]).strip()[:1].upper()
        out.append(c)
    return out[:3] or _detect_props(fallback_text)


# ---------- storyboard ----------

def storyboard(song: dict, dur: float) -> dict:
    secs = song["sections"]
    total = sum(s["seconds"] for s in secs)
    k = dur / total
    text_all = " ".join(s.get("scene", "") + " " + " ".join(s["lines"]) for s in secs) + " " + song.get("topic", "")
    song_set = song.get("set") if song.get("set") in SETS else (_detect_set(text_all) or "playground")
    shots, t, sid, prev_set = [], 0.0, 0, None
    fx_cycle = ["confetti", "notes", "hearts", "butterflies"]

    for si, s in enumerate(secs):
        d = s["seconds"] * k
        name = s.get("name", "").lower()
        kind = "intro" if si == 0 else "outro" if si == len(secs) - 1 else "chorus" if "chorus" in name else "verse"
        text = s.get("scene", "") + " " + " ".join(s["lines"]) + " " + s.get("caption", "")
        st = s.get("set") if s.get("set") in SETS else (_detect_set(text) or prev_set or song_set)
        prev_set = st
        lines_txt = " ".join(s["lines"])
        props = _clean_props(s.get("props"), lines_txt) or _detect_props(s.get("scene", ""))
        hero_props = {}
        for ln in s["lines"]:
            for h in ("pip", "lulu", "bo"):
                if h in _words(ln) and h not in hero_props:
                    found = _detect_props(ln, 1)
                    if found: hero_props[h] = found[0]
        num = max(filter(None, [_number(s.get("caption", "")), _number(" ".join(s["lines"]))]), default=None)
        if num and "count" in (song.get("topic", "") + text).lower():
            base = props[0]["kind"] if props and props[0]["kind"] != "number" else "apple"
            props = [{"kind": base, "n": num, **({"color": props[0]["color"]} if props and "color" in props[0] else {})}, {"kind": "number", "n": num}]
        cast = [c["name"].lower() for c in s.get("cast", []) if c.get("name")] or ["pip", "lulu", "bo"]
        cast = [c for c in cast if c in ("pip", "lulu", "bo")] or ["pip", "lulu", "bo"]
        all3 = ["lulu", "pip", "bo"]
        pose_of = {c.get("name", "").lower(): c.get("pose", "standing") for c in s.get("cast", [])}
        fx_set = "stars" if st == "night" else "bubbles" if st in ("beach", "home") else None
        cap = s.get("caption") or None

        n = max(1, min(4, round(d / 2.7)))
        plan: list[dict] = []
        if kind == "intro":
            plan = [dict(type="title", cast=[{"name": c, "pose": "waving"} for c in all3], title=cap or song.get("title", "")[:24], cam="down")]
            if n > 1: plan.append(dict(type="group", cast=[{"name": c, "pose": "waving"} for c in all3], props=props, cam="push"))
            if n > 2 and props: plan.append(dict(type="pass", cast=[{"name": c, "pose": "standing"} for c in all3], props=props, cam="panR"))
        elif kind == "verse":
            order = [c for c in cast if c in hero_props] + [c for c in cast if c not in hero_props]
            for i, c in enumerate(order[: max(1, n - 1)]):
                q = [hero_props[c]] if c in hero_props else ([props[i % len(props)]] if props else [])
                plan.append(dict(type="solo", cast=[{"name": c, "pose": pose_of.get(c, "standing")}], props=q, title=cap if i == 0 else None,
                                 cam=["push", "panL", "pull"][i % 3], fx=fx_set))
            if len(plan) < n:
                plan.append(dict(type="pass" if props and props[0]["kind"] not in ("number",) else "group",
                                 cast=[{"name": c, "pose": "standing"} for c in all3], props=props, cam="push"))
        elif kind == "chorus":
            fxc = fx_cycle[si % len(fx_cycle)]
            plan = [dict(type="group", cast=[{"name": c, "pose": "dancing"} for c in all3], props=props, title=cap, fx=fxc, cam="pull", colors=["#ffd23a", "#ffffff"]),
                    dict(type="duo", cast=[{"name": cast[0], "pose": "dancing"}, {"name": (cast[1:] or ["lulu"])[0], "pose": "dancing"}], fx="notes", cam="panL"),
                    dict(type="group", cast=[{"name": c, "pose": "dancing"} for c in all3], fx="hearts", cam="push"),
                    dict(type="close", cast=[{"name": cast[-1], "pose": "dancing"}], fx=fx_set or "notes", cam="push")][:n]
        else:  # outro
            plan = [dict(type="group", cast=[{"name": c, "pose": "jumping"} for c in all3], title=cap, fx="confetti", cam="pull", colors=["#ff8ad0", "#ffd23a"])]
            if n > 2: plan.append(dict(type="group", cast=[{"name": c, "pose": "dancing"} for c in all3], fx="balloons", cam="up"))
            plan.append(dict(type="end", cast=[{"name": c, "pose": "waving"} for c in all3], title="BYE BYE!", props=[], cam="pull"))

        # split the section into shots (the end card gets at least 2.5 s)
        cuts = [d / len(plan)] * len(plan)
        if plan[-1]["type"] == "end" and len(plan) > 1 and cuts[-1] < 2.5:
            extra = 2.5 - cuts[-1]; cuts[-1] = 2.5; cuts[:-1] = [c - extra / (len(plan) - 1) for c in cuts[:-1]]
        for j, p in enumerate(plan):
            sid += 1; a = t; b = t + cuts[j]; t = b
            p.setdefault("set", st); p.setdefault("props", []); p.setdefault("fx", None); p.setdefault("title", None)
            if si == 0 and j == 0: tr = {"type": "fade", "dur": 0.4}
            elif j == 0: tr = {"chorus": {"type": "iris", "at": [0.5, 0.55], "dur": 0.5}, "outro": {"type": "flash", "dur": 0.3}}.get(kind, {"type": "push", "dir": 1, "vertical": True, "dur": 0.45})
            else: tr = [{"type": "whip", "dir": 1, "dur": 0.35}, {"type": "push", "dir": -1, "dur": 0.4}, {"type": "cut"}, {"type": "whip", "dir": -1, "dur": 0.35}][(sid + j) % 4]
            sfx = []
            if tr["type"] in ("whip", "push"): sfx.append({"at": 0.0, "name": "whoosh" if tr["type"] == "whip" else "swish", "gain": -12})
            if j == 0 and kind == "chorus": sfx.append({"at": 0.05, "name": "shimmer", "gain": -14})
            if p["type"] == "title": sfx += [{"at": 0.6 + i * 0.2, "name": "pop", "gain": -10} for i in range(3)]
            if p["type"] in ("group", "solo") and p["props"]: sfx += [{"at": 0.45 + i * 0.3, "name": "pop", "gain": -12} for i in range(min(3, len(p["props"])))]
            if p["type"] == "pass": sfx += [{"at": 0.05, "name": "kick", "gain": -14}, {"at": 0.95, "name": "kick", "gain": -14}]
            if p["type"] == "end": sfx.append({"at": 0.3, "name": "ding", "gain": -12})
            shots.append({"id": f"s{sid:02d}", "start": round(a, 3), "end": round(b, 3), "seed": sid, "scene": f"{p['type']} @ {p['set']}",
                          "bars": "none", "in": tr, "sfx": sfx, "captions": False, "mb": 0, "params": p})
    shots[-1]["end"] = round(dur, 3)
    return {"title": song.get("title", ""), "duration": round(dur, 3), "shots": shots, "music": [], "sfx": []}


def sentences(song: dict, dur: float) -> list[dict]:
    secs = song["sections"]; k = dur / sum(s["seconds"] for s in secs); t = 0.0; out = []
    for s in secs:
        d = s["seconds"] * k; n = max(1, len(s["lines"]))
        for i, line in enumerate(s["lines"]):
            a = t + 0.4 + i * (d - 0.6) / n
            out.append({"i": len(out), "start": round(a, 2), "end": round(t + 0.4 + (i + 1) * (d - 0.6) / n, 2), "text": line})
        t += d
    return out


def tempo(audio: Path, fallback: float) -> dict:
    try:
        import numpy as np
        sr, hop = 22050, 512
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32)
        fr = np.lib.stride_tricks.sliding_window_view(x, 1024)[::hop]
        spec = np.abs(np.fft.rfft(fr * np.hanning(1024), axis=1))
        flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(1); flux -= flux.mean()
        ac = np.correlate(flux, flux, "full")[len(flux) - 1:]; fps = sr / hop; idx = np.arange(len(ac))
        bpm = max(np.arange(80, 160, 0.5), key=lambda b: sum(np.interp(60 / b * fps * m, idx, ac) for m in (1, 2, 4)))
        period = 60 / bpm * fps; fi = np.arange(len(flux))
        ph = max(np.arange(0, period, 0.5), key=lambda o: np.interp(np.arange(o, len(flux), period), fi, flux).sum())
        return {"bpm": float(bpm), "t0": round(float(ph / fps), 3)}
    except Exception as e:  # noqa: BLE001
        log(f"   темп не определён ({e}), беру {fallback} bpm")
        return {"bpm": float(fallback), "t0": 0.0}


# ---------- build & render ----------

def _trim_sprites(dst: Path) -> None:
    from PIL import Image
    dst.mkdir(parents=True, exist_ok=True)
    for f in POSES.glob("*.png"):
        im = Image.open(f).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        if bb: im = im.crop(bb)
        k = 900 / im.height
        im.resize((max(1, int(im.width * k)), 900), Image.LANCZOS).save(dst / f.name)


def _run(cmd: list[str], cwd: Path) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    tail = (res.stdout + res.stderr)[-3000:]
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed:\n{tail}")
    for line in tail.splitlines()[-4:]:
        log("   " + line)


def build(cfg: dict, song: dict, audio: Path, work: Path) -> Path:
    from .video import duration
    slug = "short"
    proj = work / "project"
    if proj.exists(): shutil.rmtree(proj)
    for d in ["input", "timeline", "story", "build", "out", "assets"]:
        (proj / d).mkdir(parents=True, exist_ok=True)
    shutil.copytree(SCENES, proj / "scenes")
    _trim_sprites(proj / "assets")
    shutil.copy2(audio, proj / "input" / "voiceover.mp3")
    dur = duration(audio)
    v = cfg["video"]
    (proj / "config.json").write_text(json.dumps({
        "title": re.sub(r"[^\w\- ]", "", song["title"]) or slug, "aspect": "9:16", "resolution": v.get("resolution", "1080p"),
        "fps": v.get("studio_fps", 24), "style": "kids", "voiceover": "input/voiceover.mp3", "duration": round(dur, 3),
        "captions": False, "bars": "none", "fadeIn": 0.3, "fadeOut": 0.6, "music": {"enabled": False},
        "sfx": {"enabled": True, "gainDb": -8}, "loudness": -14}, indent=1))
    (proj / "timeline" / "sentences.json").write_text(json.dumps(sentences(song, dur), ensure_ascii=False, indent=1))
    beat = tempo(audio, cfg.get("animation", {}).get("bpm", 110))
    (proj / "timeline" / "beat.json").write_text(json.dumps(beat))
    board = storyboard(song, dur)
    (proj / "story" / "shots.json").write_text(json.dumps(board, ensure_ascii=False, indent=1))
    log(f"🎬 Студия: {len(board['shots'])} кадров, темп {beat['bpm']:.0f} bpm, рендер…")

    workers = str(max(1, min(4, os.cpu_count() or 2)))
    _run(["node", "render.mjs", "--project", str(proj), "--workers", workers], STUDIO)
    _run(["python3", "audio/mix.py", "--project", str(proj)], STUDIO)
    out = next((proj / "out").glob("*.mp4"))

    final = work / f"{slug}.mp4"
    for rate in ("2600k", "1800k", "1200k"):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                        "-maxrate", rate, "-bufsize", "6M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", str(final)], check=True)
        if final.stat().st_size <= MAX_BYTES:
            break
    log(f"   готово: {final.stat().st_size // 1024} КБ")
    return final
