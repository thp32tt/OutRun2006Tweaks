"""Derive current queue counts without treating historical notes as current state."""
import csv
import json
from collections import Counter
from pathlib import Path


def summarize(repo):
    repo = Path(repo)
    rows = list(csv.DictReader((repo / "localization/graphics/asset_queue.csv").open(encoding="utf-8-sig", newline="")))
    graphics = [r for r in rows if r.get("action") == "localize_text"]
    buckets = Counter()
    members = {}
    for row in graphics:
        s = row.get("artwork_status", "").lower()
        if "rework_required" in s or "visual_fail" in s or s.endswith("_fail"):
            state = "rework_required"
        elif "hold" in s:
            state = "hold_strict_recheck"
        elif "pending_fresh_c" in s or "pending_c" in s or "pending_independent_c" in s:
            state = "pending_c"
        elif s.startswith("c") and "pass" in s or "alias_of_c" in s and "pass" in s:
            state = "declared_c_pass_not_final_approval"
        elif "preserve_original" in s:
            state = "declared_preserve_original"
        else:
            state = "other_pending"
        buckets[state] += 1
        members.setdefault(state, []).append(int(row["index"].lstrip("\ufeff")))
    return {"source": "localization/graphics/asset_queue.csv", "queue_total": len(rows),
            "localize_text_total": len(graphics), "current_status_counts": dict(buckets),
            "members": members, "runtime_validation": "UNTESTED",
            "note": "Declared C PASS is not evidence-policy approval, user acceptance or runtime completion."}


if __name__ == "__main__":
    print(json.dumps(summarize(Path.cwd()), ensure_ascii=False, indent=2))
