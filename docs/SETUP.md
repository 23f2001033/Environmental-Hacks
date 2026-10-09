# Before we start

Everything that must be ready before and during the build. Status as of Fri 9 Oct 2026, 21:00 IST. Update the status column as items are done.

## 1. Accounts and access

| Item | Owner | Status | How |
|---|---|---|---|
| GitHub repo `23f2001033/Environmental-Hacks` | Aman | ✅ Created (public) | — |
| Repo access: Reshma | Reshma | ✅ Joined | — |
| Repo access: Umar | Umar | ⏳ Invite pending | Accept the invite email or open <https://github.com/23f2001033/Environmental-Hacks/invitations> |
| Repo access: @faizsaleem8 | Faiz | ⏳ Invite pending | Same as above |
| AWS account (ap-south-1) | Aman | ✅ Ready | Admin user for deploys; teammates don't need AWS credentials |
| Bedrock (Claude Haiku 4.5, India profile) | Aman | ✅ Tested 9 Oct | Only needed for stretch S2 |
| Polly Kajal in Hindi | Aman | ✅ Tested 9 Oct | — |
| Amazon Location geocoding | Aman | ✅ Tested 9 Oct (found Behta Lakhi, Hardoi) | — |
| SES | Aman | ✅ Sandbox (200 a day, verified recipients only) | Only for stretch S4 |
| AWS budget alert at $20 | Aman | ⏳ Needs an email address | Existing "zero-spend" budget alerts at $1; fine to keep |
| **Telegram bot and token** | Anyone with Telegram | ⏳ **Blocks the first deploy** | See section 3 |
| Two phones with Telegram (relay and engineer) | Reshma, Umar | ⏳ | Any Android; used for rehearsal and recording |
| AWS Builder Center student verification | Each of us | ⏳ Check | Required for prizes and the Amazon fast-track interviews |
| WQMIS snapshot | Claude Code / Reshma | ⏳ Portal returning HTTP 500 since about 20:15 on 9 Oct | Background job retries every 15 minutes; verified fixture records are already in `data/fixtures/` |

## 2. Local tools (only for people who run code)

| Tool | Version | Check |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.12 recommended (3.11 works for tests) | `python --version` |
| uv | recent | `uv --version` |
| Node.js | 20 or newer (for `npx aws-cdk`) | `node -v` |
| AWS CLI v2 | Aman only | `aws --version` |
| Docker | Aman only, for bundling Lambda wheels | `docker --version` |
| Playwright | Lane 4, for the screen tour | `uv run playwright install chromium` |

First run, once the code lands:

```bash
git clone https://github.com/23f2001033/Environmental-Hacks.git
cd Environmental-Hacks
uv venv && uv pip install -r requirements-dev.txt
uv run pytest -q
```

## 3. Create the Telegram bot (5 minutes)

1. In Telegram, open **@BotFather** and send `/newbot`.
2. Name: `JalSaathi`. Username: something free ending in `bot`, for example `JalSaathiAlertBot`.
3. BotFather replies with a token like `123456:ABC...`. **Treat it like a password.** Don't post it in the WhatsApp group or commit it.
4. Give it to Aman privately, or store it yourself:
   - AWS console → Systems Manager → Parameter Store → Create parameter
   - Name `/jalsaathi/telegram/bot-token`, type **SecureString**, value = the token, region **Asia Pacific (Mumbai)**.
5. Optional, in BotFather: `/setdescription` (Hindi and English description), `/setuserpic` (logo), `/setcommands`:
   ```
   status - इस गाँव के पानी की स्थिति / Water status for this village
   stop - सदस्यता बंद करें / Stop and delete my data
   help - मदद / Help
   ```

## 4. Conventions

| Topic | Rule |
|---|---|
| Branches | `l1/...`, `l2/...`, `l3/...`, `l4/...`; pull request into `main` |
| Commits | Small, at least every 2 hours while working; prefix `feat:`, `fix:`, `test:`, `docs:`, `infra:`, `chore:` |
| Reviews | Rules, advice copy and Cedar policies need one teammate's review; other small PRs can be self-merged after CI passes |
| Secrets | Never in Git, chat or screenshots; SSM Parameter Store only |
| Text encoding | UTF-8 everywhere (Hindi text) |
| Copy | Hindi first; plain words; numbers with units; no fear-mongering |
| Data | Only real WQMIS records, or simulations labelled as such |
| Status | Update `state.md` when you finish something, start something big, or get blocked |

## 5. Communication

- **Check-ins** in the WhatsApp group, 10 minutes, format: done / next / blocked. Fri 23:30 · Sat 09:00, 13:00, 18:00, 22:00 · Sun 09:00, 13:00.
- **Blocked for more than 30 minutes:** post what you tried and what you need.
- **Feature freeze:** Saturday 18:00 IST. **Submit by:** Sunday 16:00 IST (deadline 20:00).

## 6. Decisions the team still needs to make

| Decision | Who | By |
|---|---|---|
| Confirm lane owners | Everyone | Fri 23:30 |
| Bot username | Whoever creates the bot | Fri 22:00 |
| Email for the budget alert and SES test inbox | Aman | Sat 09:00 |
| Repo license (MIT proposed) | Aman | Sun 12:00 |
| Who narrates the video (Hindi and English) | Umar | Sat 18:00 |
