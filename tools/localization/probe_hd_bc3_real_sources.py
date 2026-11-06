#!/usr/bin/env python3
"""Exact-SHA DXT5 A/B one-atlas canaries; never publish a game release."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path

from PIL import Image, ImageOps
from github_ab_imagegen_atlas_batch import (
    CROSS, ORIGINAL, load_cross, load_pinned_orientations, native_image,
    imported_candidate, conflicting_rois, dominant_container_holds,
)
from hd_strict_qa import process_strict_atlas

TARGETS = (
    "textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds",
    "textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds",
    "textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(root, output):
    root, output = Path(root), Path(output)
    groups = load_cross(root / CROSS)
    orientation = load_pinned_orientations(root, groups)
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema": "outrun.hd.bc3-real-source-canary.v1",
              "release_approved": False, "runtime_validation": "UNTESTED",
              "visual_qa": "REVIEW_REQUIRED", "results": []}
    successes = {}
    for target in TARGETS:
        rows = groups[target]
        expected = {r["source_dds_sha256"] for r in rows}
        assert len(expected) == 1, "UNPINNED_DDS"
        original = root / ORIGINAL / target
        assert original.is_file() and not original.is_symlink(), "MISSING_ORIGINAL"
        source = original.read_bytes()
        assert digest(source) == next(iter(expected)), "ORIGINAL_DDS_SHA_MISMATCH"
        assert source[84:88] == b"DXT5", "NOT_REAL_DXT5"
        assert all(imported_candidate(root, row) for row in rows), "A_B_PNG_NOT_IMPORTED"
        result = {"target": target, "rows": len(rows), "original_sha256": digest(source),
                  "dds_fourcc": "DXT5", "source_mips": int.from_bytes(source[28:32], "little"),
                  "orientation": orientation[target],
                  "release_approved": False, "runtime_validation": "UNTESTED"}
        try:
            data, final, clean, painted, holds = process_strict_atlas(
                source, rows, root, orientation[target], native_image,
                imported_candidate, conflicting_rois, dominant_container_holds)
            result.update(status="TEST_ONLY" if painted else "HOLD",
                          painted=len(painted), roi_ids=[p["roi_id"] for p in painted],
                          holds=holds, painted_evidence=painted)
            if data is not None:
                successes[target] = data
                result["output_sha256"] = digest(data)
                view = final.copy()
                view.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
                view.save(output / ("BC3_CANARY_" + target.rsplit("/",1)[-1] + ".png"))
        except (OSError, ValueError, OverflowError) as exc:
            result.update(status="HOLD", painted=0, holds=[
                {"roi_id": r["roi_id"], "reason": str(exc)[:200]} for r in rows])
        report["results"].append(result)
    report["total_targets"] = len(TARGETS)
    report["total_rows"] = sum(x["rows"] for x in report["results"])
    report["test_only_roi"] = sum(x["painted"] for x in report["results"])
    report["hold_roi"] = report["total_rows"] - report["test_only_roi"]
    assert report["test_only_roi"] + report["hold_roi"] == report["total_rows"]
    def stable_write(z, name, data):
        # zipfile.writestr(name, ...) uses wall-clock timestamps. Two runs
        # with identical DDS bytes can otherwise produce different ZIPs.
        info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, data, compresslevel=4)
    with zipfile.ZipFile(output / "BC3_CANARY_TEST_ONLY.zip", "w") as z:
        for name, raw in sorted(successes.items()):
            stable_write(z, name, raw)
        stable_write(z, "NOT_GAME_APPROVED.json", json.dumps({
            "release_approved": False, "game_runtime": "UNTESTED",
            "dds_sha256": {name: digest(raw) for name, raw in sorted(successes.items())}
        }, sort_keys=True).encode("utf-8"))
    (output / "bc3_real_source_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({k: report[k] for k in
        ("total_targets","total_rows","test_only_roi","hold_roi")},
        ensure_ascii=False))
    for result in report["results"]:
        print(json.dumps({k: result[k] for k in
            ("target","rows","source_mips","status","painted","holds")},
            ensure_ascii=False)[:1800])
    return report


if __name__ == "__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--repo",default=".")
    a.add_argument("--out",required=True)
    ns=a.parse_args()
    run(ns.repo,ns.out)
