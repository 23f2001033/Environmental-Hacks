# Submission form: ready-to-paste answers

Form: WeMakeDevs × AWS Environmental Hacks. Deadline Sun 11 Oct 2026, 20:00 IST (submit by 16:00). Fill once per team.
Fields marked **TODO** need a team member's own details. Everything else is ready to paste.

## Part 1: Team details

| Field | Value |
|---|---|
| Team leader's WeMakeDevs username | **TODO (Aman)**: from wemakedevs.org/home |
| Second / third / fourth member's WeMakeDevs username | **TODO** (Reshma, Faiz, Umar) |
| Team leader's GitHub | https://github.com/23f2001033 |
| Second member's GitHub | https://github.com/reshmag2023-boop |
| Third member's GitHub | https://github.com/faizsaleem8 |
| Fourth member's GitHub | https://github.com/U-m-4r |
| LinkedIn (all four) | **TODO** |
| Resumes (public Google Drive links; needed for Amazon Fast Track interviews) | **TODO** |

## Part 2: Project details

**Project title:** JalSaathi: lab-confirmed drinking-water alerts for villages

**Track:** Heat and Water

**GitHub link:** https://github.com/23f2001033/Environmental-Hacks (make it **public** before submitting)

**Deployed link:** https://d2735023v3xj6.cloudfront.net

**YouTube video:** **TODO** (unlisted or public, under 3:00; check it opens in a signed-out browser). Script: [video/SCRIPT.md](../video/SCRIPT.md)

### What does your project do? (problem, and who it is for)

> Government labs under India's Jal Jeevan Mission test village drinking water and publish every failure on a public portal (JJM-WQMIS). The result is recorded, but nothing carries it to the family drinking the water or forces a fix. In Uttar Pradesh and Rajasthan we found 573 failed tests this year; the median one is 105 days old, and 149 villages failed the same test again the year after. Water with E. coli looks clear, and 87% of these failures are nitrate, fluoride or arsenic, where the usual advice, "boil it", does nothing or makes the water worse.
>
> JalSaathi turns each failed lab test into a case that cannot be closed until the water is proven safe. The village's health worker gets a Hindi or English alert with a voice note and the right action for that contaminant, on Telegram and in a web app. People can ask questions by voice in Hindi ("can I boil it?") and get a spoken answer drawn only from their village's results. The block engineer gets the case with a deadline; missed deadlines escalate and the district official gets an email digest of overdue cases. The engineer cannot close a case: a field-kit re-test makes it provisionally safe, and only a passing lab re-test closes it.
>
> It is for the people drinking the water (through the village health worker), the block engineers who fix sources, and district officials who need to see what is overdue. It runs on real government data today: 573 cases in 496 villages.

### How did you use AWS in your project?

> **AWS open source:** **AWS CDK** (Python) defines and deploys the whole stack in one `cdk deploy`. **Cedar** expresses the case rules (only a passing lab re-test can close a case; a field kit only makes it provisionally safe; never advise boiling for chemical contamination); the same policy file runs in Amazon Verified Permissions and, as a fail-closed fallback, locally via cedarpy. **Strands Agents** runs the "Ask JalSaathi" agent on Amazon Bedrock with tools that can only read the asking village's record. We also use the **Amazon Transcribe streaming SDK** and boto3.
>
> **AWS services:**
> - **AWS Step Functions**: one Standard workflow per village case. Task tokens wait (for free) for the engineer, the field kit and the lab; deadlines escalate. An Express **Distributed Map** started 560 real cases in 611 s with 0 failures, paced to fit a new account's Lambda limit.
> - **AWS Lambda**: ingest, case steps, the Telegram webhook (function URL) and the web API.
> - **Amazon DynamoDB** stores villages, cases, timelines and subscriptions; **Amazon S3 + CloudFront** serve the two web apps and voice notes; **Amazon API Gateway** serves the API.
> - **Amazon Polly** (Kajal neural voice) speaks every alert and answer in Hindi or English.
> - **Amazon Transcribe** (streaming, Hindi) and **Amazon Translate** handle voice questions.
> - **Amazon Bedrock** (Nova Pro) runs the agent and reads field-kit photos (as a suggestion; the person decides). **Bedrock Guardrails** checks every answer is grounded in the village's own data; if not, the person gets the official advice instead.
> - **Amazon Verified Permissions** makes every rule decision.
> - **Amazon Location Service** geocodes villages (accepted only on a name and district match) and serves the map tiles.
> - **Amazon SES + EventBridge Scheduler** email each district official the overdue cases.
> - **Amazon CloudWatch** (Embedded Metric Format business metrics and a dashboard) and **AWS X-Ray** (traces) show what the system did for villages, not just server health.
> - **AWS Systems Manager Parameter Store** keeps every secret out of code.
>
> Everything runs in ap-south-1 (Mumbai). Estimated cost for the 560-case run: about $0.43.

### Blog links (optional; individual AirPods prize for the top 5 on AWS Builder Center)

**TODO**: one per member if time allows. Good topics, each from something we actually hit:
- "Fail-closed Cedar policies in Verified Permissions for a public-health workflow" (Aman)
- "Scraping a flaky government portal politely, with a guard against partial data" (Reshma)
- "Designing a Hindi-first, village-first web page" (Faiz)
- "Testing a Hindi voice bot on real phones" (Umar)

### Team members' contributions

> **Aman (team lead):** idea and research; AWS architecture and all deployments; the backend, case workflow, voice assistant, policies, digest and observability (built with Claude Code and reviewed by him); code review and merging of every pull request.
>
> **Reshma:** the JJM-WQMIS portal client and the guarded ingestion validation that refuses partial or invalid portal data; the demo village coordinates; the traceable evidence behind every number in the video and slides.
>
> **Faiz:** the village-first web design and frontend (`frontend/`): village report with contaminant-specific advice and voice notes, searchable village directory, block queue, printable poster; Hindi-first with English.
>
> **Umar:** phone testing and QA of the Telegram flows, Hindi review, the design brief for the About page, and the demo video.

(Each member should check their own line.)

## Part 3: Feedback

### What you didn't like about the AWS services you used, and what could be better

> 1. **Amazon Bedrock model access on a new account.** Claude on Bedrock failed with `AccessDeniedException ... INVALID_PAYMENT_INSTRUMENT ... AWS Marketplace subscription cannot be completed`, although the account had credits. The message doesn't say that Anthropic models need a Marketplace subscription and a card even when credits cover usage. We switched to Amazon Nova Pro, which worked at once. A clear pre-check in the console ("this model needs X") would save hours.
> 2. **New-account Lambda concurrency of 10.** Fanning out 13 Step Functions workflows already produced `Lambda.TooManyRequestsException` in 3 of them. We only found the limit at runtime. We solved it with retries plus a paced Distributed Map, but a visible warning when a state machine's fan-out exceeds the account's concurrency would help.
> 3. **Bedrock Guardrails denied topics are stance-blind.** A "false all-clear" topic also blocked the correct answer "No, the water is not safe yet", because it discusses the same topic. The relevance filter scored a correct answer to "Is the problem fixed?" at 0.03. Topic definitions are limited to 200 characters. Contextual grounding was the right tool; the docs could say when topics are the wrong one.
> 4. **Amazon Location geocoding in rural India.** For "Dhabla Kalayanpura, Anta, Baran, Rajasthan" it confidently returned a place in Jaipur district; for another village, a flour mill. We now accept a result only if its district matches, but an option to constrain results to an administrative area (district or sub-district) would help.
> 5. **Amazon Transcribe batch latency.** A 3-second Hindi clip took 42 s in batch. Streaming took about 3 s, but needs a separate SDK (with a native dependency) rather than boto3.
> 6. **AWS CDK on Windows under memory pressure.** Synth crashed inside the jsii Node process with `node::Realloc ... Assertion failed` when the PC had under 1 GB of commit memory free. A clear "not enough memory" message would have saved debugging time.
> 7. **SES sandbox** requires verifying every recipient, which is sensible but slows a demo. A short-lived "verified test inbox" for hackathons would help.

### What you liked about the AWS services you used

> 1. **Step Functions task tokens** modelled a human process that runs for weeks (wait for the engineer, then a field kit, then the lab) with free waiting, deadlines through `TimeoutSecondsPath`, and a timeline we can show. The **Distributed Map** started 560 real cases in about ten minutes with built-in failure tolerance and item counts.
> 2. **Bedrock Guardrails `ApplyGuardrail` with contextual grounding**, used standalone on the final answer with `grounding_source` and `query` qualifiers. It passed a correct Hindi answer (grounding 1.0) and blocked a made-up "boil it, it's fixed" answer (grounding 0.0), with no extra model.
> 3. **Amazon Polly's Kajal voice** speaks natural Hindi and Indian English from one voice: a single code path for both languages.
> 4. **Amazon Transcribe streaming** accepted Telegram's OGG/Opus voice notes as they are and returned accurate Hindi in about 3 seconds.
> 5. **Amazon Verified Permissions with Cedar:** the same policy file works in AWS and locally, decisions name the policy that applied, and we could make the whole system fail closed.
> 6. **Strands Agents:** tools are plain Python functions, and the Bedrock model wrapper took a few lines; it was easy to restrict the agent to one village's data.
> 7. **CloudWatch Embedded Metric Format:** business metrics (alerts sent, questions answered, Cedar refusals) from a single log line, no extra API calls, straight onto a dashboard. With **X-Ray** we got a service map of every AWS call.
> 8. **Amazon Location API keys with referer restrictions:** map tiles in the browser without exposing credentials.
> 9. **AWS CDK in Python:** 20-odd services in one stack and one `cdk deploy`, including Verified Permissions policies generated from our Cedar file.
