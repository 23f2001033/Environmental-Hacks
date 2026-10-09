# State: what's built so far

Last updated: Fri 9 Oct 2026, 23:45 IST · Deadline Sun 11 Oct, 20:00 IST · Feature freeze Sat 18:00 · Submit by Sun 16:00

Owner: lane 4 (Umar). Everyone updates it when they finish something, start something big, or get blocked.

## Live now (AWS ap-south-1, stack `JalSaathi`)

| What | Where |
|---|---|
| Site (frontend build space; placeholder for now) | https://d2735023v3xj6.cloudfront.net |
| **Test console** (every feature, demo controls) | https://d2735023v3xj6.cloudfront.net/test/ |
| API v1 ([contract](docs/API.md)) | https://d2735023v3xj6.cloudfront.net/api/v1/health |
| Telegram bot | [@Srott_bot](https://t.me/Srott_bot) |
| Demo clock | **On**: fix deadline 4 min, re-test 5 min, lab 15 min; at most 3 escalations per step |

Admin token for the test console's demo controls: SSM `/jalsaathi/console-token` (ask Aman; never post it in the group).

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

## Bugs found and fixed while testing

| Bug | Fix |
|---|---|
| 3 of 13 workflows failed: Lambda `TooManyRequestsException` (new account concurrency limit is **10**) | Every step retries throttling with backoff and jitter; `restart-case` admin route |
| A rejected action (lab result before a fix) was still written to the timeline | Check the waiting step first, record second; tests added |
| Timeline events in the same second could show out of order | Event keys use nanosecond time |
| Under the demo clock, an untouched case escalated every 4 minutes forever | Max 3 escalations per step, then it waits quietly; reminder says which deadline was missed |
| Cedar "forbid" rule errors on missing context while the "permit" still allows (fail open) | Wrapper denies on any evaluation error; test locks it in |

## Needs a person

| Item | Who | Needed by |
|---|---|---|
| **Test the bot on real phones** (links below) | Reshma, Umar | Sat 09:00 |
| Hindi review of `content/advice.json` and bot messages in `src/jalsaathi/webhook.py`, `case_steps.py` | Umar | Sat 12:00 |
| Frontend stack and direction (build space: `frontend/`, contract: `docs/API.md`) | Frontend lead | Sat 10:00 |
| Approve a Lambda concurrency increase request (10 → 1000; free) | Aman | Sat 09:00 |
| WQMIS WQ2 (Remedial Action) browser check for Hardoi, Harpalpur | Umar | Sat 09:00 |
| Accept GitHub invites | Umar, @faizsaleem8 | now |

### Phone test links

1. Relay (village worker): open <https://t.me/Srott_bot?start=v_412558> (Behta Lakhi) → tap हाँ → you get the Hindi alert and the voice note.
2. Engineer (Harpalpur block): on a second phone open <https://t.me/Srott_bot?start=e_5037> → tap हाँ. New case cards arrive there; after a demo reset and seed, every Harpalpur case sends one.
3. Engineer taps "✅ केस बंद करें" → Cedar refuses. Taps "🧪 क्लोरीनेशन किया" → the relay phone is asked for the field-kit photo.
4. Relay sends any photo, then taps 🟡 पीली (साफ़) → "provisionally safe".
5. Test console → the village → "Lab: pass (simulated)" → both phones hear "safe again".

`python scripts/demo.py links` prints links for every village.

## Next

1. Merge PR `l2/m0-core` after CI passes
2. Commit the WQMIS snapshot when the portal recovers; `source=snapshot` ingest
3. Scale run (Distributed Map over the snapshot) with time and cost measured
4. Village coordinates (Amazon Location) for the block map
5. Hindi video alert per village (stretch S1)

## Open issues

- WQMIS is flaky (HTTP 500, partial data). The snapshot job keeps retrying; so far one file saved (UP, E. coli, FY 2026-27).
- The remedial-action report can't be read by script; the app records fixes itself.
- Lambda concurrency 10: fine for the demo with retries, slow for the scale run.
