"""Rough AWS cost of an ingest run, with the assumptions written next to the number (shown in /stats)."""

from __future__ import annotations

# Approximate on-demand list prices, USD, ap-south-1, October 2026. Free tier ignored. Check the pricing pages before quoting.
PRICES = {
    "sfn_standard_per_1k_transitions": 0.025,
    "sfn_express_per_1m_requests": 1.00,
    "lambda_arm_per_gb_second": 0.0000133334,
    "lambda_per_1m_requests": 0.20,
    "ddb_per_1m_writes": 1.25,
    "polly_neural_per_1m_chars": 16.00,
    "geocode_per_1k": 0.50,
}

# Per case, from opening to waiting for the engineer: Init, Alert, AwaitFix (3 Lambda calls, ~8 state transitions).
PER_CASE = {"transitions": 8, "lambda_calls": 3, "lambda_seconds": 0.6, "lambda_gb": 0.5, "writes": 10}
VOICE_CHARS = 600


def estimate(cases: int, audio: int, geocodes: int, scale_items: int = 0) -> dict:
    p = PRICES
    parts = {
        "step_functions": cases * PER_CASE["transitions"] / 1000 * p["sfn_standard_per_1k_transitions"]
                          + scale_items * 2 / 1e6 * p["sfn_express_per_1m_requests"],
        "lambda": cases * PER_CASE["lambda_calls"] * (PER_CASE["lambda_seconds"] * PER_CASE["lambda_gb"] * p["lambda_arm_per_gb_second"]
                                                      + p["lambda_per_1m_requests"] / 1e6),
        "dynamodb": cases * PER_CASE["writes"] / 1e6 * p["ddb_per_1m_writes"],
        "polly": audio * VOICE_CHARS / 1e6 * p["polly_neural_per_1m_chars"],
        "geocoding": geocodes / 1000 * p["geocode_per_1k"],
    }
    total = sum(parts.values())
    return {
        "usd_total": round(total, 4),
        "usd_per_case": round(total / cases, 6) if cases else None,
        "usd_by_service": {k: round(v, 4) for k, v in parts.items()},
        "assumptions": {
            "prices": "approximate on-demand list prices, ap-south-1, Oct 2026; free tier ignored",
            "per_case": PER_CASE, "voice_chars": VOICE_CHARS, "audio_generated": audio, "geocode_calls": geocodes,
            "excludes": "waiting time (free), later escalations, Telegram (free), CloudFront and S3 storage",
        },
    }
