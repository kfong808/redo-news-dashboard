"""
Classifies a story as an OPPORTUNITY for REDO, a THREAT to REDO, or SKIP.

Two modes:
  - keyword (default, free, no API key needed): pattern matching
  - llm (better, requires ANTHROPIC_API_KEY env var): uses Claude

The system automatically uses the LLM mode if the API key is present.
"""

import json
import os
import re
import urllib.error
import urllib.request


# --- KEYWORDS (used by fallback classifier) ---

OPPORTUNITY_KEYWORDS = [
    "price hike", "price increase", "pricing complaint",
    "sunset", "discontinued", "shutting down", "shuts down", "closes shop", "shutdown",
    "switching from", "alternatives to", "vs klaviyo", "vs yotpo", "vs loop",
    "yotpo refugee", "looking for alternative", "frustrated with klaviyo",
    "ecommerce growth", "dtc growth", "post-purchase",
    "tool consolidation", "saas spend", "stack consolidation", "vendor consolidation",
    "agentic commerce", "ai shopping",
    "review collection", "review platform changes",
    "klaviyo bill", "too expensive", "overpriced",
]

THREAT_KEYWORDS = [
    "raises", "raised", "funding round", "series a", "series b", "series c", "series d",
    "acquires", "acquisition", "acquired",
    "launches", "launched", "introduces", "new product", "rolls out",
    "klaviyo k:ai", "k:ai agent",
    "shop email", "shop pay update", "shopify launches", "shopify native",
    "ipo", "valued at", "valuation",
    "expands into", "expansion", "growth round",
    "ai marketing agent",
]

COMPETITORS = [
    "klaviyo", "yotpo", "loop returns", "loop pos", "attentive",
    "omnisend", "postscript", "mailchimp", "shipstation", "narvar",
]


def keyword_classify(item):
    """Pattern-match classification. Returns (label, confidence, reasoning)."""
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()

    op_hits = [kw for kw in OPPORTUNITY_KEYWORDS if kw in text]
    th_hits = [kw for kw in THREAT_KEYWORDS if kw in text]
    comp_mention = [c for c in COMPETITORS if c in text]

    # Opportunity wins if it has more matches and at least one
    if len(op_hits) > len(th_hits) and op_hits:
        conf = "high" if len(op_hits) >= 2 else "medium"
        reason = f"Matched: {', '.join(op_hits[:3])}"
        return ("opportunity", conf, reason)

    # Threat needs a competitor mention plus a threat keyword
    if th_hits and comp_mention:
        conf = "high" if len(th_hits) >= 2 else "medium"
        reason = f"{comp_mention[0].title()} + {', '.join(th_hits[:2])}"
        return ("threat", conf, reason)

    # Plain competitor mention with no clear threat signal is low-confidence threat
    if comp_mention and "launch" in text or "new" in text:
        return ("threat", "low", f"Mentions {comp_mention[0].title()}")

    return ("skip", "low", "No clear classification")


# --- LLM CLASSIFIER (used when ANTHROPIC_API_KEY is set) ---

LLM_SYSTEM = (
    "You analyze news for REDO, an ecommerce post-purchase platform that competes "
    "with Klaviyo, Yotpo, Loop Returns, Attentive, Omnisend, Mailchimp, ShipStation, "
    "and Narvar. REDO sells returns software, marketing cloud (email/SMS), "
    "abandoned-cart recovery via human + AI SMS agents, and order tracking. "
    "REDO targets Shopify-based DTC brands, especially mid-market."
)

LLM_PROMPT_TEMPLATE = """Classify the following news story as one of:

- "opportunity": A development that helps REDO. Examples: competitor weakness, vendor sunset (like Yotpo killing email/SMS), pricing complaints about competitors, market growth in REDO's category, consolidation trend toward all-in-one platforms, growth in agentic commerce or AI shopping, brands publicly complaining about a competitor.

- "threat": A development that could hurt REDO. Examples: competitor product launch, competitor funding round or acquisition, Shopify launching a native feature that overlaps with REDO (Shop Email, native cart recovery), Klaviyo K:AI announcements, macro downturn affecting DTC budgets, a new entrant in REDO's category.

- "skip": Neither clearly applies, OR the story is about something unrelated (generic ecommerce news, off-topic, advertising, etc).

Story title: {title}
Source: {source}
Summary: {summary}

Respond with ONLY valid JSON (no markdown, no code fence):
{{"classification": "opportunity"|"threat"|"skip", "confidence": "high"|"medium"|"low", "reasoning": "one short sentence"}}"""


def llm_classify(item, api_key, model="claude-haiku-4-5-20251001"):
    """Call Claude API to classify. Falls back to keyword on failure."""
    prompt = LLM_PROMPT_TEMPLATE.format(
        title=item.get("title", "")[:200],
        source=item.get("source", "")[:80],
        summary=item.get("summary", "")[:400],
    )

    payload = json.dumps({
        "model": model,
        "max_tokens": 150,
        "system": LLM_SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["content"][0]["text"].strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            return keyword_classify(item)
        result = json.loads(match.group(0))
        cls = result.get("classification", "skip")
        if cls not in ("opportunity", "threat", "skip"):
            cls = "skip"
        return (cls, result.get("confidence", "medium"), result.get("reasoning", ""))
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError) as exc:
        print(f"  ! LLM error ({type(exc).__name__}), falling back to keyword: {exc}")
        return keyword_classify(item)


# --- ENTRY POINT ---

def classify(item):
    """Returns (label, confidence, reasoning). Auto-selects LLM if key is set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return llm_classify(item, api_key)
    return keyword_classify(item)


def mode():
    return "llm" if os.environ.get("ANTHROPIC_API_KEY", "").strip() else "keyword"
