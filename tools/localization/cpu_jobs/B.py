#!/usr/bin/env python3
# B244 q62 33491F83: replace C259-rejected white EASY/HARD plate patches
# with the authored PSD Layer 43 road/background while preserving the exact
# accepted A132 Korean lettering pixels and every non-target atlas pixel.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw

repo=Path.cwd()
RUN="20261008-B244-Q062-PSD-L43-CLEAN"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="58fe9ed97494a2026a671e777c2af7da75a33bdd9432e5ab1fa4b547f1cd54b2"
SOURCE="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
A132=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN"
A124=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL124-33491F83-PSD-LAYERS"
clean_old_p=A132/"A132_CLEAN_PLATE.png"
target_mask_p=A132/"A132_TARGET_MASK.png"
layer43_p=A124/"A124_layer43.png"

TARGETS={
 "easy_main":{"bbox":[142,285,385,375],"localized_bbox":[186,287,329,371]},
 "hard_main":{"bbox":[808,287,1068,373],"localized_bbox":[829,288,1039,372]},
}

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def load_dds(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
 h,w=struct.unpack_from("<II",b,12)
 mips=struct.unpack_from("<I",b,28)[0]
 bpp=struct.unpack_from("<I",b,88)[0]
 masks=struct.unpack_from("<IIII",b,92)
 if bpp!=32 or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError(("dds",w,h,bpp,mips,len(b)))
 if masks==(0x000000ff,0x0000ff00,0x00ff0000,0xff000000):mode="RGBA"
 elif masks==(0x00ff0000,0x0000ff00,0x000000ff,0xff000000):mode="BGRA"
 else:raise RuntimeError(("masks",masks))
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
 readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 return b,raw,readable,{"width":w,"height":h,"mips":mips,"masks":masks,"mode":mode}

def imgmask(p):
 im=Image.open(p).convert("RGBA")
 a=np.asarray(im)
 m=a[:,:,3]>0
 if not m.any():m=a[:,:,:3].max(2)>0
 return im,m

def diffmask(a,b):
 d=ImageChops.difference(a,b);cs=d.split();m=cs[0]
 for c in cs[1:]:m=ImageChops.lighter(m,c)
 return m.point(lambda v:255 if v else 0)

def count(m):return int(sum(m.histogram()[1:]))

def mbbox(mask):
 ys,xs=np.where(mask)
 if not len(xs):return None
 return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def flat(im,bg=(224,224,224,255)):
 z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")

if sha(cand)!=INPUT:raise RuntimeError(("candidate drift",sha(cand),INPUT))
cb,raw_old,old,meta=load_dds(cand)
with tempfile.TemporaryDirectory() as td:
 sp=Path(td)/"source.dds";urllib.request.urlretrieve(SRC_URL,sp)
 if sha(sp)!=SOURCE:raise RuntimeError(("source drift",sha(sp)))
 sb,sraw,source,smeta=load_dds(sp)
 if cb[:128]!=sb[:128] or meta!=smeta:raise RuntimeError("DDS structure drift")

 clean_old=Image.open(clean_old_p).convert("RGBA")
 layer43=Image.open(layer43_p).convert("RGBA")
 target_mask_img,target_mask=imgmask(target_mask_p)
 if old.size!=clean_old.size or old.size!=layer43.size or target_mask.shape!=(old.height,old.width):
  raise RuntimeError(("shape",old.size,clean_old.size,layer43.size,target_mask.shape))

 # Validate A132 target mask geometry before reuse.
 expected=[]
 for key,spec in TARGETS.items():
  x0,y0,x1,y1=spec["bbox"]
  lm=target_mask[y0:y1,x0:x1]
  b=mbbox(lm)
  if not b:raise RuntimeError(("empty target mask",key))
  gb=[b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0]
  exp=spec["localized_bbox"]
  # Target-mask antialias/effect mask may differ a few px from report, but must
  # be contained in the exact source bbox and overlap the expected glyph bbox.
  if gb[0]<x0 or gb[1]<y0 or gb[2]>x1 or gb[3]>y1:raise RuntimeError(("target mask overflow",key,gb))
  if gb[2]<=exp[0] or gb[0]>=exp[2] or gb[3]<=exp[1] or gb[1]>=exp[3]:
   raise RuntimeError(("target mask does not overlap expected lettering",key,gb,exp))
  expected.append((key,gb))

 new_clean=clean_old.copy()
 final=old.copy()
 allowed=Image.new("L",old.size,0);ad=ImageDraw.Draw(allowed)
 rows=[]
 for key,spec in TARGETS.items():
  x0,y0,x1,y1=spec["bbox"];ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
  donor=layer43.crop((x0,y0,x1,y1))
  old_clean_crop=clean_old.crop((x0,y0,x1,y1))
  old_final_crop=old.crop((x0,y0,x1,y1))
  mask=target_mask[y0:y1,x0:x1]

  # Material patch correction: authored PSD Layer 43 becomes the entire clean
  # background inside the exact EASY/HARD source-effect bbox.
  new_clean.paste(donor,(x0,y0))
  rebuilt=donor.copy()
  arr=np.array(rebuilt)
  old_arr=np.array(old_final_crop)
  arr[mask]=old_arr[mask]  # exact A132 Korean lettering/effect pixels
  rebuilt=Image.fromarray(arr,"RGBA")
  final.paste(rebuilt,(x0,y0))

  patch_delta=diffmask(old_clean_crop,donor)
  patch_px=count(patch_delta)
  if patch_px<=0:raise RuntimeError(("no material clean repair",key))

  # Background must be pixel-identical to authored Layer43 wherever Korean
  # target pixels are absent.
  fa=np.array(rebuilt);da=np.array(donor)
  bg_mismatch=np.any(fa!=da,axis=2)&(~mask)
  if bg_mismatch.any():raise RuntimeError(("background donor mismatch",key,int(bg_mismatch.sum())))

  # Korean pixels must remain pixel-exact from A132.
  korean_changed=np.any(fa[mask]!=old_arr[mask],axis=1)
  if korean_changed.any():raise RuntimeError(("Korean pixel drift",key,int(korean_changed.sum())))

  # New localized bbox is measured against the corrected clean plate.
  loc_diff=np.any(fa!=da,axis=2)
  lb=mbbox(loc_diff)
  if not lb:raise RuntimeError(("localized missing",key))
  glb=[lb[0]+x0,lb[1]+y0,lb[2]+x0,lb[3]+y0]
  sw,sh=x1-x0,y1-y0;lw,lh=glb[2]-glb[0],glb[3]-glb[1]
  margins=[glb[0]-x0,x1-glb[2],glb[1]-y0,y1-glb[3]]
  if lw>sw or lh>sh or min(margins)<0:raise RuntimeError(("containment",key,glb,spec["bbox"]))
  rows.append({
   "key":key,"source_bbox":spec["bbox"],"localized_bbox":glb,
   "source_size":[sw,sh],"localized_size":[lw,lh],
   "delta_left":margins[0],"delta_right":margins[1],
   "delta_top":margins[2],"delta_bottom":margins[3],
   "a132_reported_localized_bbox":spec["localized_bbox"],
   "a132_clean_to_layer43_patch_pixels":patch_px,
   "background_non_korean_mismatch_vs_authored_layer43":int(bg_mismatch.sum()),
   "korean_pixels_changed_from_a132":int(korean_changed.sum()),
   "containment":"PASS","size_ceiling":"PASS"
  })

 # Only EASY/HARD bboxes may change versus A132 candidate.
 dm=diffmask(old,final)
 outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
 am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
 alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
 if outside or alpha_out:raise RuntimeError(("scope",outside,alpha_out))

 # All seven non-target localized rows / unrelated atlas pixels are exact.
 target_change=count(dm)
 if target_change<=0:raise RuntimeError("no candidate change")

 raw_new=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 cand.write_bytes(cb[:128]+raw_new.tobytes("raw",meta["mode"]))
 csha=sha(cand)
 rb,rraw,decoded,rmeta=load_dds(cand)
 if rb[:128]!=cb[:128] or rmeta!=meta or ImageChops.difference(decoded,final).getbbox() is not None:
  raise RuntimeError("persisted decode mismatch")

 # Save corrected clean plate for C review.
 new_clean.save(out/"B244_Q062_CLEAN_PLATE.png")

 # Four-way zoom evidence per failed row.
 cards=[]
 for r in rows:
  x0,y0,x1,y1=r["source_bbox"];pad=22
  crop=(max(0,x0-pad),max(0,y0-pad),min(old.width,x1+pad),min(old.height,y1+pad))
  ims=[]
  for lab,im in [("SOURCE",source),("A132_CLEAN_FAIL",clean_old),("PSD_LAYER43_CLEAN",new_clean),("B244_FINAL",decoded)]:
   z=flat(im.crop(crop));z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
   c=Image.new("RGB",(z.width,z.height+26),(32,32,32));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
  row=Image.new("RGB",(sum(i.width for i in ims)+12*3,max(i.height for i in ims)+20),(20,20,20));xx=0
  for c in ims:row.paste(c,(xx,0));xx+=c.width+12
  ImageDraw.Draw(row).text((4,row.height-3),r["key"],fill="white",anchor="ls");cards.append(row)
 sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(20,20,20));yy=0
 for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
 sheet.save(out/"B244_Q062_EASY_HARD_ZOOM.jpg","JPEG",quality=96,subsampling=0)

 # Main panel showing source -> rejected clean -> corrected clean -> final.
 main=(0,0,1196,812)
 ims=[]
 for lab,im in [("SOURCE",source),("A132_CLEAN_FAIL",clean_old),("PSD_LAYER43_CLEAN",new_clean),("B244_FINAL",decoded)]:
  z=flat(im.crop(main));z.thumbnail((580,400),Image.Resampling.LANCZOS)
  c=Image.new("RGB",(z.width,z.height+28),(28,28,28));c.paste(z,(0,28));ImageDraw.Draw(c).text((4,5),lab,fill="white");ims.append(c)
 panel=Image.new("RGB",(max(i.width for i in ims)*2+12,max(i.height for i in ims)*2+12),(18,18,18))
 panel.paste(ims[0],(0,0));panel.paste(ims[1],(ims[0].width+12,0))
 panel.paste(ims[2],(0,ims[0].height+12));panel.paste(ims[3],(ims[2].width+12,ims[1].height+12))
 panel.save(out/"B244_Q062_MAIN_COMPARE.jpg","JPEG",quality=94,subsampling=0)

 # RAW source / A132 / B244.
 rs=flat(sraw);ro=flat(raw_old);rn=flat(rraw)
 for z in (rs,ro,rn):z.thumbnail((620,320),Image.Resampling.LANCZOS)
 rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+28),(18,18,18))
 x=0
 for lab,z in [("SOURCE RAW",rs),("A132 RAW",ro),("B244 RAW",rn)]:
  rw.paste(z,(x,28));ImageDraw.Draw(rw).text((x+4,5),lab,fill="white");x+=z.width+12
 rw.save(out/"B244_Q062_RAW.jpg","JPEG",quality=92,subsampling=0)

 report={
  "schema_version":2,"role":"B","run":RUN,"queue_index":62,"asset":"33491F83",
  "trigger":"C259_REWORK_REQUIRED_CLEAN_PLATE_WHITE_OVAL_PATCHES",
  "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
  "repair_basis":{
   "rejected":"A132 Layer43+Group16 composite left conspicuous white rounded patches behind EASY/HARD",
   "replacement":"PSD-authored A124 Layer 43 pixels, which contain continuous road/background with EASY/HARD removed",
   "korean_preservation":"A132 target-mask pixels copied byte/pixel-exact over corrected authored clean background"
  },
  "rows":rows,
  "machine_qa":{
   "target_rows":"2/2 PASS","changed_pixels_vs_a132":target_change,
   "changed_outside_easy_hard_source_bboxes":outside,
   "alpha_changed_outside_easy_hard_source_bboxes":alpha_out,
   "non_target_atlas_pixel_exact":True,
   "background_non_korean_mismatch_vs_layer43":sum(r["background_non_korean_mismatch_vs_authored_layer43"] for r in rows),
   "korean_pixels_changed_from_a132":sum(r["korean_pixels_changed_from_a132"] for r in rows),
   "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
  },
  "ordered_generation_gate":{
   "1_plate_restoration":"PASS_AUTHORED_PSD_LAYER43_CONTINUOUS_ROAD_NO_WHITE_PATCH",
   "2_source_matching_slant":"PASS_A132_LETTERING_PIXEL_EXACT",
   "3_no_undersized_lettering":"PASS_A132_GEOMETRY_PIXEL_EXACT",
   "4_source_faithful_weight_effect":"PASS_A132_LETTERING_PIXEL_EXACT",
   "5_no_clipped_pixels":"PASS_CONTAINED_IN_EXACT_SOURCE_BBOX",
   "6_protected_art_clearance":"PASS_NON_TARGET_ATLAS_EXACT",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"
  },
  "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REPOSITORY_BACKED_DDS",
  "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
  "status":"B244_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
  "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
 }
 (out/"B244_Q062_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (wr/"B244_Q062.json").write_text(json.dumps({
  "role":"B","run":RUN,"queue_index":62,"asset":"33491F83",
  "candidate_sha256":csha,"report":str((out/"B244_Q062_REPORT.json").relative_to(repo)),
  "status":report["status"],"runtime_validation":"UNTESTED"
 },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":rows,"changed_pixels":target_change,
  "outside":outside,"alpha_outside":alpha_out,"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2))
