"""Runtime configuration from environment variables and SSM. AWS clients are created lazily and cached."""

from __future__ import annotations

import os
from functools import lru_cache

REGION = os.environ.get("AWS_REGION", "ap-south-1")
SSM_BOT_TOKEN = "/jalsaathi/telegram/bot-token"
SSM_WEBHOOK_SECRET = "/jalsaathi/telegram/webhook-secret"
SSM_CONSOLE_TOKEN = "/jalsaathi/console-token"


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def table_name() -> str:
    return env("TABLE_NAME", "jalsaathi")


def bucket() -> str:
    return env("BUCKET", "")


def state_machine_arn() -> str:
    return env("STATE_MACHINE_ARN", "")


def scale_run_arn() -> str:
    return env("SCALE_RUN_ARN", "")


def map_key_name() -> str:
    return env("MAP_KEY_NAME", "")


def demo_clock() -> bool:
    return env("DEMO_CLOCK", "0") == "1"


def public_base() -> str:
    """https://<cloudfront domain>, no trailing slash."""
    domain = env("PUBLIC_DOMAIN", "")
    return f"https://{domain}" if domain else ""


def bot_username() -> str:
    return env("BOT_USERNAME", "Srott_bot")


def kit_photo_required() -> bool:
    return env("KIT_PHOTO_REQUIRED", "1") == "1"


@lru_cache(maxsize=None)
def client(service: str):
    import boto3

    return boto3.client(service, region_name=REGION)


@lru_cache(maxsize=1)
def table():
    import boto3

    return boto3.resource("dynamodb", region_name=REGION).Table(table_name())


@lru_cache(maxsize=None)
def secret(name: str) -> str:
    return client("ssm").get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]


def village_url(village_key: str) -> str:
    base = public_base()
    return f"{base}/?v={village_key}" if base else ""


def join_link(prefix: str, key: str) -> str:
    return f"https://t.me/{bot_username()}?start={prefix}_{key}"
