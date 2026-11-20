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
    """Partition one visible-alpha component by disconnected high-alpha cores.

    Returns (assigned, residual) on a bounded cosmetic rescue, else None.

    Every high-alpha core island must have exactly one exclusive ROI anchor and
    must fit completely inside that owner's ROI. Low-alpha bridge pixels are
    assigned by nearest-core geodesic distance. Equal-distance or out-of-owner
    pixels may remain only when alpha <= SOFT_BRIDGE_ALPHA.
    """
    pixel_set = set(pixels)
    core = {
        key for key in pixels
        if alpha.getpixel((key % width, key // width)) >= CORE_ALPHA
    }
    if not core:
        return None

    core_seen = set()
    seeds = {}
    owners_seen = set()
    for first in core:
        if first in core_seen:
            continue
        pending = deque([first])
        core_seen.add(first)
        component = []
        exclusive = set()
        while pending:
            key = pending.popleft()
            component.append(key)
            members = membership[key]
            if len(members) == 1:
                exclusive.update(members)
            for next_key in _adjacent(key, width, height):
                if next_key in core and next_key not in core_seen:
                    core_seen.add(next_key)
                    pending.append(next_key)
        if len(exclusive) != 1:
            return None
        owner = next(iter(exclusive))
        if owner not in pixels_owned:
            return None
        # A core island may overlap another metadata ROI, but the chosen owner
        # must contain the complete solid glyph core.
        if any(owner not in membership[key] for key in component):
            return None
        owners_seen.add(owner)
        for key in component:
            seeds.setdefault(key, set()).add(owner)

    # If two owners share the exact same core seed pixel, ownership is not
    # provable; do not invent a split.
    if any(len(v) != 1 for v in seeds.values()):
        return None

    distance = {}
    labels = {}
    pending = deque()
    for key, owner_set in seeds.items():
        distance[key] = 0
        labels[key] = set(owner_set)
        pending.append(key)

    while pending:
        key = pending.popleft()
        next_distance = distance[key] + 1
        for next_key in _adjacent(key, width, height):
            if next_key not in pixel_set:
                continue
            if next_key not in distance:
                distance[next_key] = next_distance
                labels[next_key] = set(labels[key])
                pending.append(next_key)
            elif distance[next_key] == next_distance:
                merged = labels[next_key] | labels[key]
                if merged != labels[next_key]:
                    labels[next_key] = merged
                    pending.append(next_key)

    assigned = {owner: [] for owner in owners_seen}
    residual = []
    for key in pixels:
        owner_set = labels.get(key, set())
        if len(owner_set) == 1:
            owner = next(iter(owner_set))
            # Never erase outside the chosen row's actual metadata ROI.
            if owner in membership[key]:
                assigned[owner].append(key)
                continue
        residual.append(key)

    # Cosmetic bridge/tie leftovers are allowed to remain in the source.
    # Any stronger unassigned pixel means this is a real ambiguous collision.
    if any(alpha.getpixel((key % width, key // width)) > SOFT_BRIDGE_ALPHA
           for key in residual):
        return None
    if any(not owned for owned in assigned.values()):
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