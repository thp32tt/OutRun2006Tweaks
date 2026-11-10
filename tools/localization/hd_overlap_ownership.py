"""Fail-closed overlap ownership proof for existing HD A/B PNG reuse.

An overlapping metadata rectangle is not proof that two labels own the
same source pixels. Connected source-alpha components may be assigned ONLY
if they have exactly one exclusive ROI anchor. Ambiguity stays HOLD.
This never creates Korean glyphs, approves QA, or writes game assets.
"""
from collections import deque
from PIL import Image

MAX_SOURCE_ALPHA_PIXELS = 1500000
# Only near-invisible antialias pixels are excluded from component anchoring.
COSMETIC_FRINGE_ALPHA = 8


def prove_overlap_ownership(source, rows, conflicting_ids):
    """Return (verified per-ROI source-alpha masks, audit).

    All non-coarse rows must be passed, including rows without candidate PNGs.
    A component's exclusive anchor is a native source pixel included in
    exactly one ROI rectangle. Components with zero or multiple exclusive
    anchors are ambiguous. An owned component cannot extend outside the
    claimed owner's ROI. Coordinates are in readable DDS orientation.
    """
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
            x, y = key % width, key // width
            for dx, dy in ((-1, -1), (0, -1), (1, -1),
                           (-1, 0), (1, 0),
                           (-1, 1), (0, 1), (1, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    next_key = ny * width + nx
                    if next_key in membership and next_key not in visited:
                        visited.add(next_key)
                        pending.append(next_key)
        if len(exclusive_anchors) != 1:
            unresolved.update(touched)
            continue
        owner = next(iter(exclusive_anchors))
        box = rows[owner]["_bbox"]
        if any(not (box[0] <= key % width < box[2] and
                    box[1] <= key // width < box[3]) for key in pixels):
            unresolved.update(touched)
            continue
        if owner in pixels_owned:
            pixels_owned[owner].extend(pixels)
    masks = {}
    for idx, pixels in pixels_owned.items():
        rid = rows[idx]["roi_id"]
        if idx in unresolved or not pixels:
            unresolved.add(idx)
            continue
        mask = Image.new("L", (width, height), 0)
        out = mask.load()
        for key in pixels:
            x, y = key % width, key // width
            out[x, y] = 255
        # A safe row must own every source-alpha pixel it is about to erase;
        # any foreign pixels remain untouched by the mask in strict assembler.
        masks[rid] = mask
    return masks, {
        "proven": sorted(masks),
        "ambiguous": sorted(rows[i]["roi_id"] for i in unresolved
                            if rows[i]["roi_id"] in conflicting_ids),
        "component_count": components,
        "source_alpha_pixels": len(membership),
        "reason": "EXCLUSIVE_CONNECTED_COMPONENT_ANCHOR_PROOF_TEST_ONLY",
    }
