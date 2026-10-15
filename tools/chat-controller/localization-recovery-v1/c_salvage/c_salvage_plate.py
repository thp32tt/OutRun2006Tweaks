#!/usr/bin/env python3
"""C-SALVAGE PSD-first English removal plate preparation; offline and TEST_ONLY.

Requires a reviewed native SOURCE removal mask. Never guesses Photoshop layer
identity or opaque pixels and never issues an independent QA approval.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from c_salvage_compose import checked, png, binary_mask, digest

SCHEMA = "outrun-c-salvage-plate-v1"


def export_psd(root, spec, tmp):
    psd = spec.get("psd")
    if not psd:
        return None, "PSD_UNAVAILABLE"
    paths = spec.get("english_layer_paths")
    if not isinstance(paths, list) or not paths or not all(
        isinstance(x, str) and x and all(seg.isdigit() for seg in x.split("/")) for x in paths
    ):
        return None, "PSD_LAYERS_NOT_SELECTED"
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate PSD English layer paths")
    binary = checked(root, psd)
    if len(binary) > 40 * 1024 * 1024:
        return None, "PSD_OVER_40MB_LOCAL_RESOURCE_HOLD"
    # psd-tools itself can render some Photoshop effects imperfectly.
    # It is a candidate reference only and must be compared against canonical DDS.
    import psd_layer_workbase as psdlib
    psd_path = (root / psd["path"]).resolve()
    args = argparse.Namespace(command="export", psd=psd_path,
        psd_sha256=psd["sha256"], upstream_url=spec.get("psd_upstream_url", ""),
        upstream_commit=spec.get("psd_upstream_commit", ""),
        output=tmp / "psd_extract", english_layers=",".join(paths), explode=False)
    psdlib.run(args)
    plate = Image.open(args.output / "clean_plate_candidate.png").convert("RGBA")
    return plate, "PSD_EXTRACTED_UNVERIFIED"


def prepare_plate(root: Path, spec: dict, out: Path):
    root = root.resolve()
    if spec.get("schema") != SCHEMA:
        raise ValueError("Unsupported plate job schema")
    if spec.get("orientation") not in ("IDENTITY", "FLIP_Y"):
        raise ValueError("Unknown/mixed orientation")
    source_bytes = checked(root, spec["source_dds"])
    if source_bytes[:4] != b"DDS ":
        raise ValueError("A canonical DDS is required")
    with Image.open(io.BytesIO(source_bytes)) as im:
        source_native = im.convert("RGBA")
    source = source_native.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if spec["orientation"] == "FLIP_Y" else source_native
    rem, remove = binary_mask(root, spec["removal_mask"], source.size)
    protected, protect = binary_mask(root, spec["protected_mask"], source.size)
    if np.any(remove & protect) or not np.any(remove):
        raise ValueError("Empty/conflicting English removal and protected masks")
    tmp = out.with_name("." + out.name + "-working")
    if tmp.exists() or out.exists():
        raise FileExistsError("Plate output already exists; immutable")
    tmp.mkdir(parents=True)
    plate, psd_status = export_psd(root, spec, tmp)
    kind = "PSD_CANDIDATE"
    source_arr = np.asarray(source)
    if plate is not None:
        if plate.size != source.size:
            plate, psd_status = None, "PSD_NATIVE_SIZE_MISMATCH"
        else:
            arr = np.asarray(plate)
            if np.any(np.any(arr != source_arr, axis=2) & ~remove):
                plate, psd_status = None, "PSD_OUTSIDE_SOURCE_REMOVAL_MISMATCH"
    if plate is None:
        # Non-PSD fallback is safe only with a truly text-on-transparency
        # canonical source ROI/mask that a reviewer explicitly confirmed.
        if spec.get("source_transparent_under_english_reviewed") is not True:
            raise ValueError("HOLD_SOURCE_BACKGROUND_RECONSTRUCTION_OR_PSD_REVIEW_REQUIRED:" + psd_status)
        rgba = source_arr.copy()
        rgba[remove] = (0, 0, 0, 0)
        plate = Image.fromarray(rgba, "RGBA")
        kind = "SOURCE_TRANSPARENT_MASK_TEST_ONLY"
    arr = np.asarray(plate)
    outside = int(np.count_nonzero(np.any(arr != source_arr, axis=2) & ~remove))
    protected_changed = int(np.count_nonzero(np.any(arr != source_arr, axis=2) & protect))
    if outside or protected_changed:
        raise ValueError("Protected/canonical pixel change outside English removal mask")
    if kind.startswith("SOURCE") and np.any(arr[:, :, 3][remove]):
        raise ValueError("Visible English alpha residue remains in source-derived CLEAN")
    plate.save(tmp / "clean_candidate.png", format="PNG")
    source.save(tmp / "english_original_readable.png", format="PNG")
    rem.save(tmp / "english_removal_mask.png", format="PNG")
    state = {
        "schema": SCHEMA,
        "status": "CLEAN_CANDIDATE_REQUIRES_INDEPENDENT_C1_PLATE_REVIEW",
        "psd_attempt": psd_status,
        "provenance": kind, "source_sha256": digest(source_bytes),
        "outside_removal_changed_rgba_pixels": outside, "protected_changed_rgba_pixels": protected_changed,
        "C1": "NOT_RUN", "C3": "NOT_RUN", "RUNTIME_VALIDATION": "UNTESTED",
        "files": {p.name: digest(p.read_bytes()) for p in tmp.glob("*.png")},
    }
    (tmp / "receipt.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.rename(out)
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle-root", required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    m = json.loads(Path(args.job).read_text(encoding="utf-8"))
    print(json.dumps(prepare_plate(Path(args.bundle_root), m, Path(args.output).resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()
