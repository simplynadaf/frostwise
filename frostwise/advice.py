"""FrostWise advice engine: Gemma 3 (open-weight) via local Ollama.

Takes the TabPFN frost forecast + the gardener's intent and writes short, plain-language
planting guidance. Runs fully offline against the local Ollama server. The model is
swappable (any Ollama open-weight model) via the FROSTWISE_MODEL env var.

If Ollama is unreachable, we degrade to a deterministic rule-based tip so the app never
hard-fails on the trail (the "works with no signal" promise).
"""
from __future__ import annotations
import json
import os
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("FROSTWISE_MODEL", "gemma3:270m")


SYSTEM = (
    "You are FrostWise, a concise gardening assistant. You are given a location's predicted "
    "LAST SPRING FROST date and a plant. Give practical, friendly planting guidance in 2-3 "
    "short sentences. Rules: tender crops (tomato, pepper, basil, squash) go in AFTER the "
    "last frost; hardy crops (peas, spinach, kale, onion) can go a few weeks BEFORE. Mention "
    "the frost date. Do not invent exact dates other than the one given. No preamble."
)


def _rule_based(plant: str, forecast) -> str:
    tender = any(t in plant.lower() for t in ["tomato", "pepper", "basil", "squash", "cucumber", "melon", "bean"])
    if tender:
        return (
            f"{plant.title()} is frost-tender, so wait until after your last frost around "
            f"{forecast.date_str} before transplanting outside. Start seeds indoors ~6 weeks "
            f"before that date, and harden off seedlings the week prior."
        )
    return (
        f"{plant.title()} is cold-hardy, so you can sow 2-4 weeks before the last frost around "
        f"{forecast.date_str}. A light frost won't hurt it; just protect tender new shoots on "
        f"the coldest nights."
    )


def advise(plant: str, forecast, timeout: float = 60.0) -> dict:
    """Return {text, source} where source is 'gemma' or 'offline-fallback'."""
    user = (
        f"Location: {forecast.station}. Predicted last spring frost: {forecast.date_str} "
        f"(range {forecast.low_date} to {forecast.high_date}). The gardener wants to plant: {plant}. "
        f"Give planting guidance."
    )
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM}\n\n{user}\n\nGuidance:",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 160},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read())
        text = (out.get("response") or "").strip()
        if text:
            return {"text": text, "source": "gemma", "model": MODEL}
    except Exception as e:
        pass
    return {"text": _rule_based(plant, forecast), "source": "offline-fallback", "model": "rule-based"}


if __name__ == "__main__":
    from types import SimpleNamespace
    fc = SimpleNamespace(station="Chicago, IL", date_str="May 20", low_date="May 15", high_date="May 26")
    print(advise("tomato", fc))
