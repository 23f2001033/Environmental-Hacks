"""The whole JalSaathi system in one stack (docs/BUILD_PLAN.md section 1)."""

from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integ
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_location as location
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3d
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

ROOT = Path(__file__).resolve().parent.parent

# The web app is a single-page app: every page path without a file extension (/village/412558, /officials) serves
# /index.html. The test console keeps its own directory index: /test/ -> /test/index.html.
INDEX_REWRITE = (
    "function handler(event){var r=event.request;var u=r.uri;var last=u.split('/').pop();"
    "if(u==='/test'||u.indexOf('/test/')===0){if(u.endsWith('/')){r.uri=u+'index.html';}"
    "else if(last.indexOf('.')===-1){r.uri=u+'/index.html';}return r;}"
    "if(u==='/app'||u.indexOf('/app/')===0){if(last.indexOf('.')===-1){r.uri='/app/index.html';}return r;}"
    "if(last.indexOf('.')===-1){r.uri='/index.html';}"
    "return r;}"
)


class JalSaathiStack(Stack):
    def __init__(self, scope: Construct, cid: str, *, demo_clock: bool, bot_username: str, **kwargs) -> None:
        super().__init__(scope, cid, **kwargs)

        # Storage
        table = ddb.Table(
            self, "Table",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )
        table.add_global_secondary_index(
            index_name="gsi1",
            partition_key=ddb.Attribute(name="gsi1pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="gsi1sk", type=ddb.AttributeType.STRING),
        )
        bucket = s3.Bucket(
            self, "Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # Relays upload field-kit photos straight from the app with a 5-minute presigned PUT URL
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT], allowed_origins=["*"], allowed_headers=["*"],
                              max_age=3000)],
        )

        # Web: CloudFront in front of the site (s3://bucket/site), media (s3://bucket/media) and the API (/api/*)
        http_api = apigw.HttpApi(
            self, "Api",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"], allow_methods=[apigw.CorsHttpMethod.ANY], allow_headers=["content-type", "x-admin-token"]
            ),
        )
        api_origin = origins.HttpOrigin(f"{http_api.api_id}.execute-api.{self.region}.amazonaws.com")
        index_fn = cf.Function(self, "IndexRewrite", code=cf.FunctionCode.from_inline(INDEX_REWRITE),
                               runtime=cf.FunctionRuntime.JS_2_0)
        dist = cf.Distribution(
            self, "Web",
            default_root_object="index.html",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket, origin_path="/site"),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
                function_associations=[cf.FunctionAssociation(function=index_fn, event_type=cf.FunctionEventType.VIEWER_REQUEST)],
            ),
            additional_behaviors={
                "/api/*": cf.BehaviorOptions(
                    origin=api_origin,
                    allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                ),
                "/media/*": cf.BehaviorOptions(
                    origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
                ),
            },
        )

        # Code
        layer = lambda_.LayerVersion(
            self, "Deps",
            code=lambda_.Code.from_asset(str(ROOT / "build" / "layer")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.ARM_64],
        )
        code = lambda_.Code.from_asset(str(ROOT / "build" / "lambda"))
        env = {
            "TABLE_NAME": table.table_name,
            "BUCKET": bucket.bucket_name,
            "DEMO_CLOCK": "1" if demo_clock else "0",
            "PUBLIC_DOMAIN": dist.distribution_domain_name,
            "BOT_USERNAME": bot_username,
        }
        ssm_policy = iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/jalsaathi/*"],
        )

        def fn(name: str, handler: str, timeout: int = 30, memory: int = 512, extra: dict | None = None) -> lambda_.Function:
            f = lambda_.Function(
                self, name,
                runtime=lambda_.Runtime.PYTHON_3_12,
                architecture=lambda_.Architecture.ARM_64,
                handler=handler,
                code=code,
                layers=[layer],
                timeout=Duration.seconds(timeout),
                memory_size=memory,
                environment={**env, **(extra or {})},
                log_group=logs.LogGroup(self, f"{name}Logs", retention=logs.RetentionDays.TWO_WEEKS,
                                        removal_policy=RemovalPolicy.DESTROY),
            )
            table.grant_read_write_data(f)
            bucket.grant_read_write(f)
            f.add_to_role_policy(ssm_policy)
            return f

        steps_fn = fn("CaseSteps", "jalsaathi.case_steps.handler", timeout=60)
        steps_fn.add_to_role_policy(iam.PolicyStatement(actions=["polly:SynthesizeSpeech"], resources=["*"]))

        # Case workflow (docs/BUILD_PLAN.md section 5)
        def step(sid: str, name: str, *, wait: bool = False, timeout_path: str | None = None, result_path=None,
                 extra: dict | None = None):
            payload = {"step": name, "case_id": sfn.JsonPath.string_at("$.case_id"), **(extra or {})}
            mode = {"payload_response_only": True}
            if wait:
                payload["token"] = sfn.JsonPath.task_token
                mode = {"integration_pattern": sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN}
            task = tasks.LambdaInvoke(
                self, sid,
                lambda_function=steps_fn,
                payload=sfn.TaskInput.from_object(payload),
                result_path=result_path or sfn.JsonPath.DISCARD,
                task_timeout=sfn.Timeout.at(timeout_path) if timeout_path else None,
                retry_on_service_exceptions=True,
                **mode,
            )
            # New accounts start with a Lambda concurrency limit of 10, so many cases at once get throttled.
            task.add_retry(errors=["Lambda.TooManyRequestsException"], interval=Duration.seconds(2), backoff_rate=2,
                           max_attempts=10, max_delay=Duration.seconds(60), jitter_strategy=sfn.JitterType.FULL)
            return task

        init = step("Init", "init")
        alert = step("Alert", "alert")
        reopen = step("Reopen", "reopen")
        provisional = step("MarkProvisional", "provisional")
        close = step("Close", "close")

        def waiting(sid: str, name: str, kind: str, timer: str, result: str):
            """A wait step that escalates on each deadline, at most 3 times, then keeps waiting without a deadline."""
            timed = step(sid, name, wait=True, timeout_path=f"$.timers.{timer}", result_path=result)
            final = step(f"{sid}NoDeadline", name, wait=True, result_path=result, extra={"no_deadline": True})
            escalate = step(f"{sid}Escalate", "escalate", result_path="$.esc", extra={"reason": kind})
            timed.add_catch(escalate, errors=["States.Timeout"], result_path="$.timeout")
            escalate.next(sfn.Choice(self, f"{sid}EscalationLimit")
                          .when(sfn.Condition.number_greater_than_equals("$.esc.escalations", 3), final)
                          .otherwise(timed))
            return timed, final

        await_fix, await_fix_final = waiting("AwaitFix", "await_fix", "fix", "fix_seconds", "$.fix")
        await_kit, await_kit_final = waiting("AwaitKit", "await_kit", "retest", "retest_seconds", "$.kit")
        await_lab, await_lab_final = waiting("AwaitLab", "await_lab", "lab", "lab_seconds", "$.lab")
        reopen.next(await_fix)

        kit_choice = (sfn.Choice(self, "KitResult")
                      .when(sfn.Condition.string_equals("$.kit.result", "clean"), provisional)
                      .otherwise(reopen))
        lab_choice = (sfn.Choice(self, "LabResult")
                      .when(sfn.Condition.string_equals("$.lab.result", "pass"), close)
                      .otherwise(reopen))
        provisional.next(await_lab)
        await_lab.next(lab_choice)
        await_lab_final.next(lab_choice)
        close.next(sfn.Succeed(self, "Closed"))
        await_kit.next(kit_choice)
        await_kit_final.next(kit_choice)
        await_fix.next(await_kit)
        await_fix_final.next(await_kit)
        definition = init.next(alert).next(await_fix)

        machine = sfn.StateMachine(
            self, "CaseMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.days(120),
        )

        # Scale run: start hundreds of case workflows at a steady pace (about one a second), so a new account's
        # Lambda concurrency limit of 10 is never swamped. Items come from s3://bucket/runs/scale-items.json.
        start_case = tasks.StepFunctionsStartExecution(
            self, "StartCase",
            state_machine=machine,
            name=sfn.JsonPath.string_at("$.exec_name"),
            input=sfn.TaskInput.from_object({"case_id": sfn.JsonPath.string_at("$.case_id"),
                                             "timers": sfn.JsonPath.object_at("$.timers")}),
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE,
            result_path=sfn.JsonPath.DISCARD,
        )
        pace = sfn.Wait(self, "Pace", time=sfn.WaitTime.duration(Duration.seconds(3)))
        already = sfn.Pass(self, "AlreadyStarted")  # a retried item: the deterministic name makes it a no-op
        start_case.add_catch(already, errors=["StepFunctions.ExecutionAlreadyExistsException"])
        already.next(pace)
        start_cases = sfn.DistributedMap(
            self, "StartCases",
            item_reader=sfn.S3JsonItemReader(bucket=bucket, key="runs/scale-items.json"),
            max_concurrency=3,
            tolerated_failure_percentage=5,
            map_execution_type=sfn.StateMachineType.EXPRESS,
            result_path=sfn.JsonPath.DISCARD,
        )
        start_cases.item_processor(start_case.next(pace))
        scale_machine = sfn.StateMachine(
            self, "ScaleRun",
            definition_body=sfn.DefinitionBody.from_chainable(start_cases.next(sfn.Succeed(self, "AllStarted"))),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.hours(3),
        )
        bucket.grant_read(scale_machine)

        # Map tiles for the web pages (Amazon Location, key restricted to our site and local development)
        map_key = location.CfnAPIKey(
            self, "MapKey",
            key_name=f"{self.stack_name.lower()}-maps",
            description="JalSaathi web map tiles",
            no_expiry=True,
            restrictions=location.CfnAPIKey.ApiKeyRestrictionsProperty(
                allow_actions=["geo-maps:*"],
                allow_resources=[f"arn:aws:geo-maps:{self.region}::provider/default"],
                allow_referers=[f"https://{dist.distribution_domain_name}/*", "http://localhost*"],
            ),
        )

        polly = iam.PolicyStatement(actions=["polly:SynthesizeSpeech"], resources=["*"])

        # Entry points
        ingest_fn = fn("Ingest", "jalsaathi.ingest.handler", timeout=900, memory=1024,
                       extra={"STATE_MACHINE_ARN": machine.state_machine_arn,
                              "SCALE_RUN_ARN": scale_machine.state_machine_arn})
        for m in (machine, scale_machine):
            m.grant_start_execution(ingest_fn)
            m.grant(ingest_fn, "states:ListExecutions")
            m.grant_execution(ingest_fn, "states:StopExecution")
        ingest_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["geo-places:Geocode"], resources=[f"arn:aws:geo-places:{self.region}::provider/default"]))

        webhook_fn = fn("Webhook", "jalsaathi.webhook.handler", timeout=90, memory=1024)  # also runs Ask JalSaathi
        machine.grant_task_response(webhook_fn)
        webhook_fn.add_to_role_policy(polly)
        webhook_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/apac.amazon.nova-pro-v1:0",
                       "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0"]))
        # Ask JalSaathi: Transcribe (streaming) -> Translate -> Strands agent on Bedrock -> Guardrails -> Cedar -> Polly
        ask_jalsaathi = [
            iam.PolicyStatement(actions=["translate:TranslateText"], resources=["*"]),
            iam.PolicyStatement(actions=["bedrock:ApplyGuardrail"],
                                resources=[f"arn:aws:bedrock:{self.region}:{self.account}:guardrail/*"]),
        ]
        for statement in ask_jalsaathi:
            webhook_fn.add_to_role_policy(statement)
        webhook_fn.add_to_role_policy(iam.PolicyStatement(actions=["transcribe:StartStreamTranscription"], resources=["*"]))
        webhook_fn.add_to_role_policy(iam.PolicyStatement(  # hands each question to an async run of itself
            actions=["lambda:InvokeFunction"],
            resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:{self.stack_name}-Webhook*"]))
        webhook_url = webhook_fn.add_function_url(auth_type=lambda_.FunctionUrlAuthType.NONE)

        api_fn = fn("ApiHandler", "jalsaathi.api.handler", timeout=29,
                    extra={"INGEST_FUNCTION": ingest_fn.function_name, "STATE_MACHINE_ARN": machine.state_machine_arn,
                           "SCALE_RUN_ARN": scale_machine.state_machine_arn, "MAP_KEY_NAME": map_key.key_name})
        machine.grant_task_response(api_fn)
        machine.grant_start_execution(api_fn)
        scale_machine.grant_execution(api_fn, "states:DescribeExecution", "states:ListMapRuns")
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["states:DescribeMapRun"],
            resources=[f"arn:aws:states:{self.region}:{self.account}:mapRun:{scale_machine.state_machine_name}/*"]))
        api_fn.add_to_role_policy(iam.PolicyStatement(actions=["geo:DescribeKey"], resources=[map_key.attr_key_arn]))
        api_fn.add_to_role_policy(polly)
        for statement in ask_jalsaathi:  # Ask JalSaathi from the web app (text questions)
            api_fn.add_to_role_policy(statement)
        api_fn.add_to_role_policy(iam.PolicyStatement(  # the app's field-kit photo hint
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/apac.amazon.nova-pro-v1:0",
                       "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0"]))
        ingest_fn.grant_invoke(api_fn)
        http_api.add_routes(path="/api/{proxy+}", methods=[apigw.HttpMethod.ANY],
                            integration=integ.HttpLambdaIntegration("ApiIntegration", api_fn))

        # Static content: test UI always at /test/; the frontend build at / once frontend/dist exists
        s3d.BucketDeployment(
            self, "TestUi",
            sources=[s3d.Source.asset(str(ROOT / "testui"))],
            destination_bucket=bucket, destination_key_prefix="site/test",
            distribution=dist, distribution_paths=["/test/*"], memory_limit=256,
        )
        frontend_dir = ROOT / "frontend" / ("dist" if (ROOT / "frontend" / "dist" / "index.html").exists() else "placeholder")
        s3d.BucketDeployment(
            self, "Frontend",
            sources=[s3d.Source.asset(str(frontend_dir))],
            destination_bucket=bucket, destination_key_prefix="site", exclude=["test/*", "app/*"],
            distribution=dist, distribution_paths=["/*"], memory_limit=256,
        )
        if (ROOT / "app" / "dist" / "index.html").exists():  # role screens: engineer, relay, officials, impact
            s3d.BucketDeployment(
                self, "RoleApp",
                sources=[s3d.Source.asset(str(ROOT / "app" / "dist"))],
                destination_bucket=bucket, destination_key_prefix="site/app",
                distribution=dist, distribution_paths=["/app/*"], memory_limit=256,
            )
        if (ROOT / "data" / "snapshot" / "manifest.json").exists():
            s3d.BucketDeployment(
                self, "Snapshot",
                sources=[s3d.Source.asset(str(ROOT / "data" / "snapshot"))],
                destination_bucket=bucket, destination_key_prefix="data/snapshot", prune=False,
            )

        # Daily live ingest (off until the portal is reliable; enable in the console or here)
        events.Rule(
            self, "DailyIngest",
            schedule=events.Schedule.cron(minute="30", hour="0"),  # 06:00 IST
            enabled=False,
            targets=[targets.LambdaFunction(ingest_fn, event=events.RuleTargetInput.from_object({"source": "live"}))],
        )
        cw.Alarm(
            self, "IngestErrors",
            metric=ingest_fn.metric_errors(period=Duration.minutes(5)),
            threshold=1, evaluation_periods=1,
            alarm_description="JalSaathi ingest failed",
        )

        CfnOutput(self, "SiteUrl", value=f"https://{dist.distribution_domain_name}")
        CfnOutput(self, "TestUiUrl", value=f"https://{dist.distribution_domain_name}/test/")
        CfnOutput(self, "ApiBase", value=f"https://{dist.distribution_domain_name}/api/v1")
        CfnOutput(self, "WebhookUrl", value=webhook_url.url)
        CfnOutput(self, "StateMachineArn", value=machine.state_machine_arn)
        CfnOutput(self, "ScaleRunArn", value=scale_machine.state_machine_arn)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
