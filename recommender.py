"""
Strategic recommender agent.

Reads the most recent week of classified news (news.json), pairs it with REDO's
strategy context (strategy_context.md), and asks Claude to generate 3 to 5
actionable strategic recommendations. Writes results to recommendations.json.

Requires ANTHROPIC_API_KEY env var. If missing, writes a placeholder
recommendations.json and exits gracefully so the workflow does not fail.

Designed to run on a daily schedule via GitHub Actions.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta


MODEL = "claude-sonnet-4-6"
MAX_NEWS_ITEMS = 50          # cap stories sent to Claude to keep prompt size sane
RECENCY_DAYS = 7             # only consider stories from this many days back
NUM_RECS_TARGET = "3 to 5"   # what to ask Claude to generate


SYSTEM_PROMPT = """You are a strategic advisor for REDO, an ecommerce post-purchase platform. \
Your job is to read recent ecommerce news and recommend strategic plays REDO should \
consider this week. You prioritize time-sensitive recommendations that respond to \
specific market signals. You avoid generic advice like 'do more content marketing.' \
You recommend either amplifying an existing REDO play OR proposing a new play, \
whichever fits the signal better. You ground every recommendation in specific news \
items, citing the URLs that triggered the thinking."""


USER_PROMPT_TEMPLATE = """Below is REDO's current strategic playbook, followed by the \
last {recency} days of classified ecommerce news.

Generate {num_recs} strategic recommendations as a JSON array. Prioritize \
time-sensitive items and recommendations grounded in specific news. Skip generic \
suggestions.

Each recommendation must be an object with EXACTLY these fields:

- "title": short play name, max 70 characters
- "type": either "amplify_existing" or "new_play"
- "existing_play_number": integer from 1 to 18 if type is "amplify_existing", null otherwise
- "urgency": "urgent" (act this week), "this_quarter", or "long_term"
- "impact": "opportunity_driven" (positive signal to capitalize on) or "threat_driven" (negative signal to defend against)
- "context": 1 to 2 sentences describing the specific market signal that triggered this recommendation
- "action": 1 to 2 sentences on exactly what REDO should do
- "reasoning": 2 to 3 sentences on why this will work, grounded in REDO's competitive position
- "triggering_stories": array of 1 to 3 story URLs from the news below that informed this recommendation

Respond with ONLY valid JSON (no markdown, no code fence, no preamble). The response \
must be a single JSON array of recommendation objects.

===== REDO STRATEGY CONTEXT =====

{strategy}

===== RECENT NEWS (last {recency} days) =====

{news}
"""


def load_news(path="news.json"):
    """Load news.json and return the items list."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return []


def filter_recent(items, days=RECENCY_DAYS):
    """Keep only items with a published_ts within the last N days, or undated."""
    cutoff = time.time() - days * 86400
    recent = []
    for item in items:
        ts = item.get("published_ts", 0)
        if ts == 0 or ts >= cutoff:
            recent.append(item)
    return recent


def format_news_for_prompt(items):
    """Format news items as a compact text block for the prompt."""
    lines = []
    for it in items[:MAX_NEWS_ITEMS]:
        cls = it.get("classification", "?").upper()
        title = (it.get("title") or "").strip()
        source = (it.get("source") or "").strip()
        url = (it.get("url") or "").strip()
        reason = (it.get("reasoning") or "").strip()
        summary = (it.get("summary") or "").strip()[:200]

        block = f"[{cls}] {title}\n  Source: {source}\n  URL: {url}\n  Why classified: {reason}"
        if summary:
            block += f"\n  Summary: {summary}"
        lines.append(block)
    return "\n\n".join(lines)


def load_strategy(path="strategy_context.md"):
    """Load the strategy context markdown."""
    if not os.path.exists(path):
        return "(No strategy context file found. Recommendations will be generic.)"
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def call_claude(api_key, system, user, model=MODEL):
    """Call Claude API and return the response text."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 4000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
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

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["content"][0]["text"]


def parse_recommendations(raw_text):
    """Extract the JSON array from Claude's response and validate."""
    text = raw_text.strip()
    # Strip code fences if Claude added them despite instructions
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    # Find the JSON array
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in response")
    recs = json.loads(match.group(0))
    if not isinstance(recs, list):
        raise ValueError("Parsed response is not a list")
    return recs


def write_placeholder(reason):
    """Write a placeholder recommendations.json so the dashboard knows what's up."""
    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "recommendations": [],
        "status": "no_recommendations",
        "reason": reason,
    }
    with open("recommendations.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote placeholder recommendations.json: {reason}")


def main():
    print(f"=== REDO Strategic Recommender ({datetime.now(timezone.utc).isoformat()}) ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        write_placeholder(
            "ANTHROPIC_API_KEY is not set. Add it to GitHub Secrets to enable "
            "AI-generated recommendations. See the README for instructions."
        )
        return

    all_items = load_news()
    print(f"Loaded {len(all_items)} stories from news.json")

    recent = filter_recent(all_items)
    print(f"{len(recent)} stories from the last {RECENCY_DAYS} days")

    if len(recent) < 3:
        write_placeholder(
            f"Only {len(recent)} stories in the last {RECENCY_DAYS} days. "
            "Need at least 3 to generate meaningful recommendations. "
            "The news scraper may not have run yet."
        )
        return

    # Order: threats first (more urgent), then opportunities
    recent.sort(key=lambda x: (
        0 if x.get("classification") == "threat" else 1,
        -x.get("published_ts", 0),
    ))

    strategy = load_strategy()
    news_text = format_news_for_prompt(recent)

    prompt = USER_PROMPT_TEMPLATE.format(
        recency=RECENCY_DAYS,
        num_recs=NUM_RECS_TARGET,
        strategy=strategy,
        news=news_text,
    )

    print(f"Calling Claude ({MODEL}) with {len(recent[:MAX_NEWS_ITEMS])} news items in context...")
    try:
        raw = call_claude(api_key, SYSTEM_PROMPT, prompt)
        recs = parse_recommendations(raw)
        print(f"Got {len(recs)} recommendations")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        write_placeholder(f"Claude API error {exc.code}: {body}")
        return
    except Exception as exc:
        write_placeholder(f"Failed to generate recommendations: {type(exc).__name__}: {exc}")
        return

    # Light validation: drop any rec missing required fields
    required = {"title", "type", "urgency", "impact", "context", "action", "reasoning"}
    valid = [r for r in recs if isinstance(r, dict) and required.issubset(r.keys())]
    if len(valid) != len(recs):
        print(f"Dropped {len(recs) - len(valid)} malformed recommendations")

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "news_items_considered": len(recent[:MAX_NEWS_ITEMS]),
        "recommendations": valid,
        "status": "ok" if valid else "no_recommendations",
    }
    with open("recommendations.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Wrote recommendations.json with {len(valid)} recommendations")


if __name__ == "__main__":
    main()
