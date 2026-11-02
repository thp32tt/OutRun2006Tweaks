#!/usr/bin/env python3
"""Second, ink-aware placement pass for unresolved approved ROI (TEST_ONLY).

Unlike the first pass, this protects the exact tight rendered glyph bounds,
not the often grossly oversized source-ROI rectangles. It never changes any
previously rendered glyph pixel and never draws outside the held source ROI.
This may leave original English pixels and is NOT an in-game approval.
"""
from __future__ import annotations
import numpy as np
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location(
    "offline_overlap",Path(__file__).resolve().parent/"offline_overlap_resolver.py")
geometry=importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def _intersect(a, b):
    x0,y0=max(a[0],b[0]),max(a[1],b[1])
    x1,y1=min(a[2],b[2]),min(a[3],b[3])
    return max(0,x1-x0)*max(0,y1-y0)


def _near_duplicate(a, b, threshold=0.8):
    ia=_intersect(a,b)
    if not ia:return False
    aa=(a[2]-a[0])*(a[3]-a[1])
    ab=(b[2]-b[0])*(b[3]-b[1])
    return ia/(aa+ab-ia)>=threshold


def _glyph_bounds(row, source_pixels, make_glyph, fontfile, *, padding=3):
    placement=row.get("placement_bbox") or row["bbox"]
    a,b,c,d=placement
    reference=source_pixels[b:d,a:c]
    glyph=make_glyph(row["korean"],c-a,d-b,fontfile,reference)
    ink=glyph.getchannel("A").getbbox()
    if not ink:
        raise ValueError("RENDER_EMPTY")
    x0=max(a,a+ink[0]-padding)
    y0=max(b,b+ink[1]-padding)
    x1=min(c,a+ink[2]+padding)
    y1=min(d,b+ink[3]+padding)
    return (x0,y0,x1,y1)


def bounded_free_rectangles(box, occupied, *, limit=32):
    """Keep only a safe subset of free patches to bound N100 resource use."""
    free=[tuple(box)]
    for block in occupied:
        expanded=[]
        for part in free:
            expanded.extend(geometry.subtract_rectangles(part,[block]))
        if len(expanded)>limit:
            expanded.sort(key=lambda q:(q[2]-q[0])*(q[3]-q[1]),reverse=True)
            expanded=expanded[:limit]
        free=expanded
        if not free:break
    return free


def resolve(source, initial, rows, painted, held, *,
            make_glyph, fontfile, min_side=14, min_area_ratio=0.012):
    h,w=source.height,source.width
    original=np.asarray(source)
    out=initial.copy()
    accepted=list(painted)
    still=[]
    represented=[]
    by_id={r.get("id"):r for r in rows if isinstance(r,dict)}
    protected_rects=[]
    shield=np.zeros((h,w),dtype=bool)
    for p in accepted:
        rect=_glyph_bounds(p,original,make_glyph,fontfile)
        protected_rects.append(rect)
        a,b,c,d=rect
        shield[b:d,a:c]=True
    first_protected_rects=list(protected_rects)
    initial_pixels=np.asarray(initial)
    for failure in held:
        if failure.get("reason") not in ("OVERLAP_NO_READABLE_FREE_RECT","OVERLAP_FULLY_COVERED","OVERLAPPING_ROI"):
            still.append(failure)
            continue
        row=by_id.get(failure.get("id"))
        if row is None:
            still.append({**failure,"reason":"INK_SOURCE_NOT_FOUND"})
            continue
        box=row.get("bbox_xyxy")
        if not isinstance(box,list) or len(box)!=4 or any(type(i) is not int for i in box):
            still.append({**failure,"reason":"INK_BAD_BBOX"})
            continue
        a,b,c,d=box
        if not (0<=a<c<=w and 0<=b<d<=h):
            still.append({**failure,"reason":"INK_BAD_BOUNDS"})
            continue
        # Candidate OCR annotations for essentially the SAME text and box
        # do not require a second copy of the translation.
        duplicate=next((p for p in accepted if
                        p.get("korean")==row.get("korean") and
                        _near_duplicate(box,p["bbox"])),None)
        if duplicate is not None:
            represented.append({"id":row["id"],"matched_id":duplicate["id"],
                                "reason":"DUPLICATE_TRANSLATION_REPRESENTED"})
            continue
        free=bounded_free_rectangles(box,protected_rects)
        area=(c-a)*(d-b)
        placements=sorted(free,key=lambda q:(
            (q[2]-q[0])*(q[3]-q[1]),
            min(q[2]-q[0],q[3]-q[1]),-q[1],-q[0]),reverse=True)
        selected=None
        for x0,y0,x1,y1 in placements[:8]:
            # Clip oversize empty atlas regions before creating glyph images.
            if x1-x0>1600:
                offset=(x1-x0-1600)//2
                x0+=offset;x1=x0+1600
            if y1-y0>600:
                offset=(y1-y0-600)//2
                y0+=offset;y1=y0+600
            bw,bh=x1-x0,y1-y0
            if min(bw,bh)<min_side or bw*bh < area*min_area_ratio:
                continue
            try:
                glyph=make_glyph(row["korean"],bw,bh,fontfile,
                                 original[y0:y1,x0:x1])
            except (ValueError,OSError,OverflowError):
                continue
            ink=glyph.getchannel("A").getbbox()
            if not ink:continue
            ix0,iy0,ix1,iy1=x0+ink[0],y0+ink[1],x0+ink[2],y0+ink[3]
            # Strictly require glyph pixels outside existing protected ink.
            if np.any(shield[iy0:iy1,ix0:ix1]):
                continue
            selected=(x0,y0,x1,y1,glyph,ink)
            break
        if selected is None:
            still.append({**failure,"reason":"INK_AWARE_NO_READABLE_SPACE"})
            continue
        x0,y0,x1,y1,glyph,ink=selected
        # Clear the selected sub-rectangle only, not the larger source ROI.
        # The selected rectangle never intersects an earlier ink shield.
        out.paste((0,0,0,0),(x0,y0,x1,y1))
        out.alpha_composite(glyph,(x0,y0))
        ix0,iy0=max(x0,x0+ink[0]-3),max(y0,y0+ink[1]-3)
        ix1,iy1=min(x1,x0+ink[2]+3),min(y1,y0+ink[3]+3)
        protected_rects.append((ix0,iy0,ix1,iy1))
        shield[iy0:iy1,ix0:ix1]=True
        accepted.append({"id":row["id"],"english":row["english"],
                         "korean":row["korean"],"bbox":box,
                         "placement_bbox":[x0,y0,x1,y1],
                         "resolution":"INK_AWARE_RELOCATE",
                         "original_english_may_remain":True})
    final=np.asarray(out)
    # Verify the initial shield including all previously accepted glyphs.
    first_shield=np.zeros((h,w),dtype=bool)
    for a,b,c,d in first_protected_rects:
        first_shield[b:d,a:c]=True
    if not np.array_equal(final[first_shield],initial_pixels[first_shield]):
        raise AssertionError("PREVIOUSLY_ACCEPTED_GLYPH_MODIFIED")
    allowed=np.zeros((h,w),dtype=bool)
    for p in accepted:
        a,b,c,d=p["bbox"]
        allowed[b:d,a:c]=True
    change=np.any(original!=final,axis=2)
    outside=int(np.count_nonzero(change&~allowed))
    if outside:
        raise AssertionError("OUTSIDE_APPROVED_ROI_CHANGED")
    return out,accepted,still,represented,int(np.count_nonzero(change)),outside