"""Repository-backed approval evidence. No image-quality claim is inferred from notes.

This validates evidence integrity, not aesthetic correctness. C must inspect pixels.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

POLICY = "visual-evidence-v1-20261008"
CHECKS = ("slant", "clean_plate", "style", "readability", "glyph_integrity",
          "protected_art", "placement", "orientation")
VIEWS = {"native", "zoom", "practical", "practical_75", "practical_50", "raw", "black", "white", "gray"}
APPROVALS = Path("localization/graphics/role_C/APPROVALS")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bound_file(repo, ref, png=False):
    if not isinstance(ref, dict):
        raise ValueError("missing file reference")
    path = (repo / ref.get("path", "")).resolve()
    if not path.is_relative_to(repo.resolve()) or not path.is_file():
        raise ValueError("missing or unsafe evidence path")
    if digest(path.read_bytes()) != ref.get("sha256"):
        raise ValueError("evidence hash mismatch: " + ref.get("path", ""))
    if png:
        with Image.open(path) as im:
            if im.format != "PNG":
                raise ValueError("lossless PNG evidence required")
            im.load()
    return path


def load_bound_json(repo, ref):
    return json.loads(bound_file(repo, ref).read_text(encoding="utf-8"))


def calibration_ok(repo, ref, reviewer):
    data = load_bound_json(repo, ref)
    if data.get("policy_version") != POLICY or data.get("reviewer") != reviewer:
        raise ValueError("stale calibration or different reviewer")
    cases = data.get("cases", [])
    required = {"normal", "opposite_slant", "clipped_stroke", "residue", "excessive_weight"}
    if not required.issubset({c.get("kind") for c in cases}):
        raise ValueError("calibration lacks normal/defect controls")
    for case in cases:
        bound_file(repo, case.get("image"), png=True)
        expected = "PASS" if case.get("kind") == "normal" else "FAIL"
        if case.get("observed") != expected or not case.get("observation", "").strip():
            raise ValueError("calibration missed a known control")
    # The observer records decisions before consulting the answer key.
    if data.get("blind_review_completed") is not True:
        raise ValueError("blind calibration review missing")


def verify_approval(repo, row, candidate_sha, source_sha=None, candidate_image=None, mip_count=1):
    """Return (approval, []) or (None, reasons); never promote legacy text tokens."""
    repo = Path(repo)
    try:
        idx = int(row["index"].lstrip("\ufeff"))
        # Active user in-game regression blocks approval even if historical C3
        # and exact-hash numeric evidence still say PASS. Never auto-close.
        status = str(row.get("artwork_status", "")).lower()
        if any(flag in status for flag in ("rework_required", "visual_fail", "hold_strict", "reopened")) or status.endswith("_fail"):
            raise ValueError("current queue REWORK/HOLD/FAIL blocks approval")
        backlog = repo / "localization/graphics/INGAME_REWORK_BACKLOG.csv"
        if backlog.is_file():
            with backlog.open(encoding="utf-8-sig", newline="") as handle:
                for report in csv.DictReader(handle):
                    if (report.get("status", "").strip() == "OPEN_USER_INGAME_FAIL"
                            and report.get("queue_index", "").lstrip("\ufeff").strip() == str(idx)):
                        raise ValueError("active user in-game regression blocks approval")
        path = repo / APPROVALS / f"q{idx:03d}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("policy_version") != POLICY or data.get("queue_index") != idx:
            raise ValueError("approval policy/index mismatch")
        if data.get("asset_path") != row["path"] or data.get("candidate_sha256") != candidate_sha:
            raise ValueError("approval candidate/path mismatch")
        if source_sha is not None and data.get("source_sha256") != source_sha:
            raise ValueError("export English source differs from reviewed source")
        if data.get("result") != "PASS":
            raise ValueError("approval is not PASS")
        if data.get("mode") == "preserve_original":
            if candidate_sha or not data.get("policy_reason", "").strip():
                raise ValueError("invalid explicit preserve-original decision")
            policy = load_bound_json(repo, data.get("policy_decision"))
            if (policy.get("queue_index") != idx or policy.get("decision") != "PRESERVE_ORIGINAL"
                    or policy.get("source_sha256") != data.get("source_sha256")):
                raise ValueError("preserve policy binding mismatch")
            return data, []
        if data.get("mode") != "localized" or not candidate_sha:
            raise ValueError("localized candidate required")
        machine = load_bound_json(repo, data.get("machine_report"))
        if machine.get("candidate_sha256") != candidate_sha or machine.get("result") != "PASS":
            raise ValueError("machine report is stale or failed")
        if machine.get("source_sha256") != data.get("source_sha256"):
            raise ValueError("machine/source identity mismatch")
        for field in ("changed_outside", "alpha_outside", "protected_changed", "overlap", "clipping"):
            if type(machine.get(field)) is not int or machine[field] != 0:
                raise ValueError("missing/nonzero machine gate: " + field)
        mips = data.get("text_mips", [])
        if [m.get("level") for m in mips] != list(range(mip_count)):
            raise ValueError("missing authored mip evidence")
        for mip in mips:
            if mip.get("result") != "PASS" or not mip.get("observation"):
                raise ValueError("unreviewed text mip")
            bound_file(repo, mip.get("evidence"), png=True)
        clean = bound_file(repo, data.get("clean_plate"), png=True)
        final = bound_file(repo, data.get("decoded_final"), png=True)
        with Image.open(final) as im:
            decoded = im.convert("RGBA")
        with Image.open(clean) as im:
            if im.size != decoded.size:
                raise ValueError("clean/final geometry mismatch")
        if candidate_image is not None:
            candidate_image = candidate_image.convert("RGBA")
            if decoded.size != candidate_image.size or decoded.tobytes() != candidate_image.tobytes():
                raise ValueError("final PNG is not decoded persisted DDS pixels")
        inventory = load_bound_json(repo, data.get("segment_inventory"))
        if inventory.get("source_sha256") != data.get("source_sha256"):
            raise ValueError("segment inventory source mismatch")
        ids = inventory.get("localizable_segment_ids", [])
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("missing/duplicate source segment inventory")
        regions = data.get("regions", [])
        if len(regions) != len(ids) or {r.get("id") for r in regions} != set(ids):
            raise ValueError("incomplete per-segment coverage")
        profile = load_bound_json(repo, data.get("family_profile"))
        if not profile.get("family_id") or not profile.get("reference_observation"):
            raise ValueError("source-derived family profile missing")
        bound_file(repo, profile.get("reference_image"), png=True)
        for region in regions:
            box = region.get("bbox", [])
            if (len(box) != 4 or any(type(n) is not int for n in box)
                    or not (0 <= box[0] < box[2] <= decoded.width
                            and 0 <= box[1] < box[3] <= decoded.height)):
                raise ValueError("invalid native region bbox")
            if region.get("readable_transform") not in {"identity", "flip_y", "flip_x", "rotate_180", "rotate_90", "rotate_270"}:
                raise ValueError("unresolved per-sprite orientation")
            measurement = region.get("slant", {})
            a, b = measurement.get("source_top_minus_bottom_dx"), measurement.get("candidate_top_minus_bottom_dx")
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (a, b)):
                raise ValueError("missing observed slant displacements")
            if (a > 0) != (b > 0) or (a < 0) != (b < 0):
                raise ValueError("opposite/upright slant mismatch")
            if not measurement.get("anchor_observation"):
                raise ValueError("slant anchor evidence missing")
            views = region.get("views", {})
            if not VIEWS.issubset(views):
                raise ValueError("missing native/zoom/practical/raw/background views")
            for view in views.values():
                bound_file(repo, view, png=True)
        stages = data.get("stages", {})
        if set(stages) != {"C", "C3"}:
            raise ValueError("separate C and C3 observations required")
        if stages["C"].get("review_id") == stages["C3"].get("review_id"):
            raise ValueError("C3 cannot reuse the C review identity")
        for stage_name, stage in stages.items():
            if not stage.get("review_id") or not stage.get("reviewer"):
                raise ValueError("missing review identity")
            calibration_ok(repo, stage.get("calibration"), stage["reviewer"])
            if stage_name == "C" and stage.get("pixels_before_producer_verdict") is not True:
                raise ValueError("independent first-look review missing")
            if stage_name == "C3" and not stage.get("prior_defect_observation"):
                raise ValueError("C3 regression/family review missing")
            findings = stage.get("findings", {})
            if set(findings) != set(ids):
                raise ValueError("missing stage region findings")
            for checks in findings.values():
                if set(checks) != set(CHECKS):
                    raise ValueError("eight visual findings required per region")
                for finding in checks.values():
                    if finding.get("result") != "PASS" or not finding.get("observation", "").strip():
                        raise ValueError("failed/empty visual finding")
                    bound_file(repo, finding.get("evidence"), png=True)
        return data, []
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return None, [str(exc)]
