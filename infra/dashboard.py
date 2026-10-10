"""The JalSaathi CloudWatch dashboard: what the system did for villages first, then how AWS ran it.

One builder for both the CDK stack (names are tokens there) and scripts/hotdeploy.py (real names).
Business metrics come from src/jalsaathi/metrics.py (Embedded Metric Format, namespace JalSaathi).
"""

from __future__ import annotations

import hashlib

NS = "JalSaathi"


def _id(prefix: str, text: str) -> str:
    return prefix + hashlib.md5(text.encode()).hexdigest()[:10]  # stable across runs (no CDK diff noise)


def _search(metric: str, dims: str, stat: str = "Sum", period: int = 3600, label: str = "") -> dict:
    expr = f"SEARCH('{{{NS},{dims}}} MetricName=\"{metric}\"', '{stat}', {period})"
    return {"expression": expr, "label": label or metric, "id": _id("e", expr + stat)}


def _total(metric: str, dims: str, label: str, period: int = 86400) -> dict:
    s = _search(metric, dims, "Sum", period)
    return {"expression": f"SUM({s['expression']})", "label": label, "id": _id("t", s["expression"])}


def _widget(x: int, y: int, w: int, h: int, title: str, metrics: list, view: str = "timeSeries", stat: str = "Sum",
            period: int = 3600, region: str = "ap-south-1", **extra) -> dict:
    return {"type": "metric", "x": x, "y": y, "width": w, "height": h, "properties": {
        "title": title, "view": view, "stat": stat, "period": period, "region": region, "metrics": metrics,
        "stacked": False, **extra}}


def body(region: str, functions: dict[str, str], case_machine_arn: str, scale_machine_arn: str) -> dict:
    expr = lambda e: [e]  # noqa: E731 - a metrics row that is a math/search expression
    impact = [
        expr(_total("CasesOpened", "Class,Severity", "Cases opened")),
        expr(_total("AlertsSent", "", "Alerts sent (Telegram + app)")),
        expr(_total("FixesLogged", "Action", "Fixes logged")),
        expr(_total("FieldTests", "Result", "Field-kit re-tests")),
        expr(_total("CasesClosed", "", "Closed by lab re-test")),
        expr(_total("Escalations", "Reason", "Deadlines missed → escalated")),
        expr(_total("DistrictEmails", "District", "District officials emailed")),
    ]
    widgets = [
        {"type": "text", "x": 0, "y": 0, "width": 24, "height": 3, "properties": {"markdown": (
            "# JalSaathi · live\n"
            "Failed government drinking-water lab tests → village alerts in Hindi and English → engineer's fix → re-test. "
            "**Every number here is emitted by the system as it works** (CloudWatch Embedded Metric Format), followed by "
            "the AWS services running it. Traces: X-Ray service map.")}},
        _widget(0, 3, 24, 4, "What happened to villages (last 24 h)", impact, view="singleValue", period=86400,
                region=region),
        _widget(0, 7, 8, 6, "Ask JalSaathi: questions", [
            expr(_search("Questions", "Outcome", label="")),
        ], region=region),
        _widget(8, 7, 8, 6, "Ask JalSaathi: grounding score (Bedrock Guardrails)", [
            expr(_search("GroundingScore", "", "Average", 3600, "Average grounding")),
            expr(_search("GroundingScore", "", "Minimum", 3600, "Lowest grounding")),
        ], region=region, yAxis={"left": {"min": 0, "max": 1}}),
        _widget(16, 7, 8, 6, "Ask JalSaathi: answer time (ms)", [
            expr(_search("AnswerLatency", "", "p50", 3600, "p50")),
            expr(_search("AnswerLatency", "", "p95", 3600, "p95")),
        ], region=region),
        _widget(0, 13, 12, 6, "Cedar decisions (deny = a rule stopped an unsafe action)", [
            expr(_search("CedarDecisions", "Action,Decision", label="")),
        ], view="bar", period=86400, region=region),
        _widget(12, 13, 12, 6, "Step Functions: case workflows", [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", case_machine_arn, {"label": "Case workflows started"}],
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", case_machine_arn, {"label": "Closed (succeeded)"}],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", case_machine_arn, {"label": "Failed"}],
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", scale_machine_arn, {"label": "Scale runs"}],
        ], region=region),
        _widget(0, 19, 12, 6, "Lambda: invocations and errors", [
            m for short, name in functions.items() for m in (
                ["AWS/Lambda", "Invocations", "FunctionName", name, {"label": f"{short} invocations"}],
                ["AWS/Lambda", "Errors", "FunctionName", name, {"label": f"{short} errors"}],
            )
        ], region=region),
        _widget(12, 19, 12, 6, "Lambda: duration p95 (ms) and throttles", [
            m for short, name in functions.items() for m in (
                ["AWS/Lambda", "Duration", "FunctionName", name, {"stat": "p95", "label": f"{short} p95"}],
                ["AWS/Lambda", "Throttles", "FunctionName", name, {"label": f"{short} throttles"}],
            )
        ], region=region),
        _widget(0, 25, 8, 6, "Amazon Bedrock (Nova Pro): calls", [
            expr({"expression": "SEARCH('{AWS/Bedrock,ModelId} MetricName=\"Invocations\"', 'Sum', 3600)",
                  "label": "", "id": "bedrock"}),
        ], region=region),
        _widget(8, 25, 8, 6, "Amazon Polly: characters spoken", [
            expr({"expression": "SEARCH('{AWS/Polly,Operation} MetricName=\"RequestCharacters\"', 'Sum', 3600)",
                  "label": "", "id": "polly"}),
        ], region=region),
        _widget(16, 25, 8, 6, "Voice notes made (Polly) by language", [
            expr(_search("VoiceNotes", "Lang", label="")),
        ], region=region),
    ]
    return {"start": "-P1D", "widgets": widgets}
