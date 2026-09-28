#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, os, struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[2]
ASSET="FF2462BB"; INDEX=51; TASK_ID="LOCALIZATION-LOCALIZATION_A-00001"
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
RUN_DIR=ROOT/"localization/graphics/role_A/20260928-AUTO-A00001-FF2462BB"
REPORT=RUN_DIR/"A_AUTO_00001_FF2462BB_REPORT.json"
QA_PNG=RUN_DIR/"A_AUTO_00001_FF2462BB_QA.png"

sha=lambda b: hashlib.sha256(b).hexdigest()

def parse(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise SystemExit("invalid DDS")
    h,w,pitch,mips=struct.unpack_from("<IIII",b,12); mips=mips or 1
    fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000):
        raise SystemExit(f"unsupported DDS {fourcc!r} {bits} {masks}")
    if pitch!=w*4 or len(b)!=128+w*h*4: raise SystemExit("unexpected payload")
    return w,h,mips

def rgba(b,w,h): return Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
def diffmask(a,b):
    d=ImageChops.difference(a,b); r,g,bb,aa=d.split()
    return ImageChops.lighter(ImageChops.lighter(r,g),ImageChops.lighter(bb,aa))
def mk_mask(size,boxes):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x0,y0,x1,y1 in boxes: d.rectangle((x0,y0,x1,y1),fill=255)
    return m
def nz(m): return sum(v for i,v in enumerate(m.histogram()) if i)
def alpha_bbox(im,ox,oy):
    b=im.getchannel("A").getbbox()
    return None if b is None else [ox+b[0],oy+b[1],ox+b[2]-1,oy+b[3]-1]
def inside(b,o):
    return b is not None and b[0]>=o[0] and b[1]>=o[1] and b[2]<=o[2] and b[3]<=o[3]
def clamp(v,lo,hi): return max(lo,min(v,hi))

sb=SOURCE.read_bytes(); cb=CANDIDATE.read_bytes()
# Completion guard: queued pre-close workflow runs may start after this task has
# already committed the validated FF2462BB candidate. Never re-apply transforms.
if sha(cb)=="641e317c9085e2e0f748ab4eab0618a53b20861bd65abc6373c0ac36453bfda3":
    print("FF2462BB already completed; no rework applied")
    raise SystemExit(0)
w,h,m=parse(sb); w2,h2,m2=parse(cb)
assert (w,h,m)==(w2,h2,m2)==(4096,2048,1) and sb[:128]==cb[:128]

doc=json.loads(C85.read_text("utf-8"))
asset=next(x for x in doc["assets"] if x["asset"]==ASSET)
rows=asset["rows"]; fails=[r for r in rows if r["containment"]=="FAIL"]
if len(fails)!=21: raise SystemExit(f"expected 21 fails got {len(fails)}")

src=rgba(sb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=rgba(cb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
after=before.copy(); recs=[]

for r in fails:
    l=r["localized_bbox"]; o=r["original_bbox"]
    lx0,ly0,lx1,ly1=l; ox0,oy0,ox1,oy1=o
    patch=before.crop((lx0,ly0,lx1+1,ly1+1))
    alpha=patch.getchannel("A")
    binmask=alpha.point(lambda p:255 if p else 0)
    if binmask.getbbox() is None: raise SystemExit(f"{r['key']}: empty localized alpha")

    lw,lh=patch.size; ow,oh=ox1-ox0+1,oy1-oy0+1
    # Remove only the localized visible pixels. This preserves neighboring artwork and
    # avoids the source-text restoration/collateral issue seen in the 39229D64 attempt.
    after.paste((0,0,0,0),(lx0,ly0,lx1+1,ly1+1),binmask)

    method="translate_no_resample"; transformed=patch; tx,ty=lx0,ly0
    if lw<=ow and lh<=oh:
        dx=ox0-lx0 if lx0<ox0 else (ox1-lx1 if lx1>ox1 else 0)
        dy=oy0-ly0 if ly0<oy0 else (oy1-ly1 if ly1>oy1 else 0)
        tx,ty=lx0+dx,ly0+dy
    elif lw<=ow and 0 < (lh-oh) <= 3:
        # One-to-three pixel vertical fringe excess: crop only the overflow fringe.
        # Do not resample the interior glyph raster.
        ix0=max(lx0,ox0); iy0=max(ly0,oy0); ix1=min(lx1,ox1); iy1=min(ly1,oy1)
        transformed=patch.crop((ix0-lx0,iy0-ly0,ix1-lx0+1,iy1-ly0+1))
        tx,ty=ix0,iy0; method="trim_overflow_no_resample"
    else:
        # Only the START/GOAL family should reach this path. Scale by the minimum
        # amount required to fit, rather than B91's broader shrink of every failed row.
        scale=min(1.0,ow/lw,oh/lh)
        nw=max(1,min(ow,int(math.floor(lw*scale))))
        nh=max(1,min(oh,int(math.floor(lh*scale))))
        transformed=patch.resize((nw,nh),Image.Resampling.LANCZOS)
        cx=(lx0+lx1)/2; cy=(ly0+ly1)/2
        tx=clamp(int(round(cx-nw/2)),ox0,ox1-nw+1)
        ty=clamp(int(round(cy-nh/2)),oy0,oy1-nh+1)
        method="minimal_lanczos_fit"

    after.alpha_composite(transformed,(tx,ty))
    ab=alpha_bbox(transformed,tx,ty)
    if not inside(ab,o):
        raise SystemExit(f"{r['key']}: transform still outside {ab} vs {o}")
    recs.append({
        "key":r["key"],"original_bbox":o,"before_localized_bbox":l,
        "localized_bbox":ab,"method":method,
        "scale_x":round(transformed.width/lw,6),"scale_y":round(transformed.height/lh,6),
        "containment":"PASS"
    })

# QA: all touched element bboxes must be contained. Untouched C85 PASS rows are unchanged.
failed=[x for x in recs if x["containment"]!="PASS"]
changed=diffmask(before,after)
edit_scope=mk_mask((w,h),[r["localized_bbox"] for r in fails]+[r["localized_bbox"] for r in recs])
collateral=nz(ImageChops.multiply(changed,ImageOps.invert(edit_scope)))
all_cells=mk_mask((w,h),[r["sprite_cell"] for r in rows])
outside_cells=nz(ImageChops.multiply(changed,ImageOps.invert(all_cells)))
introduced=nz(ImageChops.multiply(ImageChops.subtract(after.getchannel("A"),before.getchannel("A")),ImageOps.invert(all_cells)))
if failed or collateral or outside_cells or introduced:
    print(json.dumps({"failed":failed,"collateral_pixels":collateral,"outside_cells_changed_pixels":outside_cells,"introduced_alpha_outside_cells":introduced},ensure_ascii=False,indent=2))
    raise SystemExit("strict post-QA failed; candidate not written")

out=cb[:128]+after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA")
parse(out)
if out[:128]!=sb[:128] or len(out)!=len(cb): raise SystemExit("structure changed")
newsha=sha(out); oldsha=sha(cb)
if newsha==oldsha: raise SystemExit("no change")

# Create a focused visual proof for the six resampled START/GOAL rows and representative
# no-resample rows. The proof is evidence only; DDS is the deployable candidate.
RUN_DIR.mkdir(parents=True,exist_ok=True)
focus_keys={"BAD_NAME","DELETE_ACCOUNT_BIG","START_1","GOAL_1","START_2","GOAL_2","START_3","GOAL_3"}
focus=[r for r in recs if r["key"] in focus_keys]
tiles=[]
for r in focus:
    o=r["original_bbox"]; pad=12
    x0=max(0,o[0]-pad); y0=max(0,o[1]-pad); x1=min(w-1,o[2]+pad); y1=min(h-1,o[3]+pad)
    b=before.crop((x0,y0,x1+1,y1+1)); a=after.crop((x0,y0,x1+1,y1+1))
    bw=Image.new("RGBA",b.size,(255,255,255,255)); bw.alpha_composite(b)
    aw=Image.new("RGBA",a.size,(255,255,255,255)); aw.alpha_composite(a)
    tile=Image.new("RGB",(bw.width+aw.width,max(bw.height,aw.height)+18),"white")
    tile.paste(bw.convert("RGB"),(0,18)); tile.paste(aw.convert("RGB"),(bw.width,18))
    ImageDraw.Draw(tile).text((2,2),r["key"]+"  before | after",fill="black")
    tiles.append(tile)
qa_w=max(t.width for t in tiles); qa_h=sum(t.height for t in tiles)
sheet=Image.new("RGB",(qa_w,qa_h),"white"); yy=0
for t in tiles: sheet.paste(t,(0,yy)); yy+=t.height
sheet.save(QA_PNG)

CANDIDATE.write_bytes(out)
now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={
 "schema_version":1,"role":"A","run":"A_AUTO_00001_FF2462BB","task_id":TASK_ID,
 "timestamp_kst":now,"base_head":os.environ.get("GITHUB_SHA"),"asset":str(CANDIDATE.relative_to(ROOT)),
 "index":INDEX,"previous_candidate_sha256":oldsha,"candidate_sha256":newsha,
 "structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "reworked_elements":recs,
 "qa":{"elements_reworked":len(recs),"failed_elements":0,"collateral_pixels":collateral,
       "changed_pixels_outside_all_declared_cells":outside_cells,"introduced_alpha_outside_all_declared_cells":introduced,
       "visual_proof":str(QA_PNG.relative_to(ROOT)),
       "style_preservation":"15 rows no broad resampling; only minimum-fit rows resampled"},
 "automation_validation":"PASS","runtime_validation":"UNTESTED","final_approval":False,
 "build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False
}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")

# asset_queue.csv currently contains historical rows with extra unquoted fields that
# parse as DictReader key None. Do not rewrite that shared ledger from this production
# action; progress/resume/report carry the durable A result without risking CSV loss.
pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8"))
p["updated_at_kst"]=now
p.setdefault("graphics",{})["latest_a_production"]={"run":"A_AUTO_00001_FF2462BB","task_id":TASK_ID,"report":str(REPORT.relative_to(ROOT)),"assets":{ASSET:{"candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_VISUAL_INGAME"}}}
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")

rp=ROOT/"localization/resume_state.json"; rs=json.loads(rp.read_text("utf-8"))
rs["schema_version"]=int(rs.get("schema_version",55))+1
rs.setdefault("next_actions",[]).insert(0,"A AUTO 00001: FF2462BB containment self-QA PASS; pending independent C visual/source-style review and DDS_ONLY in-game.")
rs.setdefault("graphics_checkpoint",{})["a_auto_00001_ff2462bb"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),"candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_VISUAL_INGAME"}
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")

sp=ROOT/"localization/progress/STATUS.md"
sp.write_text(sp.read_text("utf-8")+f"\n\n### A AUTO 00001 FF2462BB {now}\n- Index 51 FF2462BB: 21 C85 bbox failures repaired with no broad shrink; no-resample translation/trim wherever possible, minimum-fit scaling only where required.\n- Automated containment 21/21 PASS; outside/collateral 0. Candidate {newsha}.\n- Visual proof: {QA_PNG.relative_to(ROOT)}. Independent C source-style/artifact QA + DDS_ONLY in-game remain required.\n- AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED.\n","utf-8")

with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - A AUTO 00001 FF2462BB\n- GitHub-only index 51 FF2462BB rework; no N100/GPT Library/VR/FFB/build.\n- Repaired 21 exact-bbox failures without B91-style broad shrink: translate/trim without resampling where possible; only minimum-fit rows resampled.\n- Automated containment 21/21 PASS, outside/collateral 0; candidate {newsha}.\n- Independent C visual/source-style QA and isolated DDS_ONLY in-game pending; RUNTIME_VALIDATION=UNTESTED.\n")
