"""Set up the district digest email (Amazon SES): sender, recipients, and SES identities.

SES starts in sandbox: every sender and recipient must be a verified identity, so this asks SES to email each address a
verification link (click it once). Settings go to SSM, never into code:
  /jalsaathi/email-sender      the From address
  /jalsaathi/district-emails   {"<district>": [...], "*": [...]}  ("*" receives every district's digest)

Usage:
  python scripts/setup_email.py --sender you@example.org --to a@example.org,b@example.org [--district Hardoi]
  python scripts/setup_email.py --status
"""

from __future__ import annotations

import argparse
import json

import boto3

REGION = "ap-south-1"


def identity_status(ses, address: str) -> str:
    try:
        return "verified" if ses.get_email_identity(EmailIdentity=address)["VerifiedForSendingStatus"] else "pending"
    except ses.exceptions.NotFoundException:
        return "missing"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sender")
    ap.add_argument("--to", help="comma-separated recipients")
    ap.add_argument("--district", default="*", help="district these recipients cover ('*' = all)")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    ses, ssm = boto3.client("sesv2", region_name=REGION), boto3.client("ssm", region_name=REGION)

    if not args.status:
        recipients = [a.strip() for a in (args.to or "").split(",") if a.strip()]
        if not args.sender or not recipients:
            ap.error("--sender and --to are required")
        for address in [args.sender, *recipients]:
            if identity_status(ses, address) == "missing":
                ses.create_email_identity(EmailIdentity=address)
                print("verification email sent to", address)
        try:
            current = json.loads(ssm.get_parameter(Name="/jalsaathi/district-emails")["Parameter"]["Value"])
        except ssm.exceptions.ParameterNotFound:
            current = {}
        current[args.district] = sorted(set(current.get(args.district, []) + recipients))
        ssm.put_parameter(Name="/jalsaathi/district-emails", Value=json.dumps(current), Type="String", Overwrite=True)
        ssm.put_parameter(Name="/jalsaathi/email-sender", Value=args.sender, Type="String", Overwrite=True)

    try:
        current = json.loads(ssm.get_parameter(Name="/jalsaathi/district-emails")["Parameter"]["Value"])
        sender = ssm.get_parameter(Name="/jalsaathi/email-sender")["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        print("not configured yet")
        return
    print("sender:", sender, identity_status(ses, sender))
    for district, addresses in current.items():
        for address in addresses:
            print(f"  {district}: {address} ({identity_status(ses, address)})")
    print("sandbox:", not ses.get_account()["ProductionAccessEnabled"])


if __name__ == "__main__":
    main()
