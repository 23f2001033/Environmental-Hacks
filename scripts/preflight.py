"""One command: is the live system ready to test or record? Prints PASS/WARN/FAIL per check, never a secret."""

import sys

import boto3
from _common import REGION, api, outputs, secret, telegram

results = []


def check(name, fn):
    try:
        ok, detail = fn()
        results.append(("PASS" if ok is True else "WARN" if ok is None else "FAIL", name, detail))
    except Exception as exc:  # noqa: BLE001
        results.append(("FAIL", name, str(exc)[:160]))


def secrets():
    for name in ("/jalsaathi/telegram/bot-token", "/jalsaathi/telegram/webhook-secret", "/jalsaathi/console-token"):
        secret(name)
    return True, "3 SSM parameters readable"


def health():
    code, body = api("/health")
    return code == 200 and body.get("ok"), f"HTTP {code}, demo_clock={body.get('demo_clock')}, bot=@{body.get('bot')}"


def webhook():
    info = telegram("getWebhookInfo")["result"]
    same = info.get("url") == outputs()["WebhookUrl"]
    err = info.get("last_error_message")
    return (same and not err) if same else False, f"url matches={same}, pending={info.get('pending_update_count')}, last error={err}"


def data():
    s = api("/stats")[1]
    if s["villages"] == 0:
        return None, "no villages yet: run python scripts/demo.py seed"
    return True, f"{s['villages']} villages, {s['open_cases']} open, {s['closed_cases']} closed, status={s['by_status']}"


def workflows():
    sfn = boto3.client("stepfunctions", region_name=REGION)
    arn = outputs()["StateMachineArn"]
    failed = sfn.list_executions(stateMachineArn=arn, statusFilter="FAILED", maxResults=20)["executions"]
    running = sfn.list_executions(stateMachineArn=arn, statusFilter="RUNNING", maxResults=100)["executions"]
    return (None if failed else True), f"{len(running)} running, {len(failed)} recently failed"


def concurrency():
    limit = boto3.client("lambda", region_name=REGION).get_account_settings()["AccountLimit"]["ConcurrentExecutions"]
    return (True if limit >= 100 else None), f"Lambda concurrency limit {limit} (10 means a new account; ask for an increase)"


for name, fn in [("secrets", secrets), ("api health", health), ("telegram webhook", webhook), ("demo data", data),
                 ("case workflows", workflows), ("lambda concurrency", concurrency)]:
    check(name, fn)
for status, name, detail in results:
    print(f"{status:4}  {name:20} {detail}")
print("\nSite:", outputs()["SiteUrl"], "· Test console:", outputs()["TestUiUrl"])
sys.exit(1 if any(r[0] == "FAIL" for r in results) else 0)
