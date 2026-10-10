from pathlib import Path
import json,struct,hashlib
import numpy as np
from PIL import Image,ImageDraw
d=Path("work/c1_q121_a235r_20261011_0710")
srcs={};facts={}
for name in ("source","official","trial"):
 p=d/(name+".dds")
 h=p.open("rb").read(128);width,height=struct.unpack_from("<II",h,12)[::-1]
 mip=struct.unpack_from("<I",h,28)[0]
 masks=struct.unpack_from("<IIII",h,92)
 assert (width,height)==(4096,4096) and mip==1 and masks==(255,65280,16711680,4278190080),(name,width,height,mip,masks)
 srcs[name]=np.memmap(p,dtype=np.uint8,mode="r",offset=128,shape=(height,width,4))
 facts[name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size,"w":width,"h":height,"mips":mip,"channel_masks":list(masks),"header_sha256":hashlib.sha256(h).hexdigest()}
roi=(3490,391,3722,440)
l,t,r,b=roi; W=r-l;H=b-t
def get(name,flip=True):
 raw=np.array(srcs[name][4096-b:4096-t,l:r])
 return np.flipud(raw).copy() if flip else raw
source=get("source"); official=get("official");trial=get("trial"); clean=np.asarray(Image.open(d/"clean_producer.png").convert("RGBA"))
prior_src=np.asarray(Image.open(d/"source_producer.png").convert("RGBA"))
prior_new=np.asarray(Image.open(d/"trial_producer.png").convert("RGBA"))
assert source.shape==trial.shape==clean.shape==(49,232,4)
def diff(a,b):return np.any(a!=b,axis=2)
def bbox(mask):
 yy,xx=np.where(mask)
 return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
def metrics(img):
 a=img[:,:,3]
 return {"visible_alpha":int((a>0).sum()),"opaque":int((a==255).sum()),"bbox_local":bbox(a>0),"near_white_face_opaque":int(((img[:,:,:3]>225).all(axis=2)&(a>240)).sum()),"dark_blue_visible":int(((img[:,:,2]<95)&(img[:,:,1]<105)&(a>32)).sum())}
total=0;alpha=0;outside=0;outside_alpha=0;data_bbox=None;unaltered_rows=0
for y in range(0,4096,128):
 old=np.asarray(srcs["official"][y:y+128]); new=np.asarray(srcs["trial"][y:y+128])
 D=diff(old,new);A=old[:,:,3]!=new[:,:,3]
 count=int(D.sum())
 if count:
  total+=count;alpha+=int(A.sum())
  ys,xs=np.where(D);bb=[int(xs.min()),int(y+ys.min()),int(xs.max()+1),int(y+ys.max()+1)]
  data_bbox=bb if data_bbox is None else [min(data_bbox[0],bb[0]),min(data_bbox[1],bb[1]),max(data_bbox[2],bb[2]),max(data_bbox[3],bb[3])]
  allowed=np.zeros(D.shape,dtype=bool)
  y0=max(y,4096-b);y1=min(y+128,4096-t)
  if y1>y0:allowed[y0-y:y1-y,l:r]=1
  outside+=int((D&~allowed).sum());outside_alpha+=int((A&~allowed).sum())
 else:unaltered_rows+=len(D)
native_values={"source":metrics(source),"official":metrics(official),"trial":metrics(trial),"clean":metrics(clean)}
m={"asset_index":121,"role":"C1","source":facts["source"],"official":facts["official"],"new_unpromoted_trial":facts["trial"],"bbox_readable":list(roi),"bbox_raw":[l,4096-b,r,4096-t],"source_candidate_png_mismatch":{"source":int(diff(source,prior_src).sum()),"trial":int(diff(trial,prior_new).sum())},"original_to_clean_rgba_changes":int(diff(source,clean).sum()),"source_clean_alpha0":int((clean[:,:,3]>0).sum()),"clean_to_trial_rgba_changes":int(diff(clean,trial).sum()),"source_to_trial_rgba_changes":int(diff(source,trial).sum()),"official_to_trial_full_atlas_rgba_changed":total,"official_to_trial_full_atlas_alpha_changed":alpha,"outside_original_GAS_PEDAL_bbox_changed_RGBA":outside,"outside_original_GAS_PEDAL_bbox_changed_alpha":outside_alpha,"changed_bbox_raw":data_bbox,"metrics":native_values,"no_new_game_test":True,"C3":"NOT_RUN"}
if native_values["trial"]["bbox_local"]:
 x0,y0,x1,y1=native_values["trial"]["bbox_local"]
 m["trial_positive_margins_ltrb"]=[x0,y0,W-x1,H-y1]
# produce actual independent evidence snapshots (white, gray, black, 100/75/50) + RAW separately
labels=["SOURCE","CLEAN","OFFICIAL","A235R"]
pictures=[source,clean,official,trial]
for name,bg in [("GRAY",(115,115,115,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
 for scale in (100,75,50):
  ow=round(W*scale/100);oh=round(H*scale/100)
  out=Image.new("RGB",(ow*4,oh+25),(222,222,222));dr=ImageDraw.Draw(out)
  for i,(label,raw) in enumerate(zip(labels,pictures)):
   overlay=Image.new("RGBA",(W,H),bg);overlay.alpha_composite(Image.fromarray(raw,"RGBA"))
   shown=overlay.convert("RGB")
   if scale!=100:shown=shown.resize((ow,oh),Image.Resampling.LANCZOS)
   out.paste(shown,(i*ow,25));dr.text((i*ow+4,7),label,fill=(10,10,10))
  out.save(d/f"C1_Q121_A235R_{name}_{scale}.png",optimize=True)
for name,bg in [("GRAY",(115,115,115,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
 out=Image.new("RGB",(W*3,H+25),(222,222,222));dr=ImageDraw.Draw(out)
 for i,kind in enumerate(("source","official","trial")):
  raw=get(kind,flip=False);p=Image.new("RGBA",(W,H),bg);p.alpha_composite(Image.fromarray(raw,"RGBA"))
  out.paste(p.convert("RGB"),(i*W,25));dr.text((i*W+4,7),kind.upper()+" RAW",fill=(10,10,10))
 out.save(d/f"C1_Q121_A235R_{name}_RAW.png",optimize=True)
(d/"C1_Q121_A235R_MACHINE.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(m,ensure_ascii=False))
