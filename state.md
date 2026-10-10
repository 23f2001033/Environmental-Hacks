# State: what's built so far

Last updated: Sat 10 Oct 2026, 00:30 IST · Deadline Sun 11 Oct, 20:00 IST · Feature freeze Sat 18:00 · Submit by Sun 16:00

Owner: lane 4 (Umar). Everyone updates it when they finish something, start something big, or get blocked.

## Live now (AWS ap-south-1, stack `JalSaathi`)

| What | Where |
|---|---|
| Site (frontend build space; placeholder for now) | https://d2735023v3xj6.cloudfront.net |
| **Test console** (map, stats, every feature, demo controls) | https://d2735023v3xj6.cloudfront.net/test/ |
| API v1 ([contract](docs/API.md)) | https://d2735023v3xj6.cloudfront.net/api/v1/health |
| Telegram bot | [@Srott_bot](https://t.me/Srott_bot) |
| Demo clock | **On for the 13 demo villages only**: fix deadline 4 min, re-test 5 min, lab 15 min; at most 3 escalations per step. Real WQMIS cases use real deadlines (48 h / 7 days) |
| Data loaded | 13 demo cases + **560 real cases** from the WQMIS snapshot (UP and Rajasthan, FY 2026-27), 496 villages (the demo villages are among them) |

Admin token for the test console's demo controls: SSM `/jalsaathi/console-token` (ask Aman; never post it in the group).

## Scale run, measured (Sat 00:03 to 00:13 IST)

| | |
|---|---|
| Input | WQMIS snapshot, every FY 2026-27 failure: 560 new cases in 496 villages |
| Ingest (parse, store, geocode) | 98 s |
| Workflows started | **560 of 560, 0 failed**, paced at about 1 per second by the ScaleRun Distributed Map (611 s) |
| All cases warned and waiting for the engineer | 573 of 573 `AWAITING_FIX` |
| Test found → village warned | demo run: median 5 s · scale run: median 347 s, p95 581 s (the pacing queue, on purpose, to stay under the Lambda limit of 10) |
| Map pins | 172 village · 202 block · 119 district (approximate, drawn hollow) · 3 none |
| Estimated AWS cost | **$0.43 for 560 cases ($0.0008 per case)**, of which geocoding $0.30; voice notes are made only when someone listens |
| Repeat failures (FY 2025-26 → 2026-27) | 149 of 1,233 villages failed the same test again, 12.1%, with only half of this year's data in |

## Done

| When (IST) | What | Verified |
|---|---|---|
| Fri 21:00 | Docs: PRD, build plan, decisions, setup, research | Pushed to `main` |
| Fri 21:30 | Bot token moved from `.env` to SSM (encrypted); webhook secret and admin token generated | `getMe` → @Srott_bot |
| Fri 22:00 | Advice library (Hindi/English, sources), rules, Cedar policies, WQMIS parser | 71 tests |
| Fri 22:30 | Ingest, case workflow steps, Telegram webhook, web API, shared actions | 88 tests |
| Fri 23:00 | CDK stack deployed: DynamoDB, S3, Step Functions, 4 Lambdas, HTTP API, CloudFront, test console, frontend placeholder | `cdk deploy` ✅ |
| Fri 23:15 | 13 verified government records ingested → 13 cases → 13 workflows → Polly Hindi voice notes | All reach AWAITING_FIX in 15 s |
| Fri 23:20 | Full loop on Behta Lakhi: Cedar denies engineer close → chlorination → kit clean (provisional) → simulated lab pass → **CLOSED** | Timeline shows every Cedar decision |
| Fri 23:40 | Reopen path: contaminated kit → back to AWAITING_FIX | ✅ |
| Fri 23:45 | WQMIS snapshot committed (20 files, UP + RJ, two years); Rajasthan demo records carry real village and sample IDs | 114 tests |
| Sat 00:00 | Repeat-failure analysis (`scripts/analyze_repeats.py`) | 149 villages failed again |
| Sat 00:10 | Paced scale run, validated geocoding, voice notes on first need, `/config`, richer `/stats`, map in test console | 560/560, see above |
| Sat 00:25 | AI reads the field-kit photo (suggestion only; the person decides). Claude Haiku first, Amazon Nova Pro fallback | 138 tests; Nova tested live |

## Bugs found and fixed while testing

| Bug | Fix |
|---|---|
| 3 of 13 workflows failed: Lambda `TooManyRequestsException` (new account concurrency limit is **10**) | Every step retries throttling with backoff and jitter; `restart-case` admin route; big runs are paced |
| A rejected action (lab result before a fix) was still written to the timeline | Check the waiting step first, record second; tests added |
| Timeline events in the same second could show out of order | Event keys use nanosecond time |
| Under the demo clock, an untouched case escalated every 4 minutes forever | Max 3 escalations per step, then it waits quietly; reminder says which deadline was missed |
| Cedar "forbid" rule errors on missing context while the "permit" still allows (fail open) | Wrapper denies on any evaluation error; test locks it in |
| Geocoder put Dhabla Kalayanpura (Baran) in Jaipur, Bhajangarh at a flour mill, and "Anta block" at Baran town | Accept only name and district matches; fall back to block, then district, and label which (D-29) |
| A kit button pressed while the case wasn't waiting used up the relay's photo | Check the waiting step before taking the photo |
| Reset at scale would exceed the 29 s API limit | Reset runs in the ingest Lambda (asynchronous) |

## Needs a person

| Item | Who | Needed by |
|---|---|---|
| **Test the bot on real phones** (links below) | Reshma, Umar | Sat 09:00 |
| Hindi review of `content/advice.json` and bot messages in `src/jalsaathi/webhook.py`, `case_steps.py`, `vision.py` | Umar | Sat 12:00 |
| Frontend stack and direction (build space: `frontend/`, contract: `docs/API.md`; `/api/v1/config` gives the map style) | Frontend lead | Sat 10:00 |
| Optional: add a payment card in AWS Billing so Bedrock can use Claude (Marketplace refuses with `INVALID_PAYMENT_INSTRUMENT`). Nova Pro already covers the kit hint | Aman | any time |
| Approve a Lambda concurrency increase request (10 → 1000; free). No longer blocking: the scale run is paced | Aman | optional |
| WQMIS WQ2 (Remedial Action) browser check for Hardoi, Harpalpur | Umar | Sat 09:00 |
| Accept GitHub invites | Umar, @faizsaleem8 | now |

### Phone test links

1. Relay (village worker): open <https://t.me/Srott_bot?start=v_412558> (Behta Lakhi) → tap हाँ → you get the Hindi alert and the voice note.
2. Engineer (Harpalpur block): on a second phone open <https://t.me/Srott_bot?start=e_5037> → tap हाँ. New case cards arrive there; after a demo reset and seed, every Harpalpur case sends one.
3. Engineer taps "✅ केस बंद करें" → Cedar refuses. Taps "🧪 क्लोरीनेशन किया" → the relay phone is asked for the field-kit photo.
4. Relay sends a photo of the vial (any photo works for testing) → the bot replies with an **AI suggestion** of the colour → relay taps 🟡 पीली (साफ़) → "provisionally safe". The timeline records the suggestion and whether the person agreed.
5. Test console → the village → "Lab: pass (simulated)" → both phones hear "safe again".

`python scripts/demo.py links` prints links for every demo village. `python scripts/demo.py scale` re-runs the scale run (after `reset`).

## Next

1. Merge PR `l1/snapshot-scale-run` after CI passes
2. Phone tests and Hindi review → fixes
3. Frontend with the frontend lead (map, village page, block dashboard)
4. Demo video script and recording (Sat evening)

## Open issues

- WQMIS is flaky (HTTP 500, partial data). The snapshot is complete (manifest says nothing missing); the daily live ingest stays off.
- The remedial-action report can't be read by script; the app records fixes itself.
- 3 old failed workflows from Fri 23:12 (before the retry fix) still show as FAILED in Step Functions; their cases were reset since.
- Not built (D-31): Hindi video alert (S1), SES email escalation (S4, SES is in sandbox).
