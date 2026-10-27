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
# Receipt = (live source path, exact retained marker, bounded patch scope).
# A review note alone is never evidence of a current implementation.
SOURCE_PATCH_RECEIPTS = {
    "01490": ("vrhost/src/main_r23.cpp",
              "cachedMenuLetterbox != currentMenuLetterbox;",
              "Menu cache redraw on accepted letterbox-only policy change"),
    "01499": ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
              "const bool f11PairComplete = SUCCEEDED(rightHr) && restored;",
              "F11 complete-eye-pair success counters only"),
    "01511": ("src/vr/d3d9/stereo_renderer_r7.inc",
              "setupOk = SUCCEEDED(device->SetVertexShader(nullptr)) && setupOk;",
              "SBS compositor setter HRESULT accounting"),
    "01513": ("src/vr/d3d9/stereo_renderer_r7.inc",
              "savedViewport.Height!=BackBufferDesc.Height)return false;",
              "Full-viewport fence before right-depth bootstrap"),
    "01515": ("src/vr/d3d9/stereo_renderer_r7.inc",
              "initViewport.Width=desc.Width;initViewport.Height=desc.Height;",
              "Full-size right-eye color allocation initialization"),
    "01516": ("src/vr/d3d9/stereo_renderer_r7.inc",
              "LEFT depth/stencil write still invalidates the RIGHT content.",
              "Occlusion-query single LEFT depth sync invalidation"),
    "01519": ("src/vr/d3d9/stereo_renderer.cpp",
              "Present/mono-shadow-restore",
              "Failed mono-shadow restore metadata propagation only"),
    "01520": ("src/vr/d3d9/stereo_renderer.cpp",
              "Draw/occlusion-query-color-mono-gap",
              "Color-writing query skip invalidates incomplete mono shadow"),
    "01521": ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
              "The first physical LEFT Draw is now imminent:",
              "R30 clean pre-WVP fallback does not dirty R9 mono gap"),
    "01523": ("src/vr/game/outrun_renderer.cpp",
              "UploadContainsOutRunWvp(startRegister, vector4fCount))",
              "Complete c64..c67 bounds before 16-float source copy"),
}
PARTIAL_PATCH_RECEIPTS = {
    "01517": ("src/vr/d3d9/stereo_renderer.cpp",
              "TrackedDepthStencil == R9MainDepthIdentity &&",
              "Scoped R9-only offscreen shared-main-depth invalidation; "
              "pre-R9 and R7-only admission remain unverified"),
    "01518": ("src/vr/d3d9/stereo_renderer_r7.inc",
              "if(stateBlock)stateBlock->Release();return false;",
              "Partial fix: COM cleanup on failed CreateStateBlock; "
              "no failed-SBS color rollback implemented"),
}
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
    verified_receipts = {}
    for ident, (relative, marker, note) in {
            **SOURCE_PATCH_RECEIPTS, **PARTIAL_PATCH_RECEIPTS}.items():
        code = (ROOT / relative).read_text(encoding="utf-8-sig")
        assert marker in code, f"stale patch receipt {ident}: {relative}"
        verified_receipts[ident] = note
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
        if ident in SOURCE_PATCH_RECEIPTS:
            status = "SOURCE_PATCH_PRESENT_RUNTIME_UNTESTED"
            note = verified_receipts[ident]
        elif ident in PARTIAL_PATCH_RECEIPTS:
            status = "PARTIAL_PATCH_PRESENT_OTHER_RISKS_OPEN"
            note = verified_receipts[ident]
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
        "## Source-verified review patch receipts (runtime untested)",
        "",
    ]
    for ident in sorted(SOURCE_PATCH_RECEIPTS):
        lines.append(f"- {ident}: {verified_receipts[ident]}")
    for ident in sorted(PARTIAL_PATCH_RECEIPTS):
        lines.append(f"- {ident}: {verified_receipts[ident]}")
    lines += [
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
