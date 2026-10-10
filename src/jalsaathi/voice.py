"""Voice notes with Amazon Polly (Kajal speaks hi-IN and en-IN), stored under media/ so CloudFront can serve them."""

from __future__ import annotations

import logging

from . import config

log = logging.getLogger()

VOICE_ID = "Kajal"
LANGUAGE_CODES = {"hi": "hi-IN", "en": "en-IN"}


def synthesize(text: str, key: str, lang: str = "hi") -> str:
    """Write an MP3 to s3://BUCKET/media/<key> and return its public URL path (/media/<key>)."""
    polly = config.client("polly")
    audio = polly.synthesize_speech(Text=text[:2900], VoiceId=VOICE_ID, Engine="neural",
                                    LanguageCode=LANGUAGE_CODES.get(lang, "hi-IN"), OutputFormat="mp3")["AudioStream"].read()
    config.client("s3").put_object(Bucket=config.bucket(), Key=f"media/{key}", Body=audio, ContentType="audio/mpeg",
                                   CacheControl="max-age=300")
    from . import metrics

    metrics.emit("VoiceNotes", Lang=lang)
    return f"/media/{key}"


def public_url(path: str | None) -> str | None:
    if not path:
        return None
    base = config.public_base()
    return f"{base}{path}" if base else path


def _field(lang: str) -> str:
    return "audio_path" if lang == "hi" else f"audio_path_{lang}"


def ensure_audio(case: dict, lang: str = "hi") -> str | None:
    """The case's voice note, made on first need (a relay joins, or someone opens the village page). Cached on the case."""
    field = _field(lang)
    if case.get(field):
        return case[field]
    from . import advice, store

    key = f"audio/{case['case_id']}.mp3" if lang == "hi" else f"audio/{case['case_id']}-{lang}.mp3"
    try:
        case[field] = synthesize(advice.voice_script(case, lang), key, lang)
        store.update_case(case["case_id"], **{field: case[field]})
        return case[field]
    except Exception as exc:  # noqa: BLE001 - text alerts still work without audio
        log.warning("polly failed for %s: %s", case.get("case_id"), exc)
        return None


def ensure_group_audio(cases: list[dict], lang: str = "hi") -> str | None:
    """One voice note for several cases that share an alert (e.g. E. coli and coliform in one village)."""
    if len(cases) == 1:
        return ensure_audio(cases[0], lang)
    from . import advice

    codes = "_".join(sorted(c["code"] for c in cases))
    key = f"audio/{cases[0]['village_key']}-{codes}-{lang}.mp3"
    try:
        config.client("s3").head_object(Bucket=config.bucket(), Key=f"media/{key}")
        return f"/media/{key}"
    except Exception:  # noqa: BLE001 - not made yet
        pass
    try:
        return synthesize(advice.voice_script(cases, lang), key, lang)
    except Exception as exc:  # noqa: BLE001
        log.warning("polly failed for %s: %s", key, exc)
        return None
