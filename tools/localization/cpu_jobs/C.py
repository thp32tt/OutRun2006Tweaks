#!/usr/bin/env python3
"""C312 C1 odd q103 fresh independent evidence; no auto visual or game approval."""
import io, json, os, hashlib, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
root=Path.cwd()
asset="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
qtext=(root/"localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "103,"+asset+",localize_text,a197_producer_self_qa_pass_pending_fresh_c1_c3" in qtext,"new queue selection appeared: stop"
tri=json.loads(subprocess.check_output(["python","tools/localization/rework_triage.py","--index","103"],text=True))["assets"][0]
assert tri["next_action"]=="FRESH_C_REVIEW",tri
expected={"source":"76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544",
"candidate":"9702957a9c6498877433bb6ff2e112647445d271ddce27bb3e37f3a076c8b1ed"}
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
sha=lambda b:hashlib.sha256(b).hexdigest()
source=urllib.request.urlopen(url,timeout=90).read()
candidate=(root/"localization/graphics/hd_candidates"/asset).read_bytes()
assert sha(source)==expected["source"] and sha(candidate)==expected["candidate"]
assert source[:128]==candidate[:128] and len(source)==len(candidate)
def decode(b):
 assert b[:4]==b"DDS " and b[84:88]==bytes([0])*4
 h,w=struct.unpack_from("<II",b,12);m=struct.unpack_from("<I",b,28)[0]
 assert (w,h,m)==(2048,2048,1) and len(b)==128+w*h*4
 masks=struct.unpack_from("<IIII",b,92)
 mode={(255,65280,16711680,4278190080):"RGBA",(16711680,65280,255,4278190080):"BGRA"}[masks]
 return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
S=decode(source);F=decode(candidate)
p=root/"localization/graphics/role_A/20261006-A-PRODUCTION108-590A4724"
C=Image.open(p/"A108_CLEAN_PLATE.png").convert("RGBA")
P=Image.open(p/"A108_FINAL_READABLE.png").convert("RGBA")
S_ref=Image.open(p/"A108_SOURCE_READABLE.png").convert("RGBA")
assert not ImageChops.difference(S,S_ref).getbbox()
assert S.size==F.size==C.size==P.size
A=np.asarray(S);B=np.asarray(C);D=np.asarray(F);O=np.asarray(P)
box=[1411,1968,1801,2040];l,t,r,b=box
allowed=np.zeros(A.shape[:2],dtype=bool);allowed[t:b,l:r]=True
counts={}
for name,x,y in (("source_clean",A,B),("clean_final",B,D),("source_final",A,D),("old_final",O,D)):
 delta=np.any(x!=y,axis=2)
 counts[name]={"changed_rgba_total":int(delta.sum()),"changed_rgba_outside_source_bbox":int((delta&~allowed).sum()),
 "alpha_changed_outside_source_bbox":int(((x[:,:,3]!=y[:,:,3])&~allowed).sum())}
assert all(v["changed_rgba_outside_source_bbox"]==0 and v["alpha_changed_outside_source_bbox"]==0 for v in counts.values())
# The glyph sits on an opaque yellow selector: CLEAN must keep its backing plate.
# Independently measure text/effect changes relative to the exact original plate,
# never infer glyph outlines from the plate's nontransparent alpha.
assert int(np.count_nonzero(np.any(A[t:b,l:r]!=B[t:b,l:r],axis=2)))>3000,"no source glyph removed"
def bb(mask):
 yy,xx=np.where(mask)
 assert len(xx)
 return [int(xx.min())+l,int(yy.min())+t,int(xx.max()+1)+l,int(yy.max()+1)+t]
srcbb=bb(np.any(A[t:b,l:r]!=B[t:b,l:r],axis=2))
finbb=bb(np.any(D[t:b,l:r]!=B[t:b,l:r],axis=2))
oldbb=bb(np.any(O[t:b,l:r]!=B[t:b,l:r],axis=2))
assert srcbb==box and finbb==[1431,1972,1780,2036] and oldbb==[1508,1986,1704,2026],(srcbb,finbb,oldbb)
def bands(a):
 arr=a[t:b,l:r,3];y,x=np.nonzero(arr>=128)
 if len(y)<20:return None
 top=x[y<=np.quantile(y,.2)];bot=x[y>=np.quantile(y,.8)]
 return {"top_left_20pct_median":round(float(np.percentile(top,10)),2),"bottom_left_20pct_median":round(float(np.percentile(bot,10)),2),
 "horizontal_top_minus_bottom_left":round(float(np.percentile(top,10)-np.percentile(bot,10)),2),
 "method":"whole-line top/bottom percentiles, not source-glyph per-character slope; must not auto-accept slant"}
metrics={"source_bbox":srcbb,"old_bbox":oldbb,"current_bbox":finbb,
"margins":[finbb[0]-l,r-finbb[2],finbb[1]-t,b-finbb[3]],
"old_size":[oldbb[2]-oldbb[0],oldbb[3]-oldbb[1]],
"current_size":[finbb[2]-finbb[0],finbb[3]-finbb[1]],
"source_size":[r-l,b-t],
"old_source_width_ratio":round((oldbb[2]-oldbb[0])/(r-l),4),
"current_source_width_ratio":round((finbb[2]-finbb[0])/(r-l),4),
"source_slant_proxy":bands(A),"old_slant_proxy":bands(O),"new_slant_proxy":bands(D),
"clean_alpha_inside_plate":int(np.count_nonzero(B[t:b,l:r,3]))}
out=root/"localization/graphics/role_C/20261009-C312-C1-Q103-A197-INDEPENDENT-NATIVE"
out.mkdir(parents=True,exist_ok=True)
crop=(1380,1948,1820,2048)
def over(im,color):
 bg=Image.new("RGBA",im.size,(*color,255));bg.alpha_composite(im)
 return bg.convert("RGB")
files=[]
images=[("SOURCE",S),("CLEAN",C),("OLD_REJECTED",P),("CURRENT",F)]
for bgname,color in (("BLACK",(0,0,0)),("GRAY",(122,122,122)),("WHITE",(245,245,245))):
 for pct in (100,75,50):
  views=[]
  for key,im in images:
   v=over(im.crop(crop),color)
   if pct!=100:v=v.resize((max(1,v.width*pct//100),max(1,v.height*pct//100)),Image.Resampling.LANCZOS)
   views.append(v)
  w,h=views[0].size
  canvas=Image.new("RGB",(4*w+24,h+28),"white")
  dr=ImageDraw.Draw(canvas)
  for j,(key,_) in enumerate(images):
   dr.text((j*(w+8)+4,5),key,fill="black");canvas.paste(views[j],(j*(w+8),28))
  fn=out/f"C312_Q103_SC_PAST_FINAL_{bgname}_{pct}.png";canvas.save(fn);files.append(fn)
for name,im in images:
 for mode in ("READABLE","RAW"):
  v=im if mode=="READABLE" else im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  if mode=="RAW":v=v.crop((1380,0,1820,100))
  else:v=v.crop(crop)
  fn=out/f"C312_Q103_{name}_{mode}_LOSSLESS.png";v.save(fn);files.append(fn)
# Exact source/plate/composite glyph-only change image, no opaque rectangle paste.
source_only=Image.fromarray(A[t:b,l:r].copy(),"RGBA")
clean_only=Image.fromarray(B[t:b,l:r].copy(),"RGBA")
final_only=Image.fromarray(D[t:b,l:r].copy(),"RGBA")
for name,img in (("SOURCE_ONLY",source_only),("CLEAN_ONLY",clean_only),("CURRENT_ONLY",final_only)):
 fn=out/f"C312_Q103_{name}_NATIVE.png";img.save(fn);files.append(fn)
manifest=[{"path":str(f.relative_to(root)),"sha256":sha(f.read_bytes()),"bytes":f.stat().st_size} for f in files]
report={"schema_version":1,"task_id":"OUTRUN-KOR-C312-C1-Q103-A197-FRESH-EVIDENCE-20261009",
"role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
"queue_index":103,"asset":asset,"triage":tri,"expected":expected,
"clean_path":str((p/"A108_CLEAN_PLATE.png").relative_to(root)),
"metrics":metrics,"pixels":counts,"native_dds":{"width":2048,"height":2048,"mips":1,"raw":"mirror_y","header_exact":True},
"published_lossless":manifest,"num_png":len(files),
"previous_C_failure":"ITALIC_SLANT_AND_UNDERSIZED A108: source 390x72 vs old 196x40, near-upright",
"visual_review_status":"NOT_AUTOMATICALLY_PASSED; requires independent human pixels-first review of files, source-family/type-weight, slant per glyph, protected/art masks and blind calibration",
"gate":"HOLD_STRICT_RECHECK","C3":"NOT_RUN","APPROVAL":"NOT_APPROVED","RUNTIME_VALIDATION":"UNTESTED",
"new_dds":0,"backend":"GitHub Actions CPU worker evidence-only; no N100 heavy compute"}
fn=out/"C312_Q103_INDEPENDENT_MACHINE_AND_EVIDENCE.json"
fn.write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
print("C312_C1_Q103",json.dumps({"sha":expected,"bbox":metrics,"outside":counts,"new_lossless_png":len(files),"status":"HOLD_VISUAL_REQUIRED"},ensure_ascii=False),flush=True)
