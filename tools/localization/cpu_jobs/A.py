#!/usr/bin/env python3
"""A228 q059 BC3 index-only interior glyph-face de-stipple TRIAL.
C1 independently rejected persisted q059 for gold Korean face perforations.
Only attempt palette-index substitutions in source-bounded gold-face holes.
Preserve all 16-byte blocks except specific color-index bits; never promote
without controller visual review, exact source/CLEAN and full pilot signoff.
"""
import hashlib, io, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
root=Path.cwd()
run="20261010-A228-Q059-BC3-INDEX-INTERIOR-REPAIR-TRIAL"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(obj,name): (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
tri=subprocess.run(["python","tools/localization/rework_triage.py","--index","59","--require-safe-rerender"],capture_output=True,text=True)
dump({"command":"rework_triage.py --index 59 --require-safe-rerender","exit":tri.returncode,
      "stdout":tri.stdout[:5000],"stderr":tri.stderr[:2000]},"A228_TRIAGE.json")
assert tri.returncode==0, "triage blocks ordinary new candidate; do not silently override"
q=json.loads(tri.stdout)["assets"][0]
assert q["index"]==59 and ("REWORK" in q["current_status"].upper() or
  "REWORK" in q.get("next_action","").upper()),q
review=json.loads((root/"localization/graphics/role_C/20261010-C1-Q059-PERSISTED-GLYPH-FACE-DEFECT/C1_Q059_INDEPENDENT_4REGION_VISUAL_REJECT.json").read_text())
assert review["decision"]=="REWORK_REQUIRED"
assert "BC3_KOREAN_GLYPH_FACE_DARK_STIPPLE" in review["defect_codes"]
target=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
original=target.read_bytes()
expected="261108cd26b2a83037162b17de08286ed1ded2634650709370c81c2a353eb83a"
assert sha(original)==expected,(sha(original),expected)
assert len(original)==128+2048*512 and original[:4]==b"DDS "
assert original[84:88]==b"DXT5" or original[88:92]==b"DXT5", "Check exact DXT5 FourCC header"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
with urllib.request.urlopen(url,timeout=120) as resp: source_bytes=resp.read()
source_sha="9c35216873d617ed68df55be424f35ddf50b1eacc8ee86072068745aea166f9f"
assert sha(source_bytes)==source_sha
source_img=Image.open(io.BytesIO(source_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
previous_img=Image.open(io.BytesIO(original)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
assert source_img.size==previous_img.size==(2048,512)
arr=np.array(previous_img,dtype=np.uint8)
after=bytearray(original)
areas=[
 ("race_rivals",(75,222,625,304)),
 ("drift_score",(119,53,609,137)),
 ("slipstream_score",(717,225,1408,320)),
]
def rgb565(v):
 return np.array([((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31],dtype=np.int32)
def palette(base):
 c0=int.from_bytes(original[base+8:base+10],"little")
 c1=int.from_bytes(original[base+10:base+12],"little")
 a,b=rgb565(c0),rgb565(c1)
 return np.stack([a,b,(2*a+b+1)//3,(a+2*b+1)//3])
changes=[]
regions={}
for name,rect in areas:
 x0,y0,x1,y1=rect
 rgb=arr[y0:y1,x0:x1,:3].astype(np.int16)
 al=arr[y0:y1,x0:x1,3]
 # Gold face derived from the original golden face colour family; no changes
 # to large NEXT MISSION, borders, text mask, alpha, gradients or protected art.
 gold=(rgb[:,:,0]>165)&(rgb[:,:,1]>90)&(rgb[:,:,2]<158)&(rgb[:,:,0]>rgb[:,:,2]*1.65)&(al>=192)
 n=ndi.convolve(gold.astype(np.uint8),np.ones((3,3),dtype=np.uint8),mode="constant",cval=0)
 # Target only enclosed, opaque dark interior freckles. A dotted outline/edge
 # is NOT a gold-face hole and is protected by this narrow rule.
 dark=(rgb[:,:,0]<120)&(rgb[:,:,1]<125)&(rgb[:,:,2]<165)
 eligible=dark&(n>=5)&(al>=220)
 pending=np.transpose(np.nonzero(eligible))
 selected=0;no_gold_palette=0;no_quality_gain=0;edge_block=0
 for yy,xx in pending:
  X,Y=x0+int(xx),y0+int(yy)
  raw_y=511-Y
  bx=X//4;by=raw_y//4
  # block must sit entirely inside source English glyph/effect region.
  if not (x0<=bx*4 and (bx+1)*4<=x1 and y0<=511-(by*4+3) and 512-by*4<=y1):
   edge_block+=1;continue
  base=128+(by*512+bx)*16
  colors=palette(base)
  local=rgb[max(0,int(yy)-1):min(rgb.shape[0],int(yy)+2),max(0,int(xx)-1):min(rgb.shape[1],int(xx)+2)]
  nearby=gold[max(0,int(yy)-1):min(rgb.shape[0],int(yy)+2),max(0,int(xx)-1):min(rgb.shape[1],int(xx)+2)]
  if nearby.sum()<5:continue
  target_rgb=np.median(local[nearby],axis=0)
  dist=((colors-target_rgb)**2).sum(axis=1)
  gold_choices=[j for j in range(4) if int(colors[j,0])>150 and int(colors[j,1])>85
      and int(colors[j,2])<165 and colors[j,0]>colors[j,2]*1.6]
  if not gold_choices:
   no_gold_palette+=1;continue
  j=min(gold_choices,key=lambda v:dist[v])
  old_rgb=rgb[int(yy),int(xx)]
  # Reject unchanged or a replacement that is not clearly closer to source gold.
  if np.sum((colors[j]-target_rgb)**2)>=np.sum((old_rgb-target_rgb)**2)*0.5:
   no_quality_gain+=1;continue
  k=(raw_y%4)*4+(X%4)
  idxoff=base+12
  packed=int.from_bytes(after[idxoff:idxoff+4],"little")
  origidx=(packed>>(2*k))&3
  if origidx==j:continue
  updated=(packed&~(3<<(2*k)))|(j<<(2*k))
  after[idxoff:idxoff+4]=updated.to_bytes(4,"little")
  changes.append({"region":name,"x":X,"y":Y,"from":old_rgb.tolist(),
       "to_palette":colors[j].tolist(),"old_index":origidx,"new_index":j})
  selected+=1
 regions[name]={"dark_gold_enclosed_candidates":int(eligible.sum()),
  "selected_index_repair":selected,"skipped_no_gold_palette":no_gold_palette,
  "skipped_no_quality_gain":no_quality_gain,"skipped_edge_block":edge_block}
newbytes=bytes(after)
# Even when no repair is possible, publish truthful method diagnosis, not
# an artificial new candidate or a rerun pretending to have repaired a DDS.
modified=sha(newbytes)!=expected
saved=None
if modified:
 trial=out/"A228_Q059_GOLD_FACE_BC3_INDEX_TRIAL_UNPROMOTED.dds"
 trial.write_bytes(newbytes)
 saved=np.array(Image.open(trial).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert np.array_equal(saved[:,:,3],arr[:,:,3]),"BC3 alpha mutation"
 changed=np.any(saved!=arr,axis=2)
 allowed=np.zeros(changed.shape,dtype=bool)
 for name,(x0,y0,x1,y1) in areas:allowed[y0:y1,x0:x1]=True
 assert int((changed&~allowed).sum())==0,"protected/outside source bbox altered"
 assert int(changed.sum())==len(changes),(int(changed.sum()),len(changes))
 assert newbytes[:128]==original[:128] and len(newbytes)==len(original)
 # Index bits are the only changed bytes; block endpoints and alpha exact.
 blockbytes=np.frombuffer(original[128:],np.uint8).reshape(-1,16)
 blocknew=np.frombuffer(newbytes[128:],np.uint8).reshape(-1,16)
 byte_diff=blockbytes!=blocknew
 assert not byte_diff[:,:12].any()
 assert int(byte_diff[:,12:].sum())>0
 for name,rect in areas:
  x0,y0,x1,y1=rect
  # Full source/candidate/trial ROI comparisons across opaque practical backgrounds.
  crops=[np.array(source_img.crop(rect)),arr[y0:y1,x0:x1],saved[y0:y1,x0:x1]]
  for bgname,bg in [("BLACK",(0,0,0)),("GRAY",(105,105,105)),("WHITE",(255,255,255))]:
   panels=[]
   for raw in crops:
    rgba=Image.fromarray(raw,mode="RGBA")
    canvas=Image.new("RGBA",rgba.size,bg+(255,))
    panels.append(Image.alpha_composite(canvas,rgba).convert("RGB"))
   for pct in (100,50):
    scale=pct/100
    if pct!=100:
     panels=[p.resize((round(p.width*scale),round(p.height*scale)),Image.Resampling.LANCZOS) for p in panels]
    w,h=panels[0].size
    sheet=Image.new("RGB",(w*3,h+24),bg)
    d=ImageDraw.Draw(sheet)
    for j,(s,p) in enumerate(zip(["SOURCE","OFFICIAL_C1_FAIL","A228_INDEX_TRIAL"],panels)):
     sheet.paste(p,(j*w,24))
     d.text((j*w+2,2),s,fill=(0,0,0) if bgname=="WHITE" else (255,255,255))
    sheet.save(out/f"A228_{name}_{bgname}_{pct}.png")
 else:
  changed=np.zeros((512,2048),dtype=bool)
else:
 changed=np.zeros((512,2048),dtype=bool)
report={"run":"A228","run_key":"OUTRUN-KOR-A228-Q059-C1-BC3-FACE-INDEX-SCOPED-20261010-2100",
 "role":"A","index":59,"source_sha256":source_sha,"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "official_sha256":expected,"current_official_unchanged":True,
 "trial_sha256":sha(newbytes) if modified else None,
 "trial_path":str(trial.relative_to(root)) if modified else None,
 "source_format":"DXT5/BC3 2048x512 mip1 RAW-mirror_y",
 "mechanism":"4x4 BC3 palette index substitution for gold-encircled alpha-opaque dark flecks; preserve palette endpoints/alpha and source-bbox outside all pixels",
 "region_counters":regions,"modified_pixels":len(changes),"modified_bytes":sum(a!=b for a,b in zip(original,newbytes)),
 "all_source_bbox_outside_identical":True,"all_alpha_exact":True,"header_and_format_preserved":True,
 "persisted_DDS_redecoded":bool(modified),"production_stage":"NEW_COMPRESSED_FACE_METHOD_EXPLORATORY_TRIAL",
 "producer_self_qa":"PENDING_CONTROLLER_OPTICAL_REVIEW","C1":"REQUIRED_NEW_BYTES",
 "official_promotion":False,"candidate_published":False,
 "fresh_source_clean_composite_gate":"NOT_YET_COMPLETE_NO_PASS",
 "C3":"NOT_RUN","USER_INGAME":"NOT_TESTED","RUNTIME_VALIDATION":"UNTESTED",
 "next_action":"Review persisted BGW 100/50 before considering promotion; if dark dot texture remains, method fails and switch to native source-family renderer/BC encoder",
 "exclusions":["VR","FFB","DX11","DXVK"]}
dump(report,"A228_MACHINE_AND_SCOPE_REPORT.json")
dump({"pixel_substitutions":changes},"A228_INDEX_CHANGE_LIST.json")
print(json.dumps({"index":59,"trial_sha":report["trial_sha256"],"pixel_repairs":len(changes),
 "regions":regions,"promoted":False},ensure_ascii=False))
