"""Hindi voice notes with Amazon Polly (Kajal, hi-IN), stored under media/ so CloudFront can serve them."""

from __future__ import annotations

import logging

from . import config

log = logging.getLogger()

VOICE_ID = "Kajal"


def synthesize(text: str, key: str) -> str:
    """Write an MP3 to s3://BUCKET/media/<key> and return its public URL path (/media/<key>)."""
    polly = config.client("polly")
    audio = polly.synthesize_speech(Text=text[:2900], VoiceId=VOICE_ID, Engine="neural", LanguageCode="hi-IN",
                                    OutputFormat="mp3")["AudioStream"].read()
    config.client("s3").put_object(Bucket=config.bucket(), Key=f"media/{key}", Body=audio, ContentType="audio/mpeg",
                                   CacheControl="max-age=300")
    return f"/media/{key}"


def public_url(path: str | None) -> str | None:
    if not path:
        return None
    base = config.public_base()
    return f"{base}{path}" if base else path


def ensure_audio(case: dict) -> str | None:
    """The case's voice note, made on first need (a relay joins, or someone opens the village page). Cached on the case."""
    if case.get("audio_path"):
        return case["audio_path"]
    from . import advice, store

    try:
        case["audio_path"] = synthesize(advice.voice_script(case), f"audio/{case['case_id']}.mp3")
        store.update_case(case["case_id"], audio_path=case["audio_path"])
        return case["audio_path"]
    except Exception as exc:  # noqa: BLE001 - text alerts still work without audio
        log.warning("polly failed for %s: %s", case.get("case_id"), exc)
        return None
