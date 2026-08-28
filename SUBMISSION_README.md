# Data Engineer Intern Challenge — Submission Notes

## Part 1 — ATS scraper (Breezy HR)

- `jobs/spiders/BreezyBase.py` — base class, follows the same shape as
  `ExampleBase.py`.
- `jobs/spiders/spiders_in_Breezy.py` — 3 company spiders: Zero Hash, Nucamp,
  Barloworld Equipment (all confirmed real, currently-live Breezy HR
  customers).
- `BREEZY_METHOD_NOTES.md` — how the `/json` endpoint was found and how the
  field mapping was verified against Breezy's public API docs.

Run with:
```bash
uv run scrapy crawl ZeroHash
uv run scrapy crawl Nucamp
uv run scrapy crawl BarloworldEquipment
```

**One honest caveat**: I could not make live outbound requests to
`*.breezy.hr` from the sandbox this was built in (network egress there is
limited to package registries), so the field mapping is based on Breezy's
published API schema plus the example the assignment itself gave, not a
live test run of these exact spiders. Worth running them once for real
before treating the output as final — if a field comes back named
slightly differently than expected, the fix is a one-line change in
`BreezyBase.parse()`.

## Part 2 — JD extraction pipeline

- `part2/DESIGN.md` — full technical design: template fingerprinting,
  tiered extraction (structured data → cached rule → cheap LLM → strong-model
  rule generation), validation heuristic, drift detection, cost model.
- `part2/pipeline.py` — runnable prototype implementing all of the above,
  calling the Anthropic API directly for both LLM tiers. Tested locally:
  fingerprinting correctly collapses same-template pages and separates
  different-template pages; the validation heuristic correctly scores real
  job-description text high (0.9) and boilerplate text low (0.05).
- `part2/ground_truth/pages.json` — 10 selected pages across different
  ATS/templates. 1 has fully verified, manually-checked ground truth text
  (Zero Hash / Breezy). The Cisco entry documents a genuinely useful find:
  the URL given as an example in the assignment (`jobs.cisco.com/.../
  ProjectDetail/...`) has since been migrated to a different platform
  entirely (Phenom People) — a live example of exactly the "template
  changed" failure case the pipeline is designed to detect and recover
  from, rather than a hypothetical.
- `part2/COMPARISON_TABLE.md` — the required comparison table, as a
  template with the exact commands to fill it in once you're running with
  a real `ANTHROPIC_API_KEY` and have finished manually verifying the
  remaining ground-truth pages.

**What's genuinely done vs. what's left for you to finish:**
- Done: design, working code (fingerprinting, validation, rule cache,
  structured-data shortcut, LLM call plumbing, cost projection), 1 fully
  verified real ground-truth example, 9 more real URLs identified across
  distinct ATS families.
- Left for you: fill in ground truth text for the remaining 9 pages (a few
  need you to go pick a live example — iCIMS/JazzHR/Workday/Teamtailor
  entries are marked `"company": "TBD"`), set `ANTHROPIC_API_KEY` and run
  `python pipeline.py compare ground_truth/pages.json`, and update
  `PRICE_PER_MTOK` in `pipeline.py` with your account's actual per-token
  pricing before trusting the cost projection.
