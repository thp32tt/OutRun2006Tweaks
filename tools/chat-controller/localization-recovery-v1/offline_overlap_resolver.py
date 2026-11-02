#!/usr/bin/env python3
"""Conservative deterministic non-OCR overlap trimming for TEST_ONLY DDS.

An overlapping label is re-rendered in a single available rectangle fully
inside its approved ROI. Previously painted labels are never overwritten.
If no readable rectangle remains, retain HOLD instead of cutting glyphs.
"""
from __future__ import annotations
import numpy as np

def subtract_rectangles(box, occupied):
    free=[tuple(box)]
    for block in occupied:
        next_free=[]
        ox0,oy0,ox1,oy1=block
        for x0,y0,x1,y1 in free:
            ix0,iy0=max(x0,ox0),max(y0,oy0)
            ix1,iy1=min(x1,ox1),min(y1,oy1)
            if ix0>=ix1 or iy0>=iy1:
                next_free.append((x0,y0,x1,y1));continue
            if y0<iy0: next_free.append((x0,y0,x1,iy0))
            if iy1<y1: next_free.append((x0,iy1,x1,y1))
            if x0<ix0: next_free.append((x0,iy0,ix0,iy1))
            if ix1<x1: next_free.append((ix1,iy0,x1,iy1))
        free=next_free
        if not free:break
    return free


def resolve(source, initial, rows, painted, held, *, make_glyph,
            fontfile, max_opaque_fraction=1.0, min_area_ratio=0.12,
            min_side=16):
    """Resolve only previously held OVERLAPPING_ROI rows; no original edits.

    Returns (new_rgba, accepted, still_held, changed_pixels, outside_pixels).
    """
    before=np.asarray(source)
    out=initial.copy()
    ids={row["id"]:row for row in rows if isinstance(row,dict) and "id" in row}
    accepted=list(painted)
    still=[]
    reserved=[tuple(p["bbox"]) for p in accepted]
    h,w=before.shape[:2]
    for record in held:
        if record.get("reason")!="OVERLAPPING_ROI":
            still.append(record);continue
        item=ids.get(record.get("id"))
        if item is None:
            still.append({**record,"reason":"OVERLAP_SOURCE_ROW_MISSING"});continue
        box=item.get("bbox_xyxy")
        if not isinstance(box,list) or len(box)!=4 or not all(type(v) is int for v in box):
            still.append({**record,"reason":"OVERLAP_INVALID_BBOX"});continue
        x0,y0,x1,y1=box
        if not (0<=x0<x1<=w and 0<=y0<y1<=h):
            still.append({**record,"reason":"OVERLAP_OUT_OF_BOUNDS"});continue
        free=subtract_rectangles(box,reserved)
        if not free:
            still.append({**record,"reason":"OVERLAP_FULLY_COVERED"});continue
        full_area=(x1-x0)*(y1-y0)
        placements=sorted(free,key=lambda r:((r[2]-r[0])*(r[3]-r[1]),
                                        min(r[2]-r[0],r[3]-r[1]),-r[1],-r[0]),reverse=True)
        chosen=None;glyph=None;alpha=0
        for a,b,c,d in placements:
            ww,hh=c-a,d-b
            if min(ww,hh)<min_side or ww*hh<min_area_ratio*full_area:
                continue
            piece=before[b:d,a:c]
            opacity=float(np.count_nonzero(piece[:,:,3]>=16))/piece[:,:,3].size
            if opacity>max_opaque_fraction:continue
            try:
                render=make_glyph(item["korean"],ww,hh,fontfile,piece)
            except (ValueError,OSError,OverflowError):
                continue
            # Entire phrase must fit in ONE rectangle, not be cropped.
            if not render.getchannel("A").getbbox():continue
            chosen=(a,b,c,d);glyph=render;alpha=opacity;break
        if chosen is None:
            still.append({**record,"reason":"OVERLAP_NO_READABLE_FREE_RECT"});continue
        # Clear all unoccupied pieces of this ROI. This removes English
        # remnants without touching a previously translated label.
        for a,b,c,d in free:
            out.paste((0,0,0,0),(a,b,c,d))
        out.alpha_composite(glyph,chosen[:2])
        reserved.append(tuple(box))
        accepted.append({"id":item["id"],"english":item["english"],
                         "korean":item["korean"],"bbox":box,
                         "placement_bbox":list(chosen),"opaque":round(alpha,5),
                         "resolution":"TRIM_TO_FREE_RECT"})
    after=np.asarray(out)
    allowed=np.zeros((h,w),dtype=bool)
    for x0,y0,x1,y1 in reserved:allowed[y0:y1,x0:x1]=True
    changed=np.any(before!=after,axis=2)
    outside=int(np.count_nonzero(changed&~allowed))
    if outside:raise AssertionError("OUTSIDE_APPROVED_ROI_CHANGED")
    return out,accepted,still,int(np.count_nonzero(changed)),outside