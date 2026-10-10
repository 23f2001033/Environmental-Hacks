# Decision log

Every decision that shapes the build, with the options we weighed and why we chose what we did. Add a new entry instead of editing an old one; mark the old one **Superseded** and link the new one.

Format: **Context** (why we had to decide) · **Options** · **Decision** · **Why** · **Consequences** · **Revisit if**

| ID | Decision | Status |
|---|---|---|
| [D-01](#d-01-problem-and-track) | Rural drinking-water contamination follow-up, Heat and Water track | Accepted |
| [D-02](#d-02-trigger-official-lab-results-not-crowd-reports) | Trigger on official lab results, not crowd reports | Accepted |
| [D-03](#d-03-demo-geography-and-scope) | Demo on Harpalpur (Hardoi, UP) and Baran (Rajasthan); ingest only UP and Rajasthan | Accepted |
| [D-04](#d-04-primary-user-is-the-village-relay) | Primary user is the anganwadi worker or water committee member | Accepted |
| [D-05](#d-05-channel-telegram) | Telegram bot as the channel | Accepted |
| [D-06](#d-06-no-model-in-the-safety-path) | No model in the safety path; Bedrock optional | Accepted |
| [D-07](#d-07-advice-is-specific-to-the-contaminant) | Advice is specific to the contaminant | Accepted |
| [D-08](#d-08-closed-by-evidence-enforced-by-cedar) | Cases close only on lab evidence, enforced by Cedar | Accepted |
| [D-09](#d-09-orchestration-step-functions) | Step Functions for the case lifecycle and the scale run | Accepted |
| [D-10](#d-10-storage-dynamodb-single-table-and-s3) | DynamoDB single table plus S3 | Accepted |
| [D-11](#d-11-python-312-on-lambda) | Python 3.12 on Lambda (arm64) | Accepted |
| [D-12](#d-12-infrastructure-as-code-aws-cdk-in-python) | AWS CDK in Python | Accepted |
| [D-13](#d-13-web-hosting-s3-and-cloudfront) | Web hosting on S3 and CloudFront | Accepted (supersedes Amplify in the first plan) |
| [D-14](#d-14-frontend-plain-html-css-and-javascript) | Plain HTML, CSS and JavaScript with MapLibre | Accepted |
| [D-15](#d-15-region-ap-south-1) | Region ap-south-1 (Mumbai) | Accepted |
| [D-16](#d-16-voice-polly-kajal-in-hindi) | Polly Kajal, hi-IN, MP3 | Accepted |
| [D-17](#d-17-data-access-replicate-the-portals-own-calls-politely) | Replicate the portal's own calls, politely, with snapshots | Accepted |
| [D-18](#d-18-wording-and-honesty-rules) | Wording and honesty rules | Accepted |
| [D-19](#d-19-secrets-and-access) | Secrets in SSM; one deployer account | Accepted |
| [D-20](#d-20-privacy) | Consent first, minimal data, delete on request | Accepted |
| [D-21](#d-21-testing-and-ci) | Table-driven tests and CI from the first commit | Accepted |
| [D-22](#d-22-execution-playbook-and-freeze) | Deploy first, living status file, freeze Saturday 18:00 | Accepted |
| [D-23](#d-23-out-of-scope) | What we will not build | Accepted |
| [D-24](#d-24-stretch-order) | Stretch order, including the Hindi video alert | Accepted |
| [D-25](#d-25-who-writes-the-code) | Claude Code implements; each lane owner accepts and tests | Accepted |

---

## D-01 Problem and track

**Context.** We had one weekend and about 1,000 competing teams. We needed a real, unclaimed problem with public data, a specific person and a decision they make today.

**Options we evaluated** (details in [RESEARCH.md](RESEARCH.md#ideas-we-rejected)):

| Option | Why not |
|---|---|
| Rooftop solar health check (post-install) | Needs each household's generation data, which we can't get; model error is as large as the loss we'd detect |
| Stubble-burning verification for incentives | About 12 stubble repos at this event; one already issues "no burn" certificates; our Sentinel-2 test worked about half the time |
| GRAP compliance alerts for societies | Felt like a civic utility, not an environmental fix |
| Waste segregation trust loop | Strong research, but needs an on-ground pilot we can't run this weekend |
| Public-transport routing (Amazon Location transit) | Crowding, street-level AQI and waterlogging data don't exist; Google Maps already routes these cities |
| AQI-spike "accountability reels" on Instagram | Little change for people living with it; source attribution is a guess; Instagram publishing needs Meta approval; AERIS (204 commits) already does attribution |
| Crowdsourced dirty-water reports | Teesri Shikayat (81 commits) and PaaniAlert already do it well |

**Decision.** Close the loop after a village's drinking water fails its official lab test. Heat and Water track.

**Why.** Largest harm we could find (diarrhoea is India's main water-linked killer), verified public data down to the sample, a clear decision for a specific person, and no team at this event works from lab results. The organizers' own fit line names "the water safer".

**Consequences.** We compete in the most crowded track against strong water projects, so our differentiation (invisible contamination, lab evidence, contaminant-specific advice) must be obvious in the first 20 seconds of the video.

**Revisit if.** WQMIS stays down through Saturday morning and the snapshot is empty. Then we run the demo from the verified fixture records and say so.

## D-02 Trigger: official lab results, not crowd reports

**Context.** Every other drinking-water project here fires when residents report dirty water.

**Options.** Crowd reports (Telegram or WhatsApp); hospital or pharmacy signals; official lab results from WQMIS.

**Decision.** Official lab results.

**Why.** Labs catch what people can't see: E. coli in clear water, nitrate, fluoride, arsenic. No cold start: cases open for every failed village on day one without enrolling anyone. Every number on screen is a government record, not a simulation.

**Consequences.** We depend on a portal with no official API that was flaky on 9 Oct (D-17). Results can be weeks old, so we always show the lab date.

**Revisit if.** Never for the core. Crowd reports could be added later as a second signal.

## D-03 Demo geography and scope

**Context.** "A small problem solved well beats a big one solved vaguely" (judging criteria).

**Decision.** Demo on the Harpalpur block cluster (Hardoi, UP: at least 8 villages with E. coli in one 15 June 2026 lab batch) and Dhabla Kalayanpura (Baran, Rajasthan: nitrate 60 mg/L). Ingest only Uttar Pradesh and Rajasthan.

**Why.** Hindi-speaking areas (Polly's Hindi voice, our reviewers' language). One real cluster tells the story; one chemical case shows why contaminant-specific advice matters. Two states keep the scale run meaningful but cheap.

**Consequences.** National coverage is a "next step", not part of the demo.

## D-04 Primary user is the village relay

**Context.** Many rural households don't have smartphones or don't read well.

**Options.** Every household directly; the gram pradhan; the anganwadi worker or water committee member; the engineer only.

**Decision.** The anganwadi worker or water committee member is the primary user; the block engineer is secondary.

**Why.** The anganwadi worker feeds under-six children every day, already relays health messages, and JJM trains five women per village to use field test kits. A forwardable voice note and a wall poster reach households without phones.

**Consequences.** The product must make relaying effortless: one voice note to forward, one poster to pin.

## D-05 Channel: Telegram

**Options.**

| Channel | Problem |
|---|---|
| WhatsApp | Needs a Meta Business account and approved templates; not doable by Sunday |
| SMS | Needs DLT registration in India |
| Phone calls (IVR) | Needs a DID number and DLT; JalSakshi's calls still aren't live |
| Email | Villagers don't use it |
| **Telegram bot** | Free, instant, works tonight; Teesri Shikayat proved it |

**Decision.** Telegram, behind a channel adapter so WhatsApp can plug in later.

**Consequences.** Most villagers use WhatsApp, so the voice note and poster are designed to be forwarded there. We say this in the video.

## D-06 No model in the safety path

**Context.** Teesri Shikayat's new AWS account had a Bedrock quota of 0. Ours works (Claude Haiku 4.5 through the India cross-region profile answered a test call on 9 Oct), but safety advice must never depend on a model anyway.

**Decision.** Severity, advice, deadlines and closure are plain code and data. Bedrock is optional, used only for stretch S2 (suggesting a field-kit result from a photo, which a person confirms).

**Why.** Correctness, auditability, and no single point of failure. Judges reward "the model decides language, code decides actions".

**Consequences.** All Hindi copy is written and reviewed by people, ahead of time.

## D-07 Advice is specific to the contaminant

**Decision.** Advice comes from an advice library keyed by contaminant: boil for E. coli and coliform; never boil for nitrate, fluoride or arsenic; use another tested source; never give nitrate water to infants under six months.

**Why.** Boiling kills bacteria but doesn't remove chemicals, and it concentrates nitrate. 3,090 villages have nitrate failures this year. Every other water project here says "boil".

**Consequences.** The rule is enforced three ways: the library, a unit test, and a Cedar policy that denies any chemical-contaminant message containing boil advice.

## D-08 Closed by evidence, enforced by Cedar

**Options.** The engineer marks it fixed; residents confirm it's clean; a test decides.

**Decision.** A field-kit "clean" result moves a case to ProvisionallySafe. Only a passing lab result moves it to Closed. Cedar (AWS open source) enforces this and fails closed: missing context or an evaluation error is a deny, recorded on the case timeline.

**Why.** Nobody can confirm invisible contamination by eye. It also gives the demo a clear moment: the engineer tries to close the case and Cedar denies it.

**Consequences.** The lab re-test in the demo is a labelled simulation (a console button), because we can't make a real lab upload this weekend.

## D-09 Orchestration: Step Functions

**Decision.** One Standard execution per case, with task tokens for engineer and field-kit callbacks and timed waits for deadlines. A Distributed Map run opens cases at scale. A demo clock shortens hours to minutes.

**Why.** Cases wait for days; Standard workflows handle long waits and callbacks cleanly, and the execution graph shows the loop on camera.

**Consequences.** Telegram button presses must find the right task token, so we store tokens server-side under a short ID (Telegram callback data is limited to 64 bytes).

## D-10 Storage: DynamoDB single table and S3

**Decision.** One DynamoDB table with keys designed for our reads (village, case, timeline, subscribers, open cases per block). S3 for raw snapshots, voice notes, field-kit photos and the web app.

**Why.** Serverless, near-free at this scale, no schema migrations under time pressure.

## D-11 Python 3.12 on Lambda

**Decision.** Python 3.12, arm64 Lambdas.

**Why.** The WQMIS client is already proven in Python; boto3 and `cedarpy` are Python; the team reads Python. arm64 is cheaper.

**Consequences.** `cedarpy` and `pycryptodome` have native wheels, so the bundling step must fetch wheels for Linux arm64.

## D-12 Infrastructure as code: AWS CDK in Python

**Options.** AWS SAM; AWS CDK; console clicks.

**Decision.** AWS CDK in Python, one stack, run through `npx aws-cdk` (no global install).

**Why.** Same language as the code; the state machine is defined in code next to the Lambdas; one command deploys everything; reproducible for judges.

## D-13 Web hosting: S3 and CloudFront

**Context.** The first plan said Amplify Hosting.

**Decision.** S3 plus CloudFront, deployed by CDK. **Supersedes** Amplify in the first plan.

**Why.** Amplify's Git integration needs the repo owner to authorise GitHub in the console. S3 and CloudFront deploy in the same command as everything else.

## D-14 Frontend: plain HTML, CSS and JavaScript

**Decision.** Two pages (village page, block view) in plain HTML, CSS and JavaScript, with MapLibre GL and Amazon Location map tiles. No build step.

**Why.** Two screens don't need a framework; fewer things can break; anyone on the team can edit them.

**Revisit if.** The UI owner is much faster in React.

## D-15 Region ap-south-1

**Decision.** Everything in Mumbai (ap-south-1).

**Why.** Users and data are in India; Bedrock has an India-only inference profile here; Polly Hindi, Amazon Location and the transit APIs are all available here; we verified each one on 9 Oct.

## D-16 Voice: Polly Kajal in Hindi

**Decision.** Polly voice Kajal (neural, bilingual Hindi and Indian English) with `LanguageCode=hi-IN`, MP3, sent with Telegram `sendAudio`.

**Why.** Tested working on 9 Oct. `hi-IN` makes Polly read numbers in Hindi. MP3 forwards cleanly to WhatsApp.

## D-17 Data access: replicate the portal's own calls, politely

**Context.** WQMIS has no public API. Its pages encrypt query parameters in the browser with a fixed key published in the site's own JavaScript.

**Decision.** Our client makes the same calls a browser makes: open the sample-list page to start a session, then call `ContaminantwiseVillagefil` and `Contaminantwisesamplefillist`. One run a day, two states, pauses between calls, retries with backoff. A partial-data guard and a committed snapshot.

**Why.** It's the only machine-readable route to the data, and everything we read is already public. Snapshots make the demo reproducible and protect against outages.

**Consequences.** On 9 Oct evening the portal returned HTTP 500 and partial zeros, so the guard and snapshot are required, not optional.

## D-18 Wording and honesty rules

**Decision.**
- Say "no fix visible to the village", never "nothing was done".
- Show "not tested" as unknown, never as safe.
- Show the lab date and "data as of" on every page and alert.
- Label every simulated part on screen (demo clock, simulated lab result, team members playing roles).
- Use illustrative personas, never real people's names.

**Why.** Judges score trust; the organizers ask teams to state data sources and freshness.

## D-19 Secrets and access

**Decision.** One AWS account (Aman's), deploys run from his machine. Secrets in SSM Parameter Store as SecureStrings (`/jalsaathi/telegram/bot-token`, `/jalsaathi/telegram/webhook-secret`, `/jalsaathi/console-token`), never in Git. The Telegram webhook checks its secret-token header.

**Why.** Speed and cost control; teammates don't need AWS credentials to contribute code, copy, tests or the video.

## D-20 Privacy

**Decision.** Store only Telegram chat ID, role, village and consent time, and only after the person taps yes. `/stop` deletes them. Public pages show village-level data only.

## D-21 Testing and CI

**Decision.** pytest from the first commit: table-driven tests for rules and advice, a policy matrix for Cedar, the WQMIS source-text parser, state transitions and Telegram update parsing. GitHub Actions runs them on every push.

**Why.** Correctness is our pitch, and tests let four people change code safely at speed.

## D-22 Execution playbook and freeze

**Context.** The strongest team here deployed a working webhook in their second commit and kept a living status file.

**Decision.**
- Deploy something real within the first hour.
- Keep `state.md` current at every milestone.
- One-command `preflight.py` and `demo.py` (seed, reset, clock, scale run).
- `video/slides-data.json` holds every on-screen number with its source.
- A Playwright script tours the pages for repeatable shots.
- Feature freeze **Saturday 18:00**; record Saturday night and Sunday morning; submit by **Sunday 16:00** (deadline 20:00).

## D-23 Out of scope

WhatsApp, SMS and IVR delivery; login screens; writing back to WQMIS; languages beyond Hindi and English; national ingest. Each is named in the video as a next step.

## D-24 Stretch order

Only after the Saturday 18:00 freeze is green, in this order:

1. **S1 Hindi video alert** per village (Polly narration over an animated card, about 20 seconds, to forward on WhatsApp). From Umar's reels idea: keeps its strength for the demo video while serving the people who drink the water.
2. **S2** Bedrock suggests the field-kit result from the photo; the person confirms.
3. **S3** Scheme-level warnings across habitations on the same scheme.
4. **S4** District escalation by SES email.
5. **S5** Repeat-failure analysis across two financial years.

## D-25 Who writes the code

**Decision.** Claude Code, in Aman's session, implements most of the code quickly. Each lane has a human owner who reviews, tests on real phones, accepts the work against the done criteria in the build plan, and owns the copy and content for that lane.

**Why.** Speed: the strongest competitor built 81 commits in a day the same way. Ownership: people still decide what is correct and what ships.

## D-26 Scale run through a Distributed Map, paced

**Decision.** Ingests with more than 25 new cases write the list to `s3://<bucket>/runs/scale-items.json` and start the `ScaleRun` state machine. Its Distributed Map (Express children, at most 3 at a time) starts one case workflow per item and then waits 3 seconds, so about one case starts per second. Workflow names are deterministic (`case id + hash + run id`), and `ExecutionAlreadyExists` is caught, so a retried item can never start a case twice. Up to 5% of items may fail without failing the run; failed cases can be restarted from the console.

**Why.** The real snapshot has about 580 open failures. A new AWS account has a Lambda concurrency limit of 10, and starting 580 workflows at once throttled earlier runs (3 of 13 failed even at demo size). Pacing keeps every case inside the limit without asking AWS for a quota increase. It is also the honest answer to "does this scale?": a measured run over real data, with its duration and failures in `/stats`.

## D-27 Real deadlines for real data; demo clock only for fixtures

**Decision.** Only the 13 demo fixture cases use the minutes-long demo clock. Cases from the snapshot or live ingest get the real deadlines (red: 48 h to fix, 7 days to re-test).

**Why.** Real villages must never get a "deadline passed" escalation four minutes after a case opens.

## D-28 Voice notes on first need

**Decision.** Polly makes a case's voice note only when someone will hear it: a relay is subscribed when the alert goes out, a relay joins later, or someone opens the village page. Demo fixtures always get theirs up front. The audio path is stored on the case, so each note is made once.

**Why.** Most of the 580 real villages have no relay yet. Making audio nobody hears costs money and time inside the paced scale run.

## D-29 Map locations are checked, not trusted

**Decision.** Villages are geocoded with Amazon Location (`geo-places` Geocode, `IntendedUse=Storage` because we keep the result). A result is accepted only when its district matches the WQMIS district, its name matches the village, and it is a place rather than a shop or street. Otherwise we try the block, then the district, each also matched by name, and mark the point `geo_precision: "block"` or `"district"` (drawn hollow on the map). If none matches, the village has no pin.

**Why.** In testing, the geocoder put "Dhabla Kalayanpura, Baran" in Jaipur district, "Bhajangarh, Baran" at a flour mill, and answered "Anta block, Baran" with Baran town. A wrong pin on a water-safety map is worse than no pin.

## D-30 AI reads the field-kit photo, the person decides (stretch S2)

**Decision.** When a village relay sends a photo, a Bedrock model suggests the vial colour (black, yellow or unclear): Claude Haiku 4.5 (India inference profile) first, Amazon Nova Pro if Claude is unavailable. Anthropic models need an AWS Marketplace subscription, which this account cannot complete without a payment card; Nova needs none. The timeline records which model answered. The message says it is only a suggestion. The case moves only when the person taps a result button. The timeline records the suggestion and whether the person agreed.

**Why.** It helps a first-time relay read the vial, and the agree/disagree record shows how reliable the suggestion is, without letting a model close or reopen a case.

## D-31 Stretch items not built

- **S1 Hindi video alert:** needs an ffmpeg layer and Devanagari text rendering in Lambda. The voice note plus the printable poster cover the same need for now.
- **S4 SES email escalation:** SES is in sandbox, so it could only email verified addresses. Telegram escalation to the block engineer is in place.
- **S5 Repeat-failure analysis** was built as a script plus bundled results (`data/analysis/repeat_failures.json`, shown in `/stats`) rather than a live job, because last year's data does not change.
