"""Text and image generation through the configured provider.

provider: cloudflare  — Cloudflare Workers AI (free daily allowance)
provider: openai      — OpenAI (paid)
"""
from __future__ import annotations

import base64
import json
import re

from .common import env, log, post_retry


def provider(cfg: dict) -> str:
    return cfg["models"].get("provider", "openai").lower()


# ── Cloudflare ──

def _cf_url(model: str) -> str:
    return (f"https://api.cloudflare.com/client/v4/accounts/{env('CLOUDFLARE_ACCOUNT_ID')}"
            f"/ai/run/{model}")


def _cf_headers() -> dict:
    return {"Authorization": f"Bearer {env('CLOUDFLARE_API_TOKEN')}"}


def _cf_result(resp) -> dict:
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"Cloudflare вернул {resp.status_code}: {resp.text[:300]}")
    if resp.status_code != 200 or not data.get("success", False):
        errors = data.get("errors") or data
        hint = ""
        text = json.dumps(errors, ensure_ascii=False)
        if "neuron" in text.lower() or "429" in text or resp.status_code == 429:
            hint = " (похоже, исчерпан бесплатный дневной лимит — он обновится в 03:00 МСК)"
        raise RuntimeError(f"Cloudflare вернул {resp.status_code}: {text[:400]}{hint}")
    return data["result"]


def _extract_json(text) -> dict:
    if isinstance(text, dict):
        return text
    text = str(text).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("в ответе нет JSON")
    return json.loads(text[start:end + 1])


# ── public API ──

def chat_json(cfg: dict, system: str, user: str, temperature: float = 0.9) -> dict:
    """Ask the text model and return its answer parsed as a JSON object."""
    model = cfg["models"]["text"]
    if provider(cfg) == "cloudflare":
        last_error = None
        for attempt in range(3):
            resp = post_retry(_cf_url(model), headers=_cf_headers(), timeout=180, json={
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "max_tokens": 3000,
                "temperature": temperature,
            })
            result = _cf_result(resp)
            try:
                return _extract_json(result.get("response", ""))
            except ValueError as e:  # JSONDecodeError is a ValueError
                last_error = e
                log(f"   модель вернула неполный JSON, пробую ещё раз ({attempt + 1}/3)")
        raise RuntimeError(f"Текстовая модель не вернула корректный JSON: {last_error}")

    resp = post_retry(
        "https://api.openai.com/v1/chat/completions", timeout=120,
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json={"model": model, "response_format": {"type": "json_object"},
              "temperature": temperature,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI вернул {resp.status_code}: {resp.text[:300]}")
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def image(cfg: dict, prompt: str, width: int = 1024, height: int = 1536) -> bytes:
    """Generate one picture from text; returns PNG/JPEG bytes."""
    model = cfg["models"]["image"]
    if provider(cfg) == "cloudflare":
        if "flux-2" in model:
            # FLUX.2 models take multipart form data and support portrait sizes
            files = {"prompt": (None, prompt), "width": (None, str(width)),
                     "height": (None, str(height)),
                     "steps": (None, str(cfg["models"].get("image_steps", 4)))}
            resp = post_retry(_cf_url(model), headers=_cf_headers(), files=files, timeout=300)
        else:
            # FLUX.1 schnell: square 1024x1024, max 8 steps
            resp = post_retry(_cf_url(model), headers=_cf_headers(), timeout=300, json={
                "prompt": prompt[:2000],
                "num_steps": min(int(cfg["models"].get("image_steps", 8)), 8),
            })
        return base64.b64decode(_cf_result(resp)["image"])

    resp = post_retry(
        "https://api.openai.com/v1/images/generations", timeout=300,
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json={"model": model, "prompt": prompt, "size": f"{width}x{height}",
              "quality": cfg["models"].get("image_quality", "medium"), "n": 1},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI Images вернул {resp.status_code}: {resp.text[:300]}")
    return base64.b64decode(resp.json()["data"][0]["b64_json"])
