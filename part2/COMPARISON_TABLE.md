# Part 2 — Comparison Table (template)

Run `python pipeline.py compare ground_truth/pages.json` once
`ANTHROPIC_API_KEY` is set and every page's `ground_truth_jd` is filled in,
then paste the resulting rows into this table. Columns match what the
assignment asks for; `pipeline.py` logs everything needed to fill them in.

| Page ID | ATS | Content completeness (vs ground truth) | Unrelated-content contamination | Full-extraction success | Latency (ms) | Cost/page ($) |
|---|---|---|---|---|---|---|
| breezy_zerohash_01 | Breezy HR | | | | | |
| breezy_nucamp_02 | Breezy HR | | | | | |
| cisco_legacy_03 | Cisco (legacy) | | | | | |
| cisco_phenom_04 | Phenom People | | | | | |
| smartrecruiters_visa_05 | SmartRecruiters | | | | | |
| avature_bloomberg_06 | Avature | | | | | |
| icims_07 | iCIMS | | | | | |
| jazzhr_08 | JazzHR | | | | | |
| workday_09 | Workday | | | | | |
| teamtailor_10 | Teamtailor | | | | | |

**Totals**

| Metric | LLM-only | Hybrid |
|---|---|---|
| Total cost (10-page pilot) | | |
| Successful full-extraction rate | | |
| Average latency | | |
| **Projected cost @ 100,000 pages** | `python pipeline.py project-cost --pages 100000` (LLM-only branch of the output) | `python pipeline.py project-cost --pages 100000` (hybrid branch) |

Notes on filling this in:
- "Unrelated-content contamination" = 1 − `completeness_vs_ground_truth`
  reported by the comparison harness is a rough proxy; for a real writeup,
  spot-check a few extractions manually since word-overlap alone can miss a
  case where boilerplate got mixed *in* alongside a fully-recovered JD.
- The 100k-pages projection is sensitive to `--pages-per-template`, which
  can't be estimated reliably from a 10-page pilot — run it at a few values
  (10, 50, 250, 1000) and report the range rather than a single number, as
  `pipeline.py`'s own docstring for `project_cost_100k` notes.
