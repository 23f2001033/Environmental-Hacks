# Data

| Folder | What | Provenance |
|---|---|---|
| `fixtures/` | Verified demo records, small and hand-checked, used by tests and as a fallback demo source | Transcribed from JJM-WQMIS responses on 9 Oct 2026; see the `notes` in each file |
| `snapshot/` | Full WQMIS snapshots for Uttar Pradesh and Rajasthan (E. coli, total coliform, nitrate, fluoride, arsenic; FY 2025-26 and 2026-27), with `manifest.json` | Written by `scripts/snapshot_wqmis.py`; added once the portal recovers |

**Source:** Jal Jeevan Mission Water Quality Management Information System (JJM-WQMIS), Department of Drinking Water and Sanitation, Ministry of Jal Shakti, Government of India. Public reports: <https://ejalshakti.gov.in/WQMIS/Main/report>.

**How we read it:** see [docs/BUILD_PLAN.md, section 3](../docs/BUILD_PLAN.md#3-data-pipeline). One run a day, two states, pauses between calls.

**Rules for using this data:**

- Show the lab approval date and the "data as of" date wherever a result appears.
- A missing remedial-action date means "no fix visible to the village", not "nothing was done".
- A village or source with no test is "unknown", never "safe".
