#!/usr/bin/env python3
"""A217 ODD q219 P1 source-profile metallic depth pilot; never auto-promote.

Keep the actual Korean glyph topology of A186R. Rebuild face/side/extrusion from
SHA pinned canonical English source, rather than A186R's shallow 3/7px outline
or the unrelated A216 q175 hand-rail method. Fail closed on plate/pixels.
"""
import hashlib,json,os,struct,tempfile,traceback,urllib.request,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import maximum_filter,gaussian_filter,distance_transform_edt
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261010-A217-Q219-SOURCE-CHROME-DEPTH-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
SOURCE_SHA="6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d"
CURRENT=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
CURRENT_SHA="8310a1e62adb6e742c7c44e489f0169c3e6139548b316d53112e9606f01a7f46"
BASE=ROOT/"localization/graphics/role_A/20261008-A186R-Q219-SOURCE-HEIGHT-CHROME"
CLEAN=BASE/"A186R_Q219_CLEAN_PLATE.png"
GLYPH_MASK=BASE/"A186R_Q219_RENDER_MASK.png"
BBOX=(6,1011,1473,1129)
RUN_KEY="OUTRUN-KOR-A217-Q219-CANONICAL-CHROME-DEPTH-PILOT-20261010-0500"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dds(path):
 b=Path(path).read_bytes()
 if b[:4]!=b"DDS " or len(b)!=128+2048*2048*4:raise ValueError("DDS signature/length mismatch")
 height,width=struct.unpack_from("<II",b,12);mips=struct.unpack_from("<I",b,28)[0]
 masks=struct.unpack_from("<IIII",b,92)
 if (width,height,mips)!=(2048,2048,1) or masks not in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)):
  raise ValueError(f"DDS header mismatch {width}x{height} mips{mips} masks{masks}")
 raw="RGBA" if masks[0]==255 else "BGRA"
 return b[:128],Image.frombytes("RGBA",(width,height),b[128:],"raw",raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw
def comp(im,rgb):
 bg=Image.new("RGBA",im.size,(*rgb,255));bg.alpha_composite(im);return bg.convert("RGB")
def offset(src,dy,dx=0):
 y0=max(0,dy);y1=min(src.shape[0],src.shape[0]+dy)
 x0=max(0,dx);x1=min(src.shape[1],src.shape[1]+dx)
 ans=np.zeros_like(src)
 if y1>y0 and x1>x0:ans[y0:y1,x0:x1]=src[y0-dy:y1-dy,x0-dx:x1-dx]
 return ans
def make_trial(source,prior,clean,source_header,raw):
 x0,y0,x1,y1=BBOX
 sc=np.asarray(source.crop(BBOX));a=sc[:,:,3]
 if np.count_nonzero(a)<9000:raise ValueError("canonical English glyph bbox blank")
 p=np.asarray(prior)
 c=np.asarray(clean)
 if c.shape!=p.shape:raise ValueError("plate dimensions differ")
 if int(np.count_nonzero(c[y0:y1,x0:x1,3])):raise ValueError("canonical source clean plate alpha is not zero")
 if np.any(np.any(p!=np.asarray(source),axis=2) & ~make_global_mask()):
  raise ValueError("old promoted candidate changes pixels outside source bbox")
 # Reuse native pixel topology (existing Korean already independently legible)
 orig=np.asarray(Image.open(GLYPH_MASK).convert("L"))
 if orig.shape!=(2048,2048):raise ValueError("authored A186R glyph mask not native")
 v=orig[y0:y1,x0:x1]
 # Distinct from simple change-of-brightness: explicitly model 12px deep side wall.
 # Source Korean is high in sprite, and the new 12px extrusion must leave positive lower margin.
 # Shift source glyph core 6 native pixels up to reserve real source-metal depth.
 core=np.float32(v>=162)
 for val in (170,200):
  if np.count_nonzero(v>=val)>9500:core=np.float32(v>=val);break
 if np.count_nonzero(core)<8000:raise ValueError("not enough original real Hangul glyph pixels")
 face=offset(core,-5,0)
 # one-pixel AA on same native source space, no scaling/tracking/stretch
 face=np.clip(gaussian_filter(face,0.46),0,1)
 solid=face>=0.38
 # sources for metal hue/brightness sampled only from positive-alpha English pixels
 src_rgb=sc[:,:,:3].astype(np.float32)
 brightness=np.empty((y1-y0,),np.float32)
 for yy in range(y1-y0):
  valid=a[yy]>130
  brightness[yy]=float(np.percentile(np.mean(src_rgb[yy,valid],axis=1),65)) if valid.sum()>10 else np.nan
 ids=np.where(np.isfinite(brightness))[0]
 if len(ids)<50:raise ValueError("source metallic highlights not measurable")
 brightness=np.interp(np.arange(len(brightness)),ids,brightness[ids])
 # Build extruded metallic wall by sweeping true Korean silhouette DOWN, not
 # skewing the whole title or copying a source background rectangular crop.
 wall=np.zeros_like(solid)
 for dy in range(2,15):wall|=offset(solid,dy,4)
 bevel_dilate=maximum_filter(solid.astype(np.uint8),size=5)>0
 outline=(maximum_filter(wall.astype(np.uint8),size=3)>0)|bevel_dilate
 h,w=solid.shape
 rgba=np.zeros((h,w,4),dtype=np.uint8)
 rgba[outline,:3]=[12,12,18];rgba[outline,3]=np.uint8(190)
 rgba[wall,:3]=[55,56,62];rgba[wall,3]=240
 for dy in range(14,1,-1):
  band=offset(solid,dy,4) & ~solid
  if dy>=10:shade=[34+dy*2,35+dy*2,39+dy*2]
  elif dy>=5:shade=[88+dy*3,88+dy*3,91+dy*3]
  else:shade=[138+dy*4,138+dy*4,140+dy*4]
  rgba[band,:3]=shade;rgba[band,3]=255
 # Native face: source row luminous chrome bands, bright upper ridge, dark lower lip.
 inward=distance_transform_edt(solid)
 dy,dx=np.gradient(inward.astype(np.float32))
 yy=np.arange(h)[:,None]
 sampled=np.broadcast_to(brightness[:,None],(h,w))
 spec=20*np.clip(-dy-0.38*dx,-1,1)
 lower=np.clip((yy-78)/36,0,1)*34
 lum=np.clip(0.85*sampled+40+spec-lower+np.clip(inward/4,0,1)*6,95,251)
 for k,delta in enumerate((2,2,0)):rgba[:,:,k][solid]=np.clip(lum[solid]+delta,0,255)
 rgba[:,:,3][solid]=255
 fg=Image.fromarray(rgba,"RGBA")
 out=prior.copy();out.paste(clean.crop(BBOX),(x0,y0));out.alpha_composite(fg,dest=(x0,y0))
 d=np.asarray(out)
 cur=np.asarray(prior)
 valid=make_global_mask()
 source_changed=int(np.count_nonzero(np.any(d!=np.asarray(source),axis=2)&~valid))
 current_changed=int(np.count_nonzero(np.any(d!=cur,axis=2)&~valid))
 alpha_changed=int(np.count_nonzero((d[:,:,3]!=cur[:,:,3])&~valid))
 ycoords,xcoords=np.nonzero(rgba[:,:,3]>0)
 if len(ycoords)==0:raise ValueError("empty new effect")
 box=[int(x0+xcoords.min()),int(y0+ycoords.min()),int(x0+xcoords.max()+1),int(y0+ycoords.max()+1)]
 margins=[box[0]-x0,x1-box[2],box[1]-y0,y1-box[3]]
 if any(z!=0 for z in (source_changed,current_changed,alpha_changed)) or min(margins)<1:
  raise ValueError("protected source escape or clipping "+str((source_changed,current_changed,alpha_changed,margins)))
 return out,rgba,box,margins,{"source_to_final_outside_rgba":source_changed,"prior_to_trial_outside_rgba":current_changed,"prior_to_trial_outside_alpha":alpha_changed,"clean_alpha_in_source_bbox":0,"effect_pixels":int(np.count_nonzero(rgba[:,:,3]))}
def make_global_mask():
 x0,y0,x1,y1=BBOX;mask=np.zeros((2048,2048),bool);mask[y0:y1,x0:x1]=True;return mask
def main():
 tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","219"],capture_output=True,text=True,check=True).stdout)["assets"][0]
 if tri["next_action"] not in ("METHOD_CHANGE_REQUIRED","MATERIAL_REWORK"):raise ValueError("q219 new state is not material REWORK")
 if sha(CURRENT)!=CURRENT_SHA:raise ValueError("q219 latest candidate changed; do not touch")
 with tempfile.TemporaryDirectory(prefix="outrun_A217_") as tmp:
  srcpath=Path(tmp)/"canonical.dds";urllib.request.urlretrieve(SOURCE_URL,srcpath)
  if sha(srcpath)!=SOURCE_SHA:raise ValueError("wrong canonical q219 revision/SHA")
  header,source,raw=dds(srcpath);h2,prior,raw2=dds(CURRENT)
  if header!=h2 or raw!=raw2:raise ValueError("canonical source/header mismatch")
  clean=Image.open(CLEAN).convert("RGBA")
  if clean.size!=source.size:raise ValueError("A186R clean not 2048 native")
  out,layer,box,margins,gates=make_trial(source,prior,clean,header,raw)
  trial=OUT/"A217_Q219_SOURCE_CHROME_DEPTH_TRIAL.dds"
  trial.write_bytes(header+out.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",raw))
  h3,decoded,raw3=dds(trial)
  if h3!=header or not np.array_equal(np.asarray(decoded),np.asarray(out)):raise ValueError("persisted trial DDS roundtrip failed")
  decoded.save(OUT/"A217_FINAL_FLIPY_NATIVE_RGBA.png",compress_level=6)
  decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A217_FINAL_RAW_NATIVE_RGBA.png",compress_level=6)
  Image.fromarray(layer,"RGBA").save(OUT/"A217_LETTERING_CHROME_EFFECT_NATIVE_RGBA.png",compress_level=6)
  plate=prior.copy();plate.paste(clean.crop(BBOX),BBOX[:2])
  crop=(0,BBOX[1]-18,BBOX[2]+15,BBOX[3]+24)
  for color,bg in [("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
   tiles=[comp(im,bg).crop(crop) for im in (source,plate,prior,decoded)]
   w,h=tiles[0].size
   panel=Image.new("RGB",(4*w+36,h+24),bg)
   ImageDraw.Draw(panel).text((9,6),"CANONICAL ENGLISH | CLEAN | CURRENT KOREAN | A217 METAL DEPTH",fill=(240,200,20) if color!="WHITE" else (0,0,0))
   for i,tile in enumerate(tiles):panel.paste(tile,(i*(w+12),24))
   for pct in (100,75,50):
    img=panel if pct==100 else panel.resize((panel.width*pct//100,panel.height*pct//100),Image.Resampling.LANCZOS)
    img.save(OUT/f"A217_{color}_{pct}.jpg",quality=92,optimize=True)
  report={"run":"A217","run_key":RUN_KEY,"role":"A","priority":"P1","queue_index":219,
   "issue":"IGR-025","triage":tri["next_action"],"source_sha256":SOURCE_SHA,"original_source_url":SOURCE_URL,
   "old_current_sha256":CURRENT_SHA,"clean_sha256":sha(CLEAN),"glyph_topology_sha256":sha(GLYPH_MASK),
   "trial_sha256":sha(trial),"trial_dds_bytes":trial.stat().st_size,"trial_path":str(trial.relative_to(ROOT)),
   "method":"Material method change: source-sampled row metal tone + 14 native pixel extrusion, top-light bevel, dark side wall. Preserve A186R independently readable Korean glyph topology; no width scaling/new font/no silhouette rail drawing. Face -5px before extrusion, one 0.46px AA pass.","source_bbox":BBOX,"new_bbox":box,"margins":margins,"pixel_gates":gates,
   "new_promoted_dds":0,"new_trial_dds":1,"producer_visual":"PENDING_DIRECT_REVIEW","C1":"BLOCKED_UNTIL_FIRSTHAND_VISUAL","C3":"NOT_RUN","runtime_validation":"UNTESTED","actual_game":"IGR025_OPEN","excluded":["VR","FFB","DX11","DXVK"]}
  (OUT/"A217_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
  print("A217_TRIAL_SUCCESS",json.dumps({"sha256":report["trial_sha256"],"bbox":box,"margins":margins}),flush=True)
try:main()
except Exception as ex:
 report={"run":"A217","run_key":RUN_KEY,"role":"A","queue_index":219,"status":"EXECUTION_HOLD_PROMOTED_DDS_UNCHANGED","exception":type(ex).__name__,"reason":str(ex),"traceback":traceback.format_exc(),"new_promoted_dds":0,"RUNTIME_VALIDATION":"UNTESTED"}
 (OUT/"A217_EXECUTION_HOLD.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print("A217_HOLD",str(ex),flush=True)
