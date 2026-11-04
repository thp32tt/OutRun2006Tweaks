"""Deterministic salvage for existing A/B ImageGen PNGs.

No fonts and no new glyph generation. Existing pixels may only be padded,
reflowed in reading order, or downscaled later into source-native HD boxes.
Every salvage action remains TEST_ONLY and requires visual QA.
"""
from itertools import combinations
from PIL import Image, ImageOps

ALPHA_THRESHOLD = 16
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
    alpha = source.getchannel("A")
    for side in touched:
        strip = strips[side]
        if strip is None or alpha.crop(strip).getbbox() is not None:
            raise ValueError("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")
    return ["SOURCE_EDGE_CLEAR_NEIGHBOR_PROOF"]


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
