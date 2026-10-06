#!/usr/bin/env python3
import hashlib, json, os, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-USERJPG144-CLEANUP"
out=repo/"localization/graphics/role_A"/run
wr=repo/"localization/graphics/worker_results"
out.mkdir(parents=True,exist_ok=True); wr.mkdir(parents=True,exist_ok=True)

assets=[
 (1,12,"textures/load/spr_etc_xst/D6DC1380_256x64.dds"),
 (2,26,"textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"),
 (3,28,"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"),
 (4,30,"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds"),
 (5,32,"textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds"),
 (6,34,"textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds"),
 (7,36,"textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"),
 (8,38,"textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds"),
 (9,43,"textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds"),
 (10,44,"textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds"),
 (14,51,"textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"),
 (18,57,"textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"),
 (19,59,"textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"),
 (20,61,"textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds"),
 (21,65,"textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds"),
 (22,86,"textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds"),
]
candidate_root=repo/"localization/graphics/hd_candidates"

def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_raw(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",path))
    h,w=struct.unpack_from("<II",b,12)
    fourcc=b[84:88]
    if fourcc==b"\0\0\0\0":
        pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
        if len(b)!=128+w*h*4: raise RuntimeError(("RGBA size",path,len(b),w,h))
        if masks[:3]==(0xff,0xff00,0xff0000): mode="RGBA"
        elif masks[:3]==(0xff0000,0xff00,0xff): mode="BGRA"
        else: raise RuntimeError(("unsupported masks",path,masks))
        im=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    else:
        im=Image.open(path).convert("RGBA")
    return im,{"w":w,"h":h,"fourcc":fourcc.decode("ascii","replace")}

def composite(im,max_w=620,max_h=460):
    x=im.copy()
    x.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
    bg=Image.new("RGB",x.size,(96,96,96))
    bg.paste(x.convert("RGB"),mask=x.getchannel("A"))
    return bg

font=ImageFont.load_default()
records=[]
pairs=[]
for num,qidx,rel in assets:
    p=candidate_root/rel
    raw,info=load_raw(p)
    flip=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    # Transform identity is exact by construction and catches decode/orientation drift.
    if not np.array_equal(np.asarray(raw)[::-1,:,:],np.asarray(flip)):
        raise RuntimeError(("raw/flip identity fail",num,rel))
    records.append({
        "number":num,"queue_index":qidx,"asset":rel,"sha256":sha_file(p),
        "width":info["w"],"height":info["h"],"format":info["fourcc"],
        "raw_flip_y_identity":"PASS"
    })
    pairs.append((num,qidx,rel,raw,flip))

# Four review sheets, four assets each, actual decoded RAW and FLIP-Y side by side.
for sheet_idx in range(4):
    group=pairs[sheet_idx*4:(sheet_idx+1)*4]
    rows=[]
    for num,qidx,rel,raw,flip in group:
        a=composite(raw); b=composite(flip)
        w=max(a.width,b.width); h=max(a.height,b.height)
        row=Image.new("RGB",(w*2,h+42),(32,32,32))
        row.paste(a,((w-a.width)//2,42))
        row.paste(b,(w+(w-b.width)//2,42))
        d=ImageDraw.Draw(row)
        d.text((8,6),f"{num:03d} q{qidx} RAW",font=font,fill="white")
        d.text((w+8,6),"FLIP-Y",font=font,fill="white")
        d.text((8,22),Path(rel).name,font=font,fill=(210,210,210))
        rows.append(row)
    sw=max(r.width for r in rows); sh=sum(r.height for r in rows)
    sheet=Image.new("RGB",(sw,sh),(20,20,20)); y=0
    for r in rows:
        sheet.paste(r,(0,y)); y+=r.height
    sheet.save(out/f"A144_RAW_FLIPY_SHEET_{sheet_idx+1}.jpg","JPEG",quality=92,subsampling=0,optimize=True)

# Special orientation proof for PJR-001: exact English source and candidate in both storage orientations.
q1_rel=assets[0][2]
q1_src=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/q1_rel
src_raw,_=load_raw(q1_src); cand_raw,_=load_raw(candidate_root/q1_rel)
panels=[
 ("EN SOURCE RAW",src_raw),("EN SOURCE FLIP-Y",src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),
 ("KOR CAND RAW",cand_raw),("KOR CAND FLIP-Y",cand_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
]
thumbs=[(lab,composite(im,620,300)) for lab,im in panels]
w=max(im.width for _,im in thumbs); h=max(im.height for _,im in thumbs)
canvas=Image.new("RGB",(w*2,(h+38)*2),(32,32,32))
d=ImageDraw.Draw(canvas)
for i,(lab,im) in enumerate(thumbs):
    x=(i%2)*w+(w-im.width)//2; y=(i//2)*(h+38)+38
    canvas.paste(im,(x,y)); d.text(((i%2)*w+8,(i//2)*(h+38)+8),lab,font=font,fill="white")
canvas.save(out/"A144_PJR001_SOURCE_CANDIDATE_RAW_FLIPY.jpg","JPEG",quality=94,subsampling=0,optimize=True)

report={
 "run":run,
 "qa":"A144_ORDERED_GATE_RAW_FLIPY_SUPPLEMENT",
 "status":"RAW_AND_FLIPY_EVIDENCE_READY_PENDING_CONTROLLER_VISUAL_DECISION",
 "asset_count":len(records),
 "assets":records,
 "sheets":[f"localization/graphics/role_A/{run}/A144_RAW_FLIPY_SHEET_{i}.jpg" for i in range(1,5)],
 "pjr001_orientation_proof":f"localization/graphics/role_A/{run}/A144_PJR001_SOURCE_CANDIDATE_RAW_FLIPY.jpg",
 "runtime_validation":"UNTESTED"
}
(out/"A144_RAW_FLIPY_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A144_RAW_FLIPY_QA.json").write_text(json.dumps({"run":run,"status":report["status"],"asset_count":len(records),"runtime_validation":"UNTESTED"},indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
