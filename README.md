# JalSaathi

**Turns failed drinking-water lab tests into Hindi alerts for the village, advice that is right for the contaminant, and a tracked fix that closes only when a re-test passes.**

Built for **Environmental Hacks** (WeMakeDevs × AWS, Bharat Builds Tour, event 02), **Heat and Water** track, 8–11 October 2026.

> Status: planning complete, build starting Fri 9 Oct 2026, 21:00 IST. Live status is in [state.md](state.md).

## The idea in one paragraph

Government labs under Jal Jeevan Mission already test village drinking water and publish every failure on a public portal (JJM-WQMIS). This year alone they found E. coli in the piped-water sources of 2,616 villages. Water carrying E. coli often looks clear, and nitrate, fluoride and arsenic are invisible, so villagers cannot notice the danger themselves, and the results never reach them. JalSaathi reads those failures, opens a case for each village, sends the anganwadi worker a Hindi alert with a voice note and a printable poster, tells her what to do for that specific contaminant (boil for E. coli; never boil for nitrate), asks the block engineer to fix the source, and keeps the case open until a field-kit test and then a lab test pass.

## Read these first

| Document | What it covers |
|---|---|
| [PRD.md](PRD.md) | The product: problem, users, requirements, scope, success metrics, release criteria |
| [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) | Architecture, components, contracts, lanes and tasks, timeline, team workflow, testing, video |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every major decision, the options we weighed, and why we chose what we did |
| [docs/SETUP.md](docs/SETUP.md) | Everything that must be ready before and during the build, with owners and status |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Evidence, data verification, AWS checks, competitor landscape, ideas we rejected |
| [state.md](state.md) | Live status: done, in progress, blockers, decisions needed |

## Team

| GitHub | Proposed lane (confirm in the group) |
|---|---|
| [@23f2001033](https://github.com/23f2001033) (Aman) | Lane 2: workflow, infrastructure, deploys |
| [@reshmag2023-boop](https://github.com/reshmag2023-boop) (Reshma) | Lane 1: data and proof |
| [@faizsaleem8](https://github.com/faizsaleem8) | Lane 3: Telegram bot and web UI |
| [@U-m-4r](https://github.com/U-m-4r) (Umar) | Lane 4: Hindi review, QA, video and submission |

## Data and credits

- Drinking-water test results: **Jal Jeevan Mission Water Quality Management Information System (JJM-WQMIS)**, Department of Drinking Water and Sanitation, Ministry of Jal Shakti, Government of India. Public reports at <https://ejalshakti.gov.in/WQMIS/Main/report>. We show the "data as of" date on every page.
- Limits: **IS 10500:2012** (Bureau of Indian Standards), as returned with each sample by WQMIS.
- Other credits (fonts, libraries, map data) are listed in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md#credits) as they are added.

## AI tools used

The event rules ask every team to list its AI tools. We use **Claude Code (Anthropic)** for research, planning, documentation and code, driven and reviewed by the team.
