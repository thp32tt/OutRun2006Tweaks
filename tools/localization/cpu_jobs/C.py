#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")

repo=Path.cwd()
run="20261006-C221-37759842-A83"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
source_sha="7b41a04e2b0736717dd0da4d82f9e18f3aac7c469a5738848c5cfa6bf28e15b5"
candidate_sha_expected="2dac8ee099120f2978eaf8ba992ffff11ecad7c11912a98aca9269a1a78f6988"
a81_dir=repo/"localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX"
a83_dir=repo/"localization/graphics/role_A/20261006-A-PRODUCTION83-C219-TRANSFORM"
r81=json.loads((a81_dir/"A81_37759842_REPORT.json").read_text(encoding="utf-8"))
r83=json.loads((a83_dir/"A83_37759842_REPORT.json").read_text(encoding="utf-8"))
clean=Image.open(a81_dir/"37759842_HD_CLEAN_PLATE.png").convert("RGBA")
old=Image.open(a81_dir/"37759842_HD_FINAL_DECODED_READABLE.png").convert("RGBA")
core=Image.open(a81_dir/"37759842_HD_SOURCE_CORE_MASK.png").convert("L")
protected=Image.open(a81_dir/"37759842_HD_PROTECTED_VISIBLE_MASK.png").convert("L")
targets=r83["rows"]
if len(targets)!=16: raise RuntimeError(("A83 target rows",len(targets)))

def sha256(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def flatten(im):
    bg=Image.new("RGBA",im.size,(92,92,92,255)); bg.alpha_composite(im); return bg.convert("RGB")

tmp=Path("/tmp/c221"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
urllib.request.urlretrieve(
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",
 srcdds)
sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha256(sb)!=source_sha: raise RuntimeError(("source SHA",sha256(sb)))
if sha256(cb)!=candidate_sha_expected: raise RuntimeError(("candidate SHA",sha256(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",cb,12)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1): raise RuntimeError((W,H,pitch,depth,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
final_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
final=final_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(final,Image.open(a83_dir/"37759842_A83_FINAL_READABLE.png").convert("RGBA")).getbbox() is not None:
    raise RuntimeError("A83 decoded evidence drift")

allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
row_checks=[]; render_union=Image.new("L",(W,H),0)
for row in targets:
    x0,y0,x1,y1=map(int,row["source_effect_bbox"])
    ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
    rm=dmask(clean.crop((x0,y0,x1,y1)),final.crop((x0,y0,x1,y1)))
    bb=rm.getbbox()
    lb=[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]] if bb else None
    prod=list(map(int,row["localized_bbox"]))
    sw,sh=x1-x0,y1-y0
    lw,lh=(lb[2]-lb[0],lb[3]-lb[1]) if lb else (0,0)
    contain=bool(lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1)
    size=bool(lb and lw<=sw and lh<=sh)
    exact=(lb==prod)
    full=Image.new("L",(W,H),0); full.paste(rm,(x0,y0)); render_union=ImageChops.lighter(render_union,full)
    row_checks.append({"idx":int(row["idx"]),"kind":row["kind"],"source_effect_bbox":[x0,y0,x1,y1],
      "producer_localized_bbox":prod,"independent_localized_bbox":lb,"bbox_exact_match":exact,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-x0 if lb else None,"delta_right":x1-lb[2] if lb else None,
      "delta_top":lb[1]-y0 if lb else None,"delta_bottom":y1-lb[3] if lb else None,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL",
      "positive_margin":"PASS" if contain else "FAIL","producer_lines":row.get("lines",[])})

# A83 must alter only C219-returned 16 transform rows relative to A81.
a81_diff=dmask(old,final)
outside=int(count(ImageChops.multiply(a81_diff,ImageOps.invert(allowed))))
alpha_diff=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A")))
alpha_out=int(count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed))))
protected_changed=int(count(ImageChops.multiply(dmask(src,final),protected)))
# A81 clean plate must still remove source core; final exact-source residue is checked outside A83 Korean render.
same=ImageOps.invert(dmask(src,final))
core_touched=ImageChops.multiply(core,allowed)
guard=render_union.filter(ImageFilter.MaxFilter(5))
residue=int(count(ImageChops.multiply(core_touched,ImageChops.multiply(same,ImageOps.invert(guard)))))
bbox_mismatch=sum(1 for r in row_checks if not r["bbox_exact_match"])
row_fail=sum(1 for r in row_checks if r["containment"]!="PASS" or r["size_ceiling"]!="PASS" or r["positive_margin"]!="PASS")
# Lines inside each row must not overlap each other.
line_overlap=0
for row in targets:
    ms=[]
    for lm in row.get("lines",[]):
        x0,y0,x1,y1=map(int,lm["localized_bbox"])
        m=Image.new("L",(W,H),0); ImageDraw.Draw(m).rectangle((x0,y0,x1-1,y1-1),fill=255)
        ms.append(m)
    for i in range(len(ms)):
        for j in range(i+1,len(ms)):
            if count(ImageChops.multiply(ms[i],ms[j])): line_overlap+=1

status="PASS" if all(v==0 for v in (outside,alpha_out,protected_changed,residue,bbox_mismatch,row_fail,line_overlap)) else "FAIL"

# Independent readable and raw evidence.
font=None
try:
    import subprocess
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR"],text=True).strip()
    fp,fi=q.rsplit("|",1); font=ImageFont.truetype(fp,18,index=int(fi or 0))
except Exception:
    font=ImageFont.load_default()
cards=[]
for row in targets:
    ob=list(map(int,row["source_effect_bbox"])); x0,y0,x1,y1=ob; pad=12
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[flatten(z.crop(box)) for z in (src,clean,old,final)]
    scaled=[]
    for q in ims:
        sc=min(1.0,165/max(1,q.height),330/max(1,q.width))
        scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+18; ch=max(q.height for q in scaled)+26
    card=Image.new("RGB",(cw,ch),(230,230,230)); d=ImageDraw.Draw(card)
    d.text((3,3),f"idx{row['idx']} SOURCE | CLEAN | A81 | A83",font=font,fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,26)); xx+=q.width+6
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(225,225,225)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.save(out/"C221_A83_TRANSFORM_CONTACTS.jpg",quality=94)

rawcmp=Image.new("RGB",(2048,1024),(90,90,90))
rawcmp.paste(flatten(src_raw).resize((1024,1024),Image.Resampling.LANCZOS),(0,0))
rawcmp.paste(flatten(final_raw).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0))
rawcmp.save(out/"C221_A83_RAW_COMPARE.jpg",quality=94)

report={"schema_version":1,"role":"C","run":run,"qa_id":"C221","queue_index":95,"asset":asset_rel,
 "producer_run":r83["run"],"source_sha256":source_sha,"candidate_sha256":candidate_sha_expected,
 "user_ingame_regressions":["IGR-014","IGR-015","IGR-016"],
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":sb[:128]==cb[:128],"raw_orientation":"mirror_y"},
 "independent_basis":"canonical source DDS + current A83 candidate DDS + A81 clean/core/protected evidence; all 16 C219-returned localized bboxes independently re-derived from clean-to-final decoded pixels",
 "row_checks":row_checks,
 "machine_checks":{"changes_outside_c219_returned_rows_vs_a81":outside,
   "alpha_changes_outside_c219_returned_rows_vs_a81":alpha_out,
   "protected_source_pixels_changed":protected_changed,
   "source_core_residue_outside_a83_korean_render":residue,
   "localized_bbox_mismatches":bbox_mismatch,"row_containment_size_margin_failures":row_fail,
   "declared_line_bbox_overlap_pairs":line_overlap},
 "machine_status":status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C221_REWORK_REQUIRED_MACHINE_GATE",
 "candidate_changed_by_C":False,"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "preview_files":[str((out/"C221_A83_TRANSFORM_CONTACTS.jpg").relative_to(repo)),str((out/"C221_A83_RAW_COMPARE.jpg").relative_to(repo))]}
(out/"C221_37759842_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C221_37759842.json").write_text(json.dumps({"run":run,"qa_id":"C221","index":95,"asset":"37759842",
 "candidate_sha256":candidate_sha_expected,"machine_status":status,"machine_checks":report["machine_checks"],
 "report":str((out/"C221_37759842_MACHINE_QA.json").relative_to(repo)),"runtime_validation":"PENDING_NEW_INGAME_RETEST"},
 ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"machine_status":status,"candidate_sha256":candidate_sha_expected,"checks":report["machine_checks"]},ensure_ascii=False,indent=2))
if status!="PASS": raise SystemExit(2)
