#!/usr/bin/env python3
"""C318 C1 q121: independent persisted-DDS source/CLEAN/A199 exact-SHA P0 review.

No machine PASS means visual approval or in-game validation.
"""
import io,os,json,hashlib,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
root=Path.cwd()
asset="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
status=(root/"localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "121,"+asset+",localize_text,user_ingame_p0_rework_required_a199_candidate_pending_c1_c3_game" in status
tri=json.loads(subprocess.check_output(["python","tools/localization/rework_triage.py","--index","121"],text=True))["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","FRESH_C_REVIEW"),tri
SH=lambda b:hashlib.sha256(b).hexdigest()
source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
final_sha="4e84afccc41dcb221a9c6eb164f0f82b15c52277647f122555e05e445a3de4d8"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
source=urllib.request.urlopen(source_url,timeout=120).read()
final=(root/"localization/graphics/hd_candidates"/asset).read_bytes()
assert SH(source)==source_sha and SH(final)==final_sha and source[:128]==final[:128]
def decode(b):
 assert b[:4]==b"DDS " and b[84:88]==bytes(4) and len(b)==128+4096*4096*4
 h,w=struct.unpack_from("<II",b,12)
 m=struct.unpack_from("<I",b,28)[0]
 masks=struct.unpack_from("<IIII",b,92)
 mode={(255,65280,16711680,4278190080):"RGBA",(16711680,65280,255,4278190080):"BGRA"}[masks]
 assert (w,h,m)==(4096,4096,1)
 return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=decode(source); fin=decode(final)
cleanpath=root/"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png"
clean=Image.open(cleanpath).convert("RGBA")
assert clean.size==src.size==fin.size
S=np.asarray(src);C=np.asarray(clean);F=np.asarray(fin)
regions=[
 ("select_game_mode","Select Game Mode","게임 모드 선택",(166,819,1166,973),(291,825,1040,948)),
 ("select_car","Select your car","차량 선택",(243,947,1156,1111),(481,964,917,1072)),
 ("select_course","Select Course","코스 선택",(302,1062,1085,1213),(462,1088,924,1202))]
allowed=np.zeros((4096,4096),dtype=bool)
for k,en,ko,box,glyphbox in regions:
 l,t,r,b=box;allowed[t:b,l:r]=True
 assert l<glyphbox[0]<glyphbox[2]<r and t<glyphbox[1]<glyphbox[3]<b
 assert np.count_nonzero(C[t:b,l:r,3])==0,("not a clean plate",k)
diff=np.any(C!=F,axis=2);alphadiff=C[:,:,3]!=F[:,:,3]
counts={"clean_final_rgba_outside_exact_region_union":int((diff&~allowed).sum()),
"clean_final_alpha_outside_exact_region_union":int((alphadiff&~allowed).sum()),
"clean_final_rgba_inside_exact_region_union":int((diff&allowed).sum()),
"source_clean_rgba_outside_exact_region_union":int((np.any(S!=C,axis=2)&~allowed).sum()),
"source_final_rgba_outside_exact_region_union":int((np.any(S!=F,axis=2)&~allowed).sum())}
assert counts["clean_final_rgba_outside_exact_region_union"]==0 and counts["clean_final_alpha_outside_exact_region_union"]==0
# SOURCE/CLEAN may differ outside due other earlier localized atlas cells. Do not assert zero there.
def bgview(p,color):
 plate=Image.new("RGBA",p.size,(*color,255));plate.alpha_composite(p);return plate.convert("RGB")
out=root/"localization/graphics/role_C/20261009-C318-C1-Q121-A199-P0-NEW-SHA"
out.mkdir(parents=True,exist_ok=True)
files=[]
def save(name,im):
 f=out/name;im.save(f);files.append({"path":str(f.relative_to(root)),"sha256":SH(f.read_bytes()),"bytes":f.stat().st_size})
details=[]
for i,(k,en,ko,box,glyphbox) in enumerate(regions):
 l,t,r,b=box
 crop=(max(0,l-24),max(0,t-24),min(4096,r+24),min(4096,b+24))
 tiles=[im.crop(crop) for im in (src,clean,fin)]
 for stage,p in zip(("SOURCE","CLEAN","A199"),tiles):
  save(f"C318_q121_{k}_{stage}_NATIVE.png",p)
  mirror=im=None
  mirror=p.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  save(f"C318_q121_{k}_{stage}_RAW.png",mirror)
 # Check raw output isn't just a duplicate of native view
 assert np.array_equal(np.asarray(tiles[2].transpose(Image.Transpose.FLIP_TOP_BOTTOM)),np.asarray(mirror))
 for pct in (100,75,50):
  for cname,color in (("BLACK",(0,0,0)),("GRAY",(127,127,127)),("WHITE",(245,245,245))):
   cells=[bgview(p,color) for p in tiles]
   if pct!=100:cells=[p.resize((p.width*pct//100,p.height*pct//100),Image.Resampling.LANCZOS) for p in cells]
   w,h=cells[0].size
   board=Image.new("RGB",(w*3+24,h+26),"white")
   draw=ImageDraw.Draw(board)
   for j,(lbl,p) in enumerate(zip(("EN_SOURCE","A176_CLEAN","A199_NEW_SHA"),cells)):
    board.paste(p,(j*(w+12),26))
    draw.text((j*(w+12)+3,3),lbl,fill=(0,0,0))
   save(f"C318_q121_{k}_SCF_{cname}_{pct}.png",board)
 m=[glyphbox[0]-l,r-glyphbox[2],glyphbox[1]-t,b-glyphbox[3]]
 assert min(m)>0
 details.append({"id":k,"english":en,"korean":ko,"source_original_bbox":box,
 "A199_candidate_bbox":glyphbox,"source_size":[r-l,b-t],
 "A199_size":[glyphbox[2]-glyphbox[0],glyphbox[3]-glyphbox[1]],
 "source_relative_width_ratio":round((glyphbox[2]-glyphbox[0])/(r-l),4),
 "source_relative_height_ratio":round((glyphbox[3]-glyphbox[1])/(b-t),4),
 "positive_margins":m,"CLEAN_alpha_in_source_box":0})
report={"schema_version":1,"TASK_ID":"OUTRUN-KOR-C318-C1-Q121-A199-NEW-SHA-NATIVE-20261009",
"TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","queue_index":121,
"p0_regressions":["IGR-030","IGR-031","IGR-040"],"triage":tri,
"canonical_source_url":source_url,"source_sha256":source_sha,"candidate_sha256":final_sha,
"supersedes_old_C316_SHA":"d1bb0c7cc22a398b47085445787bc15fc10db1125b5298d1c38d1f5deaf7dc27",
"structure":{"width":4096,"height":4096,"format":"RGBA32","mips":1,"raw_orientation":"mirror_y","header_equal":True},
"clean_provenance":str(cleanpath.relative_to(root)),"metrics":counts,"rows":details,
"new_lossless_png":len(files),"manifest":files,
"limit":"This is current persisted-DDS evidence only, not scene-composed runtime proof or blind calibration; annotated screenshot black outlines cannot prove native sprite box residues",
"C":"PENDING_INDEPENDENT_CONTROLLER","C3":"NOT_APPROVED",
"USER_RETEST":"NOT_PERFORMED","RUNTIME_VALIDATION":"UNTESTED","new_DDS":0}
(out/"C318_Q121_A199_INDEPENDENT_MACHINE_PROOF.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C318_C1_Q121",json.dumps({"source":source_sha,"candidate":final_sha,"new_PNG":len(files),"rows":details,"metrics":counts},ensure_ascii=False),flush=True)
