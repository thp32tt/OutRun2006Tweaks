"""Conservative flat opaque-panel cleanplate lane, TEST_ONLY.

Only exact uniform 3-pixel opaque border, one isolated ROI, one to three
native ink bands and no other ROI intersection. Source art is not inferred
from a complex background; leave such crops HOLD. Rebuild from native source
RGBA32 mip1 and verify every encoded pixel. Never touch BC3 mip chains here.
"""
from __future__ import annotations
import hashlib,math,struct
from PIL import Image,ImageChops,ImageOps
import hd_strict_qa as strict
from hd_existing_candidate_salvage import candidate_lines

def diff_mask(a,b):
    d=ImageChops.difference(a,b)
    out=d.getchannel(0)
    for ch in d.split()[1:]:out=ImageChops.lighter(out,ch)
    return out.point(lambda n:255 if n else 0)

def flat_source_mask(crop):
    w,h=crop.size
    if w<12 or h<12:raise ValueError("FLAT_SOURCE_SMALL")
    color=crop.getpixel((0,0))
    if color[3]!=255:raise ValueError("FLAT_SOURCE_NOT_OPAQUE")
    # Source pixels are exact: no color tolerance which might delete a frame.
    bg=Image.new("RGBA",crop.size,color)
    mask=diff_mask(crop,bg)
    if any(mask.crop(b).getbbox() for b in ((0,0,w,3),(0,h-3,w,h),(0,0,3,h),(w-3,0,w,h))):
        raise ValueError("FLAT_SOURCE_BACKGROUND_NOT_UNIFORM")
    if mask.getbbox() is None:raise ValueError("FLAT_SOURCE_NO_INK")
    occupancy=mask.histogram()[255]/(w*h)
    if not 0.005<=occupancy<=0.48:raise ValueError("FLAT_SOURCE_INK_OCCUPANCY")
    lines,actions=strict.source_effect_band_lines(mask)
    if not 1<=len(lines)<=3 or any(min(b[2]-b[0],b[3]-b[1])<8 for b in lines):
        raise ValueError("FLAT_SOURCE_INK_LAYOUT_UNVERIFIED")
    # Any isolated photo/art could still look like a letter band. Keep this
    # as separate TEST_ONLY evidence and require the subsequent visual model.
    return bg,mask,lines,occupancy,actions

def overlap(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]

def trial(source,clean,result,row,raw_candidate,fit,candidate_guard):
    x0,y0,x1,y1=row["_bbox"]
    box=(x0,y0,x1,y1)
    if not 0<=x0<x1<=source.width or not 0<=y0<y1<=source.height:
        raise ValueError("FLAT_SOURCE_BOUNDS")
    crop=source.crop(box)
    bg,mask,lines,occ,actions=flat_source_mask(crop)
    cand,ca=candidate_guard(raw_candidate)
    glyphs,detected,reflow=candidate_lines(cand,lines,strict.alpha_lines)
    if len(glyphs)!=len(lines):raise ValueError("FLAT_SOURCE_LINE_COUNT")
    placements=[];ink=Image.new("RGBA",crop.size)
    for src,glyph in zip(lines,glyphs):
        fitted=fit(glyph,src)
        x=src[0]+((src[2]-src[0])-fitted.width)//2
        y=src[1]+((src[3]-src[1])-fitted.height)//2
        ink.alpha_composite(fitted,(x,y))
        placements.append([x0+x,y0+y,x0+x+fitted.width,y0+y+fitted.height])
    cleaned=crop.copy()
    cleaned.paste(bg,(0,0),mask)
    if diff_mask(cleaned,bg).getbbox():raise ValueError("FLAT_SOURCE_CLEAN_NOT_EXACT")
    composed=Image.alpha_composite(cleaned,ink)
    # No pixels beyond source mask and actual Korean alpha may change.
    allowed=ImageChops.lighter(mask,ink.getchannel("A").point(lambda n:255 if n else 0))
    if ImageChops.multiply(diff_mask(crop,composed),ImageOps.invert(allowed)).getbbox():
        raise ValueError("FLAT_SOURCE_PROTECTED_PIXEL_CHANGED")
    clean.paste(cleaned,box);result.paste(composed,box)
    return {"roi_id":row["roi_id"],"english":row["english"],"korean":row["korean"],"roi":list(box),
            "original_native_lines":[[x0+a,y0+b,x0+c,y0+d] for a,b,c,d in lines],
            "translated_native_lines":placements,
            "source_alpha_occupancy":round(occ,5),"original_line_count":len(lines),
            "translated_line_count":len(placements),"candidate_detected_line_count":detected,
            "candidate_sha256":hashlib.sha256(raw_candidate).hexdigest(),
            "clean_type":"EXACT_UNIFORM_OPAQUE_BORDER_BACKGROUND_TEST_ONLY",
            "auto_salvage":actions+ca+reflow+["FLAT_PANEL_EXACT_BACKGROUND_VISUAL_REVIEW_REQUIRED"],
            "qa_gate":"FLAT_PANEL_TEST_ONLY_C1_C3_GAME_UNTESTED"}

def add_flat_repairs(raw,source,clean,result,painted,holds,rows,root,orientation,fit,candidate_guard,decode):
    # Original format only, no compressed/multi-mip conversion.
    if (raw[84:88]!=b"\0"*4 or struct.unpack_from("<I",raw,28)[0]!=1
        or len(raw)!=128+source.width*source.height*4):
        return None
    if not any(h["reason"]=="QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT" for h in holds):return None
    # The existing native decoder enforces pixel format, shape and header.
    try:decode(raw)
    except ValueError:return None
    clean=clean.copy();result=result.copy()
    accepted=list(painted);remaining=[]
    byid={r["roi_id"]:r for r in rows}
    for h in holds:
        r=byid[h["roi_id"]];box=r["_bbox"]
        if h["reason"]!="QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT" or any(overlap(box,x["_bbox"]) for x in rows if x is not r) or any(overlap(box,x["roi"]) for x in accepted):
            remaining.append(h);continue
        path=root/r["_candidate_rel"]
        if not path.is_file() or path.is_symlink():remaining.append(h);continue
        try:
            rec=trial(source,clean,result,r,path.read_bytes(),fit,candidate_guard)
            accepted.append(rec)
        except (ValueError,OSError,OverflowError):
            remaining.append(h)
    if len(accepted)==len(painted):return None
    native=ImageOps.flip(result) if orientation=="FLIPY" else result
    masks=struct.unpack_from("<IIII",raw,92)
    fmt="BGRA" if masks==(0x00ff0000,0x0000ff00,0x000000ff,0xff000000) else "RGBA"
    data=raw[:128]+native.tobytes("raw",fmt)
    if len(data)!=len(raw) or data[:128]!=raw[:128] or diff_mask(decode(data),native).getbbox():
        raise ValueError("FLAT_SOURCE_NATIVE_ROUNDTRIP")
    return data,result,clean,accepted,remaining
