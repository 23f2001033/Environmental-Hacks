# JalSaathi demo video: script and shot list

**Length: 2:50 (hard limit 3:00).** English narration, about 400 words. Hindi on screen is subtitled in English.
Judges score only what the video shows (rubric: AWS Usage 10, Idea & Impact 8, Execution 4, Demo Video 4, Design 4),
so **every AWS service is named on screen while it is working**: a small lower-third label, e.g.
`Amazon Transcribe · streaming, Hindi`.

Rules for the edit:
- Lead with a person, not a map. Numbers come second, architecture third.
- Everything shown is live on AWS. Label the two simulated parts on screen: the **lab re-test** button and the
  **demo clock** (deadlines in minutes instead of days).
- Captions on all narration (many judges watch muted).
- Upload as **unlisted** on YouTube; check the link in a signed-out browser.

## Before recording (10 minutes)

1. Reset the demo: test console `https://d2735023v3xj6.cloudfront.net/test/` → **Restart the 13 demo villages**
   (or `python scripts/demo.py restart-demo`). Phones already joined get the alert again; that is shot 3.
2. Phone A (village relay): joined to Behta Lakhi (`t.me/Srott_bot?start=v_412558`), language Hindi.
3. Phone B (engineer): joined to Harpalpur block (`t.me/Srott_bot?start=e_5037`).
4. Laptop tabs:
   - Village site: `https://d2735023v3xj6.cloudfront.net/?v=412558`
   - Engineer screen: `/app/engineer/5037?k=demo`
   - Health worker: `/app/relay/412558?k=demo`
   - Officials: `/app/officials`; Impact: `/app/impact`
   - AWS console (ap-south-1): Step Functions → CaseMachine (a running execution's graph) and ScaleRun (the map run:
     560 succeeded), X-Ray → Service map (last 1 hour), CloudWatch → Dashboards → **JalSaathi**,
     Bedrock → Guardrails → `jalsaathi-answers`.
5. Screen recorder at 1080p; phone screen recordings for Telegram (Android: built-in recorder).

## Script

| Time | Narration | On screen | AWS label |
|---|---|---|---|
| 0:00–0:12 | "This water looks clean. A government lab tested it in June and found E. coli. The result is in a public portal. Nothing in that portal tells the village." | A clear glass of water (stock or filmed), then the WQMIS record for Behta Lakhi: E. coli 80 CFU/100 ml, 15 Jun 2026 | none |
| 0:12–0:30 | "Across Uttar Pradesh and Rajasthan we found 573 failed tests like this. The median one is 105 days old. 149 villages failed the same test again the next year. And 87% are chemicals like nitrate, where the usual advice, 'boil it', makes the water worse." | Big numbers, one per beat: **573 · 105 days · 149 · 87%**. Small source line: "JJM-WQMIS, snapshot 9 Oct 2026" | none |
| 0:30–0:38 | "JalSaathi closes that gap. It turns each failed lab test into a case that cannot be closed until the water is proven safe." | Title card: **JalSaathi: from a failed lab test to safe water again** | none |
| 0:38–1:00 | "Within seconds, the village's health worker gets a Hindi alert on Telegram, with a voice note for people who can't read, and the right advice for this contaminant. One tap switches it to English." | Phone A: the alert arrives; play 3 s of the voice note; tap **🇬🇧 Read in English** | `Amazon Polly · Kajal, Hindi + English` · `AWS Step Functions · one workflow per case` · `AWS Lambda` |
| 1:00–1:25 | "She can ask a question by voice: 'Can I boil this water and drink it?' Transcribe hears the Hindi; a Strands agent on Bedrock reads only this village's lab results; Guardrails checks every claim is grounded in that data, and a Cedar policy blocks 'boil' for chemicals. The answer comes back in Hindi, spoken." | Phone A: record the voice question on the **nitrate** village (Dhabla Kalayanpura, `t.me/Srott_bot?start=v_651384`); the reply text + voice. Overlay the pipeline as a strip of six icons lighting up in turn | `Amazon Transcribe` → `Amazon Translate` → `Strands Agents on Amazon Bedrock (Nova Pro)` → `Bedrock Guardrails · grounding 1.0` → `Cedar` → `Amazon Polly` |
| 1:25–1:45 | "The block engineer gets the case with a deadline. He tries to close it without any repair. JalSaathi refuses: only a passing lab re-test can close a case. That rule is a Cedar policy, checked on every action." | Phone B: the engineer card; tap **✅ Close case** → refusal pop-up. Cut to the web engineer screen: the "Close refused by policy" dialog | `Cedar policy · close-needs-lab-pass` |
| 1:45–2:05 | "He chlorinates the tank and logs it. The health worker tests with a field kit and sends a photo; Bedrock reads the vial, but she decides. The village is marked safe only provisionally, until the lab confirms." | Phone B: **🧪 Chlorinated**. Phone A: the kit request → send the vial photo → AI suggestion → tap **🟡 Yellow (clean)** → "provisionally safe". Test console: **Lab: pass (simulated)** (label it on screen) → both phones: "safe again" | `Amazon Bedrock · Nova Pro vision` · `Step Functions · task tokens` |
| 2:05–2:25 | "It runs at state scale. One Distributed Map started 560 real cases in ten minutes with zero failures, for about forty cents. X-Ray traces every call, and the dashboard counts what happened to villages, not just servers." | Step Functions ScaleRun map run (560/560) · X-Ray service map · CloudWatch **JalSaathi** dashboard · the officials' live feed at `/app/officials` | `Step Functions Distributed Map` · `AWS X-Ray` · `Amazon CloudWatch` · `Amazon DynamoDB` · `Amazon S3 + CloudFront` · `Amazon Location Service` · `AWS CDK` |
| 2:25–2:42 | "Built in three days by four of us, entirely on AWS. What's real: 573 government lab results and the full loop. What's next: SMS and phone-call alerts, and the lab re-test read straight from the portal." | Architecture diagram (`/app/impact`, bottom), then the team names | `16+ AWS services` list as a closing strip |
| 2:42–2:50 | "Clear water can still make a child sick. JalSaathi makes sure the village knows, and that someone fixes it." | Back to the glass of water; logo; site URL | none |

## Lower-thirds (exact text)

`Amazon Polly · Kajal voice, Hindi + English` · `AWS Step Functions · one workflow per village case` ·
`Amazon Transcribe · streaming, Hindi` · `Amazon Translate` · `Strands Agents (AWS open source) on Amazon Bedrock · Nova Pro` ·
`Amazon Bedrock Guardrails · contextual grounding` · `Cedar (AWS open source) · fail-closed policies` ·
`Amazon Bedrock · Nova Pro vision` · `Step Functions Distributed Map · 560 cases, 0 failed` · `AWS X-Ray` ·
`Amazon CloudWatch · business metrics (EMF)` · `Amazon Location Service · maps + geocoding` ·
`Amazon DynamoDB` · `Amazon S3 + CloudFront` · `Amazon API Gateway` · `AWS Lambda` · `AWS CDK (AWS open source)`

## Facts used (all traceable)

| Claim | Source |
|---|---|
| 573 failed tests, UP + Rajasthan | `/api/v1/stats`, WQMIS snapshot 9 Oct 2026 |
| Median 105 days since the lab found it; 74% over 60 days | `data/analysis/days_since_test.json` |
| 149 villages failed the same test again | `data/analysis/repeat_failures.json` (149 of 1,233, FY 2025-26 → 2026-27 to 9 Oct) |
| 87% chemical | `/api/v1/stats` → `open_by_code` (499 of 573) |
| 560 cases, 0 failed, ~10 minutes, ~$0.43 | Step Functions map run 2026-10-09 18:33–18:43 UTC; `state.md` (cost is an estimate) |
| Behta Lakhi: E. coli 80 CFU/100 ml, lab test 15 Jun 2026 | `/api/v1/villages/412558` |

Do not say "the village was never told": we can only say nothing in the portal tells them.
