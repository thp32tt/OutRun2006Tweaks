#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[2]
ASSET="A064FDFC"; INDEX=60; TASK_ID="B94-20260928-1336"
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91=ROOT/"localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
RUN_DIR=ROOT/"localization/graphics/role_B/20260928-1336-B94"
REPORT=RUN_DIR/"B94_A064FDFC_EXACT_BBOX_REWORK_REPORT.json"
QA_PNG=RUN_DIR/"B94_A064FDFC_BEFORE_AFTER_QA.png"

def sha(b): return hashlib.sha256(b).hexdigest()
def parse(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise SystemExit("invalid DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0] or 1
    fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000): raise SystemExit(f"unsupported DDS {fourcc!r} {bits} {masks}")
    if pitch!=w*4 or len(b)!=128+w*h*4: raise SystemExit("unexpected DDS payload")
    return w,h,mips
def rgba(b,w,h): return Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
def dds(header,img): return header+img.tobytes("raw","RGBA")
def anydiff(a,b):
    d=ImageChops.difference(a,b)
    r,g,bb,aa=d.split()
    return ImageChops.lighter(ImageChops.lighter(r,g),ImageChops.lighter(bb,aa))
def absdiffbbox(src,loc,cell):
    x0,y0,x1,y1=cell
    m=anydiff(src.crop((x0,y0,x1+1,y1+1)),loc.crop((x0,y0,x1+1,y1+1)))
    b=m.getbbox()
    return None if b is None else [x0+b[0],y0+b[1],x0+b[2]-1,y0+b[3]-1]
def inside(b,o): return b is not None and b[0]>=o[0] and b[1]>=o[1] and b[2]<=o[2] and b[3]<=o[3]
def union_mask(size,cells):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x0,y0,x1,y1 in cells: d.rectangle((x0,y0,x1,y1),fill=255)
    return m
def nonzero_count(m): return sum(v for i,v in enumerate(m.histogram()) if i)
def clear_old_preserving_source_outside_original(img,src,old,orig):
    ox0,oy0,ox1,oy1=old
    img.paste((0,0,0,0),(ox0,oy0,ox1+1,oy1+1))
    # Any old overflow outside the permitted original bbox must exactly match HD source.
    strips=[
      (ox0,oy0,min(ox1,orig[0]-1),oy1),
      (max(ox0,orig[2]+1),oy0,ox1,oy1),
      (max(ox0,orig[0]),oy0,min(ox1,orig[2]),min(oy1,orig[1]-1)),
      (max(ox0,orig[0]),max(oy0,orig[3]+1),min(ox1,orig[2]),oy1),
    ]
    for x0,y0,x1,y1 in strips:
        if x0<=x1 and y0<=y1:
            img.paste(src.crop((x0,y0,x1+1,y1+1)),(x0,y0))

src_blob=SOURCE.read_bytes(); cand_blob=CANDIDATE.read_bytes()
w,h,mips=parse(src_blob); w2,h2,m2=parse(cand_blob)
assert (w,h,mips)==(w2,h2,m2)==(4096,2048,1)
assert src_blob[:128]==cand_blob[:128]
doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]==ASSET)
rows=asset["rows"]; fails=[r for r in rows if r["containment"]=="FAIL"]
if len(fails)!=6: raise SystemExit(f"expected 6 C85 fails, got {len(fails)}")
acts=json.loads(B91.read_text("utf-8")); aa=next(x for x in acts["assets"] if x["asset"]==ASSET)
actions={r["key"]:r for r in aa["rows"]}

src=rgba(src_blob,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=rgba(cand_blob,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
after=before.copy(); records=[]
for r in fails:
    a=actions[r["key"]]; old=r["localized_bbox"]; orig=r["original_bbox"]
    x0,y0,x1,y1=old
    patch=before.crop((x0,y0,x1+1,y1+1))
    clear_old_preserving_source_outside_original(after,src,old,orig)
    nx0,ny0,nx1,ny1=a["new_localized_bbox"]; tw=nx1-nx0+1; th=ny1-ny0+1
    if patch.size!=(tw,th): patch=patch.resize((tw,th),Image.Resampling.LANCZOS)
    after.alpha_composite(patch,(nx0,ny0))
    records.append({"key":r["key"],"old_localized_bbox":old,"original_bbox":orig,"target_bbox":a["new_localized_bbox"],"scale":a.get("scale",1)})

qa=[]; failed=[]
for r in rows:
    b=absdiffbbox(src,after,r["sprite_cell"]); o=r["original_bbox"]; ok=inside(b,o)
    rec={"key":r["key"],"source":r.get("source"),"korean":r.get("korean"),"sprite_cell":r["sprite_cell"],"original_bbox":o,"localized_diff_bbox":b,"containment":"PASS" if ok else "FAIL"}
    qa.append(rec)
    if not ok: failed.append(rec)

fail_mask=union_mask((w,h),[r["sprite_cell"] for r in fails])
all_mask=union_mask((w,h),[r["sprite_cell"] for r in rows])
changed=anydiff(before,after)
collateral=nonzero_count(ImageChops.multiply(changed,ImageOps.invert(fail_mask)))
srcdiff=anydiff(src,after)
outside=nonzero_count(ImageChops.multiply(srcdiff,ImageOps.invert(all_mask)))
sa=src.getchannel("A"); aaft=after.getchannel("A")
introduced=ImageChops.subtract(aaft,sa)
introduced_outside=nonzero_count(ImageChops.multiply(introduced,ImageOps.invert(all_mask)))
if failed or collateral or outside or introduced_outside:
    print(json.dumps({"failed":failed,"collateral_pixels":collateral,"outside_cells_changed_pixels":outside,"introduced_alpha_outside_cells":introduced_outside},ensure_ascii=False,indent=2))
    raise SystemExit("B94 strict post-QA failed; candidate not written")

outimg=after.transpose(Image.Transpose.FLIP_TOP_BOTTOM); out=dds(cand_blob[:128],outimg)
parse(out)
if out[:128]!=src_blob[:128] or len(out)!=len(cand_blob): raise SystemExit("DDS structure changed")
newsha=sha(out); oldsha=sha(cand_blob)
if newsha==oldsha: raise SystemExit("no binary change")
CANDIDATE.write_bytes(out)

RUN_DIR.mkdir(parents=True,exist_ok=True)
panels=[]
for r in fails:
    x0,y0,x1,y1=r["sprite_cell"]; b=before.crop((x0,y0,x1+1,y1+1)); a=after.crop((x0,y0,x1+1,y1+1))
    W=900; scale=min(1.0,(W//2-12)/b.width,180/b.height); sz=(max(1,int(b.width*scale)),max(1,int(b.height*scale)))
    p=Image.new("RGBA",(W,max(64,sz[1]+28)),(30,30,30,255)); p.paste(b.resize(sz,Image.Resampling.LANCZOS),(5,24)); p.paste(a.resize(sz,Image.Resampling.LANCZOS),(W//2+5,24))
    d=ImageDraw.Draw(p); d.text((5,5),r["key"]+" BEFORE",fill="white"); d.text((W//2+5,5),r["key"]+" AFTER",fill="white"); panels.append(p)
sheet=Image.new("RGBA",(900,sum(p.height for p in panels)),(20,20,20,255)); y=0
for p in panels: sheet.paste(p,(0,y)); y+=p.height
sheet.convert("RGB").save(QA_PNG,quality=93)

now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={"schema_version":1,"role":"B","run":"B94","task_id":TASK_ID,"timestamp_kst":now,"base_head":os.environ.get("GITHUB_SHA"),"asset":"textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds","index":INDEX,"source_sha256":sha(src_blob),"previous_candidate_sha256":oldsha,"candidate_sha256":newsha,"structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":mips,"bytes":len(out),"header_128_exact":True,"raw_orientation":"mirror_y"},"reworked_elements":records,"qa":{"elements":len(qa),"failed_elements":0,"rows":qa,"changed_pixels_outside_reworked_cells":collateral,"changed_pixels_outside_all_declared_cells":outside,"introduced_alpha_outside_all_declared_cells":introduced_outside,"containment":"PASS"},"result":"B94_SELF_QA_PASS_PENDING_C_AND_DDS_ONLY_INGAME","runtime_validation":"UNTESTED","final_approval":False,"build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False,"qa_image":str(QA_PNG.relative_to(ROOT))}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")

q=ROOT/"localization/graphics/asset_queue.csv"
with q.open("r",encoding="utf-8",newline="") as f: qr=list(csv.DictReader(f)); fields=list(qr[0])
for row in qr:
    if int(row["index"])==INDEX:
        row["artwork_status"]="b94_self_qa_pass_pending_c"; row["notes"]=(row.get("notes","").rstrip("; ")+"; B94 exact source-diff bbox rework PASS 21/21; C + isolated DDS_ONLY in-game pending").strip("; ")
with q.open("w",encoding="utf-8",newline="") as f: wr=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); wr.writeheader(); wr.writerows(qr)

pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8")); p["updated_at_kst"]=now; g=p.setdefault("graphics",{})
g["latest_b_first_qa"]={"run":"B94","report":str(REPORT.relative_to(ROOT)),"result":"1_RGBA_REWORK_SELF_QA_PASS_PENDING_C_INGAME","assets":{ASSET:{"candidate_sha256":newsha,"status":"B94_SELF_QA_PASS_PENDING_C_INGAME"}}}
nr=g.get("next_hd_rework",{}); nr["assets"]=[x for x in nr.get("assets",[]) if x!=ASSET]; nr["remaining"]=len(nr["assets"]); pend=nr.setdefault("pending_c_revalidation",[])
if ASSET not in pend: pend.append(ASSET)
g["next_hd_rework"]=nr; p["next_checkpoint"]="B94: A064FDFC exact source-diff bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game."
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")

rp=ROOT/"localization/resume_state.json"; rs=json.loads(rp.read_text("utf-8")); rs["schema_version"]=int(rs.get("schema_version",55))+1
acts=rs.get("next_actions",[]); acts.insert(0,"B94: A064FDFC exact source-diff bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game."); rs["next_actions"]=acts
rs.setdefault("graphics_checkpoint",{})["b94_a064fdfc"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),"candidate_sha256":newsha,"status":"B94_SELF_QA_PASS_PENDING_C_INGAME"}
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")

sp=ROOT/"localization/progress/STATUS.md"; s=sp.read_text("utf-8")
s+=f"\n\n### B94 exact-bbox rework {now}\n- A064FDFC index 60: six C85 failures reworked against the canonical HD source.\n- Strict source-diff containment: 21/21 PASS; outside declared cells 0; collateral outside reworked cells 0.\n- DDS 4096x2048 RGBA32 mip1/header/raw mirror_y preserved. Candidate SHA-256 {newsha}.\n- Pending independent C and isolated DDS_ONLY in-game validation; runtime UNTESTED.\n"; sp.write_text(s,"utf-8")
with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - B94 A064FDFC exact-bbox rework\n\n- B even shard index 60; six C85 failing regions reworked from current GitHub HD candidate/source only.\n- 21/21 source-diff bbox containment PASS; no outside-cell/collateral changes.\n- Candidate {newsha}; C + isolated DDS_ONLY in-game pending; no build/VR/FFB/N100/GPT Library.\n")
