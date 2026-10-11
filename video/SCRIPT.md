# Srot demo video: script and shot list

**Length: 2:50 (hard limit 3:00).** English narration, about 410 words. Hindi on screen is subtitled in English.
Judges score only what the video shows (rubric: AWS Usage 10, Idea & Impact 8, Execution 4, Demo Video 4, Design 4),
so **every AWS service is named on screen while it is working**: a small lower-third label, e.g.
`Amazon Transcribe · streaming, Hindi`. Every line below was checked against the live system on 11 Oct 2026.

Rules for the edit:
- Lead with a person, not a map. Numbers come second, architecture third.
- Everything shown is live on AWS. Label the two simulated parts on screen: the **lab re-test** button and the
  **demo clock** (deadlines in minutes instead of days).
- Captions on all narration (many judges watch muted).
- Never show the AWS account number (console, top right), the test-console token or phone numbers.
- Upload as **unlisted** on YouTube; check the link in a signed-out browser.

## Before recording (30 minutes)

1. Phone A (health worker): join Behta Lakhi `t.me/Srott_bot?start=v_412558`, keep Hindi.
   Phone B (engineer): join Harpalpur block `t.me/Srott_bot?start=e_5037`, send `/english`.
2. Then, on Phone A only, join the nitrate village Dhabla Kalayanpura `t.me/Srott_bot?start=v_651384`. Join it **last**:
   a voice question is answered for the village the chat joined most recently.
3. Screen recording on both phones (with sound).
4. Laptop tabs: `/` · `/?v=412558` · `/app/engineer/5037?k=demo` · `/app/officials` · `/app/impact`; AWS console
   (ap-south-1): Step Functions → ScaleRun → Map Run, X-Ray → Trace Map, CloudWatch → Dashboards → **Srot**.
5. Aman runs the test console `https://d2735023v3xj6.cloudfront.net/test/`: **Restart the 13 demo villages** (scene 4)
   and **Lab: pass (simulated)** on the Behta Lakhi E. coli card (scene 7). The token is shared privately, never in the group.
6. Demo clock: the engineer's deadline is 4 minutes after the restart (48 hours in real use); the escalation arrives on its own.
7. A field-kit vial photo on Phone A (a real H2S vial, or any clear yellow-vial photo captioned "sample photo").

## Script

| Time | Narration | On screen | Lower-third |
|---|---|---|---|
| 0:00–0:10 | "This water looks clean. In June, a government lab found E. coli in it. The result is on a public portal, and nothing on that portal tells the village." | A clear glass of water; then `/?v=412558`: E. coli 80 CFU/100 ml, 15 Jun 2026 | Source: JJM-WQMIS |
| 0:10–0:26 | "Across Uttar Pradesh and Rajasthan, 573 tests like this have failed. The typical result is 105 days old. 149 villages failed the same test again the next year. And 87% are chemicals like nitrate, where 'boil it' makes the water worse." | About page loading (dots animate onto the map), then **573 · 105 days · 149 · 87%** | Source: JJM-WQMIS snapshot, 9 Oct 2026 |
| 0:26–0:33 | "Srot turns each failed test into a case that stays open until a new lab test proves the water safe." | Title card: **Srot · from a failed lab test to safe water again** | none |
| 0:33–0:53 | "As soon as a case opens, AWS Step Functions starts a workflow for that village. The health worker gets a Telegram alert in Hindi, with an Amazon Polly voice note for anyone who can't read, and advice for this exact contaminant. One tap shows it in English." | Restart demo → Phone A: alert arrives, 3 s of the voice note, tap **🇬🇧 Read in English** | `AWS Step Functions · one workflow per village case` · `Amazon Polly · Kajal voice, Hindi + English` · `AWS Lambda` |
| 0:53–1:18 | "In a nitrate village, she asks by voice: can I boil this water and drink it? Amazon Transcribe hears the Hindi. A Strands agent on Amazon Bedrock reads only this village's lab results. Guardrails checks the answer is grounded in that data. The reply comes back spoken: don't boil it, boiling makes nitrate stronger." | Phone A: voice question "क्या मैं इस पानी को उबालकर पी सकता हूँ?"; cut the ~8 s wait; Hindi reply + voice, subtitled "Do not boil this water. Boiling makes nitrate stronger. Use another tested source." | `Amazon Transcribe · streaming, Hindi` → `Amazon Translate` → `Strands Agents on Amazon Bedrock · Nova Pro` → `Amazon Bedrock Guardrails · grounding check` → `Amazon Verified Permissions · no 'boil' for chemicals` → `Amazon Polly` |
| 1:18–1:38 | "The block engineer gets the case with a deadline; miss it, and it escalates. He tries to close it without a repair. Refused. Amazon Verified Permissions checks a Cedar policy on every action: only a passing lab re-test can close a case." | Phone B: case card, ⏰ escalation if it has arrived, **✅ Close case** → refusal; laptop engineer screen → "Close refused by policy" | `Amazon Verified Permissions · Cedar policy, checked on every action` · `Demo clock: 4 minutes here, 48 hours in real use` |
| 1:38–2:00 | "So he chlorinates the tank and logs it. The health worker tests with a field kit and sends a photo. Amazon Nova reads the vial, but she makes the call. Until the lab confirms, the village is only provisionally safe. Then both phones get the news: the water is safe again." | Phone B **🧪 Chlorinated** → Phone A kit request → photo → AI suggestion → **🟡 पीली (साफ़)** → "provisionally safe" → test console **Lab: pass (simulated)** → both phones "safe again" | `Amazon Bedrock · Nova Pro reads the photo` · `AWS Step Functions · waits for people (task tokens)` · `Lab re-test simulated for this demo` |
| 2:00–2:12 | "The same loop runs on the web. Villagers find their village in Hindi or English, engineers act from a link, and officials watch every alert, refusal and fix live." | Find my village → "Behta" → village page, toggle हिंदी/English; `/app/officials` live feed | `Amazon S3 + CloudFront` · `Amazon API Gateway + AWS Lambda` · `Amazon Location Service · maps` |
| 2:12–2:30 | "It scales. One Step Functions Distributed Map opened 560 real cases in ten minutes with zero failures, for about forty cents. X-Ray traces every call, and our CloudWatch dashboard counts alerts, escalations and fixes, not just servers." | ScaleRun Map Run (560 succeeded, 0 failed) · X-Ray Trace Map · CloudWatch **Srot** dashboard | `Step Functions Distributed Map · 560 cases, 0 failed` · `AWS X-Ray` · `Amazon CloudWatch · business metrics` · `Amazon DynamoDB` |
| 2:30–2:42 | "It's all serverless on AWS, deployed with the CDK. The lab results are real; the re-test in this demo is simulated. Next: SMS and phone calls, and re-tests read straight from the portal." | Architecture diagram (bottom of `/app/impact`), team names | `AWS CDK` · `Real: 573 government lab results · Simulated: the lab re-test` |
| 2:42–2:50 | "Clear water can still make a child sick. Srot makes sure the village knows, and that someone fixes it." | Glass of water; logo; site URL; repo | none |

If the cut runs long, trim in this order: scene 8 "engineers act from a link" → scene 10 "Next: …" → scene 2 the 149
sentence. Never trim the alert, the voice question, the refusal or the fix.

## Facts used (all traceable, checked live 11 Oct 2026)

| Claim | Source |
|---|---|
| 573 failed tests, UP + Rajasthan | `/api/v1/stats`, WQMIS snapshot 9 Oct 2026 |
| Median 105 days since the lab found it; 74% over 60 days | `data/analysis/days_since_test.json` |
| 149 villages failed the same test again | `data/analysis/repeat_failures.json` (149 of 1,233, FY 2025-26 → 2026-27 to 9 Oct) |
| 87% chemical | `/api/v1/stats` → `open_by_code` (499 of 573) |
| 560 cases, 0 failed, ~10 minutes, ~$0.43 | Step Functions map run 2026-10-09 (611 s, 560/560); cost is an estimate |
| Behta Lakhi: E. coli 80 CFU/100 ml, lab approval 15 Jun 2026 | `/api/v1/villages/412558` |
| Nitrate answer "Do not boil … boiling makes nitrate stronger", grounding 1.0 | `POST /api/v1/ask` (village 651384, Hindi) |
| Close refused by Amazon Verified Permissions | `POST /api/v1/engineer/5037/close` → `engine: verified-permissions, allowed: false` |
| Nova reads a vial photo | `POST /api/v1/relay/{village}/hint` → `yellow, high` |

Do not say "the village was never told": we can only say nothing in the portal tells them. Do not mention email
digests until Amazon SES identities are verified (`scripts/setup_email.py`).
