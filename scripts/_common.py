"""Shared helpers for scripts: stack outputs and secrets, without ever printing a secret."""

from __future__ import annotations

import json
import urllib.request
from functools import lru_cache

import boto3

REGION = "ap-south-1"
STACK = "JalSaathi"


@lru_cache(maxsize=1)
def outputs() -> dict:
    stack = boto3.client("cloudformation", region_name=REGION).describe_stacks(StackName=STACK)["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}


@lru_cache(maxsize=None)
def secret(name: str) -> str:
    return boto3.client("ssm", region_name=REGION).get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]


def telegram(method: str, **params) -> dict:
    url = f"https://api.telegram.org/bot{secret('/jalsaathi/telegram/bot-token')}/{method}"
    req = urllib.request.Request(url, data=json.dumps(params).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def api(path: str, method: str = "GET", body: dict | None = None, admin: bool = False) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if admin:
        headers["x-admin-token"] = secret("/jalsaathi/console-token")
    req = urllib.request.Request(outputs()["ApiBase"] + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")
