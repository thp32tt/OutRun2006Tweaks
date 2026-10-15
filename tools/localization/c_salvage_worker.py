#!/usr/bin/env python3
"""C-SALVAGE autonomous offline worker. No ImageGen, game deployment or approval.

Scans completed A/B generated PNGs read-only, exports transparent lettering
*proposals*, indexes exact PSD sources, optionally runs SHA-pinned manually
reviewed native composite recipes. Running this tool NEVER grants QA PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

import c_salvage_compose as composer
import c_salvage_atlas

SCHEMA = "outrun-c-salvage-worker-v1"
NAME = re.compile(r"^(Q(?P<index>\d+)_)(?P<hash>[0-9A-Fa-f]{7,8})_.+_k\.png$")
MAX_IMAGE_PIXELS = 4096 * 4096


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(data)


def store_json(path: Path, item: dict):
    write_new(path, (json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())


def inspect_psd_catalog(path: Path | None):
    if path is None or not path.is_file():
        return {}
    o = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(o.get("files"), list) or not isinstance(o.get("upstream_commit"), str):
        raise ValueError("Invalid pinned PSD catalog")
    matches = {}
    for obj in o["files"]:
        for q in obj.get("queue_indexes", []):
            matches.setdefault(int(q), []).append(obj)
    return matches


def psd_evidence(index: int, texture: str, matches: dict, repo_root: Path | None):
    result = []
    for m in matches.get(index, []):
        if m["texture_hash"].lower() != texture.lower():
            continue
        copies = []
        for c in m.get("current_copies", []):
            origin = c.get("path", "")
            # For historical catalog evidence and optional validated local staged copy.
            entry = {"repo_relative_path": origin, "catalog_sha256": c.get("source_sha256"),
                     "local_present": False, "status": "CATALOG_ONLY"}
            if repo_root and origin and not Path(origin).is_absolute():
                p = (repo_root / origin).resolve()
                if p.is_relative_to(repo_root) and p.is_file():
                    entry["local_present"] = True
                    entry["size_bytes"] = p.stat().st_size
                    entry["status"] = "PSD_PRESENT_SHA_CHECK_REQUIRED"
                    if c.get("source_sha256") and p.stat().st_size <= 100 * 1024 * 1024:
                        entry["sha256_verified"] = sha(p.read_bytes()) == c["source_sha256"]
                        entry["status"] = ("PSD_SHA_VERIFIED_LAYER_REVIEW_PENDING" if entry["sha256_verified"]
                                           else "PSD_SHA_MISMATCH_HOLD")
            copies.append(entry)
        result.append({"upstream_source_path": m.get("source_path"),
                       "upstream_blob_sha": m.get("git_blob_sha"),
                       "copied_into_branch": bool(m.get("copied_into_branch")),
                       "copies": copies, "source_match_only": True})
    return result


def mask_input(candidate: Path, mask_dir: Path | None, generated_size: tuple[int, int]):
    if mask_dir is None:
        return None, None
    path = mask_dir / (candidate.stem + ".mask.png")
    if not path.is_file():
        return None, None
    raw = path.read_bytes()
    with Image.open(path) as im:
        if im.format != "PNG" or im.mode != "L" or im.size != generated_size:
            raise ValueError("Generated text mask must be L PNG at generated dimensions")
        a = np.array(im)
    if not np.isin(a, (0, 255)).all() or not np.any(a):
        raise ValueError("Nonbinary or empty generated mask")
    return raw, a.astype(bool)


def source_tile_evidence(candidate: Path, source_dirs: list[Path]):
    name = candidate.name[:-6] + ".png"  # strip "_k.png"
    for directory in source_dirs:
        orig = directory / name
        if orig.is_file():
            raw = orig.read_bytes()
            try:
                with Image.open(orig) as im:
                    if im.format != "PNG": continue
                    return {"path": str(orig), "sha256": sha(raw),
                            "native_source_tile_size": list(im.size),
                            "source_status": "SOURCE_TILE_FOUND_NOT_FULL_ATLAS_PROOF"}
            except OSError:
                continue
    return {"source_status": "SOURCE_TILE_MISSING_NEEDS_STAGING"}


def handle_png(role: str, p: Path, output: Path, source_dirs: list[Path],
               masks: Path | None, catalog: dict, repo_root: Path | None,
               atlas_proof: dict | None = None):
    match = NAME.match(p.name)
    if not match:
        return "SKIP_FILENAME", False
    raw = p.read_bytes()
    if len(raw) > 50 * 1024 * 1024:
        return "HOLD_TOO_LARGE", False
    with Image.open(p) as im:
        if im.format != "PNG" or im.width * im.height > MAX_IMAGE_PIXELS:
            return "HOLD_INVALID_PNG", False
        im.load()
        rgba = np.asarray(im.convert("RGBA")).copy()
        dimensions = im.size
    mask_blob, manual_mask = mask_input(p, masks, dimensions)
    rawsha = sha(raw)
    masksha = sha(mask_blob)[:10] if mask_blob is not None else "autoalpha"
    source_ev = source_tile_evidence(p, source_dirs)
    if atlas_proof is not None:
        source_ev['assembled_full_atlas'] = atlas_proof
    psd_ev = psd_evidence(int(match.group("index")), match.group("hash"), catalog, repo_root)
    # A formerly missing source/PSD may be staged after the first HOLD. It must
    # cause a new receipt without overwriting the historical inspection.
    inputs_fingerprint = sha(json.dumps({"source": source_ev, "psd": psd_ev},
                                        sort_keys=True).encode())[:12]
    key = f"{role}-{match.group('index')}-{rawsha[:16]}-{masksha}-{inputs_fingerprint}"
    target = output / "candidates" / key
    if (target / "receipt.json").is_file():
        return "ALREADY_RECORDED", False
    if target.exists():
        return "HOLD_INCOMPLETE_PREVIOUS_OUTPUT", False
    visible = rgba[:, :, 3] > 0
    transparent_fraction = float(np.mean(~visible))
    positive = int(np.count_nonzero(visible))
    ev = {
        "schema": SCHEMA,
        "candidate": {"role": role, "filename": p.name, "sha256": rawsha,
                      "dimensions": list(dimensions), "positive_alpha_pixels": positive,
                      "transparent_fraction": round(transparent_fraction, 6)},
        "queue_index": int(match.group("index")), "texture_hash": match.group("hash"),
        "source": source_ev,
        "psd_sources": psd_ev,
        "generated_text_mask": {"kind": "REVIEW_PENDING", "manual_mask_sha256": sha(mask_blob) if mask_blob else None},
        "C1": "NOT_RUN", "C3": "NOT_RUN", "RUNTIME_VALIDATION": "UNTESTED",
        "official_promoted": False,
    }
    if not positive:
        ev["status"] = "HOLD_EMPTY_GENERATED_ALPHA"
    elif manual_mask is None and transparent_fraction < 0.05:
        ev["status"] = "HOLD_OPAQUE_GENERATED_REQUIRES_EXPLICIT_GLYPH_MASK"
    else:
        # Cropping a native transparent PNG is *not* visual certification that
        # all positive pixels are Hangul. A human still marks the actual phrase.
        selected = visible if manual_mask is None else manual_mask & visible
        if not np.any(selected):
            ev["status"] = "HOLD_EMPTY_GLYPH_INTERSECTION"
        else:
            ys, xs = np.where(selected)
            bounds = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            out = rgba[bounds[1]:bounds[3], bounds[0]:bounds[2]].copy()
            sel = selected[bounds[1]:bounds[3], bounds[0]:bounds[2]]
            out[~sel] = [0, 0, 0, 0]
            # Pixel RGB hidden by alpha must never contaminate recomposition.
            out[out[:, :, 3] == 0, :3] = 0
            from io import BytesIO
            buffer = BytesIO()
            Image.fromarray(out, "RGBA").save(buffer, "PNG")
            layer_blob = buffer.getvalue()
            ev["layer"] = {"filename": "lettering_PROPOSAL.png", "sha256": sha(layer_blob),
                           "generated_pixel_bbox": list(bounds),
                           "status": "LAYER_PROPOSAL_PENDING_GLYPH_TRANSLATION_VISUAL_REVIEW"}
            ev["status"] = "LAYER_PROPOSAL_REVIEW_REQUIRED"
    target.mkdir(parents=True)
    if ev.get("layer"):
        write_new(target / "lettering_PROPOSAL.png", layer_blob)
    store_json(target / "receipt.json", ev)
    return ev["status"], True


def handle_recipe(p: Path, root: Path, output: Path):
    blob = p.read_bytes()
    if len(blob) > 2_000_000:
        return "HOLD_RECIPE_SIZE", False
    key = re.sub(r"[^a-zA-Z0-9_.-]", "_", p.stem) + "-" + sha(blob)[:16]
    done = output / "composites" / key
    if (done / "C_SALVAGE_TEST_ONLY.json").is_file():
        return "ALREADY_COMPOSED", False
    if (output / "recipe_failures" / (key + ".json")).is_file():
        return "ALREADY_HELD", False
    try:
        spec = json.loads(blob)
        if spec.get("schema") != composer.SCHEMA:
            raise ValueError("Unexpected C recipe schema")
        if spec.get("translation_verified") is not True:
            raise ValueError("Korean glyph translation not verified")
        # Require exact SHA-bound input references; no automatic guess of
        # opaque background, mask, font, cell, transform, or codec.
        result = composer.compose(root, spec, done)
        return result["status"], True
    except Exception as e:
        store_json(output / "recipe_failures" / (key + ".json"),
                   {"schema": SCHEMA, "recipe": p.name, "sha256": sha(blob),
                    "status": "HOLD_RECIPE_FAIL_CLOSED", "reason": str(e),
                    "RUNTIME_VALIDATION": "UNTESTED"})
        return "HOLD_RECIPE_FAIL_CLOSED", True


def handle_plate_job(p: Path, root: Path, output: Path):
    import c_salvage_plate
    blob = p.read_bytes()
    if len(blob) > 2_000_000:
        return "HOLD_PLATE_JOB_SIZE", False
    key = re.sub(r"[^a-zA-Z0-9_.-]", "_", p.stem) + "-" + sha(blob)[:16]
    done = output / "plates" / key
    held = output / "plate_failures" / (key + ".json")
    if (done / "receipt.json").exists() or held.exists():
        return "ALREADY_RECORDED", False
    try:
        spec = json.loads(blob)
        result = c_salvage_plate.prepare_plate(root, spec, done)
        return result["status"], True
    except Exception as e:
        store_json(held, {"schema": SCHEMA, "job": p.name, "sha256": sha(blob),
                          "status": "HOLD_PLATE_PREPARATION", "reason": str(e),
                          "C1": "NOT_RUN", "RUNTIME_VALIDATION": "UNTESTED"})
        return "HOLD_PLATE_PREPARATION", True


def run_once(args):
    root = Path(args.input_root).resolve()
    out = Path(args.output_root).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    bundle_root = Path(args.bundle_root).resolve() if getattr(args, 'bundle_root', None) else root
    catalog = inspect_psd_catalog(
        repo_root / "localization/graphics/plate_library/PSD_UPSTREAM_FULL_INDEX.json"
        if repo_root else None)
    counts = {}
    added = 0
    # Assemble the full English texture first. Never treat one tile as a DDS.
    atlas_result = c_salvage_atlas.run_atlas_first(
        root, out, max_groups=min(4, args.max_per_cycle))
    added += atlas_result["new"]
    counts.update(atlas_result["counts"])
    atlas_ready = atlas_result["ready"]
    require_atlas = getattr(args, "require_atlas", False) or atlas_result["mapping_present"]
    if require_atlas and not atlas_result["mapping_present"]:
        counts["HOLD_CANONICAL_TILE_MAPPING_MISSING"] = 1
    source_dirs = [root / name for name in (
        "a_tile_batches/upright_sources", "ab_batches/upright_sources",
        str(c_salvage_atlas.MAP_REL.parent))]
    mask_dir = Path(args.masks_dir).resolve() if args.masks_dir else None
    for role in ("A", "B"):
        directory = root / "ab_batches/candidate_outputs" / role
        if not directory.is_dir():
            counts["HOLD_INPUT_FOLDER_MISSING_" + role] = 1
            continue
        for path in sorted(directory.glob("*.png")):
            if added >= args.max_per_cycle:
                break
            # Never extract/move an A/B tile before its entire source atlas
            # has been reassembled with exact SHA and complete pixel coverage.
            original_name = path.name[:-6] + ".png" if path.name.endswith("_k.png") else ""
            proof = atlas_ready.get(original_name)
            if require_atlas and proof is None:
                counts["HOLD_ATLAS_NOT_READY"] = counts.get("HOLD_ATLAS_NOT_READY", 0) + 1
                continue
            try:
                status, changed = handle_png(role, path, out, source_dirs,
                                             mask_dir, catalog, repo_root, proof)
            except (ValueError, OSError) as err:
                status, changed = ("HOLD_CANDIDATE_ERROR", False)
                print(json.dumps({"file": path.name, "error": str(err)}, ensure_ascii=False), file=sys.stderr)
            if status != "ALREADY_RECORDED":
                counts[status] = counts.get(status, 0) + 1
            added += int(changed)
        if added >= args.max_per_cycle: break
    if getattr(args, "plate_jobs_dir", None):
        plate_dir = Path(args.plate_jobs_dir).resolve()
        if plate_dir.is_dir():
            for job in sorted(plate_dir.glob("*.json")):
                if added >= args.max_per_cycle: break
                status, changed = handle_plate_job(job, bundle_root, out)
                if status != "ALREADY_RECORDED":
                    counts[status] = counts.get(status, 0) + 1
                added += int(changed)
    if args.recipes_dir:
        recipe_dir = Path(args.recipes_dir).resolve()
        if recipe_dir.is_dir():
            for manifest in sorted(recipe_dir.glob("*.json")):
                if added >= args.max_per_cycle: break
                status, changed = handle_recipe(manifest, bundle_root, out)
                if status not in ("ALREADY_COMPOSED", "ALREADY_HELD"):
                    counts[status] = counts.get(status, 0) + 1
                added += int(changed)
    report = {"schema": SCHEMA, "at": datetime.now(timezone.utc).isoformat(),
              "new_processed_items": added, "counts": counts,
              "source_atlas_groups_processed": atlas_result["new"],
              "source_atlas_ready_tile_count": len(atlas_ready),
              "require_source_atlas": require_atlas,
              "source_root": str(root), "output_root": str(out),
              "mode": "OFFLINE_NO_IMAGEGEN_TEST_ONLY",
              "C1": "NOT_RUN", "game": "UNTESTED", "deployment_attestation": "NOT_CHECKED_BY_WORKER"}
    # Atomic current snapshot; not an official queue/approval record.
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / ".last_cycle.tmp"
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out / "last_cycle.json")
    print(json.dumps(report, ensure_ascii=False))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-root", required=True)
    p.add_argument("--output-root", required=True)
    p.add_argument("--repo-root", default=None)
    p.add_argument("--recipes-dir", default=None)
    p.add_argument("--bundle-root", default=None, help="Optional isolated reviewed source/DDS/PSD/CLEAN bundle; never A/B live data")
    p.add_argument("--plate-jobs-dir", default=None, help="Reviewed PSD/source English-removal jobs")
    p.add_argument("--masks-dir", default=None)
    p.add_argument("--require-atlas", action="store_true",
                   help="Fail closed when canonical tile mapping/full atlas is absent")
    p.add_argument("--max-per-cycle", type=int, default=10)
    p.add_argument("--interval-seconds", type=int, default=1800)
    p.add_argument("--loop", action="store_true", help="Only after user's manual deployment")
    args = p.parse_args()
    if args.max_per_cycle < 1 or args.max_per_cycle > 50 or args.interval_seconds < 300:
        p.error("max-per-cycle must be 1..50 and interval >=300 seconds")
    if not Path(args.input_root).is_dir():
        p.error("Actual A/B source root not mounted; refusing empty, fake success")
    if Path(args.output_root).resolve().is_relative_to(Path(args.input_root).resolve()):
        p.error("Output must be outside the read-only A/B input root")
    if not args.loop:
        run_once(args)
        return
    while True:
        try:
            run_once(args)
        except Exception as exc:
            print(json.dumps({"status": "C_WORKER_ERROR", "error": str(exc)}), file=sys.stderr)
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
