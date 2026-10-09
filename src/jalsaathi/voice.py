"""Hindi voice notes with Amazon Polly (Kajal, hi-IN), stored under media/ so CloudFront can serve them."""

from __future__ import annotations

from . import config

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
