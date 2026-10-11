"""Read-only QA status report; no status token grants whole-file approval."""
import csv
import json
from collections import Counter
from pathlib import Path


def classify_status(value):
    s = (value or "").lower()
    if "rework_required" in s or "visual_fail" in s or s.endswith("_fail"):
        return "rework_required"
    if "scoped" in s and "pass" in s:
        return "scoped_static_pass_unapproved"
    if "hold" in s:
        return "hold_strict_recheck"
    if any(k in s for k in ("pending_fresh_c", "pending_c", "pending_independent_c")):
        return "pending_independent_qa"
    if "preserve_original" in s:
        return "declared_preserve_original"
    if "c3_strict_pass" in s:
        return "historical_c3_status_not_current_approval"
    if (s.startswith("c") and "pass" in s) or ("alias_of_c" in s and "pass" in s):
        return "declared_c_pass_not_final_approval"
    return "other_pending"


def summarize(repo):
    repo = Path(repo)
    with (repo / "localization/graphics/asset_queue.csv").open(
            encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    graphics = [r for r in rows if r.get("action") == "localize_text"]
    buckets = Counter()
    members = {}
    for row in graphics:
        state = classify_status(row.get("artwork_status"))
        buckets[state] += 1
        members.setdefault(state, []).append(int(row["index"].lstrip("\ufeff").strip()))

    reports, mapped = 0, set()
    backlog = repo / "localization/graphics/INGAME_REWORK_BACKLOG.csv"
    if backlog.is_file():
        with backlog.open(encoding="utf-8-sig", newline="") as fh:
            for report in csv.DictReader(fh):
                if not str(report.get("status", "")).strip().startswith("OPEN_USER_INGAME_FAIL"):
                    continue
                reports += 1
                idx = str(report.get("queue_index", "")).lstrip("\ufeff").strip()
                # Unmapped mixed/domain user failures stay OPEN but do not
                # invent a concrete DDS index.
                if idx.isdecimal():
                    mapped.add(int(idx))
    graphics_ids = {int(r["index"].lstrip("\ufeff").strip()) for r in graphics}
    mapped &= graphics_ids
    historic = set(members.get("historical_c3_status_not_current_approval", []))
    return {
        "source": "localization/graphics/asset_queue.csv",
        "queue_total": len(rows),
        "localize_text_total": len(graphics),
        "current_status_counts": dict(buckets),
        "members": members,
        "open_user_ingame_fail_reports": reports,
        "open_user_ingame_fail_graphics_indexes": sorted(mapped),
        "historical_c3_status_with_open_game": sorted(historic & mapped),
        "approval_count": None,
        "runtime_validation": "UNTESTED",
        "note": "SCOPED PASS and historical C3 status are not whole-asset approval. Exact-SHA evidence gate and fresh user game retest remain mandatory."
    }


if __name__ == "__main__":
    print(json.dumps(summarize(Path.cwd()), ensure_ascii=False, indent=2))
