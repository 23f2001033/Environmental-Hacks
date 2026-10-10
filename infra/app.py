"""CDK entry point. Deploy: python scripts/build.py && npx -y aws-cdk@2 deploy (see docs/SETUP.md)."""

import os
import sys
from pathlib import Path

import aws_cdk as cdk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import JalSaathiStack  # noqa: E402

app = cdk.App()
JalSaathiStack(
    app,
    "JalSaathi",
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region="ap-south-1"),
    demo_clock=app.node.try_get_context("demo_clock") != "0",
    bot_username=app.node.try_get_context("bot_username") or "Srott_bot",
)
app.synth()
