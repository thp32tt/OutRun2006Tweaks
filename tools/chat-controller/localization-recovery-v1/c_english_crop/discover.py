#!/usr/bin/env python3
"""Offline verified-full-source English ROI discovery.

Geometry proposals are NOT trusted as English: they stay review-only until a
reviewed region with an exact phrase is provided. Auto-admission never uses
unverified DDS, tile/reassembled images, or guessed OCR text.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from PIL import Image, ImageFilter
import numpy as np

BASE = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
SRC = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012")
MASTER = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/MASTER_CROP_MANIFEST_255.json")
REGIONS = BASE/"docker"/"reviewed_regions.json"
CANDIDATES = BASE/"auto_discovery"
SCHEMA = "outrun-c-n100-hd-original-crop-v1"

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""): h.update(part)
    return h.hexdigest()

def save_json_atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",dir=str(path.parent),prefix=".discover-",delete=False,encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")
        tmp=f.name
    os.replace(tmp,path)

def overlap(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]))
    y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    return x*y/max(1,min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1])))

def components(mask):
    # Run-length connected component union-find; no OpenCV/OCR dependency.
    parent=[]
    bboxes=[]
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    prev=[]
    for y,row in enumerate(mask):
        padded=np.pad(row.astype(np.int8),(1,1))
        diff=np.diff(padded)
        starts=np.flatnonzero(diff==1)
        ends=np.flatnonzero(diff==-1)
        cur=[]
        idx=0
        for x0,x1 in zip(starts.tolist(),ends.tolist()):
            while idx<len(prev) and prev[idx][1]<x0-1: idx+=1
            touching=[]
            j=idx
            while j<len(prev) and prev[j][0]<=x1+1:
                touching.append(root(prev[j][2]))
                j+=1
            if touching:
                me=touching[0]
                for other in touching[1:]:
                    other=root(other)
                    me=root(me)
                    if other!=me:
                        parent[other]=me
                        box=bboxes[me]; oth=bboxes[other]
                        box[0]=min(box[0],oth[0]);box[1]=min(box[1],oth[1])
                        box[2]=max(box[2],oth[2]);box[3]=max(box[3],oth[3])
            else:
                me=len(parent)
                parent.append(me)
                bboxes.append([x0,y,x1,y+1])
            me=root(me)
            box=bboxes[me]
            box[0]=min(box[0],x0);box[1]=min(box[1],y)
            box[2]=max(box[2],x1);box[3]=max(box[3],y+1)
            cur.append((x0,x1,me))
        prev=cur
    return [bboxes[i] for i in range(len(parent)) if root(i)==i]

def propose(full,excluded,limit=150):
    # Work at 1/4 resolution: detector is a conservative proposal generator.
    scale=max(1,(max(full.size)+1023)//1024)
    small=full.getchannel("A").resize(((full.width+scale-1)//scale,(full.height+scale-1)//scale))
    strong=small.point(lambda p:255 if p>=32 else 0).filter(ImageFilter.MaxFilter(9))
    mask=np.asarray(strong,dtype=np.uint8)>0
    results=[]
    for x0,y0,x1,y1 in components(mask):
        box=[max(0,(x0-3)*scale),max(0,(y0-3)*scale),min(full.width,(x1+3)*scale),min(full.height,(y1+3)*scale)]
        w=box[2]-box[0]; h=box[3]-box[1]
        if not (45<=w<=1800 and 18<=h<=340 and w/h>=1.35): continue
        if any(overlap(box,old)>0.28 for old in excluded):continue
        roi=np.asarray(full.getchannel("A").crop(tuple(box)),dtype=np.uint8)
        density=float(np.count_nonzero(roi>24))/roi.size
        if not .025<=density<=.86:continue
        # No English label is guessed from geometry.
        results.append({"bbox_xyxy":box,"alpha_density":round(density,4),
                        "status":"REVIEW_REQUIRED_UNVERIFIED_TEXT",
                        "english":None,"output_generated":False})
    results.sort(key=lambda a:(a["bbox_xyxy"][1],a["bbox_xyxy"][0]))
    return results[:limit]

def indexed_phrases(q):
    result=[]
    src=SRC/"transcriptions.jsonl"
    if not src.exists():return []
    for line in src.read_text(encoding="utf-8").splitlines():
        try: entry=json.loads(line)
        except ValueError:continue
        if str(entry.get("index","")).zfill(3)==q[1:]:
            result.extend([seg.get("source","") for seg in entry.get("segments",[])])
    return result

def run(verified,check_original):
    if not MASTER.is_file() or not REGIONS.is_file():raise ValueError("MISSING_PINNED_ARCHIVE_OR_REVIEWED_REGIONS")
    archive=json.loads(MASTER.read_text(encoding="utf-8"))
    if len(archive.get("items",[]))!=255:raise ValueError("ARCHIVE_255_INVALID")
    registry=json.loads(REGIONS.read_text(encoding="utf-8"))
    if registry.get("schema")!="outrun-discovery-reviewed-regions-v1":raise ValueError("REGION_REVIEW_SCHEMA_INVALID")
    summary={"status":"AUTO_DISCOVERY","sources_scanned":0,"source_holds":[],"proposals":0,
             "new_queued":0,"already_queued":0,"unreviewed_held":0,"candidate_files":[]}
    for q,rec in sorted(verified.items()):
        source=SRC/rec["png"]
        checked={"queue_id":q,"source_kind":"N100_DDS_VERIFIED_READABLE_FULL_HD_PNG",
              "source_png":rec["png"],"source_sha256":rec["png_sha256"],
              "source_dimensions":rec["size"],"source_dds_path":rec["dds_repo_path"],
              "source_dds_sha256":rec["dds_sha256"]}
        try:
            check_original(checked)
        except Exception as e:
            summary["source_holds"].append({"q":q,"reason":str(e)[:200]});continue
        taken=[x["bbox_xyxy"] for x in archive["items"]
               if str(x.get("id","")).upper().startswith(q+"-") and len(x.get("bbox_xyxy",[]))==4]
        for spec in sorted((BASE/"queue_specs").glob("*.json")):
            try:
                t=json.loads(spec.read_text(encoding="utf-8"))
                if t.get("queue_id")==q:
                    taken.extend([r["bbox_xyxy"] for r in t.get("regions",[])])
            except (ValueError,KeyError):pass
        with Image.open(source) as im:
            full=im.copy()
        proposals=propose(full,taken)
        CANDIDATES.mkdir(parents=True,exist_ok=True)
        target=CANDIDATES/(q+"_candidates.json")
        save_json_atomic(target,{"source_png":rec["png"],"source_sha256":rec["png_sha256"],
                                 "source_dds_sha256":rec["dds_sha256"],"size":rec["size"],
                                 "source_verified_pixel_exact":True,"candidates":proposals,
                                 "text_recognition":"NOT_AVAILABLE_NO_OCR","status":"HOLD_REVIEW_ONLY"})
        summary["sources_scanned"]+=1
        summary["proposals"]+=len(proposals)
        summary["unreviewed_held"]+=len(proposals)
        summary["candidate_files"].append(str(target))
        approved=[x for x in registry.get("regions",[]) if x.get("queue_id")==q]
        for item in approved:
            text=item.get("english","")
            box=item.get("bbox_xyxy")
            rid=item.get("id","")
            if (not isinstance(text,str) or not re.fullmatch(r"[A-Za-z0-9 ?!:.&'+-]{2,100}",text)
                or not isinstance(box,list) or len(box)!=4 or not all(type(n)==int for n in box)
                or not isinstance(rid,str) or not re.fullmatch(r"[a-z0-9-]{3,60}",rid)):
                summary["source_holds"].append({"q":q,"reason":"UNSAFE_APPROVED_REGION"});continue
            if any(not (0<=box[0]<box[2]<=full.width and 0<=box[1]<box[3]<=full.height) for _ in [0]):
                summary["source_holds"].append({"q":q,"reason":"BOX_OUTSIDE"});continue
            # A reviewed fragment may match an official longer transcription.
            if not any(text.casefold() in phrase.casefold() for phrase in indexed_phrases(q)):
                summary["source_holds"].append({"q":q,"reason":"ENGLISH_NOT_IN_OFFICIAL_TRANSCRIPT","text":text});continue
            if not item.get("visually_reviewed") or not item.get("source_dds_pixel_verified"):
                summary["source_holds"].append({"q":q,"reason":"REGION_REVIEW_MISSING"});continue
            if any(overlap(box,old)>=.55 for old in taken):continue
            al=np.asarray(full.getchannel("A").crop(tuple(box)),dtype=np.uint8)
            if not np.any(al>=16):
                summary["source_holds"].append({"q":q,"reason":"EMPTY_ALPHA_REGION"});continue
            name=q+"_AUTO_REVIEWED_"+rid+".json"
            spec=BASE/"queue_specs"/name
            if spec.exists():
                summary["already_queued"]+=1;continue
            if (BASE/"outputs"/(q+"-"+rid)).exists():continue
            receipt=dict(checked,schema=SCHEMA,regions=[{"id":rid,"english":text,"bbox_xyxy":box}])
            save_json_atomic(spec,receipt)
            taken.append(box)
            summary["new_queued"]+=1
    save_json_atomic(CANDIDATES/"last_scan.json",summary)
    return summary