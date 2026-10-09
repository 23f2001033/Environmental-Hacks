# State: what's built so far

Last updated: Fri 9 Oct 2026, 21:00 IST · Deadline Sun 11 Oct, 20:00 IST · Feature freeze Sat 18:00 · Submit by Sun 16:00

Owner: lane 4 (Umar). Everyone updates it when they finish something, start something big, or get blocked.

## Done

| When (IST) | What | Notes |
|---|---|---|
| Thu–Fri | Idea research and selection | See [docs/RESEARCH.md](docs/RESEARCH.md) and [docs/DECISIONS.md](docs/DECISIONS.md) |
| Fri 18:15 | WQMIS data access proven by script; demo records verified | `data/fixtures/wqmis_demo_records.json` |
| Fri 20:30 | AWS checks in ap-south-1: Bedrock (Claude Haiku 4.5, India profile), Polly Kajal Hindi, Amazon Location geocode, SES sandbox | All working |
| Fri 20:46 | Repo collaborators invited | Reshma joined; Umar and @faizsaleem8 pending |
| Fri 21:00 | PRD, build plan, decision log, setup checklist, research, this file | This commit |

## In progress

| What | Who | Notes |
|---|---|---|
| WQMIS snapshot job | Claude Code | Portal returning HTTP 500 since about 20:15; retrying every 15 minutes |

## Live resources

None yet. The first deploy (Telegram webhook echo) needs the bot token.

## Blocked / needs a person

| Item | Who | Needed by |
|---|---|---|
| Telegram bot token (see [docs/SETUP.md §3](docs/SETUP.md#3-create-the-telegram-bot-5-minutes)) | Anyone | Fri 22:00 |
| Accept GitHub invites | Umar, @faizsaleem8 | Fri 22:00 |
| Confirm lane owners | Everyone | Fri 23:30 check-in |
| Email for the budget alert | Aman | Sat 09:00 |
| WQMIS Format WQ2 (Remedial Action) browser check for Hardoi, Harpalpur, FY 2026-27 | Umar | Sat 09:00 |

## Next (M0, tonight)

1. CDK stack and webhook echo deployed (needs the token)
2. Rules engine and advice library with tests
3. Cedar policies with the policy matrix tests
4. WQMIS client moved into `src/jalsaathi/` with recorded-response tests
5. CI running pytest

## Open issues

- WQMIS is flaky: HTTP 500 and partial zeros on 9 Oct evening. The demo runs from the snapshot or the fixtures.
- Remedial-action data can't be read by script; the app records fixes itself.
