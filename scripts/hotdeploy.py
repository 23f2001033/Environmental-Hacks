"""Deploy code and site changes without CDK synth (for when this machine is too low on memory to run jsii).

Pushes exactly what the CDK stack already declares, so the next `cdk deploy` finds nothing new to change:
Lambda code and dependency layer, the CloudFront routing function, S3 CORS for photo uploads, the API's Bedrock
permission, and the web app in frontend/dist. Run scripts/build.py and `npm run build` (in frontend/) first.

Usage: python scripts/hotdeploy.py [--code] [--infra] [--observability] [--site]   (no flags = everything)
"""

from __future__ import annotations

import io
import mimetypes
import re
import sys
import time
import zipfile
from pathlib import Path

import boto3

from _common import outputs

ROOT = Path(__file__).resolve().parent.parent
REGION = "ap-south-1"
FUNCTIONS = ("CaseSteps", "Ingest", "Webhook", "ApiHandler")


def _zip(folder: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                z.write(path, path.relative_to(folder).as_posix())
    return buf.getvalue()


def _functions(lam) -> dict[str, dict]:
    found = {}
    for page in lam.get_paginator("list_functions").paginate():
        for f in page["Functions"]:
            for short in FUNCTIONS:
                if f["FunctionName"].startswith(f"JalSaathi-{short}"):
                    found[short] = f
    return found


def deploy_code() -> None:
    lam = boto3.client("lambda", region_name=REGION)
    funcs = _functions(lam)
    layer_name = funcs["CaseSteps"]["Layers"][0]["Arn"].split(":layer:")[1].split(":")[0]
    stamp, published = ROOT / "build" / "layer" / ".requirements", ROOT / "build" / "layer" / ".published"
    current = funcs["CaseSteps"]["Layers"][0]["Arn"]
    if published.exists() and stamp.exists() and published.read_text().split("\n", 1)[1:] == [stamp.read_text()] \
            and published.read_text().split("\n", 1)[0] == current:
        layer = {"LayerVersionArn": current, "Version": current.rsplit(":", 1)[1]}
        print("layer unchanged", layer["Version"])
    else:
        # Through S3: the layer zip can be over Lambda's 50 MB direct-upload limit
        bucket, key = outputs()["BucketName"], "deploy/layer.zip"
        boto3.client("s3", region_name=REGION).put_object(Bucket=bucket, Key=key, Body=_zip(ROOT / "build" / "layer"))
        layer = lam.publish_layer_version(LayerName=layer_name, Content={"S3Bucket": bucket, "S3Key": key},
                                          CompatibleRuntimes=["python3.12"], CompatibleArchitectures=["arm64"],
                                          Description="hotdeploy")
        published.write_text(layer["LayerVersionArn"] + "\n" + stamp.read_text())
        print("layer", layer["Version"])
    code = _zip(ROOT / "build" / "lambda")
    for short, f in funcs.items():
        name = f["FunctionName"]
        lam.update_function_code(FunctionName=name, ZipFile=code)
        lam.get_waiter("function_updated_v2").wait(FunctionName=name)
        lam.update_function_configuration(FunctionName=name, Layers=[layer["LayerVersionArn"]])
        lam.get_waiter("function_updated_v2").wait(FunctionName=name)
        print("updated", short)


def deploy_infra() -> None:
    out = outputs()
    account = boto3.client("sts").get_caller_identity()["Account"]
    funcs = _functions(boto3.client("lambda", region_name=REGION))
    api_role = funcs["ApiHandler"]["Role"].split("/")[-1]
    webhook = funcs["Webhook"]
    iam = boto3.client("iam")
    ask = ('{"Version":"2012-10-17","Statement":['
           '{"Effect":"Allow","Action":"translate:TranslateText","Resource":"*"},'
           f'{{"Effect":"Allow","Action":"bedrock:ApplyGuardrail","Resource":"arn:aws:bedrock:{REGION}:{account}:guardrail/*"}}')
    iam.put_role_policy(RoleName=api_role, PolicyName="ask-jalsaathi", PolicyDocument=ask + "]}")
    iam.put_role_policy(RoleName=webhook["Role"].split("/")[-1], PolicyName="ask-jalsaathi", PolicyDocument=ask + (
        ',{"Effect":"Allow","Action":"transcribe:StartStreamTranscription","Resource":"*"},'
        f'{{"Effect":"Allow","Action":"lambda:InvokeFunction","Resource":"{webhook["FunctionArn"]}"}}]}}'))
    lam = boto3.client("lambda", region_name=REGION)
    lam.update_function_configuration(FunctionName=webhook["FunctionName"], Timeout=90, MemorySize=1024)
    lam.get_waiter("function_updated_v2").wait(FunctionName=webhook["FunctionName"])
    print("ask jalsaathi: permissions, webhook 90 s / 1024 MB")
    boto3.client("iam").put_role_policy(RoleName=api_role, PolicyName="app-photo-hint-bedrock", PolicyDocument=(
        '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"bedrock:InvokeModel","Resource":['
        f'"arn:aws:bedrock:{REGION}:{account}:inference-profile/apac.amazon.nova-pro-v1:0",'
        '"arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0"]}]}'))
    print("api role: bedrock")
    boto3.client("s3", region_name=REGION).put_bucket_cors(Bucket=out["BucketName"], CORSConfiguration={"CORSRules": [
        {"AllowedMethods": ["PUT"], "AllowedOrigins": ["*"], "AllowedHeaders": ["*"], "MaxAgeSeconds": 3000}]})
    print("bucket: cors")
    stack = (ROOT / "infra" / "stack.py").read_text(encoding="utf-8")
    body = re.search(r"INDEX_REWRITE = \(\r?\n(.*?)\r?\n\)", stack, re.S).group(1)
    js = "".join(re.findall(r'"(.*)"', body))
    cf = boto3.client("cloudfront")
    name = next(i["Name"] for i in cf.list_functions()["FunctionList"]["Items"] if "IndexRewrite" in i["Name"])
    current = cf.describe_function(Name=name, Stage="DEVELOPMENT")
    updated = cf.update_function(Name=name, IfMatch=current["ETag"], FunctionCode=js.encode(),
                                 FunctionConfig=current["FunctionSummary"]["FunctionConfig"])
    cf.publish_function(Name=name, IfMatch=updated["ETag"])
    print("cloudfront function: published")


def deploy_observability() -> None:
    """X-Ray tracing on every function and both state machines, and the JalSaathi CloudWatch dashboard."""
    import json
    sys.path.insert(0, str(ROOT / "infra"))
    from dashboard import body

    out = outputs()
    lam, iam = boto3.client("lambda", region_name=REGION), boto3.client("iam")
    sfn = boto3.client("stepfunctions", region_name=REGION)
    xray = ('{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["xray:PutTraceSegments",'
            '"xray:PutTelemetryRecords","xray:GetSamplingRules","xray:GetSamplingTargets"],"Resource":"*"}]}')
    funcs = _functions(lam)
    for short, f in funcs.items():
        iam.put_role_policy(RoleName=f["Role"].split("/")[-1], PolicyName="xray-tracing", PolicyDocument=xray)
        cfg = lam.get_function_configuration(FunctionName=f["FunctionName"])
        variables = {**cfg.get("Environment", {}).get("Variables", {}), "TRACING": "1"}
        lam.update_function_configuration(FunctionName=f["FunctionName"], TracingConfig={"Mode": "Active"},
                                          Environment={"Variables": variables})
        lam.get_waiter("function_updated_v2").wait(FunctionName=f["FunctionName"])
    for arn in (out["StateMachineArn"], out["ScaleRunArn"]):
        role = sfn.describe_state_machine(stateMachineArn=arn)["roleArn"].split("/")[-1]
        iam.put_role_policy(RoleName=role, PolicyName="xray-tracing", PolicyDocument=xray)
        sfn.update_state_machine(stateMachineArn=arn, tracingConfiguration={"enabled": True})
    dash = body(REGION, {k: v["FunctionName"] for k, v in funcs.items()}, out["StateMachineArn"], out["ScaleRunArn"])
    msgs = boto3.client("cloudwatch", region_name=REGION).put_dashboard(
        DashboardName="JalSaathi", DashboardBody=json.dumps(dash)).get("DashboardValidationMessages")
    print("observability: X-Ray on", len(funcs), "functions + 2 state machines; dashboard", msgs or "ok")


def deploy_site() -> None:
    out = outputs()
    _upload(out, ROOT / "frontend" / "dist", "site/")
    if (ROOT / "app" / "dist" / "index.html").exists():
        _upload(out, ROOT / "app" / "dist", "site/app/")
    domain = out["SiteUrl"].replace("https://", "")
    cf = boto3.client("cloudfront")
    dist_id = next(d["Id"] for d in cf.list_distributions()["DistributionList"]["Items"] if d["DomainName"] == domain)
    cf.create_invalidation(DistributionId=dist_id, InvalidationBatch={
        "Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": str(time.time())})
    print("site: uploaded and invalidated")


def _upload(out: dict, dist: Path, prefix: str) -> None:
    s3 = boto3.client("s3", region_name=REGION)
    for path in sorted(dist.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(dist).as_posix()
        ctype = mimetypes.guess_type(rel)[0] or "application/octet-stream"
        if rel.endswith(".webmanifest"):
            ctype = "application/manifest+json"
        cache = "public, max-age=31536000, immutable" if rel.startswith("assets/") else "no-cache"
        s3.put_object(Bucket=out["BucketName"], Key=f"{prefix}{rel}", Body=path.read_bytes(), ContentType=ctype,
                      CacheControl=cache)
    print(f"uploaded {dist.parent.name} -> {prefix}")


if __name__ == "__main__":
    flags = set(sys.argv[1:]) or {"--code", "--infra", "--observability", "--site"}
    if "--code" in flags:
        deploy_code()
    if "--infra" in flags:
        deploy_infra()
    if "--observability" in flags:
        deploy_observability()
    if "--site" in flags:
        deploy_site()
