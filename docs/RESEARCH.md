# Research

Evidence behind JalSaathi, what we verified ourselves, the competitive landscape at this event, and the ideas we rejected. Collected on 9 Oct 2026. Use this for the writeup and the blog.

## 1. The problem in numbers

| Fact | Source |
|---|---|
| JJM labs had tested 38.78 lakh drinking-water samples across 4,49,961 villages (as of 21 Oct 2025); women trained to use field test kits in 5.07 lakh villages | [PIB JJM factsheet, Oct 2025](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/oct/doc20251026676401.pdf) |
| FY 2026-27 (April to 9 Oct 2026), piped-water sources, lab tests: villages with contamination found — E. coli 2,616; total coliform 5,334; nitrate 3,090; fluoride 1,359; arsenic 35 | JJM-WQMIS Format WQ6, read by our script on 9 Oct 2026 about 18:15 IST (later calls that evening returned partial data) |
| FY 2025-26, same report: E. coli 4,640; total coliform 7,122; nitrate 5,701; fluoride 2,217; arsenic 282 villages | Same |
| Counts per parameter overlap (one village can appear under several), so they must not be added together | — |
| WHO (2019 data): about 4,97,738 deaths in India attributable to unsafe water, sanitation and hygiene, about 4,45,638 of them from diarrhoea; safely managed drinking water for all households could avert nearly 4 lakh diarrhoeal deaths | [WHO health impact study, JJM workshop deck](https://jaljeevanmission.gov.in/sites/default/files/2023-06/WHO-health-impact-study-workshop.pdf); [Tribune](https://tribuneindia.com/news/har-ghar-jal-can-avert-4-lakh-diarrhoeal-deaths-says-who-515774) |
| CAG Report No. 10 of 2025 on JJM: in Jammu and Kashmir, 897 samples that failed at sub-divisional labs (2019-20 to 2023-24) were never referred to district or state labs; in Rajasthan no block-level lab was functional as of July 2024 | [CAG](https://cag.gov.in/en/audit-report/details/123724); [Gulistan News](https://gulistannewstv.com/cag-flags-gaps-in-jk-water-quality-monitoring-under-jal-jeevan-mission/); [The Wire](https://m.thewire.in/article/government/over-70-of-central-funds-allocated-for-jal-jeevan-mission-not-utilised-in-rajasthan) |
| JJM guidance: a failed test requires remedial action and, for chemical contamination, restricting the water for drinking and providing an alternative supply | [JJM community training material](https://ejalshakti.gov.in/KRC/Content/PDF/L3_Training_Material_Final_with_instructions.pdf) |
| Indore (Bhagirathpura), Dec 2025 to Feb 2026: sewage entered the drinking-water main through a leak; reported deaths range from 16 to 32, about 1,400 ill; residents had complained about foul water for months | [Wikipedia](https://en.wikipedia.org/wiki/2025_Indore_drinking_water_contamination); [Newsweek](https://www.newsweek.com/indore-india-drinking-tap-water-10-dead-11297559); [AIR](https://www.newsonair.gov.in/madhya-pradesh-hc-sets-up-commission-of-inquiry-to-investigate-water-contamination-issue-in-bhagirathpura/) |
| Boiling kills bacteria but does not remove nitrate and concentrates it as water evaporates | [Iowa DNR](https://iowadnr.gov/media/4809/download) |
| Drinking-water limits (acceptable / permissible): fluoride 1.0 / 1.5 mg/L; nitrate 45 mg/L; arsenic 0.01 mg/L acceptable; E. coli and total coliform not detectable in 100 mL; turbidity 1 / 5 NTU; TDS 500 / 2,000 mg/L. Secondary tables disagree on some permissible values (arsenic, iron), so we use the limits WQMIS returns with each sample | [IS 10500:2012](https://consumerhelpline.gov.in/public/assets/docs/bis/IS10500-2012.pdf) |

## 2. Demo records we verified

Pulled from JJM-WQMIS on 9 Oct 2026 by script. Full list with IDs in [`data/fixtures/wqmis_demo_records.json`](../data/fixtures/wqmis_demo_records.json).

- **Harpalpur block, Hardoi, UP:** one lab batch approved 15 Jun 2026 found E. coli in at least 8 villages (Behta Lakhi 80, Murcha 32, Dhakpura 32, Basi 72, Bhusehra 100, Shyampur Panja 52, Varra 22, Nagra Choudharpur 40 CFU/100 mL; limit 0). Each runs its own deep-tubewell JJM scheme. The block lists 10 villages with E. coli this year; Hardoi district 18.
- **Mahmood Pur Keerat, Chhibramau, Kannauj, UP:** sample U3027060S38720650, deep tubewell, scheme 20014829, E. coli 50 CFU/100 mL, State Level Water Analysis Laboratory, U.P. Jal Nigam (Rural), Lucknow, approved 21 Aug 2026.
- **Dhabla Kalayanpura, Anta, Baran, Rajasthan:** deep tubewell, scheme 20004324, nitrate 60 mg/L (limit 45), approved 5 Aug 2026. Rajasthan has 50 villages with nitrate failures this year, 33 of them in Dausa.

## 3. Data access we verified

- WQMIS reports are public. The page encrypts query parameters in the browser (AES-128-CBC, key and IV from the site's own `frmValidate.js`); a script can make the same calls.
- Working on 9 Oct: `ContaminantwiseVillagefil` (villages with failures) and `Contaminantwisesamplefillist` (samples with values, limits, lab, approval time, source and scheme).
- Not working by script on 9 Oct: district-level `GetContaminantwiseData` (HTTP 500) and the remedial-action report `get_both_structure_delivery_remedial` (redirects). Format WQ2 (Remedial Action) needs a browser check.
- From about 20:15 IST on 9 Oct the portal returned HTTP 500 and partial zeros for large states. Hence the snapshot and the partial-data guard (see [DECISIONS.md, D-17](DECISIONS.md#d-17-data-access-replicate-the-portals-own-calls-politely)).

## 4. AWS checks (9 Oct 2026, ap-south-1)

| Service | Result |
|---|---|
| Bedrock | Claude Haiku 4.5 answered through the India cross-region profile `in.anthropic.claude-haiku-4-5-20251001-v1:0`; account quota for Haiku 4.5 is 50 requests and 5 million tokens per minute |
| Polly | Voice Kajal (neural, bilingual Hindi and Indian English) synthesized Hindi text with `LanguageCode=hi-IN` |
| Amazon Location | `Geocode` found "Behta Lakhi, Sawayajpur, Uttar Pradesh" (Harpalpur block is in Sawayajpur tehsil of Hardoi) |
| SES | Sandbox: 200 emails per day, verified recipients only |
| Step Functions, Lambda, DynamoDB, S3, CloudFront, API Gateway | Available in ap-south-1 |
| Note from a competitor's notes | Their new account had a Bedrock quota of 0 in every region; ours is fine, but nothing in our safety path depends on a model anyway |

## 5. The field at this event (Heat and Water track)

About 90 public repos reference the track. These set the bar on 9 Oct evening:

| Project | What it does | Where it's strong | What it can't do |
|---|---|---|---|
| [Teesri Shikayat](https://github.com/aryangorde6/teesri-shikayat) | Mumbai residents report dirty tap water on Telegram; 3 reports within 250 m warn everyone nearby; only residents can close the case | 81 commits in about 30 hours; Telegram, Transcribe, Polly, Step Functions, Cedar, 64 tests, scripted video pipeline | Fires only after enrolled residents *see* dirty water; 22 of its homes are simulated; its Indore replay is a reconstruction; always advises boiling |
| [Talaab](https://github.com/shloknarvekar/talaab) | Sentinel-2 dry-by countdowns for drought ponds, timed to Maharashtra's 15 Oct scarcity plans | Backtested and validated on a held-out season; whole district on AWS in 161 s for $0; CI | Different problem |
| [JalSakshi](https://github.com/Galabavamsi/jalsakshi) | Hindi phone calls ask JJM villages whether tap water came and whether it was clean | Same villages and loop shape; Cedar, Strands, CDK | Real calls not live yet; "was it clean?" can't detect E. coli in clear water or any chemical |
| [PaaniAlert](https://github.com/ruthvik418/paanialert) | WhatsApp reports of bad water; clusters trigger boil-water advisories | WhatsApp via Twilio; Hindi voice | Same blind spot; boiling is wrong for nitrate |
| [Outbreak Watch](https://github.com/prathignas/outbreak-watch-water_safety) | Early warning for contaminated water in Bengaluru from ward signals | Urban outbreak framing | Early stage on 9 Oct |
| [₹800](https://github.com/himanshu748/rs800), [Chhaon](https://github.com/souvikDevloper/chhaon) | Heat-safe work plans for outdoor workers | ₹800 already has a live app and a published video | Off-season; different problem |

**Our differentiation, in one line:** the only project here that starts from official lab results, so it sees contamination people can't, needs no enrolment, gives advice that is right for the contaminant, and closes cases on test evidence.

## 6. Ideas we rejected

| Idea | Why we dropped it |
|---|---|
| Rooftop solar health check after installation | Needs each household's generation readings, which we can't get; model error (±10–15%) is as large as the losses we'd detect; [WattBack](https://github.com/rohitsagar9/wattBack) does it in the Waste and Energy track |
| Stubble-burning "no burn" verification | About 12 stubble repos here; [parali-se-paisa](https://github.com/AshbinSaji2006/parali-se-paisa) already issues no-burn certificates; our Sentinel-2 test separated burned fields only when a clear image existed within about 3 days |
| GRAP compliance alerts for housing societies | The team felt it was a civic utility; four school projects already encode GRAP rules |
| Waste segregation "trust loop" | Strong research (households stop sorting when collectors mix waste), but it needs an on-ground pilot |
| Public-transport routing on Amazon Location transit | Crowding, street-level air and waterlogging data don't exist; Google Maps already routes these cities; Timestream is closed to new customers |
| AQI-spike "accountability reels" on Instagram | Little change for people living with it; attribution is a guess; Instagram publishing needs a business account and an approved Meta app; [AERIS](https://github.com/sinhaaditya5/AERIS) (204 commits) already does attribution. We kept its best part as stretch S1, a Hindi video alert per village. |
| Crowdsourced dirty-water reports | Teesri Shikayat and PaaniAlert already do this well, and we'd start 36 hours behind |
| Plastic recycling-certificate fraud checker | Real fraud (about 6 lakh fake certificates, ₹355 crore in fines), but CPCB's portal data isn't publicly reachable |
