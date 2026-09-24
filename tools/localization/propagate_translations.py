#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

def load_catalog(path):
    rows = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header_seen = False
        for row in reader:
            if not row:
                continue
            if row[0] == "id":
                header_seen = True
                continue
            if not header_seen or row[0].startswith("#"):
                continue
            rows[int(row[0])] = row[1]
    return rows

def main():
    ap = argparse.ArgumentParser(
        description="Expand explicit Korean draft IDs to exact duplicate source strings."
    )
    ap.add_argument("catalog_csv")
    ap.add_argument("draft_json")
    ap.add_argument("output_json")
    args = ap.parse_args()

    sources = load_catalog(args.catalog_csv)
    draft = json.loads(Path(args.draft_json).read_text(encoding="utf-8"))
    explicit = {int(k): v for k, v in draft["translations"].items()}

    source_to_translation = {}
    for idx, item in explicit.items():
        source = sources.get(idx)
        if not source:
            continue
        ko = item["ko"]
        previous = source_to_translation.get(source)
        if previous is not None and previous != ko:
            raise SystemExit(
                f"conflicting Korean translations for duplicate source {source!r}: "
                f"{previous!r} vs {ko!r}"
            )
        source_to_translation[source] = ko

    expanded = {}
    for idx, source in sources.items():
        if source in source_to_translation:
            expanded[str(idx)] = {
                "ko": source_to_translation[source],
                "status": "DRAFT_EXACT_PROPAGATED" if idx not in explicit else explicit[idx].get("status", "DRAFT"),
                "source_id": idx if idx in explicit else next(
                    src_id for src_id, item in explicit.items()
                    if sources.get(src_id) == source and item["ko"] == source_to_translation[source]
                ),
            }

    result = {
        "schema_version": 1,
        "explicit_count": len(explicit),
        "expanded_count": len(expanded),
        "total_entries": len(sources),
        "coverage_percent": round(len(expanded) * 100.0 / max(len(sources), 1), 1),
        "translations": expanded,
    }
    Path(args.output_json).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"explicit={len(explicit)} expanded={len(expanded)} "
        f"coverage={result['coverage_percent']}%"
    )

if __name__ == "__main__":
    main()
