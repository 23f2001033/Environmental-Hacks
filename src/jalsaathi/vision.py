"""AI suggestion for a field-kit photo (Bedrock). Advisory only: the person always chooses the result.

Claude Haiku 4.5 first; Amazon Nova Pro if Claude is unavailable (Anthropic models need an AWS Marketplace
subscription, which needs a payment card on the account).
"""

from __future__ import annotations

import json
import logging
import re

from . import config

log = logging.getLogger()

MODEL_ID = "in.anthropic.claude-haiku-4-5-20251001-v1:0"
FALLBACK_MODEL_ID = "apac.amazon.nova-pro-v1:0"
MODELS = (MODEL_ID, FALLBACK_MODEL_ID)
_unavailable: set[str] = set()  # models refused with AccessDenied in this Lambda container
PROMPT = (
    "This photo should show an H2S field test vial or strip used in India to check drinking water for faecal bacteria, "
    "read 24 to 48 hours after filling. Black or dark grey liquid or strip means contaminated. Yellow, clear or "
    "unchanged means no H2S-producing bacteria seen. Reply with only this JSON: "
    '{"colour": "black" | "yellow" | "unclear", "confidence": "low" | "medium" | "high", "reason": "<at most 12 words>"}. '
    'If the photo is not a test vial, or you cannot tell, use "unclear".'
)
HINT_HI = {
    "black": "शीशी <b>काली</b> दिखती है, यानी पानी दूषित हो सकता है।",
    "yellow": "शीशी <b>पीली</b> दिखती है, यानी पानी साफ़ हो सकता है।",
    "unclear": "फ़ोटो से रंग साफ़ नहीं दिख रहा।",
}


def parse_hint(text: str, model: str = MODEL_ID) -> dict | None:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    colour = str(data.get("colour", "")).lower()
    if colour not in HINT_HI:
        return None
    confidence = str(data.get("confidence", "low")).lower()
    return {"colour": colour, "confidence": confidence if confidence in ("low", "medium", "high") else "low",
            "reason": str(data.get("reason", ""))[:120], "model": model}


def kit_hint(image: bytes) -> dict | None:
    """Ask each model in turn; a model the account can't use (e.g. Marketplace not set up) is skipped."""
    for model in MODELS:
        if model in _unavailable:
            continue
        try:
            resp = config.client("bedrock-runtime").converse(
                modelId=model,
                messages=[{"role": "user", "content": [{"image": {"format": "jpeg", "source": {"bytes": image}}},
                                                        {"text": PROMPT}]}],
                inferenceConfig={"maxTokens": 120, "temperature": 0},
            )
            return parse_hint(resp["output"]["message"]["content"][0]["text"], model)
        except Exception as exc:  # noqa: BLE001 - the hint is optional
            if "AccessDenied" in type(exc).__name__ or "AccessDenied" in str(exc):
                _unavailable.add(model)
            log.warning("kit hint with %s failed: %s", model, exc)
    return None


def hint_message(hint: dict | None) -> str:
    base = "📷 फ़ोटो मिल गई।"
    if not hint:
        return base + " अब जांच वाले संदेश में नतीजा चुनें।"
    return (f"{base}\n🤖 <i>AI सुझाव</i>: {HINT_HI[hint['colour']]}\n"
            "यह सिर्फ़ सुझाव है। शीशी को खुद देखकर जांच वाले संदेश में सही नतीजा चुनें।")
