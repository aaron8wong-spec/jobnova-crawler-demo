"""
Hybrid Job Description extraction pipeline.

Usage
-----
    export ANTHROPIC_API_KEY=sk-...
    python pipeline.py extract <url>
    python pipeline.py compare ground_truth/pages.json
    python pipeline.py project-cost --pages 100000 --pages-per-template 250

Design notes are in DESIGN.md. This file is a runnable prototype, not a
polished library: network fetching is minimal (requests + BeautifulSoup),
and the LLM calls go straight to the Anthropic Messages API. Swap in
Playwright for JS-rendered ATSs (Workday, Avature) the same way
jobs/spiders/pr_bloomberg.py already does elsewhere in this repo.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup, Comment

HERE = Path(__file__).parent
RULES_CACHE_PATH = HERE / "rules_cache" / "rules.json"
LOG_PATH = HERE / "logs" / "extractions.jsonl"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Model tiers -- see DESIGN.md for why these two tiers exist.
CHEAP_MODEL = "claude-haiku-4-5-20251001"   # per-page fallback extraction
STRONG_MODEL = "claude-sonnet-5"            # per-template rule generation

# $ / million tokens -- update to whatever your account's actual pricing is.
# These are placeholders so the cost model is runnable end-to-end; treat the
# absolute numbers as illustrative and re-run project_cost_100k() with real
# pricing before using the estimate for a real budget decision.
PRICE_PER_MTOK = {
    CHEAP_MODEL: {"input": 1.00, "output": 5.00},
    STRONG_MODEL: {"input": 3.00, "output": 15.00},
}

BOILERPLATE_MARKERS = [
    "privacy policy", "all rights reserved", "cookie", "sign in",
    "create an account", "similar jobs", "share this job", "terms of use",
    "subscribe to our newsletter", "follow us on",
]
JD_SHAPE_MARKERS = [
    "responsibilit", "requirement", "qualificat", "about the role",
    "about the job", "benefit", "what you'll do", "what you will do",
    "who you are",
]


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    url: str
    template_fingerprint: str
    path_taken: str          # structured_data | cached_rule | llm_cheap | llm_strong_regen | manual_review
    text: Optional[str]
    confidence: float
    latency_ms: float
    model_used: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


# --------------------------------------------------------------------------
# Structured-data tier (tier 0 -- cheapest, most reliable when present)
# --------------------------------------------------------------------------

def try_structured_data(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    # 1) schema.org JobPosting via JSON-LD
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for c in candidates:
            if isinstance(c, dict) and c.get("@type") in ("JobPosting", ["JobPosting"]):
                desc = c.get("description")
                if desc:
                    return BeautifulSoup(desc, "html.parser").get_text("\n").strip()

    # 2) SmartRecruiters-style raw JSON API response passed in as "html"
    #    (the caller can pass the API JSON body directly for such platforms)
    try:
        data = json.loads(html)
        job_ad = data.get("jobAd", {}).get("sections", {})
        if job_ad:
            parts = []
            for key in ("jobDescription", "qualifications", "additionalInformation"):
                section = job_ad.get(key, {})
                text = section.get("text")
                if text:
                    parts.append(BeautifulSoup(text, "html.parser").get_text("\n").strip())
            if parts:
                return "\n\n".join(parts)
    except (json.JSONDecodeError, AttributeError):
        pass

    return None


# --------------------------------------------------------------------------
# Template fingerprinting
# --------------------------------------------------------------------------

def fingerprint(html: str, domain: str, max_depth: int = 6) -> str:
    """Hash of the DOM *skeleton* (tags + classes, no text), not the raw HTML,
    so pages on the same template collapse to the same fingerprint."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    def walk(node, depth):
        if depth > max_depth or not hasattr(node, "name") or node.name is None:
            return ""
        classes = ".".join(sorted(node.get("class", [])))[:40]
        children = "".join(walk(c, depth + 1) for c in node.find_all(recursive=False))
        return f"<{node.name}.{classes}>{children}</{node.name}>"

    skeleton = walk(soup.body or soup, 0)
    digest = hashlib.sha256(skeleton.encode("utf-8", "ignore")).hexdigest()[:16]
    return f"{domain}:{digest}"


# --------------------------------------------------------------------------
# Validation heuristic
# --------------------------------------------------------------------------

def validate(text: Optional[str]) -> float:
    """Returns a confidence score in [0, 1]. Cheap, deterministic, runs on
    every extraction (rule-based or LLM) before it's accepted."""
    if not text:
        return 0.0
    words = text.split()
    n = len(words)
    if n < 120:
        return 0.15
    if n > 6000:
        return 0.3

    lower = text.lower()
    boilerplate_hits = sum(lower.count(m) for m in BOILERPLATE_MARKERS)
    boilerplate_density = boilerplate_hits / max(n / 100, 1)  # hits per 100 words
    shape_hits = sum(1 for m in JD_SHAPE_MARKERS if m in lower)

    score = 0.5
    score += min(shape_hits, 4) * 0.1          # up to +0.4 for JD-shaped content
    score -= min(boilerplate_density, 3) * 0.15  # penalize boilerplate density
    return max(0.0, min(1.0, score))


# --------------------------------------------------------------------------
# Rule cache
# --------------------------------------------------------------------------

def load_rules() -> dict:
    if RULES_CACHE_PATH.exists():
        return json.loads(RULES_CACHE_PATH.read_text())
    return {}


def save_rules(rules: dict) -> None:
    RULES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_CACHE_PATH.write_text(json.dumps(rules, indent=2))


def apply_rule(html: str, rule: dict) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(rule["css_selector"])
    if not nodes:
        return None
    return "\n\n".join(n.get_text("\n").strip() for n in nodes).strip()


# --------------------------------------------------------------------------
# LLM calls
# --------------------------------------------------------------------------

def _call_anthropic(model: str, system: str, user: str, max_tokens: int = 2000):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
    usage = data.get("usage", {})
    return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def llm_extract_cheap(html: str) -> tuple[str, int, int]:
    # Trim to keep the cheap-model call cheap; a real implementation would
    # pre-strip <script>/<style>/nav/footer tags before this truncation.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n\n", text).strip()[:12000]

    system = (
        "Extract only the job description from the page text below: title, "
        "responsibilities, requirements/qualifications, and benefits if "
        "present. Remove navigation, cookie notices, headers, footers, and "
        "recommended-jobs content. Return plain text only, no commentary."
    )
    return _call_anthropic(CHEAP_MODEL, system, text)


def llm_generate_rule(html: str) -> tuple[Optional[dict], int, int]:
    truncated = html[:20000]
    system = (
        "You analyze the HTML of a job-detail page and output a single JSON "
        "object with one field, css_selector, giving a CSS selector that "
        "matches the element(s) containing ONLY the job description body "
        "(title/responsibilities/requirements/benefits), excluding nav, "
        "footer, cookie banners, and related-jobs widgets. Return JSON only."
    )
    text, in_tok, out_tok = _call_anthropic(STRONG_MODEL, system, truncated, max_tokens=300)
    try:
        rule = json.loads(re.sub(r"^```json|```$", "", text.strip()))
    except json.JSONDecodeError:
        rule = None
    return rule, in_tok, out_tok


def cost_of(model: str, in_tok: int, out_tok: int) -> float:
    price = PRICE_PER_MTOK[model]
    return (in_tok / 1_000_000) * price["input"] + (out_tok / 1_000_000) * price["output"]


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def extract(url: str, html: Optional[str] = None) -> ExtractionResult:
    t0 = time.time()
    domain = url.split("/")[2] if "://" in url else url

    if html is None:
        html = fetch(url)

    # Tier 0: structured data
    structured = try_structured_data(html)
    if structured and validate(structured) >= 0.6:
        return _finish(url, domain, html, "structured_data", structured, t0)

    fp = fingerprint(html, domain)
    rules = load_rules()
    cached = rules.get(fp)

    if cached:
        applied = apply_rule(html, cached)
        conf = validate(applied)
        if conf >= 0.6:
            return _finish(url, domain, html, "cached_rule", applied, t0, fp=fp)
        # cached rule looks stale (template drift) -- fall through to regen

    # Tier: cheap LLM extraction (always computed so we have a usable
    # result even while a new rule is being (re)generated)
    try:
        cheap_text, in_tok, out_tok = llm_extract_cheap(html)
    except Exception as e:  # noqa: BLE001 - prototype-level error handling
        cheap_text, in_tok, out_tok = None, 0, 0
        cheap_err = str(e)
    else:
        cheap_err = None
    cheap_conf = validate(cheap_text)
    cheap_cost = cost_of(CHEAP_MODEL, in_tok, out_tok)

    # Tier: strong-model rule generation for this (new or drifted) template
    rule, rin, rout = (None, 0, 0)
    try:
        rule, rin, rout = llm_generate_rule(html)
    except Exception:
        rule = None
    rule_cost = cost_of(STRONG_MODEL, rin, rout) if rule else 0.0

    if rule:
        applied = apply_rule(html, rule)
        rule_conf = validate(applied)
        if rule_conf >= 0.6:
            rule["_history"] = rules.get(fp, {}).get("_history", []) + (
                [rules[fp]] if fp in rules else []
            )
            rules[fp] = rule
            save_rules(rules)
            return _finish(
                url, domain, html, "llm_strong_regen", applied, t0, fp=fp,
                model=STRONG_MODEL, in_tok=rin, out_tok=rout, cost=rule_cost,
            )

    # Neither cached/regenerated rule nor cheap LLM produced a confident
    # result -> return the best of what we have, flagged for review.
    if cheap_conf >= 0.4:
        result = _finish(
            url, domain, html, "llm_cheap", cheap_text, t0, fp=fp,
            model=CHEAP_MODEL, in_tok=in_tok, out_tok=out_tok, cost=cheap_cost,
        )
        result.confidence = cheap_conf
        return result

    return ExtractionResult(
        url=url, template_fingerprint=fp, path_taken="manual_review",
        text=cheap_text, confidence=cheap_conf,
        latency_ms=(time.time() - t0) * 1000,
        model_used=CHEAP_MODEL, input_tokens=in_tok, output_tokens=out_tok,
        cost_usd=cheap_cost, error=cheap_err,
    )


def _finish(url, domain, html, path, text, t0, fp=None, model=None,
            in_tok=0, out_tok=0, cost=0.0) -> ExtractionResult:
    result = ExtractionResult(
        url=url,
        template_fingerprint=fp or fingerprint(html, domain),
        path_taken=path,
        text=text,
        confidence=validate(text),
        latency_ms=(time.time() - t0) * 1000,
        model_used=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=cost,
    )
    _log(result)
    return result


def _log(result: ExtractionResult) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(asdict(result)) + "\n")


# --------------------------------------------------------------------------
# Comparison harness
# --------------------------------------------------------------------------

def _word_overlap(a: str, b: str) -> float:
    """Cheap completeness proxy: fraction of ground-truth words recovered."""
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa:
        return 0.0
    return len(wa & wb) / len(wa)


def run_comparison(ground_truth_path: str):
    pages = json.loads(Path(ground_truth_path).read_text())
    rows = []
    for page in pages:
        if not page.get("verified") or not page.get("ground_truth_jd"):
            rows.append({"id": page["id"], "url": page.get("url"), "status": "no_ground_truth_yet"})
            continue
        try:
            result = extract(page["url"])
        except Exception as e:  # noqa: BLE001
            rows.append({"id": page["id"], "url": page["url"], "status": f"fetch_error: {e}"})
            continue
        completeness = _word_overlap(page["ground_truth_jd"], result.text or "")
        rows.append({
            "id": page["id"],
            "path_taken": result.path_taken,
            "confidence": round(result.confidence, 2),
            "completeness_vs_ground_truth": round(completeness, 2),
            "latency_ms": round(result.latency_ms, 1),
            "model_used": result.model_used,
            "tokens": result.input_tokens + result.output_tokens,
            "cost_usd": round(result.cost_usd, 5),
        })
    return rows


def project_cost_100k(pages_per_template: int, n_pages: int = 100_000,
                       strong_call_cost: float = 0.02, cheap_call_cost: float = 0.002,
                       drift_retry_rate: float = 0.05):
    """See DESIGN.md 'Cost model / 100k-page projection' for the reasoning.
    pages_per_template is the one assumption the 10-page pilot can't estimate
    well -- pass a few values to see sensitivity."""
    n_templates = max(1, n_pages // pages_per_template)
    hybrid_cost = (
        n_templates * strong_call_cost
        + n_templates * drift_retry_rate * strong_call_cost  # occasional re-generation
    )
    llm_only_cost = n_pages * cheap_call_cost
    return {
        "n_pages": n_pages,
        "assumed_pages_per_template": pages_per_template,
        "estimated_n_templates": n_templates,
        "hybrid_total_cost_usd": round(hybrid_cost, 2),
        "llm_only_total_cost_usd": round(llm_only_cost, 2),
        "savings_usd": round(llm_only_cost - hybrid_cost, 2),
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract")
    p_extract.add_argument("url")

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("ground_truth_path")

    p_cost = sub.add_parser("project-cost")
    p_cost.add_argument("--pages", type=int, default=100_000)
    p_cost.add_argument("--pages-per-template", type=int, default=250)

    args = parser.parse_args()

    if args.cmd == "extract":
        r = extract(args.url)
        print(json.dumps(asdict(r), indent=2)[:3000])

    elif args.cmd == "compare":
        rows = run_comparison(args.ground_truth_path)
        print(json.dumps(rows, indent=2))

    elif args.cmd == "project-cost":
        print(json.dumps(
            project_cost_100k(args.pages_per_template, args.pages), indent=2
        ))
