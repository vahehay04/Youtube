"""Builds the vertical Short.

Each scene: smooth eased camera move over the background picture, characters as
separate layers that hop in and bounce/sway to the beat, a big caption bouncing on
the beat, and varied soft transitions between scenes. The song is laid on top.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import images
from .common import log

FONT_CANDIDATES = [
    "assets/fonts/main.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
FADE = 0.5  # seconds of transition between scenes
TRANSITIONS = ["smoothleft", "circleopen", "smoothup", "fade", "smoothright"]
MAX_BYTES = 19 * 1024 * 1024  # Telegram bots can download files up to 20 MB
CAPTION_COLORS = ["0xFF6B6B", "0x4D96FF", "0x6BCB77", "0xFFB830", "0xB967FF"]
# Motion per pose: (bounce height px, sway degrees)
POSE_MOTION = {"standing": (14, 2.5), "waving": (18, 4.0), "dancing": (34, 7.0), "jumping": (60, 4.0)}


def _run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("ffmpeg error:\n" + res.stderr[-2500:])


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


# ── character layers ──

def _prepare_layer(src: Path, height: int, max_w: int, out: Path) -> Path:
    """Trim transparent margins, fit into height x max_w, add a soft ground shadow."""
    img = Image.open(src).convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    k = min(height / img.height, max_w / img.width)
    w, height = max(int(img.width * k), 1), max(int(img.height * k), 1)
    img = img.resize((w, height), Image.LANCZOS)
    pad_x, shadow_h = int(w * 0.15), int(height * 0.06)
    canvas = Image.new("RGBA", (w + 2 * pad_x, height + shadow_h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [pad_x + w * 0.12, height - shadow_h * 0.6, pad_x + w * 0.88, height + shadow_h * 0.9],
        fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_h * 0.5))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(img, (pad_x, 0))
    canvas.save(out)
    return out


def _layout(n: int) -> tuple[float, list[float]]:
    """Character height (share of frame) and x centers for n characters."""
    return {1: (0.42, [0.5]), 2: (0.36, [0.27, 0.73]), 3: (0.30, [0.17, 0.5, 0.83])}[min(n, 3)]


# ── one scene ──

def _scene_clip(bg: Path, section: dict, seconds: float, idx: int, cfg: dict, font: str,
                work: Path, layered: bool) -> Path:
    v = cfg["video"]
    w, h, fps = v["width"], v["height"], v["fps"]
    bpm = float(cfg.get("animation", {}).get("bpm", 110))
    beat = f"PI*t*{bpm / 60:.4f}"  # abs(sin(beat)) peaks once per beat
    frames = max(int(round(seconds * fps)), 1)

    # Background: pre-scale 3x once (single input frame) so the slow move is smooth
    S = 3
    ease = f"(0.5-0.5*cos(PI*on/{frames}))"
    if idx % 2 == 0:  # gentle zoom in
        zp = f"z='1+0.10*{ease}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    else:  # slow pan across at a fixed zoom
        zp = f"z='1.10':x='(iw-iw/zoom)*(0.15+0.7*{ease})':y='ih/2-(ih/zoom/2)'"
    graph = [
        f"[0:v]scale={w * S}:{h * S}:force_original_aspect_ratio=increase,crop={w * S}:{h * S},"
        f"zoompan={zp}:d={frames}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p[bg0]"
    ]
    inputs = ["-i", str(bg)]
    last = "[bg0]"

    cast = section.get("cast", []) if layered else []
    if cast:
        share, xs = _layout(len(cast))
        ch_h = int(h * share)
        ground = int(h * 0.95)
        for i, member in enumerate(cast[:3]):
            src = images.pose_path(member["name"], member["pose"])
            max_w = int(w * (0.92 if len(cast) == 1 else 0.98 / len(cast)))
            layer = _prepare_layer(src, ch_h, max_w, work / f"layer_{idx:02d}_{i}.png")
            inputs += ["-loop", "1", "-framerate", str(fps), "-i", str(layer)]
            amp, sway = POSE_MOTION.get(member["pose"], (18, 3.0))
            ph = i * 0.9  # characters move slightly out of sync
            delay = 0.12 * i  # and hop in one after another
            graph.append(
                f"[{i + 1}:v]format=rgba,"
                f"rotate=a='{sway}*PI/180*sin({beat}+{ph})':c=none:ow='iw*1.08':oh='ih*1.04'[c{i}]"
            )
            x_expr = f"{int(w * xs[i])}-w/2+10*sin({beat}/2+{ph})"
            hop_in = f"{int(h * 0.6)}*pow(max(0\\,1-(t-{delay})/0.5)\\,2)"
            y_expr = (f"{ground}-h-{amp}*abs(sin({beat}+{ph}))"
                      f"+if(lt(t\\,{delay})\\,{h}\\,{hop_in})")
            graph.append(f"{last}[c{i}]overlay=x='{x_expr}':y='{y_expr}':eval=frame:shortest=1[v{i}]")
            last = f"[v{i}]"

    caption = section.get("caption", "")
    if caption and v.get("show_captions", True):
        txt = work / f"caption_{idx:02d}.txt"
        txt.write_text(caption.upper(), encoding="utf-8")
        size = int(min(150, w * 0.85 / (0.68 * max(len(caption), 1))))
        graph.append(
            f"{last}drawtext=fontfile='{font}':textfile='{txt}':fontsize={size}:fontcolor=white"
            f":borderw=14:bordercolor={CAPTION_COLORS[idx % len(CAPTION_COLORS)]}"
            f":x=(w-text_w)/2:y=h*0.11-16*abs(sin({beat}))"
            f":alpha='min(1,max(0,(t-0.3)/0.4))'[vc]"
        )
        last = "[vc]"

    out = work / f"clip_{idx:02d}.mp4"
    _run([
        "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", last,
        "-t", f"{seconds:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", str(out),
    ])
    return out


# ── whole video ──

def build(cfg: dict, song: dict, pictures: list[Path], audio: Path, out_path: Path,
          root: Path, layered: bool = False) -> Path:
    work = out_path.parent
    font = _font(root)
    audio_len = duration(audio)
    planned = [s["seconds"] for s in song["sections"]]
    scale = audio_len / sum(planned)
    # Every clip except the last overlaps the next one by FADE seconds
    secs = [p * scale + (FADE if i < len(planned) - 1 else 0) for i, p in enumerate(planned)]

    log(f"🎬 Собираю видео: {len(pictures)} сцен, {audio_len:.1f} с"
        + (", анимированные персонажи" if layered else ""))
    clips = [
        _scene_clip(pic, song["sections"][i], secs[i], i, cfg, font, work, layered)
        for i, pic in enumerate(pictures)
    ]

    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    inputs += ["-i", str(audio)]

    filters, last, offset = [], "[0:v]", 0.0
    for i in range(1, len(clips)):
        offset += secs[i - 1] - FADE
        label = f"[x{i}]"
        trans = TRANSITIONS[(i - 1) % len(TRANSITIONS)]
        filters.append(f"{last}[{i}:v]xfade=transition={trans}:duration={FADE}:offset={offset:.3f}{label}")
        last = label
    if len(clips) == 1:
        filters.append("[0:v]null[x0]")
        last = "[x0]"
    a_idx = len(clips)
    filters.append(f"[{a_idx}:a]afade=t=out:st={max(audio_len - 1.2, 0):.2f}:d=1.2[a]")

    def encode(maxrate: str) -> None:
        _run([
            "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
            "-map", last, "-map", "[a]", "-t", f"{audio_len:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-maxrate", maxrate, "-bufsize", "5M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_path),
        ])

    encode("2600k")
    if out_path.stat().st_size > MAX_BYTES:
        encode("1500k")
    log(f"   готово: {out_path.name} ({out_path.stat().st_size // 1024} КБ)")
    return out_path
