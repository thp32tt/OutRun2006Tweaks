#!/usr/bin/env python3
"""Regression QA for the C167-accepted index24 runtime-evidence binder.

This harness uses only the exact C163/A00279 canonical glyph geometry and the
C167/A00297 fail-closed binder. Synthetic observations are test fixtures only:
they MUST NOT be used as runtime evidence and MUST NOT authorize a DDS.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

GEOMETRY_PATH = Path(
    "localization/graphics/role_A/20260930-A00279-P00163/"
    "A00279_P00163_INDEX24_NAME_ENTRY_ATLAS_PREFLIGHT.json"
)
BINDER_PATH = Path(
    "localization/graphics/role_A/20261001-A00297-P00178/"
    "bind_name_entry_runtime_trace.py"
)
EXPECTED_GEOMETRY_GIT_BLOB = "9c8faffcc41b49410ff8135dd6ea3ab010702020"
EXPECTED_BINDER_GIT_BLOB = "3d261f3d83165de5b3c71c8e3f48702249786815"
EXPECTED_SOURCE_SHA256 = "7aa21de138af2d7f2aae54022a08f0aca79093a2a34a2bd74a87a442efaa60aa"

def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()

def load_binder(path: Path):
    spec = importlib.util.spec_from_file_location("index24_runtime_binder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load binder module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def selection_observations(glyphs):
    rows = []
    for i, g in enumerate(glyphs, 1):
        rows.append((i, {
            "kind": "selection_uv",
            "selection_index": i - 1,
            "space": "raw_px",
            "uv_rect": list(g["raw_bbox"]),
            "visual_label": g["visual_label"],
            "fixture_provenance": "SYNTHETIC_REGRESSION_ONLY",
        }))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    root = Path(args.repo_root)

    geometry_bytes = (root / GEOMETRY_PATH).read_bytes()
    binder_bytes = (root / BINDER_PATH).read_bytes()
    if git_blob_sha(geometry_bytes) != EXPECTED_GEOMETRY_GIT_BLOB:
        raise SystemExit("GEOMETRY_BLOB_DRIFT")
    if git_blob_sha(binder_bytes) != EXPECTED_BINDER_GIT_BLOB:
        raise SystemExit("BINDER_BLOB_DRIFT")

    geometry = json.loads(geometry_bytes.decode("utf-8"))
    if geometry["source_acquisition"]["pinned_release"]["member_sha256"] != EXPECTED_SOURCE_SHA256:
        raise SystemExit("CANONICAL_SOURCE_DRIFT")

    binder = load_binder(root / BINDER_PATH)
    _, glyphs = binder.load_geometry(root)
    if len(glyphs) != 48:
        raise SystemExit("GLYPH_COUNT_DRIFT")

    # Positive synthetic fixture: each exact raw glyph bbox is supplied once,
    # followed by one committed Hangul composition observation.
    positive_obs = selection_observations(glyphs)
    positive_obs.append((49, {
        "kind": "composition",
        "selection_indices": [0],
        "result_utf8": "가",
        "committed": True,
        "fixture_provenance": "SYNTHETIC_REGRESSION_ONLY",
    }))
    positive = binder.analyze(root, positive_obs)
    if not positive["mapping"]["complete_48_unique_mapping"]:
        raise SystemExit("POSITIVE_MAPPING_NOT_COMPLETE")
    if not positive["composition"]["committed_hangul_result_observed"]:
        raise SystemExit("POSITIVE_HANGUL_GATE_NOT_EXERCISED")
    if positive["production_readiness"] != "PREFLIGHT_ONLY_RUNTIME_MAPPING_EVIDENCE_READY_FOR_C_REVIEW":
        raise SystemExit("POSITIVE_READINESS_UNEXPECTED")

    # Conflict fixture: selection slot 1 intentionally reuses glyph A.
    conflict_obs = selection_observations(glyphs)
    conflict_obs[1] = (2, {
        "kind": "selection_uv",
        "selection_index": 1,
        "space": "raw_px",
        "uv_rect": list(glyphs[0]["raw_bbox"]),
        "visual_label": glyphs[0]["visual_label"],
        "fixture_provenance": "SYNTHETIC_REGRESSION_ONLY",
    })
    conflict_obs.append((49, {
        "kind": "composition",
        "selection_indices": [0],
        "result_utf8": "가",
        "committed": True,
        "fixture_provenance": "SYNTHETIC_REGRESSION_ONLY",
    }))
    conflict = binder.analyze(root, conflict_obs)
    if conflict["mapping"]["complete_48_unique_mapping"]:
        raise SystemExit("CONFLICT_FALSE_PASS")
    if glyphs[0]["visual_label"] not in conflict["mapping"]["visual_label_conflicts"]:
        raise SystemExit("CONFLICT_NOT_REPORTED")

    invalid = binder.analyze(root, [(1, {
        "kind": "selection_uv",
        "selection_index": 0,
        "space": "invalid_space",
        "uv_rect": list(glyphs[0]["raw_bbox"]),
        "visual_label": glyphs[0]["visual_label"],
        "fixture_provenance": "SYNTHETIC_REGRESSION_ONLY",
    })])
    if not invalid["observations"]["parse_errors"]:
        raise SystemExit("INVALID_SPACE_FALSE_PASS")
    if invalid["mapping"]["complete_48_unique_mapping"]:
        raise SystemExit("INVALID_SPACE_MAPPING_FALSE_PASS")

    empty = binder.analyze(root, [])
    if empty["production_readiness"] != "PREFLIGHT_ONLY_RUNTIME_TRACE_REQUIRED":
        raise SystemExit("EMPTY_TRACE_NOT_FAIL_CLOSED")

    out = {
        "schema_version": 16,
        "schema": "outrun-a00348-index24-runtime-binder-regression-qa-v1",
        "task_id": "LOCALIZATION-LOCALIZATION_A-00348",
        "wave_id": "P00219",
        "asset": "66743AA8",
        "queue_index": 24,
        "lineage": {
            "geometry_git_blob_sha": EXPECTED_GEOMETRY_GIT_BLOB,
            "binder_git_blob_sha": EXPECTED_BINDER_GIT_BLOB,
            "canonical_source_sha256": EXPECTED_SOURCE_SHA256,
            "glyph_count": 48,
        },
        "cases": {
            "positive_48_unique_plus_committed_hangul": {
                "pass": True,
                "complete_48_unique_mapping": positive["mapping"]["complete_48_unique_mapping"],
                "committed_hangul_result_observed": positive["composition"]["committed_hangul_result_observed"],
                "readiness": positive["production_readiness"],
            },
            "duplicate_visual_label_conflict": {
                "pass": True,
                "complete_48_unique_mapping": conflict["mapping"]["complete_48_unique_mapping"],
                "visual_label_conflicts": conflict["mapping"]["visual_label_conflicts"],
                "readiness": conflict["production_readiness"],
            },
            "invalid_uv_space": {
                "pass": True,
                "parse_error_count": len(invalid["observations"]["parse_errors"]),
                "complete_48_unique_mapping": invalid["mapping"]["complete_48_unique_mapping"],
                "readiness": invalid["production_readiness"],
            },
            "no_observations": {
                "pass": True,
                "readiness": empty["production_readiness"],
            },
        },
        "synthetic_fixture_policy": {
            "fixtures_are_runtime_evidence": False,
            "fixtures_authorize_candidate": False,
            "fixtures_authorize_runtime_pass": False,
            "purpose": "Regression-test fail-closed binder behavior only.",
        },
        "production_readiness": "PREFLIGHT_ONLY_RUNTIME_OBSERVATIONS_STILL_REQUIRED",
        "candidate_dds_authorized": False,
        "candidate_dds_modified": False,
        "runtime_validation": "UNTESTED",
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload, end="")

if __name__ == "__main__":
    main()
