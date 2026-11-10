"""Deterministic salvage for existing A/B ImageGen PNGs.

No fonts and no new glyph generation. Existing pixels may only be padded,
reflowed in reading order, or downscaled later into source-native HD boxes.
Every salvage action remains TEST_ONLY and requires visual QA.
"""
from itertools import combinations
from PIL import Image, ImageChops, ImageFilter, ImageOps

ALPHA_THRESHOLD = 16
# Explicit user-approved visual tolerance: discard only barely-visible
# source/candidate antialias fringe (<=8 of 255). Core alpha remains protected.
COSMETIC_FRINGE_ALPHA = 8
MIN_COLUMN_GAP = 2


def pad_candidate_edge(image, margin=2):
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    if not box:
        return image, []
    touched = min(box[0], box[1], image.width-box[2], image.height-box[3]) < margin
    if not touched:
        return image, []
    pad = margin + 2
    return ImageOps.expand(image, border=pad, fill=(0,0,0,0)), [
        "PAD_EXISTING_CANDIDATE_EDGE_VISUAL_QA_REQUIRED"
    ]


def native_alpha_crosses_box_edge(alpha, box, side):
    """Require a REAL 8-connected native ink crossing before an edge HOLD.

    An unrelated neighbor farther along the rectangle is not a continuation
    of the source text. Preserve even the faintest nonzero source alpha.
    """
    x0, y0, x1, y1 = box
    width, height = alpha.size
    if side in ("LEFT", "RIGHT"):
        inside = x0 if side == "LEFT" else x1 - 1
        outside = x0 - 1 if side == "LEFT" else x1
        if not 0 <= outside < width:
            return False
        for y in range(y0, y1):
            if alpha.getpixel((inside, y)) > COSMETIC_FRINGE_ALPHA and any(
                alpha.getpixel((outside, yy)) > COSMETIC_FRINGE_ALPHA
                for yy in (y - 1, y, y + 1) if 0 <= yy < height
            ):
                return True
    else:
        inside = y0 if side == "TOP" else y1 - 1
        outside = y0 - 1 if side == "TOP" else y1
        if not 0 <= outside < height:
            return False
        for x in range(x0, x1):
            if alpha.getpixel((x, inside)) > COSMETIC_FRINGE_ALPHA and any(
                alpha.getpixel((xx, outside)) > COSMETIC_FRINGE_ALPHA
                for xx in (x - 1, x, x + 1) if 0 <= xx < width
            ):
                return True
    return False


def translated_touches_external_native_ink(source, box, rendered):
    """Protect native ink just OUTSIDE a tight ROI from new Korean pixels.

    Restrict the calculation to a 1px halo around the source ROI. The
    caller must still prove source ownership and check every other ROI.
    """
    x0, y0, x1, y1 = box
    region = (max(0, x0 - 1), max(0, y0 - 1),
              min(source.width, x1 + 1), min(source.height, y1 + 1))
    rx0, ry0, rx1, ry1 = region
    protected = source.getchannel("A").crop(region).point(
        lambda n: n if n > COSMETIC_FRINGE_ALPHA else 0)
    protected.paste(0, (x0 - rx0, y0 - ry0, x1 - rx0, y1 - ry0))
    halo = protected.filter(ImageFilter.MaxFilter(3))
    for glyph, left, top in rendered:
        dest = (left, top, left + glyph.width, top + glyph.height)
        intersection = (max(rx0, dest[0]), max(ry0, dest[1]),
                        min(rx1, dest[2]), min(ry1, dest[3]))
        a, b, c, d = intersection
        if a >= c or b >= d:
            continue
        visible = glyph.getchannel("A").crop(
            (a - left, b - top, c - left, d - top))
        neighbor = halo.crop((a - rx0, b - ry0, c - rx0, d - ry0))
        if ImageChops.multiply(visible, neighbor).getbbox():
            return True
    return False


def prove_source_edge_clear(source, box, extent, margin=2):
    """Allow a tight ROI only when immediate source pixels outside it are transparent."""
    x0,y0,x1,y1 = box
    touched = []
    if extent[0] < margin: touched.append("LEFT")
    if extent[1] < margin: touched.append("TOP")
    if (x1-x0)-extent[2] < margin: touched.append("RIGHT")
    if (y1-y0)-extent[3] < margin: touched.append("BOTTOM")
    if not touched:
        return []
    strips = {
        "LEFT": (x0-margin,y0,x0,y1) if x0 >= margin else None,
        "TOP": (x0,y0-margin,x1,y0) if y0 >= margin else None,
        "RIGHT": (x1,y0,x1+margin,y1) if x1+margin <= source.width else None,
        "BOTTOM": (x0,y1,x1,y1+margin) if y1+margin <= source.height else None,
    }
    alpha = source.getchannel("A").point(
        lambda n: n if n > COSMETIC_FRINGE_ALPHA else 0)
    edge_rules = {
        "LEFT": x0 == 0,
        "TOP": y0 == 0,
        "RIGHT": x1 == source.width,
        "BOTTOM": y1 == source.height,
    }
    actions = []
    for side in touched:
        strip = strips[side]
        if strip is None:
            # No source pixel exists beyond a PHYSICAL atlas boundary.
            # This is NOT permission to clip translated ink: the caller
            # must prove the new glyph/effect stays inset >= margin.
            if not edge_rules[side]:
                raise ValueError("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")
            actions.append("SOURCE_NATIVE_ATLAS_" + side + "_EDGE_INSET_REQUIRED")
        elif native_alpha_crosses_box_edge(alpha, box, side):
            # This also checks diagonal 8-connected pixels at ROI CORNERS:
            # the rectangular strips alone exclude those outside corners.
            raise ValueError("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")
        elif alpha.crop(strip).getbbox() is not None:
            # Nearby native alpha without a real connection is some other
            # label or art. A subsequent translated-ink halo guard protects it.
            actions.append("SOURCE_EDGE_DISJOINT_EXTERNAL_ALPHA_PROOF")
        else:
            actions.append("SOURCE_EDGE_CLEAR_NEIGHBOR_PROOF")
    return actions


def _column_components(line_image):
    alpha = line_image.getchannel("A").point(lambda n: 255 if n >= ALPHA_THRESHOLD else 0)
    active = []
    for x in range(alpha.width):
        if alpha.crop((x,0,x+1,alpha.height)).getbbox() is not None:
            active.append(x)
    if not active:
        return []
    ranges=[]
    start=prev=active[0]
    for x in active[1:]:
        if x-prev >= MIN_COLUMN_GAP+1:
            ranges.append((start,prev+1))
            start=x
        prev=x
    ranges.append((start,prev+1))
    parts=[]
    for x0,x1 in ranges:
        crop=line_image.crop((x0,0,x1,line_image.height))
        b=crop.getchannel("A").getbbox()
        if b:
            parts.append(crop.crop(b))
    return parts


def _merge_horizontal(images, gap=2):
    images=[im for im in images if im.getchannel("A").getbbox()]
    if not images:
        raise ValueError("QA_CANDIDATE_INVISIBLE")
    width=sum(im.width for im in images)+gap*(len(images)-1)
    height=max(im.height for im in images)
    out=Image.new("RGBA",(width,height),(0,0,0,0))
    x=0
    for im in images:
        y=(height-im.height)//2
        out.alpha_composite(im,(x,y))
        x += im.width+gap
    return out


def _best_partition(parts, target_widths):
    n=len(parts); k=len(target_widths)
    if k == 1:
        return [parts]
    if n < k:
        raise ValueError("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED")
    total_target=max(1,sum(target_widths))
    best=None
    for cuts in combinations(range(1,n),k-1):
        bounds=(0,)+cuts+(n,)
        groups=[parts[bounds[i]:bounds[i+1]] for i in range(k)]
        widths=[sum(p.width for p in g)+2*(len(g)-1) for g in groups]
        total=max(1,sum(widths))
        cost=sum(((widths[i]/total)-(target_widths[i]/total_target))**2 for i in range(k))
        # Deterministic tie-break: earlier cut tuple wins.
        key=(round(cost,12),cuts)
        if best is None or key < best[0]:
            best=(key,groups)
    return best[1]


def candidate_lines(candidate, source_boxes, line_fn):
    """Return source-line-count pixel rows using only existing candidate pixels."""
    detected=line_fn(candidate.getchannel("A"))
    desired=len(source_boxes)
    if not detected:
        raise ValueError("QA_CANDIDATE_INVISIBLE")
    if len(detected) == desired:
        return [candidate.crop(b) for b in detected], len(detected), []

    parts=[]
    for line_box in detected:
        line=candidate.crop(line_box)
        split=_column_components(line)
        parts.extend(split if split else [line])
    if len(parts) < desired:
        raise ValueError("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED")

    groups=_best_partition(parts,[b[2]-b[0] for b in source_boxes])
    lines=[_merge_horizontal(group) for group in groups]
    if len(lines) != desired:
        raise ValueError("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED")
    return lines, len(detected), [
        f"REFLOW_EXISTING_CANDIDATE_{len(detected)}_TO_{desired}_LINES_VISUAL_QA_REQUIRED"
    ]
