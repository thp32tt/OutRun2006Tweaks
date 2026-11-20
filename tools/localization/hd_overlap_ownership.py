"""Overlap ownership proof for existing HD A/B PNG reuse.

The original gate required every visible connected-alpha component to have one
exclusive ROI anchor. That is safe but over-conservative for antialiased UI:
low-alpha shadow/outline pixels can bridge two otherwise independent labels.

This module keeps the fail-closed path for real core collisions, while allowing
a bounded dual-alpha rescue. Alpha >= CORE_ALPHA is treated as source glyph
core. When multiple core islands are connected only through cosmetic alpha,
a multi-source pixel partition assigns the bridge back to the proven core
owners. High-alpha ambiguous pixels remain HOLD.

This never creates Korean glyphs, approves QA, or writes game assets.
"""
from collections import deque
from PIL import Image

MAX_SOURCE_ALPHA_PIXELS = 1500000
# General source-alpha floor. <=15 remains the pre-existing cosmetic tolerance.
COSMETIC_FRINGE_ALPHA = 15
# Core ownership is intentionally much stricter than the visible-alpha floor.
CORE_ALPHA = 96
# Only residual/tie pixels at or below this level may remain unassigned.
# 63/255 ~= 24.7% opacity: bounded to antialias/shadow, never solid glyph core.
SOFT_BRIDGE_ALPHA = 63

_NEIGHBORS = ((-1, -1), (0, -1), (1, -1),
              (-1, 0),           (1, 0),
              (-1, 1),  (0, 1),  (1, 1))


def _adjacent(key, width, height):
    x, y = key % width, key // width
    for dx, dy in _NEIGHBORS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield ny * width + nx


def _core_partition(alpha, membership, pixels, rows, pixels_owned, width, height):
    """Partition one visible-alpha component from exclusive solid-core seeds.

    The seed for an owner is alpha>=CORE_ALPHA source ink that belongs to only
    that ROI. Shared solid pixels are then assigned by multi-source geodesic
    distance while propagation is constrained to the candidate owner's ROI.
    This permits two outlined labels that physically touch to be separated
    without allowing a nested/identical ROI (which has no exclusive seed) to
    invent ownership.

    Returns (assigned, residual) on a bounded rescue, else None. Residual
    pixels may remain only when alpha <= SOFT_BRIDGE_ALPHA.
    """
    pixel_set = set(pixels)
    core = {
        key for key in pixels
        if alpha.getpixel((key % width, key // width)) >= CORE_ALPHA
    }
    if not core:
        return None

    # Solid exclusive source pixels are the only ownership seeds. Require more
    # than a single accidental pixel before an ROI can participate.
    seed_counts = {}
    seeds = {}
    for key in core:
        members = membership[key]
        if len(members) != 1:
            continue
        owner = next(iter(members))
        if owner not in pixels_owned:
            continue
        seed_counts[owner] = seed_counts.get(owner, 0) + 1
        seeds[key] = owner
    valid_owners = {owner for owner, count in seed_counts.items() if count >= 4}
    seeds = {key: owner for key, owner in seeds.items() if owner in valid_owners}
    if not seeds:
        return None

    # Every solid core pixel must be claimable by at least one seeded owner.
    # A core island visible only to unseeded/identical ROIs remains ambiguous.
    if any(not (membership[key] & valid_owners) for key in core):
        return None

    distance = {}
    labels = {}
    pending = deque()
    for key, owner in seeds.items():
        distance[key] = 0
        labels[key] = {owner}
        pending.append(key)

    while pending:
        key = pending.popleft()
        next_distance = distance[key] + 1
        for next_key in _adjacent(key, width, height):
            if next_key not in pixel_set:
                continue
            allowed = {owner for owner in labels[key]
                       if owner in membership[next_key]}
            if not allowed:
                continue
            if next_key not in distance:
                distance[next_key] = next_distance
                labels[next_key] = set(allowed)
                pending.append(next_key)
            elif distance[next_key] == next_distance:
                merged = labels[next_key] | allowed
                if merged != labels[next_key]:
                    labels[next_key] = merged
                    pending.append(next_key)

    centers = {
        owner: ((rows[owner]["_bbox"][0] + rows[owner]["_bbox"][2]) / 2.0,
                (rows[owner]["_bbox"][1] + rows[owner]["_bbox"][3]) / 2.0)
        for owner in valid_owners
    }
    assigned = {owner: [] for owner in valid_owners}
    residual = []
    for key in pixels:
        candidates = labels.get(key, set()) & membership[key]
        if candidates:
            x, y = key % width, key // width
            # Equal geodesic distance is resolved by distance to ROI center;
            # stable owner index is a deterministic final tie-break.
            owner = min(
                candidates,
                key=lambda item: ((x-centers[item][0])**2 +
                                  (y-centers[item][1])**2, item)
            )
            assigned[owner].append(key)
        else:
            residual.append(key)

    if any(alpha.getpixel((key % width, key // width)) > SOFT_BRIDGE_ALPHA
           for key in residual):
        return None
    assigned = {owner: owned for owner, owned in assigned.items() if owned}
    if not assigned:
        return None
    return assigned, residual

def prove_overlap_ownership(source, rows, conflicting_ids, diagnostics=None):
    """Return (verified per-ROI source-alpha masks, audit).

    First use the original exclusive connected-component proof. If that fails,
    a second bounded pass may split only low-alpha bridges between independently
    proven high-alpha core islands. Solid/ambiguous glyph collisions stay HOLD.
    Coordinates are in readable DDS orientation.
    """
    if diagnostics is not None:
        diagnostics.clear()
    if not conflicting_ids:
        return {}, {"proven": [], "ambiguous": [], "reason": "NO_CONFLICTS"}
    alpha = source.getchannel("A")
    width, height = source.size
    membership = {}
    for idx, row in enumerate(rows):
        x0, y0, x1, y1 = row["_bbox"]
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            return {}, {"proven": [], "ambiguous": sorted(conflicting_ids),
                        "reason": "ROI_OUT_OF_NATIVE_BOUNDS"}
        clip = alpha.crop((x0, y0, x1, y1))
        span = x1 - x0
        for offset, opacity in enumerate(clip.getdata()):
            if opacity <= COSMETIC_FRINGE_ALPHA:
                continue
            key = (y0 + offset // span) * width + (x0 + offset % span)
            membership.setdefault(key, set()).add(idx)
            if len(membership) > MAX_SOURCE_ALPHA_PIXELS:
                return {}, {"proven": [], "ambiguous": sorted(conflicting_ids),
                            "reason": "SOURCE_ALPHA_PROOF_MEMORY_BUDGET"}

    unresolved = set()
    pixels_owned = {i: [] for i, r in enumerate(rows)
                    if r["roi_id"] in conflicting_ids}
    visited = set()
    components = 0
    partitioned_components = 0
    cosmetic_residual_pixels = 0
    unowned_pixels = []

    for first in membership:
        if first in visited:
            continue
        components += 1
        pending = deque([first])
        visited.add(first)
        pixels = []
        exclusive_anchors = set()
        touched = set()
        while pending:
            key = pending.popleft()
            pixels.append(key)
            members = membership[key]
            touched.update(members)
            if len(members) == 1:
                exclusive_anchors.update(members)
            for next_key in _adjacent(key, width, height):
                if next_key in membership and next_key not in visited:
                    visited.add(next_key)
                    pending.append(next_key)

        # Preserve the original strongest proof unchanged.
        if len(exclusive_anchors) == 1:
            owner = next(iter(exclusive_anchors))
            box = rows[owner]["_bbox"]
            if owner in pixels_owned and all(
                box[0] <= key % width < box[2] and
                box[1] <= key // width < box[3]
                for key in pixels
            ):
                pixels_owned[owner].extend(pixels)
                continue

        # New bounded rescue: split only when high-alpha core islands prove
        # their owners and every unassigned boundary pixel is cosmetic.
        partition = _core_partition(
            alpha, membership, pixels, rows, pixels_owned, width, height
        )
        if partition is not None:
            assigned, residual = partition
            for owner, owned in assigned.items():
                pixels_owned[owner].extend(owned)
            unowned_pixels.extend(residual)
            cosmetic_residual_pixels += len(residual)
            partitioned_components += 1
            continue

        unresolved.update(touched)
        unowned_pixels.extend(pixels)

    masks = {}
    for idx, pixels in pixels_owned.items():
        rid = rows[idx]["roi_id"]
        if idx in unresolved or not pixels:
            unresolved.add(idx)
            continue
        mask = Image.new("L", (width, height), 0)
        out = mask.load()
        for key in pixels:
            out[key % width, key // width] = 255
        masks[rid] = mask

    if diagnostics is not None:
        partial_masks = {}
        for idx, pixels in pixels_owned.items():
            if not pixels:
                continue
            segment = Image.new("L", (width, height), 0)
            dst = segment.load()
            for key in pixels:
                dst[key % width, key // width] = 255
            partial_masks[rows[idx]["roi_id"]] = segment
        ambiguous = Image.new("L", (width, height), 0)
        dst = ambiguous.load()
        for key in unowned_pixels:
            dst[key % width, key // width] = 255
        diagnostics.update({
            "partial_owned_masks": partial_masks,
            "ambiguous_native_mask": ambiguous,
            "partial_proof_not_assembly_approval": True,
            "core_partitioned_components": partitioned_components,
            "cosmetic_residual_pixels": cosmetic_residual_pixels,
        })

    return masks, {
        "proven": sorted(masks),
        "ambiguous": sorted(rows[i]["roi_id"] for i in unresolved
                            if rows[i]["roi_id"] in conflicting_ids),
        "component_count": components,
        "core_partitioned_components": partitioned_components,
        "cosmetic_residual_pixels": cosmetic_residual_pixels,
        "core_alpha_threshold": CORE_ALPHA,
        "soft_bridge_alpha_ceiling": SOFT_BRIDGE_ALPHA,
        "source_alpha_pixels": len(membership),
        "reason": "EXCLUSIVE_OR_CORE_PARTITION_OVERLAP_PROOF_TEST_ONLY",
    }