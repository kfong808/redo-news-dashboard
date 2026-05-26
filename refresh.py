"""
Main entry point. Runs the scrape, classifies each story, writes news.json.

Designed to be called by GitHub Actions on an hourly schedule.
"""

import json
import os
import time
from datetime import datetime, timezone

from scraper import fetch_all
from classifier import classify, mode


def safe_published_ts(item):
    """Best-effort sort key. Recent stories first."""
    raw = item.get("published", "")
    if not raw:
        return 0
    # Try a few common formats
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw.strip(), fmt).timestamp()
        except (ValueError, TypeError):
            continue
    return 0


def main():
    t0 = time.time()
    print(f"=== REDO News Dashboard refresh ({datetime.now(timezone.utc).isoformat()}) ===")
    print(f"Classifier mode: {mode()}")

    items = fetch_all()
    print(f"\nClassifying {len(items)} stories...")

    classified = []
    for i, item in enumerate(items):
        cls, conf, reason = classify(item)
        if cls in ("opportunity", "threat"):
            item["classification"] = cls
            item["confidence"] = conf
            item["reasoning"] = reason
            item["published_ts"] = safe_published_ts(item)
            classified.append(item)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(items)} classified, {len(classified)} kept")

    # Sort: opportunities first, then threats; within each, most recent first
    classified.sort(
        key=lambda x: (
            0 if x["classification"] == "opportunity" else 1,
            -x.get("published_ts", 0),
        )
    )

    opportunities = sum(1 for c in classified if c["classification"] == "opportunity")
    threats = sum(1 for c in classified if c["classification"] == "threat")

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": classified,
        "stats": {
            "total_fetched": len(items),
            "kept": len(classified),
            "opportunities": opportunities,
            "threats": threats,
            "classifier_mode": mode(),
            "runtime_seconds": round(time.time() - t0, 1),
        },
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWrote news.json: {opportunities} opportunities, {threats} threats")
    print(f"Total runtime: {output['stats']['runtime_seconds']}s")


if __name__ == "__main__":
    main()
