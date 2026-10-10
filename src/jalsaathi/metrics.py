"""Business metrics in CloudWatch via Embedded Metric Format: a JSON log line becomes a metric, no API call needed.

Namespace JalSaathi. What happened to villages (cases opened, alerts sent, fixes, field tests, closures), what the
assistant did (questions, grounding, latency) and what Cedar decided. Shown on the JalSaathi CloudWatch dashboard.
"""

from __future__ import annotations

import json
import os
import time

NAMESPACE = "JalSaathi"


def emit(name: str, value: float = 1, unit: str = "Count", **dimensions: str) -> None:
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return  # only inside Lambda (keeps tests and scripts quiet)
    dims = {k: str(v) for k, v in dimensions.items() if v is not None}
    print(json.dumps({
        "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [
            {"Namespace": NAMESPACE, "Dimensions": [sorted(dims)], "Metrics": [{"Name": name, "Unit": unit}]}]},
        name: value, **dims}))


def enable_tracing() -> None:
    """X-Ray: trace every AWS SDK call from our Lambdas (DynamoDB, S3, Polly, Bedrock, Translate, Step Functions...).

    Only botocore is patched: plain HTTP is not, because Telegram API URLs carry the bot token.
    """
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("TRACING") != "1":
        return
    try:
        from aws_xray_sdk.core import patch, xray_recorder

        xray_recorder.configure(context_missing="IGNORE_ERROR")
        patch(["botocore"])
    except Exception:  # noqa: BLE001 - tracing must never break a case
        pass


enable_tracing()
