#!/usr/bin/env python3
"""Read every DX9Ex REVIEW_ONLY document and emit a bounded evidence inventory.

A review document's PATCH_APPLIED=NO is historical: it does not prove that
later independent manual fixes never landed. Do not infer HMD correctness.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/reviews/dx9ex/automation"
OUT = ROOT / "out/reviews/dx9ex"
OUT.mkdir(parents=True, exist_ok=True)

CATEGORIES = (
    ("SOURCE_QUEUE_D3DX", r"\+TIME|GOAL|SPIRITENODE|SPRITENODE|D3DX|PRODUCER|QUEUE|BATCH"),
    ("COMPOSITION_MONO_DEPTH", r"DEPTH|STENCIL|OCCLUSION|RIGHT.EYE|SBS|PRESENT|MONO.SHADOW|COMPOSIT|RESTOR"),
    ("SKY_LENS_EFFECT", r"SKYGLOW|LENS|FLARE|SUN|CABE|C993|SKY"),
    ("MENU_F11_HUD_RANK", r"MENU|F11|HUD|RANK|RIVAL|OVERLAY|GLYPH|SPRITE"),
    ("PERFORMANCE_PARTICLES", r"PERF|PARTICLE|SMOKE|SAND|GLASS|WATER|TRANSPAREN|CACHE|HOTPATH"),
    ("OTHER", r"."),
)
EXACT_APPLIED = {"01516": "R7 query-main-depth sync invalidation",
                 "01521": "R30 pre-WVP R9 mono-gap deferral"}
MANUAL_OVERLAP = {"01350": "R26 SkyGlow capture generation manual integration",
                  "01418": "R26 SkyGlow capture generation manual integration"}


def field(content: str, key: str) -> str:
    match = re.search(r"(?m)^-\s*"+re.escape(key)+r"=([^\n]+)", content)
    return match.group(1).strip() if match else ""


def category(text: str) -> str:
    for name, regex in CATEGORIES:
        if re.search(regex, text, re.I):
            return name
    return "OTHER"


def main():
    files = sorted(DOCS.glob("CONVERSION-DX9EX-*.md"))
    rows = []
    for file in files:
        content = file.read_text(encoding="utf-8")
        identity = re.search(r"CONVERSION-DX9EX-(\d{5})\.md$", file.name)
        assert identity, file
        ident = identity.group(1)
        title = next((s.lstrip("# ").strip() for s in content.splitlines() if s.startswith("# ")), "")
        finding = field(content, "NEW_FINDING")
        candidate = field(content, "PATCH_CANDIDATE_ONLY")
        if not finding:
            # Legacy records may not have the later structured NEW_FINDING key.
            finding = "UNSTRUCTURED_REVIEW"
        if ident in EXACT_APPLIED:
            status = "SOURCE_PATCH_APPLIED_CI_RUNTIME_UNTESTED"
            note = EXACT_APPLIED[ident]
        elif ident in MANUAL_OVERLAP:
            status = "MANUAL_INTEGRATION_OVERLAP_REVIEW"
            note = MANUAL_OVERLAP[ident]
        elif finding == "NONE":
            status = "NO_NEW_FINDING_IN_REVIEW"
            note = ""
        else:
            status = "POST_REVIEW_SOURCE_STATUS_NOT_REVALIDATED"
            note = ""
        row = {
            "task_id": "CONVERSION-DX9EX-" + ident,
            "category": category(title + " " + finding),
            "finding": finding,
            "patch_candidate": candidate or "UNSTRUCTURED_REVIEW",
            "review_code_change": field(content, "CODE_CHANGE") or "UNKNOWN",
            "review_patch_applied": field(content, "PATCH_APPLIED") or "UNKNOWN",
            "source_status": status,
            "note": note,
            "review_file": str(file.relative_to(ROOT)),
            "title": title,
        }
        rows.append(row)
    # The hourly REVIEW_ONLY writer continues to append distinct new IDs;
    # inventory every document in this exact checkout, never pin a count.
    assert len(rows) >= 447, "Earlier review history disappeared"
    assert rows[0]["task_id"] == "CONVERSION-DX9EX-01075"
    ids = [int(row["task_id"][-5:]) for row in rows]
    assert ids == list(range(1075, ids[-1] + 1)), "Duplicate/missing review IDs"

    with (OUT / "review_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    stats = {
        "documents_read": len(rows),
        "category_counts": dict(Counter(x["category"] for x in rows)),
        "source_status_counts": dict(Counter(x["source_status"] for x in rows)),
        "runtime_validation": "UNTESTED",
        "source_scope": "vr-d3d9ex-focus / R26+HUD",
        "caveat": "Source status unknown for unverified historical findings. No bulk auto-apply.",
    }
    (OUT / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = [
        "# DX9Ex automation review inventory — 2026-10-27",
        "",
        f"All {len(rows)} review bodies read, ending at {rows[-1]['task_id']}. Source status outside separately verified patches",
        "requires a current source diff; historical REVIEW_ONLY does not equal",
        "current unpatched code. Quest3/HMD runtime UNTESTED.",
        "",
        "## Source review patch receipts (this task)",
        "",
        "- CONVERSION-DX9EX-01516: R7 occlusion query write invalidation.",
        "- CONVERSION-DX9EX-01521: R30 pre-WVP failed upload mono-gap deferral.",
        "- 01350/01418: overlapping SkyGlow manual integration; not double-counted.",
        "",
        "## Counts",
    ]
    for group, count in sorted(stats["category_counts"].items()):
        lines.append(f"- {group}: {count}")
    lines += ["", "## Source status counts"]
    for group, count in sorted(stats["source_status_counts"].items()):
        lines.append(f"- {group}: {count}")
    lines += ["", f"See review_inventory.csv for {len(rows)} independent IDs, findings and links.",
              "SOURCE_BUILD_GATE=GitHub Actions; Quest3 runtime UNTESTED."]
    (OUT / "README.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    print(f"PASS complete DX9Ex REVIEW_ONLY document inventory: 01075..{ids[-1]:05d}")


if __name__ == "__main__":
    main()
