"""District digest: one email per district official listing overdue water cases (Amazon SES, on an EventBridge schedule).

An escalation on Telegram reaches the block engineer; this reaches the person above them. One email per district per
run, and only when something changed since the last one, so a demo clock that escalates every few minutes never floods.
Recipients live in SSM (/jalsaathi/district-emails, JSON: {"Hardoi": ["..."], "*": ["..."]}; "*" gets every district)
and the sender in /jalsaathi/email-sender. While SES is in sandbox, both must be verified identities.
"""

from __future__ import annotations

import html
import json
import logging
from datetime import date

from . import advice, config, metrics, rules, store

log = logging.getLogger()

SSM_RECIPIENTS = "/jalsaathi/district-emails"
SSM_SENDER = "/jalsaathi/email-sender"


def overdue(cases: list[dict]) -> dict[str, list[dict]]:
    """Open cases whose deadline has passed at least once, grouped by district, worst first."""
    out: dict[str, list[dict]] = {}
    for c in cases:
        if c.get("status") in store.OPEN_STATUSES and (c.get("status") == "ESCALATED" or int(c.get("escalations") or 0) > 0):
            out.setdefault(c.get("district") or "?", []).append(c)
    for rows in out.values():
        rows.sort(key=lambda c: (rules.SEVERITY_ORDER.get(c.get("severity"), 9), -int(c.get("escalations") or 0)))
    return out


def _days(iso: str | None) -> str:
    if not iso:
        return "?"
    return str((date.today() - date.fromisoformat(iso[:10])).days)


def render(district: str, rows: list[dict]) -> tuple[str, str, str]:
    """(subject, text, html) for one district."""
    base = config.public_base()
    subject = f"JalSaathi · {district}: {len(rows)} overdue drinking-water case{'s' if len(rows) != 1 else ''} need action"
    lines = [f"{len(rows)} village drinking-water case(s) in {district} have missed their deadline.",
             "Each failed a government lab test (JJM-WQMIS). A case closes only when a lab re-test passes.", ""]
    trs = []
    for c in rows:
        name = advice.name(c["code"], "en")
        value = f"{c.get('value')} {(c.get('unit') or '').replace('/ ', '/')}".strip()
        days = _days(c.get("lab_approval"))
        lines.append(f"- {c['village']} ({c.get('block')}): {name} {value}, lab test {days} days ago, "
                     f"escalated {c.get('escalations', 0)} time(s). {base}/?v={c['village_key']}")
        trs.append(
            "<tr>" + "".join(f"<td style='padding:8px;border-bottom:1px solid #e7e0d0'>{cell}</td>" for cell in (
                f"<a href='{base}/?v={html.escape(str(c['village_key']))}'>{html.escape(c['village'])}</a>",
                html.escape(c.get("block") or ""), html.escape(name), html.escape(value), days,
                str(c.get("escalations", 0)))) + "</tr>")
    lines += ["", f"All districts and the live activity feed: {base}/app/officials",
              "JalSaathi relays government test information; it does not certify water."]
    head = "".join(f"<th style='text-align:left;padding:8px;border-bottom:2px solid #173f55'>{h}</th>" for h in (
        "Village", "Block", "Contaminant", "Measured", "Days since lab test", "Escalations"))
    body = (f"<div style='font-family:Arial,sans-serif;color:#173f55;max-width:720px'>"
            f"<h2 style='margin:0 0 6px'>{len(rows)} overdue drinking-water case{'s' if len(rows) != 1 else ''} in "
            f"{html.escape(district)}</h2><p>Each failed a government lab test (JJM-WQMIS) and missed the fix deadline. "
            f"A case closes only when a lab re-test passes.</p><table style='border-collapse:collapse;width:100%;font-size:14px'>"
            f"<tr>{head}</tr>{''.join(trs)}</table><p><a href='{base}/app/officials'>Open the officials' view</a></p>"
            f"<p style='color:#566d79;font-size:12px'>JalSaathi relays government test information; it does not certify "
            f"water.</p></div>")
    return subject, "\n".join(lines), body


def _settings() -> tuple[dict, str] | None:
    try:
        return json.loads(config.secret(SSM_RECIPIENTS)), config.secret(SSM_SENDER)
    except Exception:  # noqa: BLE001 - not configured: the digest is optional
        return None


def run(force: bool = False) -> dict:
    settings = _settings()
    if not settings:
        log.info("district digest skipped: no recipients configured")
        return {"sent": 0, "skipped": "not configured"}
    recipients, sender = settings
    sent, districts = 0, overdue(store.list_cases())
    for district, rows in districts.items():
        to = sorted(set(recipients.get(district, []) + recipients.get("*", [])))
        if not to:
            continue
        last = store.digest_sent_at(district)
        if not force and last and all((c.get("updated_at") or "") <= last for c in rows):
            continue  # nothing new since the last email
        subject, text, body = render(district, rows)
        config.client("sesv2").send_email(
            FromEmailAddress=sender, Destination={"ToAddresses": to},
            Content={"Simple": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}, "Html": {"Data": body}}}})
        store.set_digest_sent(district)
        for c in rows:
            store.add_event(c["case_id"], "district_notified", note=f"overdue case emailed to the {district} district official")
        metrics.emit("DistrictEmails", len(to), District=district)
        sent += 1
    return {"sent": sent, "districts_overdue": len(districts)}
