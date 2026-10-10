"""Create (once) the Bedrock guardrail that checks every 'Ask JalSaathi' answer, and record its id in SSM.

The answer must be grounded in the facts the agent looked up (contextual grounding); content
filters and PII masking apply too. Grounding is what stops a false all-clear or a medicine name: neither is in our facts.
(Denied topics and the relevance filter were tried and dropped: topics block any answer that merely discusses the
subject, e.g. "not fixed yet", and relevance scored correct answers to "is it fixed?" near zero.)
Safe to re-run.
Usage: python scripts/setup_guardrail.py
"""

from __future__ import annotations

import boto3

REGION = "ap-south-1"
NAME = "jalsaathi-answers"
SSM_NAME = "/jalsaathi/guardrail"

BLOCKED = ("I can't answer that safely. Please follow the steps in your village alert, and ask your ASHA worker "
           "or the block engineer.")


def main() -> None:
    bedrock = boto3.client("bedrock", region_name=REGION)
    existing = next((g for g in bedrock.list_guardrails()["guardrails"] if g["name"] == NAME), None)
    config = dict(
            description="Checks JalSaathi's answers to villagers: grounded in their case data.",
            contentPolicyConfig={"filtersConfig": [
                {"type": t, "inputStrength": "HIGH", "outputStrength": "HIGH"}
                for t in ("HATE", "INSULTS", "SEXUAL", "VIOLENCE", "MISCONDUCT")
            ] + [{"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"}]},
            sensitiveInformationPolicyConfig={"piiEntitiesConfig": [
                {"type": "PHONE", "action": "ANONYMIZE"}, {"type": "EMAIL", "action": "ANONYMIZE"}]},
            contextualGroundingPolicyConfig={"filtersConfig": [
                {"type": "GROUNDING", "threshold": 0.7}]},
            blockedInputMessaging=BLOCKED,
            blockedOutputsMessaging=BLOCKED,
    )
    if existing:
        gid = existing["id"]
        bedrock.update_guardrail(guardrailIdentifier=gid, name=NAME, **config)
        print("guardrail updated:", gid)
    else:
        gid = bedrock.create_guardrail(name=NAME, **config)["guardrailId"]
        print("guardrail created:", gid)
    version = bedrock.create_guardrail_version(guardrailIdentifier=gid, description="published by setup_guardrail.py")["version"]
    boto3.client("ssm", region_name=REGION).put_parameter(Name=SSM_NAME, Value=f"{gid}:{version}", Type="String",
                                                          Overwrite=True)
    print(f"{SSM_NAME} = {gid}:{version}")


if __name__ == "__main__":
    main()
