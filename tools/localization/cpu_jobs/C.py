#!/usr/bin/env python3
"""C306 C2 EVEN q154: native lossless gray-menu SRC/CLEAN/FINAL orientation and practical-size evidence only.
No image may be labeled PASS by this compute worker. Final independent visual verdict is controller-owned.
"""
import hashlib, json, os, subprocess, urllib.request
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER") == "github-actions"
assert os.getenv("OUTRUN_CPU_ROLE") == "C"
T = json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","154"],capture_output=True,text=True,check=True).stdout)
assert T["assets"][0]["next_action"] == "EVIDENCE_ONLY_HOLD", T
q = Path("localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "154,textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds" in q
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
srcb=urllib.request.urlopen(source_url,timeout=180).read()
finb=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds").read_bytes()
cleanb=Path("localization/graphics/role_B/20261005-B-PRODUCTION60/4D38_HD_CLEAN_PLATE.png").read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
expected={"source":"15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf","clean":"a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380","final":"94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"}
assert (sha(srcb),sha(cleanb),sha(finb)) == (expected["source"],expected["clean"],expected["final"])
assert srcb[:128]==finb[:128], "DDS headers differ"
s=np.flipud(np.asarray(Image.open(BytesIO(srcb)).convert("RGBA"))).copy()
f=np.flipud(np.asarray(Image.open(BytesIO(finb)).convert("RGBA"))).copy()
clean=np.asarray(Image.open(BytesIO(cleanb)).convert("RGBA")).copy()
assert s.shape==f.shape==clean.shape==(1024,4096,4)
specs=[
 ("06_single_player_gray","SINGLE PLAYER","싱글 플레이",(1610,286,2197,350)),
 ("07_showroom_gray","SHOWROOM","쇼룸",(2674,288,3094,350)),
 ("08_multiplayer_gray","MULTIPLAYER","멀티플레이",(2566,952,3086,1014))]
out=Path("localization/graphics/role_C/20261008-C306-C2-Q154-GRAY-LOSSLESS-100-75-50")
out.mkdir(parents=True,exist_ok=True)
rows=[]
def composed(a,rgb):
 rgba=Image.fromarray(a,"RGBA")
 return Image.alpha_composite(Image.new("RGBA",rgba.size,(*rgb,255)),rgba).convert("RGB")
for rid,english,korean,(l,t,r,b) in specs:
 src=s[t:b,l:r].copy();plate=clean[t:b,l:r].copy();fin=f[t:b,l:r].copy()
 assert not np.any(plate[:,:,3]),rid
 assert np.array_equal(np.flipud(s)[1024-b:1024-t,l:r][::-1],src)
 sw=r-l; ht=b-t
 reg={"id":rid,"source_text":english,"korean":korean,"bbox_readable":[l,t,r,b],"raw_bbox":[l,1024-b,r,1024-t],
  "exact_source_sha256":expected["source"],"exact_clean_sha256":expected["clean"],"exact_candidate_sha256":expected["final"],
  "clean_nonzero_alpha":int(np.count_nonzero(plate[:,:,3])),
  "source_nonzero_alpha":int(np.count_nonzero(src[:,:,3])),"final_nonzero_alpha":int(np.count_nonzero(fin[:,:,3])),
  "source_clean_rgba_changed":int(np.count_nonzero(np.any(src!=plate,axis=2))),
  "clean_final_rgba_changed":int(np.count_nonzero(np.any(plate!=fin,axis=2))),
  "source_final_rgba_changed":int(np.count_nonzero(np.any(src!=fin,axis=2))),
  "source_final_alpha_changed":int(np.count_nonzero(src[:,:,3]!=fin[:,:,3])),
  "final_opaque_alpha_245":int(np.count_nonzero(fin[:,:,3]>=245)),
  "source_opaque_alpha_245":int(np.count_nonzero(src[:,:,3]>=245)),
  "decode_header_exact":True,"source_clean_final_pngs":[]}
 for bgname,bgc in (("BLACK",(16,16,16)),("GRAY",(96,96,96)),("WHITE",(245,245,245))):
  panel=Image.new("RGB",(sw*3,ht+25),(26,26,26))
  d=ImageDraw.Draw(panel)
  for idx,(name,rgba) in enumerate((("EXACT SOURCE",src),("AUTHORED CLEAN",plate),("PERSISTED FINAL",fin))):
   panel.paste(composed(rgba,bgc),(idx*sw,25));d.text((idx*sw+3,5),name,fill="white")
  for scale,mode in ((1.0,"100"),(0.75,"75"),(0.5,"50")):
   o=panel if scale==1.0 else panel.resize((max(1,int(round(panel.width*scale))),max(1,int(round(panel.height*scale)))),Image.Resampling.LANCZOS)
   name=f"{rid}_{bgname}_{mode}pct_SOURCE_CLEAN_FINAL.png"
   o.save(out/name);reg["source_clean_final_pngs"].append({"path":str(out/name),"scale":mode,"background":bgname,"sha256":sha((out/name).read_bytes())})
 # RAW independent DDS data: proof of matching Y inversion for original and final, not an in-game UV verdict.
 raw_s=np.flipud(src);raw_f=np.flipud(fin)
 raw=Image.new("RGB",(sw*2,ht+25),(26,26,26))
 for i,(lab,a) in enumerate((("ORIGINAL RAW",raw_s),("FINAL RAW",raw_f))):
  raw.paste(composed(a,(96,96,96)),(i*sw,25));ImageDraw.Draw(raw).text((i*sw+3,5),lab,fill="white")
 n=f"{rid}_RAW_ORIENTATION.png";raw.save(out/n);reg["raw_preview"]={"path":str(out/n),"sha256":sha((out/n).read_bytes())}
 # Numeric color/alpha coverage: not a font-family or visual PASS.
 reg["visual_decision"]="CONTROLLER_PENDING";rows.append(reg)
report={"run":"C306-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":154,
 "policy_version":"visual-evidence-v1-20261008","triage":T["assets"][0],
 "exact_shas":expected,"dds_headers_identical":True,
 "evidence_kind":"NEW native 100/75/50 original/authored CLEAN/persisted DDS black-gray-white plus RAW; 3 gray rows only",
 "prior_C305_evidence_not_repeated":"All 8 rows and background 50%-fit existed; this provides full native and independent practical-size lossless evidence for faint gray 3 rows.",
 "per_region":rows,"C":"HOLD_PENDING_INDEPENDENT_VISUAL_AND_BLIND_CALIBRATION","C3":"NOT_APPROVED",
 "RUNTIME_VALIDATION":"UNTESTED","no_candidate_changes":True}
(out/"C306_Q154_GRAY_NATIVE_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C306","regions":len(rows),"png_count":sum(len(z["source_clean_final_pngs"])+1 for z in rows),
 "output":str(out),"result":"EVIDENCE_ONLY_CONTROLLER_PENDING"},ensure_ascii=False))
