#!/usr/bin/env python3
"""Deadline repair: recover exact native English coordinates from source pixels.

Offline Tesseract is used ONLY to propose narrower geometry, not to approve
translation or erase art. Existing strict CLEAN/scale/native DDS gates run
again. Source SHA and orientation are checked independently for each atlas.
"""
import argparse,csv,io,json,math,re,subprocess,tempfile
from pathlib import Path
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageOps
import numpy as np
import github_ab_imagegen_atlas_batch as atlas
import hd_cleanplate_repair as repair

def norm(s):
    return re.sub(r"[^a-z0-9]","",s.lower())

def contains(a,b):
    return a[0]<=b[0]<b[2]<=a[2] and a[1]<=b[1]<b[3]<=a[3]

def overlap(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def union(boxes):
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]

def recognize(mask):
    # Text styles have dark outlines that confuse OCR on a gray composite.
    # Separate the foreground fill, avoiding transparency-only hidden RGB.
    buf=io.BytesIO();Image.fromarray(np.uint8(~mask)*255).save(buf,format="PNG")
    try:
        p=subprocess.run(["tesseract","stdin","stdout","-l","eng","--psm","11","tsv"],input=buf.getvalue(),capture_output=True,timeout=40,check=False)
    except subprocess.TimeoutExpired:
        return []
    if p.returncode:return []
    lines=defaultdict(list)
    for row in csv.DictReader(io.StringIO(p.stdout.decode("utf-8",errors="replace")),delimiter="\t"):
        if row.get("level")!="5" or not row.get("text","").strip():continue
        try:
            conf=float(row["conf"]);x,y,w,h=[int(row[k]) for k in ("left","top","width","height")]
        except (TypeError,ValueError):continue
        if w<=0 or h<=0:continue
        lines[tuple(row[k] for k in ("block_num","par_num","line_num"))].append((row["text"],conf,[x,y,x+w,y+h]))
    return list(lines.values())

def matches(lines,english):
    wanted=norm(english)
    if len(wanted)<4:return []
    found=[]
    for words in lines:
        for i in range(len(words)):
            txt="";boxes=[];scores=[]
            for word,conf,box in words[i:i+12]:
                part=norm(word)
                if not part:continue
                txt+=part;boxes.append(box);scores.append(conf)
                if not wanted.startswith(txt):break
                if txt==wanted:
                    if min(scores)>=65 and sum(scores)/len(scores)>=83:
                        # Do not join disjoint labels across a wide atlas gap.
                        h=max(b[3]-b[1] for b in boxes)
                        if all(b[0]-a[2]<=max(12,1.5*h) for a,b in zip(boxes,boxes[1:])):
                            found.append((union(boxes),round(sum(scores)/len(scores),2)))
                    break
    return found

def masks(im):
    v=np.asarray(im,dtype=np.int16)
    r,g,b,a=(v[:,:,i] for i in range(4))
    visible=a>=128
    yield "gold",visible&(r>140)&(g>90)&(r>b+40)&(g>b+22)
    yield "white",visible&(r>185)&(g>185)&(b>185)&(np.maximum(np.maximum(r,g),b)-np.minimum(np.minimum(r,g),b)<55)
    yield "red",visible&(r>135)&(r>g+55)&(r>b+55)
    yield "dark",visible&(r<85)&(g<85)&(b<85)

def refine(source,ocr_box,old,scale):
    # OCR is the inner glyph fill. Use a bounded halo to include outline,
    # shadow, anti-aliasing, and then let native strict edge checks decide.
    l,t,r,b=ocr_box
    mapped=[math.floor(l/scale[0]),math.floor(t/scale[1]),math.ceil(r/scale[0]),math.ceil(b/scale[1])]
    if not contains(old,mapped):return None
    h=mapped[3]-mapped[1]
    pad=max(3,min(44,math.ceil(h*.26)))
    box=[max(old[0],mapped[0]-pad),max(old[1],mapped[1]-pad),min(old[2],mapped[2]+pad),min(old[3],mapped[3]+pad)]
    if box==old or min(box[2]-box[0],box[3]-box[1])<8:return None
    # Do not propose a background panel, or a wholly occupied crop, as
    # an isolated text sprite. This only proposes transparent text layers.
    a=source.crop(box).getchannel("A").point(lambda n:255 if n>15 else 0)
    if not a.getbbox() or a.histogram()[255]/(a.width*a.height)>.62:return None
    return box

def one(root,target,rows,direction):
    raw=(root/atlas.ORIGINAL/target).read_bytes()
    sha=repair.sha(raw)
    if {r["source_dds_sha256"] for r in rows}!={sha}:raise ValueError("OCR_SOURCE_SHA:"+target)
    src=repair.readable(raw,direction)
    small=src.copy();small.thumbnail((1900,1900),Image.Resampling.LANCZOS)
    scale=(small.width/src.width,small.height/src.height)
    hits=defaultdict(list)
    for style,mask in masks(small):
        if not .0002<mask.mean()<.55:continue
        lines=recognize(mask)
        for row in rows:
            for box,conf in matches(lines,row["english"]):
                proposal=refine(src,box,row["_bbox"],scale)
                if proposal:
                    hits[row["roi_id"]].append((proposal,conf,style))
    proposed=[]
    for row in rows:
        rid=row["roi_id"];options=hits[rid]
        if not options:continue
        # Multiple style reads may describe the same exact label. Distinct
        # spatial matches are ambiguous, not permission to select one.
        options.sort(key=lambda x:-x[1])
        best=options[0]
        if any(not overlap(best[0],x[0]) for x in options[1:]):continue
        proposed.append({"target":target,"roi_id":rid,"source_dds_sha256":sha,
                         "bbox_xyxy":best[0],"old_bbox_xyxy":row["_bbox"],
                         "english":row["english"],"confidence":best[1],"style":best[2]})
    # Two different labels must not claim overlapping OCR geometry.
    safe=[p for p in proposed if not any(overlap(p["bbox_xyxy"],q["bbox_xyxy"]) for q in proposed if q is not p)]
    return safe,{"target":target,"proposals":len(safe),"ambiguous":len(proposed)-len(safe)}

def run(root,out,limit=104):
    root=Path(root);groups=atlas.load_cross(root/atlas.CROSS)
    dirs=atlas.load_pinned_orientations(root,groups)
    targets=sorted(groups,key=repair.priority)[:limit]
    result=[];audit=[]
    # Two workers only, and Tesseract OMP_THREAD_LIMIT=1 in workflow.
    with ThreadPoolExecutor(max_workers=2) as ex:
        for proposals,stat in ex.map(lambda target:one(root,target,groups[target],dirs[target]),targets):
            result.extend(proposals);audit.append(stat)
            print(json.dumps(stat,ensure_ascii=False),flush=True)
    doc={"schema":"outrun.hd.cleanplate-feedback.v1","origin":"SOURCE_SHA_EXACT_ENGLISH_COLOR_MASK_OCR_PROPOSALS_ONLY","proposals":result,"audit":audit}
    Path(out).write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    print("OCR_PROPOSALS",len(result),"ATLASES",len(targets),flush=True)
    return doc

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--repo-root",default=".");p.add_argument("--out",required=True);p.add_argument("--limit",type=int,default=104)
    a=p.parse_args();run(a.repo_root,a.out,a.limit)
