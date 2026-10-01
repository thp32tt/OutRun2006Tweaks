#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

TARGET_SHA = "a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
DONOR411_SHA = "bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
BLUE_PANEL = (0, 79, 159, 255)
RANDOM_FILL = (245, 247, 247, 255)
RANDOM_TEXT_ROI = (1710, 1410, 2008, 1515)
DONOR_TEXT_ROI = (1570, 820, 1930, 1110)
PANEL_ROI = (1690, 1430, 2010, 1605)
PANEL_X_BOUNDS = (1707, 1992)
MAX_HORIZONTAL_SAMPLE_DISTANCE = 96


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_readable(path: Path) -> np.ndarray:
    # Canonical selector DDS is stored mirror-Y relative to readable/game inspection.
    return np.asarray(
        Image.open(path).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ).copy()


def exact(image: np.ndarray, rgba: tuple[int, int, int, int]) -> np.ndarray:
    return np.all(image == np.array(rgba, dtype=np.uint8), axis=2)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    k = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
    return cv2.dilate(mask.astype(np.uint8), k).astype(bool)


def textmask(image: np.ndarray, fill: tuple[int, int, int, int], roi, radius=6):
    x0, y0, x1, y1 = roi
    out = np.zeros(image.shape[:2], bool)
    out[y0:y1, x0:x1] = dilate(exact(image[y0:y1, x0:x1], fill), radius)
    return out


def largest_bbox(mask: np.ndarray, roi=None):
    if roi:
        x0, y0, x1, y1 = roi
        sub = mask[y0:y1, x0:x1].astype(np.uint8)
    else:
        x0 = y0 = 0
        sub = mask.astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sub, 8)
    if n <= 1:
        raise RuntimeError("NO_COMPONENT")
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = stats[i]
    return (int(x0 + x), int(y0 + y), int(x0 + x + w), int(y0 + y + h), int(area))


def transform_from_bbox(src, dst):
    sx = (dst[2] - dst[0]) / (src[2] - src[0])
    sy = (dst[3] - dst[1]) / (src[3] - src[1])
    return sx, sy, dst[0] - src[0] * sx, dst[1] - src[1] * sy


def inverse_map(x, y, transform):
    sx, sy, tx, ty = transform
    return int(round((x - tx) / sx)), int(round((y - ty) / sy))


def bbox(mask: np.ndarray):
    yy, xx = np.where(mask)
    if not len(xx):
        return None
    return [int(xx.min()), int(yy.min()), int(xx.max() + 1), int(yy.max() + 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("donor411")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    target_bytes = Path(args.target).read_bytes()
    donor_bytes = Path(args.donor411).read_bytes()
    if sha256(target_bytes) != TARGET_SHA:
        raise SystemExit("TARGET_IDENTITY_FAIL")
    if sha256(donor_bytes) != DONOR411_SHA:
        raise SystemExit("DONOR411_IDENTITY_FAIL")

    target = load_readable(Path(args.target))
    donor = load_readable(Path(args.donor411))
    if target.shape != (2048, 2048, 4) or donor.shape != (2048, 2048, 4):
        raise SystemExit("DECODED_DIMENSION_FAIL")

    # Reproduce the A00309/C-accepted RANDOM unresolved set. A00309 recorded
    # donor53 incremental clean coverage as exactly zero, so donor411-only
    # replay is byte-equivalent for this unresolved mask.
    target_panel_bbox = largest_bbox(exact(target, BLUE_PANEL))[:4]
    donor_panel_bbox = largest_bbox(exact(donor, BLUE_PANEL), DONOR_TEXT_ROI)[:4]
    transform = transform_from_bbox(donor_panel_bbox, target_panel_bbox)
    target_text = textmask(target, RANDOM_FILL, RANDOM_TEXT_ROI, 6)
    donor_text = textmask(donor, RANDOM_FILL, DONOR_TEXT_ROI, 6)

    unresolved = np.zeros(target.shape[:2], bool)
    donor_clean = 0
    for y, x in zip(*np.where(target_text)):
        xd, yd = inverse_map(x, y, transform)
        if 0 <= yd < 2048 and 0 <= xd < 2048 and not donor_text[yd, xd]:
            donor_clean += 1
        else:
            unresolved[y, x] = True

    prior_fp = (int(target_text.sum()), donor_clean, int(unresolved.sum()), bbox(unresolved))
    if prior_fp != (9606, 4414, 5192, [1761, 1448, 1943, 1481]):
        raise SystemExit("A00309_RANDOM_FINGERPRINT_FAIL: " + repr(prior_fp))

    # Stage 3A: fill only pixels inside the external contour of the largest
    # exact dark-blue source panel component. This is source geometry, not a
    # candidate-derived shape, and remains intersected with the accepted
    # A00309 unresolved text neighborhood.
    x0, y0, x1, y1 = PANEL_ROI
    panel_sub = exact(target[y0:y1, x0:x1], BLUE_PANEL).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(panel_sub, 8)
    if n <= 1:
        raise SystemExit("NO_RANDOM_PANEL_COMPONENT")
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    component = (labels == i).astype(np.uint8)
    contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise SystemExit("NO_RANDOM_PANEL_CONTOUR")
    contour = max(contours, key=cv2.contourArea)
    filled = np.zeros_like(component)
    cv2.drawContours(filled, [contour], -1, 1, thickness=cv2.FILLED)
    panel_interior = np.zeros_like(unresolved)
    panel_interior[y0:y1, x0:x1] = filled.astype(bool)
    stage3a = unresolved & panel_interior

    # Stage 3B: only the three anti-aliased upper-border rows lie outside the
    # exact dark-blue panel contour. Resolve a pixel only if the nearest source
    # sample outside the text-neighborhood on both horizontal sides exists,
    # lies inside the exact target panel x-bounds, and the two RGBA values are
    # identical. This preserves the source border gradient exactly.
    upper_remaining = unresolved & ~stage3a
    upper_remaining[1451:, :] = False
    stage3b = np.zeros_like(unresolved)
    stage3b_values = {}
    for y, x in zip(*np.where(upper_remaining)):
        samples = []
        for dx in (-1, 1):
            found = None
            for distance in range(1, MAX_HORIZONTAL_SAMPLE_DISTANCE + 1):
                xx = x + dx * distance
                if xx < PANEL_X_BOUNDS[0] or xx >= PANEL_X_BOUNDS[1]:
                    break
                if not target_text[y, xx]:
                    found = tuple(int(v) for v in target[y, xx])
                    break
            if found is None:
                samples = []
                break
            samples.append(found)
        if len(samples) == 2 and samples[0] == samples[1]:
            stage3b[y, x] = True
            stage3b_values[(y, x)] = samples[0]

    proposal = stage3a | stage3b
    preview = target.copy()
    preview[stage3a] = np.array(BLUE_PANEL, dtype=np.uint8)
    for (y, x), value in stage3b_values.items():
        preview[y, x] = np.array(value, dtype=np.uint8)
    changed = np.any(preview != target, axis=2)
    remaining = unresolved & ~proposal
    remaining_coords = [[int(x), int(y)] for y, x in zip(*np.where(remaining))]
    unique_border_values = sorted({list(v) for v in stage3b_values.values()}) if False else sorted(set(stage3b_values.values()))

    fingerprint = (
        int(stage3a.sum()),
        int(stage3b.sum()),
        int(proposal.sum()),
        int((changed & proposal).sum()),
        int((changed & ~proposal).sum()),
        int(np.sum(preview[:, :, 3] != target[:, :, 3])),
        int(remaining.sum()),
        remaining_coords,
    )
    expected = (4831, 360, 5191, 3490, 0, 0, 1, [[1774, 1450]])
    if fingerprint != expected:
        raise SystemExit("A00394_FINGERPRINT_FAIL: " + repr(fingerprint))

    out = {
        "schema_version": 16,
        "schema": "outrun-a00394-index111-random-source-only-background-reconstruction-v1",
        "task_id": "LOCALIZATION-LOCALIZATION_A-00394",
        "wave_id": "P00260",
        "lane": "LOCALIZATION_A",
        "queue_index": 111,
        "asset": "C075FB49",
        "asset_path": "textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds",
        "coordinate_space": "readable/display after raw mirror_y -> flip_y",
        "source_identity": {
            "target_sha256": TARGET_SHA,
            "donor411_sha256": DONOR411_SHA,
            "decoded_canvas": [2048, 2048],
            "format": "RGBA32",
            "mip_count": 1,
        },
        "accepted_prior_evidence": {
            "a00309_random_scope_pixels": 9606,
            "a00309_donor411_clean_coverage_pixels": 4414,
            "a00309_donor53_incremental_clean_coverage_pixels": 0,
            "a00309_random_unresolved_pixels": 5192,
            "a00346_current_total_unresolved_pixels": 5734,
            "a00346_tuned_remaining_pixels": 463,
            "a00346_normal_remaining_pixels": 79,
            "a00346_random_remaining_pixels": 5192,
            "c176_disposition": "PASS_PREFLIGHT_ONLY",
        },
        "method": {
            "scope": "RANDOM_REMAINDER_ONLY__TUNED_NORMAL_UNCHANGED",
            "source_only": True,
            "candidate_pixels_used": False,
            "stage3a": "Intersect A00309 RANDOM unresolved mask with filled RETR_EXTERNAL contour of largest exact BLUE_PANEL source component inside conservative panel ROI.",
            "stage3b": "For unresolved y<1451 only, accept nearest non-text-neighborhood source samples left/right within 96px when both RGBA samples are exactly equal; write that exact source RGBA value.",
            "candidate_or_clean_plate_status": "NOT_EMITTED_PREFLIGHT_ONLY",
        },
        "random": {
            "prior_unresolved_pixels": 5192,
            "prior_unresolved_bbox": [1761, 1448, 1943, 1481],
            "stage3a_panel_interior_proposal_pixels": 4831,
            "stage3a_bbox": [1761, 1451, 1943, 1481],
            "stage3a_actual_changed_pixels": int((changed & stage3a).sum()),
            "stage3b_border_proposal_pixels": 360,
            "stage3b_bbox": [1779, 1448, 1941, 1451],
            "stage3b_source_rgba_values": [list(v) for v in unique_border_values],
            "stage3b_actual_changed_pixels": int((changed & stage3b).sum()),
            "new_proposal_pixels": 5191,
            "new_actual_changed_pixels": 3490,
            "remaining_unresolved_pixels": 1,
            "remaining_coordinates_xy": remaining_coords,
        },
        "aggregate_after": {
            "tuned_setting_remaining_pixels": 463,
            "normal_setting_remaining_pixels": 79,
            "random_remaining_pixels": 1,
            "total_remaining_unresolved_pixels": 543,
            "new_unresolved_reduction_pixels": 5191,
            "outside_prior_unresolved_changed_pixels": 0,
            "alpha_changed_pixels": 0,
        },
        "self_qa": {
            "exact_target_identity": "PASS",
            "exact_donor_identity": "PASS",
            "a00309_random_fingerprint_reproduced": "PASS",
            "proposal_subset_of_prior_unresolved": "PASS",
            "source_only_background_rule": "PASS",
            "outside_prior_unresolved_changes": 0,
            "alpha_changes": 0,
            "candidate_dds_modified": False,
            "clean_plate_emitted": False,
        },
        "readiness_after": "PREFLIGHT_ONLY__RANDOM_SOURCE_ONLY_RECONSTRUCTION_ADVANCED__543_TOTAL_UNRESOLVED__NO_CLEAN_PLATE_OR_DDS",
        "candidate_dds_authorized": False,
        "candidate_dds_modified": False,
        "runtime_validation": "UNTESTED",
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
