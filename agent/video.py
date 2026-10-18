"""Builds the vertical Short: gentle zoom on each picture, big caption, song on top."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .common import log

FONT_CANDIDATES = [
    "assets/fonts/main.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
FADE = 0.4  # seconds of crossfade between scenes
MAX_BYTES = 19 * 1024 * 1024  # Telegram bots can download files up to 20 MB


def _run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("ffmpeg error:\n" + res.stderr[-2000:])


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _font(root: Path) -> str:
    for c in FONT_CANDIDATES:
        p = Path(c) if c.startswith("/") else root / c
        if p.exists():
            return str(p)
    raise FileNotFoundError("Не найден шрифт для подписей (установите fonts-dejavu-core)")


def _scene_clip(img: Path, seconds: float, caption: str, idx: int, cfg: dict, font: str,
                work: Path) -> Path:
    v = cfg["video"]
    w, h, fps = v["width"], v["height"], v["fps"]
    frames = max(int(seconds * fps), 1)
    # Pre-scale 1.5x so the slow zoom stays smooth, crop to 9:16
    bw, bh = int(w * 1.5), int(h * 1.5)
    zoom = (f"'min(1+0.12*on/{frames},1.12)'" if idx % 2 == 0
            else f"'max(1.12-0.12*on/{frames},1)'")
    vf = (
        f"scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
        f"zoompan=z={zoom}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps}"
    )
    if caption and v.get("show_captions", True):
        txt = work / f"caption_{idx:02d}.txt"
        txt.write_text(caption.upper(), encoding="utf-8")
        # Fit the longest word line into ~85% of the width
        size = int(min(150, w * 0.85 / (0.68 * max(len(caption), 1))))
        colors = ["0xFF6B6B", "0x4D96FF", "0x6BCB77", "0xFFB830", "0xB967FF"]
        vf += (
            f",drawtext=fontfile='{font}':textfile='{txt}':fontsize={size}:fontcolor=white"
            f":borderw=14:bordercolor={colors[idx % len(colors)]}"
            f":x=(w-text_w)/2:y=h*0.12+18*sin(t*3.2)"
            f":alpha='min(1,max(0,(t-0.3)/0.4))'"
        )
    out = work / f"clip_{idx:02d}.mp4"
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf, "-t", f"{seconds:.3f}",
        "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", str(out),
    ])
    return out


def build(cfg: dict, song: dict, images: list[Path], audio: Path, out_path: Path,
          root: Path) -> Path:
    work = out_path.parent
    font = _font(root)
    audio_len = duration(audio)
    planned = [s["seconds"] for s in song["sections"]]
    scale = audio_len / sum(planned)
    # Every clip except the last overlaps the next one by FADE seconds
    secs = [p * scale + (FADE if i < len(planned) - 1 else 0) for i, p in enumerate(planned)]

    log(f"🎬 Собираю видео: {len(images)} сцен, {audio_len:.1f} с")
    clips = [
        _scene_clip(img, secs[i], song["sections"][i].get("caption", ""), i, cfg, font, work)
        for i, img in enumerate(images)
    ]

    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    inputs += ["-i", str(audio)]

    filters, last, offset = [], "[0:v]", 0.0
    for i in range(1, len(clips)):
        offset += secs[i - 1] - FADE
        label = f"[v{i}]"
        filters.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}{label}")
        last = label
    if len(clips) == 1:
        last = "0:v"
    a_idx = len(clips)
    filters.append(f"[{a_idx}:a]afade=t=out:st={max(audio_len - 1.2, 0):.2f}:d=1.2[a]")

    def encode(maxrate: str) -> None:
        _run([
            "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
            "-map", last, "-map", "[a]", "-t", f"{audio_len:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-maxrate", maxrate, "-bufsize", "4M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_path),
        ])

    encode("2M")
    if out_path.stat().st_size > MAX_BYTES:
        encode("1200k")
    log(f"   готово: {out_path.name} ({out_path.stat().st_size // 1024} КБ)")
    return out_path
