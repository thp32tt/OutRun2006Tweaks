#!/usr/bin/env python3
# C259 C2 independent static QA for q050 CBF8ECBF after B210 visual rework.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, json, hashlib, struct, tempfile, urllib.request
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT="localization/graphics/role_C/20261008-C259-C2-Q212-Q050-Q062"
os.makedirs(OUT, exist_ok=True)
CAND="localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds"
CAND_SHA="af6a189de92ccade79687c92a46cd2304a5f631f73e96a24a9d6a74844de5c33"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds"
SRC_SHA="3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe"
CLEAN="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_CLEAN_PLATE.png"
ALLOWED="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_ALLOWED_TEXT_REGION_MASK.png"
SOURCE_MASK="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_SOURCE_TEXT_MASK.png"
ROWS=[
 ("friend_request",[646,1017,1345,1090]),
 ("players",[1647,1017,2021,1090]),
 ("your_friends",[2668,1023,3244,1092]),
 ("please_wait",[1928,1124,2660,1224]),
 ("time_over",[241,1274,1610,1515]),
 ("game_over",[1915,1287,3409,1525]),
 ("goal",[1620,1660,2814,2024]),
]

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_dds(path):
    data=open(path,"rb").read()
    if data[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",data,12)[0]; w=struct.unpack_from("<I",data,16)[0]
    bpp=struct.unpack_from("<I",data,88)[0]
    masks=struct.unpack_from("<IIII",data,92)
    if bpp!=32:
        raise RuntimeError("unexpected bpp "+repr(bpp))
    px=np.frombuffer(data,dtype=np.uint8,offset=128,count=w*h*4).reshape(h,w,4)
    if masks==(0x00ff0000,0x0000ff00,0x000000ff,0xff000000):
        rgba=px[:,:,[2,1,0,3]].copy()
    elif masks==(0x000000ff,0x0000ff00,0x00ff0000,0xff000000):
        rgba=px.copy()
    else:
        raise RuntimeError("unexpected RGBA32 masks "+repr(masks))
    return rgba, data[:128]

def read_mask(path):
    a=np.array(Image.open(path).convert("RGBA"))
    m=a[:,:,3]>0
    if not m.any(): m=a[:,:,:3].max(2)>0
    return m

def bbox(m):
    ys,xs=np.where(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def composite(a,bg=(112,112,112,255)):
    fg=Image.fromarray(a,"RGBA")
    return Image.alpha_composite(Image.new("RGBA",fg.size,bg),fg).convert("RGB")

with tempfile.TemporaryDirectory() as td:
    srcp=os.path.join(td,"source.dds")
    urllib.request.urlretrieve(SRC_URL,srcp)
    if sha256(srcp)!=SRC_SHA: raise RuntimeError("source SHA mismatch")
    if sha256(CAND)!=CAND_SHA: raise RuntimeError("candidate SHA mismatch")
    src,sh=load_dds(srcp); cand,ch=load_dds(CAND)
    clean=np.array(Image.open(CLEAN).convert("RGBA"))
    allowed=read_mask(ALLOWED); smask=read_mask(SOURCE_MASK)
    if src.shape!=cand.shape or src.shape!=clean.shape or src.shape[:2]!=allowed.shape:
        raise RuntimeError("shape mismatch")

    # Policy evidence says this atlas is persisted mirror-Y; clean/source bboxes use readable coordinates.
    S=src[::-1]; C=cand[::-1]
    adiff=C[:,:,3]!=clean[:,:,3]
    rgbdiff=np.any(C[:,:,:3]!=clean[:,:,:3],axis=2)
    visible=(C[:,:,3]>0)|(clean[:,:,3]>0)
    diff=adiff | (rgbdiff & visible)
    outside=~allowed
    outside_changed=int(diff[outside].sum())
    outside_alpha=int(adiff[outside].sum())

    rows=[]
    for key,b in ROWS:
        x0,y0,x1,y1=b
        bb=bbox(diff[y0:y1,x0:x1])
        if bb:
            loc=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
            w=loc[2]-loc[0]; h=loc[3]-loc[1]
            margins=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
        else:
            loc=None; w=h=0; margins=None
        ok=loc is not None and min(margins)>0 and w<=x1-x0 and h<=y1-y0
        rows.append({
            "key":key,"source_bbox":b,"source_size":[x1-x0,y1-y0],
            "localized_bbox":loc,"localized_size":[w,h],"margins":margins,
            "containment":"PASS" if loc and min(margins)>=0 else "FAIL",
            "size_ceiling":"PASS" if loc and w<=x1-x0 and h<=y1-y0 else "FAIL",
            "positive_margin":"PASS" if loc and min(margins)>0 else "FAIL"
        })

    passed=sum(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows)
    src_alpha=S[:,:,3]>0
    src_eq=(C[:,:,3]==S[:,:,3]) & np.all(C[:,:,:3]==S[:,:,:3],axis=2) & src_alpha
    src_clean=(S[:,:,3]!=clean[:,:,3]) | (np.any(S[:,:,:3]!=clean[:,:,:3],axis=2) & ((S[:,:,3]>0)|(clean[:,:,3]>0)))
    residue_diag=int((src_eq & smask & src_clean).sum())
    machine="PASS" if passed==len(rows) and outside_changed==0 and outside_alpha==0 and sh==ch else "FAIL"

    report={
      "schema_version":1,"role":"C","run":"20261008-C259-C2-Q212-Q050-Q062",
      "TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":50,
      "asset":"CBF8ECBF","candidate_sha256":sha256(CAND),"source_sha256":sha256(srcp),
      "dimensions":[int(src.shape[1]),int(src.shape[0])],"header_128_exact":bool(sh==ch),
      "review_coordinate_orientation":"FLIP_Y","independent_basis":"C104-established exact source bboxes + canonical source + validated clean plate; current persisted DDS independently decoded and remeasured.",
      "changed_pixels_outside_allowed_bboxes":outside_changed,
      "alpha_changed_pixels_outside_allowed_bboxes":outside_alpha,
      "source_exact_pixel_residue_diagnostic":residue_diag,
      "rows":rows,"row_summary":{"pass":passed,"total":len(rows)},
      "machine_status":machine,"controller_visual_qa":"PENDING_CONTROLLER",
      "c3_strict_decision":"PENDING_CONTROLLER","runtime_validation":"UNTESTED",
      "forbidden_domains_touched":[]
    }
    with open(os.path.join(OUT,"C259_Q050_MACHINE_QA.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)

    # Readable row contacts.
    cards=[]
    for key,b in ROWS:
        x0,y0,x1,y1=b; p=12
        xx0=max(0,x0-p); yy0=max(0,y0-p); xx1=min(S.shape[1],x1+p); yy1=min(S.shape[0],y1+p)
        a=composite(S[yy0:yy1,xx0:xx1]); c=composite(C[yy0:yy1,xx0:xx1])
        scale=min(2.5,1200/max(1,a.width+c.width))
        if scale>1:
            a=a.resize((int(a.width*scale),int(a.height*scale)),Image.Resampling.NEAREST)
            c=c.resize((int(c.width*scale),int(c.height*scale)),Image.Resampling.NEAREST)
        card=Image.new("RGB",(a.width+c.width,max(a.height,c.height)+24),(235,235,235))
        d=ImageDraw.Draw(card); d.text((4,4),key+" SOURCE",fill=(0,0,0)); d.text((a.width+4,4),key+" CURRENT",fill=(0,0,0))
        card.paste(a,(0,24)); card.paste(c,(a.width,24)); cards.append(card)
    sheet=Image.new("RGB",(max(x.width for x in cards),sum(x.height for x in cards)),(220,220,220))
    y=0
    for c in cards: sheet.paste(c,(0,y)); y+=c.height
    sheet.save(os.path.join(OUT,"C259_Q050_CONTACTS.jpg"),quality=90)

    # Whole RAW + readable comparison.
    panels=[]
    for label,A,B in [("RAW",src,cand),("FLIP-Y",S,C)]:
        ia=composite(A); ib=composite(B)
        scale=min(1.0,900/max(ia.width,ib.width))
        if scale<1:
            z=(int(ia.width*scale),int(ia.height*scale)); ia=ia.resize(z,Image.Resampling.LANCZOS); ib=ib.resize(z,Image.Resampling.LANCZOS)
        p=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+24),(235,235,235))
        d=ImageDraw.Draw(p); d.text((4,4),label+" SOURCE",fill=(0,0,0)); d.text((ia.width+4,4),label+" CURRENT",fill=(0,0,0))
        p.paste(ia,(0,24)); p.paste(ib,(ia.width,24)); panels.append(p)
    full=Image.new("RGB",(max(x.width for x in panels),sum(x.height for x in panels)),(220,220,220))
    y=0
    for p in panels: full.paste(p,(0,y)); y+=p.height
    full.save(os.path.join(OUT,"C259_Q050_RAW_FLIPY.jpg"),quality=88)

    print(json.dumps({"q50":{"machine_status":machine,"row_summary":report["row_summary"],"outside":outside_changed,"alpha_outside":outside_alpha,"candidate_sha256":report["candidate_sha256"]}},ensure_ascii=False,indent=2))
