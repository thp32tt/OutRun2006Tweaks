from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import hashlib, json, struct
import numpy as np
r=Path.cwd()
folder=r/"localization/graphics/role_A/20261011-A245-Q193-ONLINE-CLEAN-REAL-GLYPH"
source=r/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT/A243_PINNED_CANONICAL_SOURCE.dds"
official=r/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
trial=folder/"A245_Q193_ONLINE_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds"
clean=folder/"A245_TRUE_CLEAN_FULL_RAW.png"
letter=folder/"A245_LETTERING_RAW.png"
out=r/"localization/graphics/role_C/20261011-C2-Q193-A245-ONLINE-FIRST-INDEPENDENT"
out.mkdir(parents=True,exist_ok=True)
files=dict(source=source,official=official,trial=trial,clean=clean,lettering=letter)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pimg=lambda p:Image.open(p).convert("RGBA")
src=np.asarray(ImageOps.flip(pimg(source))).copy()
old=np.asarray(ImageOps.flip(pimg(official))).copy()
new=np.asarray(ImageOps.flip(pimg(trial))).copy()
raw=np.asarray(pimg(trial))
plate_raw=np.asarray(pimg(clean))
# producer named raw clean; flip to readable
plate=np.flipud(plate_raw).copy()
glyph_rgba=np.flipud(np.asarray(pimg(letter))).copy()
assert new.shape==(1024,2048,4) and glyph_rgba.shape==new.shape,glyph_rgba.shape
l,t,rr,b=1660,156,1832,194
shape=new.shape[:2];mask=np.zeros(shape,bool);mask[t:b,l:rr]=True
diff=lambda x,y:np.any(x!=y,axis=2)
d=diff(old,new);dd=diff(old,plate);dn=diff(plate,new)
def bbox_alpha(x):
 ys,xs=np.nonzero(x[t:b,l:rr,3])
 return [int(xs.min()+l),int(ys.min()+t),int(xs.max()+l+1),int(ys.max()+t+1)] if len(xs) else None
m={
"official_to_trial_rgba_inside":int(np.count_nonzero(d&mask)),
"official_to_trial_rgba_outside":int(np.count_nonzero(d&~mask)),
"official_to_trial_alpha_outside":int(np.count_nonzero((old[:,:,3]!=new[:,:,3])&~mask)),
"official_to_clean_rgba_outside":int(np.count_nonzero(dd&~mask)),
"clean_to_trial_rgba_outside":int(np.count_nonzero(dn&~mask)),
"clean_roi_alpha_nonzero":int(np.count_nonzero(plate[t:b,l:rr,3])),
"raw_flipY_exact":bool(np.array_equal(np.flipud(raw),new)),
"original_source_bbox_native":bbox_alpha(src),
"new_trial_bbox_native":bbox_alpha(new),
"trial_header_identical":bool(official.read_bytes()[:128]==trial.read_bytes()[:128]),
"mip_count":int(struct.unpack_from("<I",trial.read_bytes(),28)[0]),
"glyph_rgba_size":list(glyph_rgba.shape)}
# letter full vs cropped: x/y layouts; independently check source composites
if glyph_rgba.shape==new.shape:
 composite=np.asarray(Image.alpha_composite(Image.fromarray(plate),Image.fromarray(glyph_rgba)))
 m["clean_plus_lettering_vs_persisted_diff_pixels"]=int(np.count_nonzero(diff(composite,new)))
 m["lettering_alpha_outside"]=int(np.count_nonzero((glyph_rgba[:,:,3]>0)&~mask))
else:
 m["clean_plus_lettering_vs_persisted_diff_pixels"]=None
 m["lettering_alpha_outside"]=None
m["source_canonical_sha256"]=sha(source);m["trial_sha256"]=sha(trial);m["official_sha256"]=sha(official);m["clean_file_sha256"]=sha(clean);m["lettering_sha256"]=sha(letter)
# render lossless source/official/clean/glyph/saved native with normalized blank bg
elements=[("SOURCE",src),("OFFICIAL",old),("CLEAN",plate),("GLYPH",glyph_rgba if glyph_rgba.shape==new.shape else new*0),("PERSISTED",new)]
for bg,label in [((160,160,160),"GRAY"),((255,255,255),"WHITE"),((0,0,0),"BLACK")]:
 w=rr-l;h=b-t
 pane=Image.new("RGB",(w*5,h+23),bg)
 dr=ImageDraw.Draw(pane)
 for i,(name,arr) in enumerate(elements):
  cropped=Image.fromarray(arr[t:b,l:rr],"RGBA")
  mte=Image.new("RGBA",cropped.size,bg+(255,));mte.alpha_composite(cropped)
  pane.paste(mte.convert("RGB"),(i*w,23))
  dr.text((i*w+2,2),name,fill=(255,255,255) if label=="BLACK" else (0,0,0))
 pane.save(out/f"C2_Q193_A245_{label}_100.png")
 if label=="WHITE":
  for q in (75,50):
   pane.resize((round(pane.width*q/100),round(pane.height*q/100)),Image.Resampling.LANCZOS).save(out/f"C2_Q193_A245_{label}_{q}.png")
Image.fromarray(new[t:b,l:rr]).save(out/"C2_Q193_A245_PERSISTED_NATIVE_FLIPY.png")
Image.fromarray(raw[1024-b:1024-t,l:rr]).save(out/"C2_Q193_A245_PERSISTED_RAW.png")
report={
"review":"C2-Q193-A245-FIRST-INDEPENDENT","candidate_sha256":sha(trial),
"readable_roi":[l,t,rr,b],"file_refs":{k:{"path":str(v.relative_to(r)),"sha256":sha(v),"dimensions":list(Image.open(v).size)} for k,v in files.items()},
"metrics":m,"proofs":[str(p.relative_to(r)) for p in sorted(out.glob("*.png"))],
"producer_claims_not_used_for_numeric_evaluation":True,"runtime_validation":"UNTESTED"}
(out/"C2_Q193_A245_MEASUREMENTS.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(m,ensure_ascii=False))
