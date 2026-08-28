# Part 2 — Job Description Extraction Pipeline: Technical Design

## Problem restated

Given a job detail page from an arbitrary ATS/company template, produce just
the Job Description (title, responsibilities, requirements, benefits, etc.)
with navigation, cookie banners, headers, footers, and "similar jobs" widgets
stripped out — reliably and cheaply across thousands of distinct templates
and eventually hundreds of thousands of pages.

## Core insight driving the design

Any given ATS **template** (e.g. "Breezy HR's default layout", "this specific
company's custom Workday theme") repeats across every job posting on that
site. The *content* changes per page, but the *DOM shape around* the content
does not. That means:

- Paying an LLM to re-read boilerplate on every single page is wasted spend
  once a template has been seen once.
- A rule (CSS selector / XPath / a JSON-path into a structured-data blob)
  learned from *one* page on a template is reusable across every other page
  on that same template, for free.
- The expensive step (understanding page structure) only needs to happen:
  1. the first time a template is seen, and
  2. again if the template changes (redesign, vendor migration) and the
     learned rule silently stops matching.

This is exactly the Cisco case found while researching Part 1: the
`jobs.cisco.com/jobs/ProjectDetail/...` template used in the original example
now 302-redirects to a completely different Phenom-People-based site. Any
extraction rule cached against the old template needs to be detected as
stale and regenerated — the design below treats this as the normal case, not
an edge case.

## Architecture

```
                         ┌──────────────────────┐
   URL ──▶ fetch(url) ──▶│ template fingerprint  │
                         └──────────┬───────────┘
                                    │
                       cache lookup │ (keyed on fingerprint)
                                    ▼
                     ┌─────────────────────────────┐
                     │ rule cache hit?              │
                     └───────┬─────────────┬────────┘
                       yes    │             │  no
                              ▼             ▼
                 ┌────────────────────┐   ┌─────────────────────────┐
                 │ apply cached rule  │   │ LLM-only extraction      │
                 │ (CSS/XPath/JSON-   │   │ (cheap model) -- always  │
                 │  path, zero LLM    │   │ runs so we always return │
                 │  calls)            │   │ a usable result now      │
                 └─────────┬──────────┘   └────────────┬─────────────┘
                           │                            │
                           ▼                            ▼
                 ┌────────────────────────────────────────────┐
                 │ validate(extracted_text)                    │
                 │  - length within expected band               │
                 │  - JD-shaped (has qualifications/responsib.  │
                 │    keywords) and NOT boilerplate-shaped       │
                 │    (no nav/footer/cookie phrases)              │
                 └───────────────┬──────────────────────────────┘
                          pass    │    fail
                                  ▼
                    (rule path passed) → done, logged
                                  │
                          fail (no cached rule matched, or
                          cached rule's output failed validation
                          → template drift suspected)
                                  ▼
                 ┌───────────────────────────────────────────┐
                 │ strong-model template analysis:            │
                 │ generate CSS/XPath rule (or structured-data │
                 │ JSON-path if page embeds JSON-LD / a JSON   │
                 │ blob), store in cache keyed by fingerprint  │
                 └───────────────┬─────────────────────────────┘
                                 ▼
                     re-apply new rule, validate again,
                     fall back to the cheap-LLM result if it
                     still fails (never block on template gen)
```

### Template fingerprinting

`fingerprint(html)` is **not** a hash of the raw HTML (content changes per
page, so that hash would never repeat). It's a hash of the *structural
skeleton*: tag names + class names with all text content stripped, down to a
bounded depth, e.g. `div.job-details > div.section > ul.bullets`. Pages
rendered by the same template produce the same skeleton hash; a redesign
changes it, which is exactly the signal needed to know a cached rule needs
refreshing. Domain + skeleton hash together form the cache key, since two
different companies can share the exact same ATS template (all Breezy
companies do) and should share the same rule.

### Structured-data shortcut

Before falling back to either LLM path, check for:
- `<script type="application/ld+json">` `JobPosting` schema.org blocks
  (very common — Cisco's old template already used this, per
  `ExampleBase.get_dateposted`).
- A platform's own public JSON API (SmartRecruiters' `postings` endpoint
  returns `jobAd.sections.jobDescription` directly — no HTML cleaning needed
  at all).

  When either is present, extraction is a JSON-path read, not a selector —
  effectively free and the most reliable extraction available. The design
  treats "structured data available" as tier 0, ahead of both cached CSS
  rules and any LLM call.

### Validation heuristic (governs every fallback decision)

A quick, cheap, deterministic check run on *any* candidate extraction
(rule-based or LLM) before it's accepted:
- Length: reject candidates that are implausibly short (< ~150 words —
  likely grabbed a summary snippet) or implausibly long relative to the
  page's visible text (likely grabbed the whole page).
- Boilerplate-phrase density: reject candidates containing a high
  proportion of nav/footer markers ("privacy policy", "all rights
  reserved", "sign in", "cookie", "similar jobs").
- JD-shape check: expect at least one of a small set of section-heading
  markers ("responsibilities", "requirements", "qualifications", "about
  the role", "benefits") somewhere in the text.

This heuristic is intentionally cheap (regex/keyword-based, no model call)
because it runs on every page, including cache hits, as a tripwire for
silent template drift.

## Model choice (and why)

| Role | Model | Why |
|---|---|---|
| Per-page LLM-only extraction / fallback | a small, fast model (e.g. Claude Haiku-class) | Called potentially per-page on cache misses; needs to be cheap enough that it doesn't dominate the per-page cost at 100k-page scale. Good enough at a well-specified "extract and clean this text" task, which doesn't require deep reasoning. |
| Template-rule generation | a stronger model (e.g. Claude Sonnet-class) | Called *once per template*, not once per page, so its higher per-call cost is amortized over every future page on that template. Needs the stronger structural/spatial reasoning to reliably emit correct CSS/XPath selectors or JSON-paths from a full raw page, including reasoning about ambiguous or nested markup. |

Both are Claude models called through the standard `/v1/messages` endpoint
(see `pipeline.py`); swap the model strings for whatever the account has
access to. The important property is the *cost ratio* between the two tiers,
not the specific vendor.

## Handling extraction failures / page-structure changes

1. Every extraction (cache hit or miss) passes through the validation
   heuristic above.
2. A cache-hit rule that fails validation is treated as **suspected drift**,
   not a one-off fluke: it triggers rule regeneration via the strong model,
   and the old rule is replaced (with the old version kept in a `_history`
   list in the cache entry for auditability/rollback).
3. If *both* the (re)generated rule and the cheap-LLM fallback fail
   validation, the page is flagged `needs_manual_review` rather than
   silently returning bad data — this is logged with the raw page snapshot
   path so a human can diagnose a genuinely new template family.
4. Rule generation itself can fail (LLM returns a selector that doesn't
   exist on the page) — this is caught by immediately test-applying the
   generated rule to the same page before caching it; only rules that
   actually extract validated content on their source page get cached.

## Instrumentation

Every page processed emits one log record (`part2/logs/extractions.jsonl`)
with: `url`, `template_fingerprint`, `path_taken` (`structured_data` /
`cached_rule` / `llm_cheap` / `llm_strong_regen`), `confidence` (validation
score, 0–1), `latency_ms`, `model_used` (or `null` for rule-only paths),
`input_tokens`/`output_tokens` (0 for rule-only paths), `cost_usd`. This is
what the comparison table and the 100k-page cost projection are built from
— see `pipeline.py::run_comparison()`.

## Cost model / 100k-page projection

Because the cache means most pages hit `cached_rule` or `structured_data`
(effectively free), the dominant cost driver is **how many distinct
templates** exist in the corpus, not how many pages. For N pages drawn from
T distinct templates with average `k` pages/template:
- LLM-only baseline cost ≈ N × (cheap-model cost per page)
- Hybrid cost ≈ T × (strong-model cost per template, generation + one
  validation pass) + N × (near-zero rule-application cost) + (retry budget
  for drifted templates, empirically small)

`pipeline.py::project_cost_100k()` takes empirical per-page/per-template
costs measured from the 10-page pilot and extrapolates both ways, with the
key sensitivity being the assumed template-reuse ratio (pages/template),
since that's the one number the 10-page pilot can't estimate well from a
sample this size — it's called out explicitly as an assumption in the
output rather than silently baked in.

## Final recommendation (given the design)

For production at 100k-page scale: the hybrid pipeline, with structured-data
extraction (JSON-LD / native ATS APIs) preferred wherever available, cached
CSS/XPath rules for everything else, and the cheap LLM reserved for (a) true
cache misses on brand-new templates and (b) the fallback when validation
fails. Pure LLM-only extraction is only worth it below a template-reuse
ratio of roughly 1–2 pages/template (i.e., a corpus that's *mostly*
one-off/unique templates), which is not the expected shape of an
ATS-sourced job corpus, where a handful of platforms (Workday, iCIMS,
Greenhouse, SmartRecruiters, Breezy, etc.) account for the large majority of
postings.
