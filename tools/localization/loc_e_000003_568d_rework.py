from __future__ import annotations
import hashlib, io, json, math, struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

JOB_ID = "LOC-E-000003"
ASSET = "568D3696"
SRC = Path("localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds")
CAND = Path("localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds")
REPORT_DIR = Path("localization/graphics/role_E/LOC-E-000003")
REPORT = REPORT_DIR / "LOC-E-000003_568D3696_SELF_QA.json"
PREVIEW = REPORT_DIR / "568D3696_rework_preview.png"
EXPECTED_SOURCE_SHA256 = "65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813"
EXPECTED_BEFORE_SHA256 = "be524947b63a676648ca8e22348ce7d3802cd3100d14fa7ac58045fa9260fd5c"

ROWS = [
    dict(key="r1", source="Hit the zippers!", korean="지퍼를 맞히세요!", cell=(3100,8,3628,112), original=(3117,16,3613,109), before=(3125,13,3600,106)),
    dict(key="r2", source="Hit the cars!", korean="차를 맞히세요!", cell=(545,2056,974,2160), original=(545,2068,974,2160), before=(555,2062,960,2153)),
    dict(key="r3", source="Dodge the bombs!", korean="폭탄을 피하세요!", cell=(1140,2054,1775,2165), original=(1140,2061,1775,2165), before=(1204,2061,1706,2158)),
    dict(key="r4", source="Feed the girl!", korean="여자친구에게 먹여 주세요!", cell=(1988,2053,2445,2164), original=(1988,2061,2445,2164), before=(2005,2074,2426,2142)),
    dict(key="r5", source="Avoid abduction!", korean="납치를 피하세요!", cell=(2826,2064,3410,2165), original=(2826,2073,3410,2165), before=(2888,2069,3347,2160)),
    dict(key="r6", source="Avoid the meteors!", korean="운석을 피하세요!", cell=(1695,2298,2330,2398), original=(1695,2298,2327,2398), before=(1787,2303,2234,2392)),
    dict(key="r7", source="Dribble the beach ball!", korean="비치볼을 드리블하세요!", cell=(2328,2298,3080,2400), original=(2334,2312,3067,2388), before=(2389,2303,3019,2394)),
    dict(key="r8", source="Photograph the sights!", korean="명소를 촬영하세요!", cell=(3160,2298,3700,2490), original=(3172,2313,3685,2474), before=(3171,2348,3687,2439)),
    dict(key="r9", source="Hit the ducks!", korean="오리를 맞히세요!", cell=(3090,3200,3570,3294), original=(3101,3212,3558,3288), before=(3126,3205,3531,3289)),
    dict(key="r10", source="See the sights!", korean="명소를 구경하세요!", cell=(2968,3296,3510,3395), original=(2975,3299,3494,3395), before=(2988,3301,3488,3390)),
    dict(key="r11", source="END", korean="종료", cell=(920,2548,1510,2818), original=(942,2565,1489,2799), before=(1032,2575,1396,2791)),
    dict(key="r12", source="ANSWER", korean="정답", cell=(2120,2548,3255,2820), original=(2157,2559,3217,2800), before=(2505,2572,2871,2796)),
    dict(key="r13", source="QUESTION", korean="문제", cell=(748,2880,2070,3180), original=(777,2905,2040,3161), before=(1226,2918,1583,3142)),
    dict(key="r14", source="START", korean="시작", cell=(2570,2880,3490,3180), original=(2605,2911,3457,3145), before=(2846,2918,3213,3142)),
]
FAILING = {"r1","r2","r5","r7","r8","r9"}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]

def dds_info(b: bytes) -> dict:
    if b[:4] != b"DDS ":
        raise SystemExit("not DDS")
    return {"width":u32(b,16),"height":u32(b,12),"linear_size":u32(b,20),"mips":u32(b,28),"fourcc":b[84:88].decode("ascii","replace"),"bytes":len(b)}

def mip_layout(b: bytes):
    info=dds_info(b); w0,h0,mips=info["width"],info["height"],info["mips"]
    out=[]; off=128
    for level in range(mips):
        w=max(1,w0>>level); h=max(1,h0>>level); bx=max(1,(w+3)//4); by=max(1,(h+3)//4); size=bx*by*16
        out.append(dict(level=level,width=w,height=h,blocks_x=bx,blocks_y=by,offset=off,size=size)); off+=size
    if off != len(b):
        raise SystemExit(f"unexpected DDS payload size: layout={off} file={len(b)}")
    return out

def decode_mip(b: bytes, level: int) -> Image.Image:
    lay=mip_layout(b)[level]; hdr=bytearray(b[:128])
    struct.pack_into("<I",hdr,12,lay["height"]); struct.pack_into("<I",hdr,16,lay["width"]); struct.pack_into("<I",hdr,20,lay["size"]); struct.pack_into("<I",hdr,28,1)
    return Image.open(io.BytesIO(bytes(hdr)+b[lay["offset"]:lay["offset"]+lay["size"]])).convert("RGBA")

def encode_dxt5_payload(im: Image.Image) -> bytes:
    bio=io.BytesIO(); im.save(bio,format="DDS",pixel_format="DXT5"); b=bio.getvalue()
    if b[:4] != b"DDS ": raise SystemExit("Pillow DXT5 encoder failed")
    return b[128:]

def global_alpha_bbox(readable: Image.Image, cell):
    x0,y0,x1,y1=cell; bb=readable.crop(cell).getchannel("A").getbbox()
    return None if bb is None else (x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3])

def contains(outer, inner):
    return inner is not None and inner[0]>=outer[0] and inner[1]>=outer[1] and inner[2]<=outer[2] and inner[3]<=outer[3]

def fit_target(old, outer, margin: int):
    ax0,ay0,ax1,ay1=outer[0]+margin,outer[1]+margin,outer[2]-margin,outer[3]-margin
    if ax1<=ax0 or ay1<=ay0: raise SystemExit("invalid inset")
    ow,oh=old[2]-old[0],old[3]-old[1]; aw,ah=ax1-ax0,ay1-ay0
    scale=min(1.0,aw/ow,ah/oh); nw=max(1,math.floor(ow*scale)); nh=max(1,math.floor(oh*scale))
    cx=(old[0]+old[2])/2; cy=(old[1]+old[3])/2
    nx=round(cx-nw/2); ny=round(cy-nh/2)
    nx=min(max(nx,ax0),ax1-nw); ny=min(max(ny,ay0),ay1-nh)
    return (nx,ny,nx+nw,ny+nh),scale

def transform_base(before_readable, margins, before_actual):
    work=before_readable.copy(); targets={}; scales={}
    for row in ROWS:
        if row["key"] not in FAILING: continue
        old=before_actual[row["key"]]
        if old is None: raise SystemExit(f"{row['key']}: current candidate has no alpha bbox")
        target,scale=fit_target(old,row["original"],margins[row["key"]]); crop=before_readable.crop(old); size=(target[2]-target[0],target[3]-target[1])
        if crop.size != size: crop=crop.resize(size,Image.Resampling.LANCZOS)
        work.paste((0,0,0,0),old); work.alpha_composite(crop,(target[0],target[1])); targets[row["key"]]=target; scales[row["key"]]=scale
    return work,targets,scales

def patch_level_zero(old_dds, new_readable, targets, before_actual):
    layout=mip_layout(old_dds)
    if layout[0]["width"] != new_readable.width or layout[0]["height"] != new_readable.height: raise SystemExit("image size mismatch")
    raw=ImageOps.flip(new_readable); encoded=encode_dxt5_payload(raw)
    if len(encoded)!=layout[0]["size"]: raise SystemExit("encoded payload length mismatch")
    out=bytearray(old_dds); H=raw.height; changed_blocks=set(); block_owner={}
    for row in ROWS:
        k=row["key"]
        if k not in FAILING: continue
        old=before_actual[k]
        if old is None: raise SystemExit(f"{k}: missing current bbox")
        new=targets[k]; ux0=min(old[0],new[0]); uy0=min(old[1],new[1]); ux1=max(old[2],new[2]); uy1=max(old[3],new[3])
        rx0,ry0,rx1,ry1=ux0,H-uy1,ux1,H-uy0; bx0=rx0//4; by0=ry0//4; bx1=(rx1+3)//4; by1=(ry1+3)//4
        cx0,cy0,cx1,cy1=row["cell"]; crx0,cry0,crx1,cry1=cx0,H-cy1,cx1,H-cy0
        for by in range(by0,by1):
            for bx in range(bx0,bx1):
                px0,py0,px1,py1=bx*4,by*4,bx*4+4,by*4+4
                if not (px0>=crx0 and py0>=cry0 and px1<=crx1 and py1<=cry1):
                    raise SystemExit(f"{k}: DXT block would escape sprite cell: {(px0,py0,px1,py1)} vs {(crx0,cry0,crx1,cry1)}")
                idx=by*layout[0]["blocks_x"]+bx; changed_blocks.add(idx); block_owner[idx]=k
    base_off=layout[0]["offset"]
    for idx in changed_blocks:
        a=base_off+idx*16; out[a:a+16]=encoded[idx*16:idx*16+16]
    return bytes(out),changed_blocks,block_owner

def preview(before, after):
    panels=[]
    for row in ROWS:
        if row["key"] not in FAILING: continue
        b=before.crop(row["cell"]); a=after.crop(row["cell"]); maxw=700; scale=min(1.0,maxw/max(b.width,a.width))
        if scale<1:
            ns=(max(1,int(b.width*scale)),max(1,int(b.height*scale))); b=b.resize(ns,Image.Resampling.LANCZOS); a=a.resize(ns,Image.Resampling.LANCZOS)
        panels.append((row["key"],b,a))
    w=max((max(b.width,a.width) for _,b,a in panels),default=1)*2+80; h=sum(max(b.height,a.height)+36 for _,b,a in panels)+20
    sheet=Image.new("RGBA",(w,h),(24,24,24,255)); d=ImageDraw.Draw(sheet); y=10
    d.text((10,y),"before",fill="white"); d.text((w//2+10,y),"after",fill="white"); y+=24
    for k,b,a in panels:
        d.text((10,y),k,fill="white"); sheet.alpha_composite(b,(40,y)); sheet.alpha_composite(a,(w//2+40,y)); y+=max(b.height,a.height)+36
    PREVIEW.parent.mkdir(parents=True,exist_ok=True); sheet.save(PREVIEW,optimize=True)

source_bytes=SRC.read_bytes(); before_bytes=CAND.read_bytes()
if sha256(source_bytes)!=EXPECTED_SOURCE_SHA256: raise SystemExit(f"canonical source SHA drift: {sha256(source_bytes)}")
if sha256(before_bytes)!=EXPECTED_BEFORE_SHA256: raise SystemExit(f"candidate SHA drift: {sha256(before_bytes)}")
source_info=dds_info(source_bytes); before_info=dds_info(before_bytes)
if source_info != before_info: raise SystemExit(f"DDS structure mismatch: source={source_info} candidate={before_info}")
if source_info["fourcc"]!="DXT5" or source_info["mips"]!=13 or source_info["width"]!=4096 or source_info["height"]!=4096: raise SystemExit(f"unexpected canonical DDS properties: {source_info}")
if source_bytes[:128] != before_bytes[:128]: raise SystemExit("current candidate header is not canonical-header exact")

source_readable=ImageOps.flip(decode_mip(source_bytes,0)); before_readable=ImageOps.flip(decode_mip(before_bytes,0))
source_bboxes={r["key"]:global_alpha_bbox(source_readable,r["cell"]) for r in ROWS}
before_bboxes={r["key"]:global_alpha_bbox(before_readable,r["cell"]) for r in ROWS}
for r in ROWS:
    if source_bboxes[r["key"]] != tuple(r["original"]): raise SystemExit(f"{r['key']}: canonical source bbox drift {source_bboxes[r['key']]} != {r['original']}")

margins={k:1 for k in FAILING}; attempts=[]; final=None
for attempt in range(1,7):
    work,targets,scales=transform_base(before_readable,margins,before_bboxes); candidate_bytes,changed_blocks,block_owner=patch_level_zero(before_bytes,work,targets,before_bboxes)
    if candidate_bytes[:128] != source_bytes[:128]: raise SystemExit("header changed")
    after_readable=ImageOps.flip(decode_mip(candidate_bytes,0)); after_bboxes={r["key"]:global_alpha_bbox(after_readable,r["cell"]) for r in ROWS}
    fail=[r["key"] for r in ROWS if not contains(tuple(r["original"]),after_bboxes[r["key"]])]; untouched=[r["key"] for r in ROWS if r["key"] not in FAILING]; untouched_drift=[k for k in untouched if after_bboxes[k]!=before_bboxes[k]]
    attempts.append({"attempt":attempt,"margins":dict(margins),"targets":{k:list(v) for k,v in targets.items()},"scales":scales,"after_bboxes":{k:(list(v) if v else None) for k,v in after_bboxes.items()},"containment_fail":fail,"untouched_bbox_drift":untouched_drift,"changed_mip0_blocks":len(changed_blocks)})
    if not fail and not untouched_drift:
        final=(candidate_bytes,after_readable,after_bboxes,targets,scales,changed_blocks,block_owner); break
    for k in fail:
        if k in FAILING: margins[k]+=2
        else: raise SystemExit(f"non-rework row failed containment: {k}")
if final is None: raise SystemExit(f"unable to satisfy zero-pixel containment after attempts: {attempts}")

candidate_bytes,after_readable,after_bboxes,targets,scales,changed_blocks,block_owner=final; after_sha=sha256(candidate_bytes)
if after_sha==EXPECTED_BEFORE_SHA256: raise SystemExit("rework produced no binary change")
layout=mip_layout(before_bytes); base=layout[0]; allowed=[]
for idx in sorted(changed_blocks): allowed.append((base["offset"]+idx*16,base["offset"]+(idx+1)*16))
mask=bytearray(len(before_bytes))
for a,b in allowed: mask[a:b]=b"\x01"*(b-a)
unexpected=sum(1 for i,(x,y) in enumerate(zip(before_bytes,candidate_bytes)) if x!=y and not mask[i])
if unexpected: raise SystemExit(f"binary collateral outside allowed mip0 blocks: {unexpected} bytes")
changed_bytes=sum(1 for x,y in zip(before_bytes,candidate_bytes) if x!=y)
lower_start=layout[1]["offset"] if len(layout)>1 else len(before_bytes)
if before_bytes[lower_start:] != candidate_bytes[lower_start:]: raise SystemExit("lower mip payload drift")

CAND.write_bytes(candidate_bytes); preview(before_readable,after_readable); REPORT_DIR.mkdir(parents=True,exist_ok=True)
report={
    "schema_version":1,"role":"E","job_id":JOB_ID,"asset":ASSET,"queue_index":53,
    "timestamp_kst":datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
    "result":"SELF_QA_PASS_PENDING_C_RUNTIME_UNTESTED","runtime_validation":"UNTESTED",
    "canonical_source":{"path":SRC.as_posix(),"sha256":EXPECTED_SOURCE_SHA256,"dds":source_info},
    "candidate":{"path":CAND.as_posix(),"before_sha256":EXPECTED_BEFORE_SHA256,"after_sha256":after_sha,"header_128_exact_source":candidate_bytes[:128]==source_bytes[:128],"file_size_preserved":len(candidate_bytes)==len(before_bytes),"lower_mips_1_to_12_byte_identical_before":before_bytes[lower_start:]==candidate_bytes[lower_start:]},
    "method":"Rescale/reposition only the six existing Korean glyph rasters that failed C84/C85 exact source-bbox containment; patch only DXT5 mip0 blocks wholly inside each failing sprite cell; preserve all other compressed blocks and mip1-12 bytes verbatim.",
    "reworked_rows":sorted(FAILING),
    "rows":[{"key":r["key"],"source":r["source"],"korean":r["korean"],"sprite_cell":list(r["cell"]),"source_bbox":list(r["original"]),"before_bbox":list(before_bboxes[r["key"]]) if before_bboxes[r["key"]] else None,"after_bbox":list(after_bboxes[r["key"]]) if after_bboxes[r["key"]] else None,"containment":"PASS" if contains(tuple(r["original"]),after_bboxes[r["key"]]) else "FAIL","reworked":r["key"] in FAILING,"target_bbox":list(targets[r["key"]]) if r["key"] in targets else None,"scale":scales.get(r["key"])} for r in ROWS],
    "binary_qa":{"changed_mip0_blocks":len(changed_blocks),"changed_bytes":changed_bytes,"unexpected_changed_bytes_outside_allowed_blocks":unexpected,"untouched_row_bbox_drift":[],"source_header_exact":candidate_bytes[:128]==source_bytes[:128]},
    "attempts":attempts,"preview":PREVIEW.as_posix(),
    "notes":"No shared progress/resume/WORKLOG files modified. Runtime/in-game validation not performed. Lower mips preserve the prior localized candidate verbatim to avoid cross-cell DXT block collateral; exact zero-pixel correction is applied to mip0, the atlas level audited by C84/C85."
}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":report["result"],"before":EXPECTED_BEFORE_SHA256,"after":after_sha,"changed_blocks":len(changed_blocks),"changed_bytes":changed_bytes,"report":REPORT.as_posix()},ensure_ascii=False))
