"""Production-stage pixel checks. A mechanical pass is NEVER visual/C/game approval.

Inputs are full native RAW images and source-authored masks, bound by SHA-256.
The optional changed-candidate mode is used before CPU-worker publication.
"""
import argparse
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

VERSION = "production-pixels-v1-20261009"
CANDIDATES = "localization/graphics/hd_candidates/"
MANIFESTS = Path("localization/graphics/worker_results/production_manifests")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bound(repo, ref):
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise ValueError("Missing bound input")
    name = ref["path"]
    path = (repo / name).resolve()
    if not path.is_relative_to(repo.resolve()) or Path(name).is_absolute():
        raise ValueError("Input must be repository-relative")
    revision = ref.get("git_revision")
    if revision:
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
            raise ValueError("Pin git_revision to a full commit SHA")
        data = subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=repo)
    else:
        data = path.read_bytes()
    if sha(data) != ref.get("sha256"):
        raise ValueError("Input hash mismatch: " + name)
    return data


def rgba(data):
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in {"DDS", "PNG"}:
            raise ValueError("Use DDS or lossless PNG, never JPG")
        return np.array(im.convert("RGBA"))


def mask(data, shape):
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "PNG" or im.mode != "L":
            raise ValueError("Masks must be binary L-mode PNG")
        a = np.array(im)
    if a.shape != shape or not np.all((a == 0) | (a == 255)):
        raise ValueError("Mask size/value mismatch; implicit resizing is forbidden")
    return a != 0


def changed(a, b):
    return np.any(a != b, axis=2)


def pixel_checks(source, baseline, clean, masks, lettering=None, final=None):
    """Compare to canonical source AND previous candidate; neither substitutes for the other."""
    if any(a.shape != source.shape for a in (baseline, clean)):
        raise ValueError("Native dimensions differ")
    if any(a.shape != source.shape[:2] for a in masks.values()):
        raise ValueError("Mask dimensions differ")
    removal, protected, edit = (masks[k] for k in ("removal", "protected", "edit"))
    restore = masks["restore"]
    transparent = masks["transparent"]
    counts = {
        "removal_outside_edit": int(np.count_nonzero(removal & ~edit)),
        "removal_over_protected": int(np.count_nonzero(removal & protected)),
        "restore_outside_protected_edit": int(np.count_nonzero(restore & ~(protected & edit))),
        "clean_changed_outside_removal_or_restore": int(np.count_nonzero(changed(clean, baseline) & ~(removal | restore))),
        "clean_protected_diff_from_source": int(np.count_nonzero(changed(clean, source) & protected)),
        "transparent_plate_residue": int(np.count_nonzero((clean[:, :, 3] != 0) & transparent)),
        "transparent_outside_removal": int(np.count_nonzero(transparent & ~removal)),
    }
    if lettering is not None and final is not None:
        if lettering.shape != source.shape or final.shape != source.shape:
            raise ValueError("Native final/lettering dimensions differ")
        effect = masks["effect"]
        ink = lettering[:, :, 3] != 0
        counts.update({
            "effect_outside_edit": int(np.count_nonzero(effect & ~edit)),
            "lettering_outside_effect": int(np.count_nonzero(ink & ~effect)),
            "lettering_over_protected": int(np.count_nonzero(ink & protected)),
            "final_protected_diff_from_source": int(np.count_nonzero(changed(final, source) & protected)),
            "final_changed_outside_edit": int(np.count_nonzero(changed(final, baseline) & ~edit)),
            "final_changed_outside_effect": int(np.count_nonzero(changed(final, clean) & ~effect)),
        })
    return counts


def slant_direction(anchors):
    """Anchors are measured in readable coordinates; y increases DOWN, not RAW shear values."""
    top, bottom = anchors["top"], anchors["bottom"]
    values = list(top) + list(bottom)
    if len(top) != 2 or len(bottom) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("Missing/invalid measured slant anchors")
    if top[1] >= bottom[1]:
        raise ValueError("Slant anchors must be in readable top/bottom order")
    dx = top[0] - bottom[0]
    return (dx > 0) - (dx < 0)


def verify(repo, manifest):
    repo = Path(repo).resolve()
    if manifest.get("version") != VERSION or manifest.get("coordinates") != "native_raw":
        raise ValueError("Unknown version or coordinates")
    stage = manifest.get("stage")
    if stage not in {"plate", "final"}:
        raise ValueError("Stage must be plate or final")
    inputs = manifest["inputs"]
    data = {k: bound(repo, inputs[k]) for k in ("source", "baseline", "clean")}
    source, baseline, clean = (rgba(data[k]) for k in ("source", "baseline", "clean"))
    masks = {k: mask(bound(repo, manifest["masks"][k]), source.shape[:2])
             for k in ("removal", "protected", "edit", "transparent", "restore")}
    if not np.any(masks["removal"]) or not np.any(masks["edit"]):
        raise ValueError("Empty edit/removal mask cannot qualify production")
    # The pre-lettering check is reusable. No candidate exists at that stage.
    final = lettering = None
    errors = []
    if stage == "final":
        data.update({k: bound(repo, inputs[k]) for k in ("candidate", "lettering")})
        if inputs["candidate"].get("git_revision"):
            raise ValueError("Candidate must be current persisted working-tree bytes")
        if any(data[k][:4] != b"DDS " for k in ("source", "baseline", "candidate")):
            raise ValueError("Final stage requires actual source/baseline/candidate DDS")
        if len(data["candidate"]) != len(data["source"]) or data["candidate"][:128] != data["source"][:128]:
            errors.append("DDS_CONTRACT_CHANGED")
        final, lettering = rgba(data["candidate"]), rgba(data["lettering"])
        masks["effect"] = mask(bound(repo, manifest["masks"]["effect"]), source.shape[:2])
        # Lossless paths must equal the intended alpha composite exactly. Lossy paths
        # still enforce zero protected/outside changes, and need visual codec/mip review.
        if data["source"][84:88] in (b"\0\0\0\0", b"RGBA"):
            composed = np.array(Image.alpha_composite(Image.fromarray(clean), Image.fromarray(lettering)))
            if composed.shape != final.shape or np.any(composed != final):
                errors.append("UNEXPECTED_COMPOSITE_PIXELS")
        regions = manifest.get("regions", [])
        if not regions or len({r["id"] for r in regions}) != len(regions):
            raise ValueError("Unique measured text regions required")
        for region in regions:
            # The marked evidence lets C audit the chosen semantic stems. Numeric
            # anchors alone cannot prove family likeness or correct correspondence.
            rgba(bound(repo, region["anchor_evidence"]))
            if slant_direction(region["source_anchors"]) != slant_direction(region["candidate_anchors"]):
                errors.append("OPPOSITE_OR_UPRIGHT_SLANT:" + region["id"])
    counts = pixel_checks(source, baseline, clean, masks, lettering, final)
    errors.extend(k for k, value in counts.items() if value)
    return {"version": VERSION, "stage": stage, "candidate_sha256":
            inputs.get("candidate", {}).get("sha256"), "source_sha256": inputs["source"]["sha256"],
            "counts": counts, "errors": errors,
            "result": "FAIL" if errors else "MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED",
            "runtime_validation": "UNTESTED",
            "limitations": "Mask semantics, opaque plate residue, typography, full segment coverage, mip aesthetics and actual game appearance require independent visual review."}


def check_changed(repo, base):
    """Gate only newly changed production DDS; never reclassify historical candidates."""
    repo = Path(repo).resolve()
    names = subprocess.check_output(["git", "diff", "--name-only", base, "--", CANDIDATES], cwd=repo, text=True).splitlines()
    names += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", CANDIDATES], cwd=repo, text=True).splitlines()
    reports = []
    for name in sorted(set(names)):
        if not name.lower().endswith(".dds") or not (repo / name).exists():
            continue  # deletion/removal is not promotion
        digest = sha((repo / name).read_bytes())
        p = repo / MANIFESTS / (digest + ".json")
        m = json.loads(p.read_text(encoding="utf-8"))
        if m.get("stage") != "final" or m["inputs"]["candidate"].get("path") != name:
            raise ValueError("Missing current final-stage manifest for " + name)
        previous = subprocess.run(["git", "show", f"{base}:{name}"], cwd=repo, capture_output=True)
        if previous.returncode == 0:
            expected_baseline = sha(previous.stdout)
        else:
            # A new candidate starts from the canonical source, never an arbitrary
            # already-damaged baseline. Invalid base itself must still fail closed.
            subprocess.run(["git", "rev-parse", "--verify", base + "^{commit}"],
                           cwd=repo, check=True, capture_output=True)
            expected_baseline = m["inputs"]["source"]["sha256"]
        if m["inputs"]["baseline"]["sha256"] != expected_baseline:
            raise ValueError("Baseline is not the pre-change candidate: " + name)
        report = verify(repo, m)
        if report["candidate_sha256"] != digest or report["errors"]:
            raise ValueError("Production pixel gate rejected " + name + ": " + str(report["errors"]))
        reports.append({"path": name, **report})
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest")
    group.add_argument("--changed-since", help="Git base revision; check changed hd_candidates before publishing")
    parser.add_argument("--report")
    args = parser.parse_args()
    try:
        if args.manifest:
            report = verify(args.repo, json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        else:
            report = {"checked": check_changed(args.repo, args.changed_since)}
        failed = report.get("result") == "FAIL"
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        report, failed = {"result": "HOLD_MISSING_OR_INVALID_INPUT", "error": str(exc)}, True
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        Path(args.report).write_text(output, encoding="utf-8")
    print(output, end="")
    raise SystemExit(2 if failed else 0)


if __name__ == "__main__":
    main()
