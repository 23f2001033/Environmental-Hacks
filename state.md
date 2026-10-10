# State: what's built so far

Last updated: Sat 10 Oct 2026, 21:45 IST · Deadline Sun 11 Oct, 20:00 IST · Feature freeze Sat 18:00 · Submit by Sun 16:00

Owner: lane 4 (Umar). Everyone updates it when they finish something, start something big, or get blocked.

## Live now (AWS ap-south-1, stack `JalSaathi`)

| What | Where |
|---|---|
| **Village site** (Faiz's design, `frontend/`): find your village, what to do now, voice note, block queue, poster | https://d2735023v3xj6.cloudfront.net (`/?v=412558`, `/?b=5037`) |
| **Role screens** (`app/`): engineer, health worker, officials + live feed, impact | https://d2735023v3xj6.cloudfront.net/app/ (`/app/engineer/5037?k=demo`, `/app/relay/412558?k=demo`) |
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
| Sat 15:00 | Late joiners catch up (engineer gets open cases); restart only the 13 demo villages; Reshma's ingestion guard merged (#5, #6) | Live |
| Sat 16:00 | Bot in Hindi and English (one tap), combined village alerts, Hindi review (#7) | English voice notes served |
| Sat 18:00 | Web app: signed links, engineer/relay actions, Web Push, officials' overview, activity feed (#8–#10); Faiz's village site at `/`, role screens at `/app/` (#11) | Full demo loop run live |
| Sat 20:40 | **Ask JalSaathi**: Hindi voice questions → Transcribe → Translate → Strands agent on Bedrock → Guardrails → Cedar → Polly (#15) | Live; grounded answers, unsafe ones replaced |
| Sat 20:50 | X-Ray tracing and the JalSaathi CloudWatch dashboard (#16); video script (#17) | Metrics flowing |
| Sat 21:05 | About-first site from Umar's brief, adapted to the water story (#18) | No overflow at 360/390 px |
| Sat 21:30 | District digest (SES + EventBridge Scheduler), Cedar in Amazon Verified Permissions, **real `cdk deploy`** (#19) | Decisions show `engine: verified-permissions` |
| Sat 21:40 | README to judging standard (#20); submission answers in `docs/SUBMISSION.md` (#21) | 226 + 9 tests |

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
| **Record the demo video** from `video/SCRIPT.md` (two phones; restart the demo villages first) | Umar, Faiz | Sun 12:00 |
| **Phone test**, including a Hindi voice question from the nitrate village (`t.me/Srott_bot?start=v_651384`) | Umar, Faiz | Sun 10:00 |
| **Email addresses** for the district digest: `python scripts/setup_email.py --sender <you> --to <a,b>`, then click the SES verification emails | Aman | Sun 10:00 |
| **Submission TODOs** in `docs/SUBMISSION.md`: WeMakeDevs usernames, LinkedIn, resumes, YouTube link | Everyone | Sun 15:00 |
| Check your own line in README "Team" and in `docs/SUBMISSION.md` | Everyone | Sun 12:00 |
| Make the repo public; add a licence (MIT proposed) | Aman | Sun 15:00 |
| Verify the 13 demo village pins (`data/fixtures/coordinates.json`, `verified: true` + source) | Reshma | optional |

### Phone test (Umar = village relay phone, Faiz = engineer phone; both read Hindi)

0. Aman: test console → **Restart the 13 demo villages** (or `python scripts/demo.py restart-demo`). Fresh timers; real cases untouched. Phones already joined get the alert again.
1. Umar opens <https://t.me/Srott_bot?start=v_412558> (Behta Lakhi) → taps हाँ → Hindi alert + voice note (same words in both).
2. Faiz opens <https://t.me/Srott_bot?start=e_5037> (Harpalpur block) → taps हाँ → gets the 10 worst open cases as cards with buttons (Behta Lakhi among them) and "17 more".
3. Faiz taps "✅ केस बंद करें" on Behta Lakhi → refused (only a lab re-test closes). Then "🧪 क्लोरीनेशन किया".
4. Umar gets the field-kit request → sends any photo → AI suggestion of the colour → taps 🟡 पीली (साफ़) → "provisionally safe".
5. Aman: test console → Behta Lakhi → "Lab: pass (simulated)" → both phones get "safe again".

Demo clock: if nobody acts, the fix deadline passes after 4 minutes and an escalation arrives (at most 3). Report each step ✅/❌ with screenshots.

## Next

1. Phone test and video recording (Sun morning); fixes only after Sun 12:00
2. Submit by Sun 16:00

## Open issues

- WQMIS is flaky (HTTP 500, partial data). The snapshot is complete (manifest says nothing missing); a daily live ingest is not switched on (a full pull takes longer than one Lambda run; next step: a Distributed Map per state and parameter).
- The remedial-action report can't be read by script; the app records fixes itself.
- 3 old failed workflows from Fri 23:12 (before the retry fix) still show as FAILED in Step Functions; their cases were reset since.
- Not built (D-31): Hindi video alert (S1). SES email is built (district digest) but waits for verified addresses (sandbox).
