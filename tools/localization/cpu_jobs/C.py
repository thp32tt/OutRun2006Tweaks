#!/usr/bin/env python3
"""C316 C1 P0 q121: independently pin 2026-10-09 in-game failures to actual native DDS.

Generate clean/source/current proof, not automatic game/C approvals. Used solely
because the local sandbox cannot acquire remote binary DDS inputs (DNS unavailable).
"""
import io,json,hashlib,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="C"
root=Path.cwd();index=121
asset="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
out=root/"localization/graphics/role_C/20261009-C316-C1-Q121-IGR030-031-040-P0-NATIVE"
sha=lambda b:hashlib.sha256(b).hexdigest()
queue=(root/"localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "121,"+asset+",localize_text,user_ingame_20261009_rework_required" in queue,"q121 no longer P0 rework, stop"
tri=json.loads(subprocess.check_output(["python","tools/localization/rework_triage.py","--index","121"],text=True))["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri
en_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
ko_sha="d1bb0c7cc22a398b47085445787bc15fc10db1125b5298d1c38d1f5deaf7dc27"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
source=urllib.request.urlopen(source_url,timeout=120).read()
current=(root/"localization/graphics/hd_candidates"/asset).read_bytes()
assert sha(source)==en_sha and sha(current)==ko_sha,(sha(source),sha(current))
assert source[:128]==current[:128]
def decode(b):
 assert b[:4]==b"DDS " and b[84:88]==bytes(4) and len(b)==128+4096*4096*4
 h,w=struct.unpack_from("<II",b,12)
 m=struct.unpack_from("<I",b,28)[0]
 mode={(255,65280,16711680,4278190080):"RGBA",(16711680,65280,255,4278190080):"BGRA"}[struct.unpack_from("<IIII",b,92)]
 assert (w,h,m)==(4096,4096,1)
 return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=decode(source);final=decode(current)
clean_path=root/"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png"
clean=Image.open(clean_path).convert("RGBA")
assert src.size==final.size==clean.size==(4096,4096)
sc=np.asarray(src);fi=np.asarray(final);cl=np.asarray(clean)
bboxes=[("select_game_mode","Select Game Mode","게임 모드 선택",(166,819,1166,973),(341,846,990,945)),
("select_car","Select your car","차량 선택",(243,947,1156,1111),(485,979,913,1078)),
("select_course","Select Course","코스 선택",(302,1062,1085,1213),(478,1088,908,1187))]
allow=np.zeros((4096,4096),dtype=bool)
for key,en,ko,bb,kb in bboxes:
 x0,y0,x1,y1=bb;allow[y0:y1,x0:x1]=True
 assert 0<x0<kb[0]<kb[2]<x1<4096 and 0<y0<kb[1]<kb[3]<y1<4096
 assert int(np.count_nonzero(cl[y0:y1,x0:x1,3]))==0,(key,"clean alpha not zero")
outside=np.any(cl!=fi,axis=2)&~allow
outside_alpha=(cl[:,:,3]!=fi[:,:,3])&~allow
assert not outside.any() and not outside_alpha.any(),(int(outside.sum()),int(outside_alpha.sum()))
out.mkdir(parents=True,exist_ok=True)
def view(im,bg):
 plate=Image.new("RGBA",im.size,(*bg,255));plate.alpha_composite(im);return plate.convert("RGB")
manifest=[];regions=[]
def add(name,img):
 fp=out/name;img.save(fp)
 manifest.append({"path":str(fp.relative_to(root)),"sha256":sha(fp.read_bytes()),"bytes":fp.stat().st_size})
for idx,(key,en,ko,bb,kb) in enumerate(bboxes):
 x0,y0,x1,y1=bb;z=(max(0,x0-24),max(0,y0-24),min(4096,x1+24),min(4096,y1+24))
 crops=[src.crop(z),clean.crop(z),final.crop(z)]
 # Verify RAW really reflects persisted DDS vertical flip, not an invented orientation.
 raws=[img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((z[0],4096-z[3],z[2],4096-z[1])) for img in (src,clean,final)]
 for img,raw in zip(crops,raws):assert ImageChops.difference(raw,img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)).getbbox() is None
 for stage,im,raw in zip(("SOURCE","CLEAN","CURRENT"),crops,raws):
  add(f"C316_Q121_{idx}_{key}_{stage}_NATIVE.png",im)
  add(f"C316_Q121_{idx}_{key}_{stage}_RAW.png",raw)
 for bgname,color in (("BLACK",(0,0,0)),("GRAY",(127,127,127)),("WHITE",(245,245,245))):
  for pct in (100,75,50):
   panels=[view(im,color) for im in crops]
   if pct!=100:panels=[p.resize((max(1,p.width*pct//100),max(1,p.height*pct//100)),Image.Resampling.LANCZOS) for p in panels]
   w,h=panels[0].size
   board=Image.new("RGB",(3*w+16,h+28),"white");d=ImageDraw.Draw(board)
   d.text((4,4),f"EN | A176 CLEAN | PERSISTED KO | {key} | {bgname} {pct}%",fill="black")
   for k,p in enumerate(panels):board.paste(p,(k*(w+8),28))
   add(f"C316_Q121_{idx}_{key}_SCF_{bgname}_{pct}.png",board)
 # Numeric SOURCE face bbox includes shadows/protected effects, do not call font-metric equality.
 srcbox=[x0,y0,x1,y1];cw=kb[2]-kb[0];ch=kb[3]-kb[1]
 regions.append({"id":key,"english":en,"ko":ko,"source_effect_bbox":list(bb),"candidate_effect_bbox":list(kb),
 "source_size":[x1-x0,y1-y0],"candidate_size":[cw,ch],
 "source_height_coverage_ratio":round(ch/(y1-y0),4),"source_width_coverage_ratio":round(cw/(x1-x0),4),
 "margins":[kb[0]-x0,x1-kb[2],kb[1]-y0,y1-kb[3]],
 "source_current_exact_byte_identity":"PINNED_SHA","clean_alpha_in_source_region":0,
 "clean_to_final_changed_outside_exact_union":0})
# Verify neither source-only title effects nor unrelated lower-level silhouettes can be misread as runtime composition.
counts={"clean_to_current_rgba_outside_original_header_union":int(outside.sum()),
"clean_to_current_alpha_outside_original_header_union":int(outside_alpha.sum()),
"src_current_rgba_changed_inside_headers":int((np.any(sc!=fi,axis=2)&allow).sum()),
"src_current_rgba_changed_outside_header_union":int((np.any(sc!=fi,axis=2)&~allow).sum()),
"clean_to_current_changed_inside_headers":int((np.any(cl!=fi,axis=2)&allow).sum())}
report={"schema_version":1,"review_id":"C316-C1-Q121-20261009-IGR030-031-040",
"TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
"queue_index":121,"user_regressions":["IGR-030","IGR-031","IGR-040"],"asset":asset,"source_sha256":en_sha,
"candidate_sha256":ko_sha,"A176_author_clean_path":str(clean_path.relative_to(root)),"candidate_not_changed":True,
"dds_native_dimensions":[4096,4096],"mips":1,"raw_orientation":"mirror_y","source_url":source_url,
"triage":tri,"regions":regions,"pixel_counts":counts,
"lossless_images_new":len(manifest),"manifest":manifest,
"limitation":"No user marked screenshot bytes are in repository. Inspect exact native persisted source, authored clean, current against the user's already registered IGR defect. Static atlas cannot resolve actual game screen compositor clipping nor protected Dino vehicle-model art without exact source ID mapping.",
"independent_C":"PENDING_CONTROLLER_VISUAL_DECISION","C3":"BLOCKED_INGAME_USER_FAIL","APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED","new_dds":0}
(out/"C316_Q121_MACHINE_AND_LOSSLESS_MANIFEST.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("C316_Q121_DONE",json.dumps({"source_sha":en_sha,"candidate_sha":ko_sha,"new_png":len(manifest),"regions":regions,"pixels":counts},ensure_ascii=False),flush=True)
