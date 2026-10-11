from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import numpy as np,hashlib,struct,json
r=Path.cwd();p=r/"localization/graphics/role_A/20261011-A244-Q012-ROUNDED-SOURCE-BEVEL-TRIAL"
out=r/"localization/graphics/role_C/20261011-C2-Q012-A244-NEW-SAVED-DDS-INDEPENDENT";out.mkdir(parents=True,exist_ok=True)
files={"source_display":p/"A244_CANONICAL_ENGLISH_DISPLAY_4X_ONLY.png",
"official":r/"localization/graphics/hd_candidates/textures/load/spr_etc_xst/D6DC1380_256x64.dds",
"trial":p/"A244_Q012_ROUNDED_BEVEL_PERSISTED_UNPROMOTED.dds",
"clean":p/"A244_CLEAN_PLATE_READABLE.png",
"glyph":p/"A244_LETTERING_ONLY_READABLE.png",
"face":p/"A244_FACE_READABLE.png","rim":p/"A244_RIM_READABLE.png","depth":p/"A244_DEPTH_READABLE.png","highlight":p/"A244_HIGHLIGHT_READABLE.png"}
assert all(f.is_file() for f in files.values()),[k for k,f in files.items() if not f.is_file()]
sha=lambda v:hashlib.sha256(v.read_bytes()).hexdigest()
arr={k:np.asarray(Image.open(f).convert("RGBA")).copy() for k,f in files.items()}
for k in ["official","trial"]: arr[k]=np.flipud(arr[k]).copy()
h,w=arr["trial"].shape[:2]
assert (w,h)==(1024,256)
roi=[32,80,992,216];x0,y0,x1,y1=roi;area=np.zeros((h,w),bool);area[y0:y1,x0:x1]=True
chg=lambda a,b:np.any(a!=b,axis=2)
co=chg(arr["official"],arr["trial"])
cp=chg(arr["clean"],arr["trial"])
oc=chg(arr["official"],arr["clean"])
sg=chg(arr["source_display"],arr["clean"])
glyph_alpha=arr["glyph"][:,:,3]>0
metrics={
 "official_to_trial_changed_inside":int(np.count_nonzero(co&area)),
 "official_to_trial_changed_outside":int(np.count_nonzero(co&~area)),
 "official_to_trial_alpha_changed_outside":int(np.count_nonzero((arr["official"][:,:,3]!=arr["trial"][:,:,3])&~area)),
 "official_to_clean_changed_outside":int(np.count_nonzero(oc&~area)),
 "clean_to_trial_changed_outside":int(np.count_nonzero(cp&~area)),
 "glyph_alpha_outside":int(np.count_nonzero(glyph_alpha&~area)),
 "clean_alpha_remaining_inside":int(np.count_nonzero(arr["clean"][y0:y1,x0:x1,3])),
 "source_display_to_clean_changed_outside":int(np.count_nonzero(sg&~area)),
 "source_display_alpha_inside":int(np.count_nonzero(arr["source_display"][y0:y1,x0:x1,3])),
 "clean_to_trial_inside":int(np.count_nonzero(cp&area))}
compose=np.asarray(Image.alpha_composite(Image.fromarray(arr["clean"]),Image.fromarray(arr["glyph"])))
metrics["clean_plus_glyph_vs_saved_diff_pixels"]=int(np.count_nonzero(chg(compose,arr["trial"])))
raw= np.asarray(Image.open(files["trial"]).convert("RGBA"))
metrics["raw_to_readable_exact"] = bool(np.array_equal(np.flipud(raw),arr["trial"]))
metrics["official_dds_header_exact"] = files["trial"].read_bytes()[:128]==files["official"].read_bytes()[:128]
metrics["native_dds_mips"]=struct.unpack_from("<I",files["trial"].read_bytes(),28)[0]
# Bbox visible alpha and margins
def bbox(a):
 yy,xx=np.nonzero(a[y0:y1,x0:x1])
 return [int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)] if len(xx) else None
metrics["trial_bbox"]=bbox(arr["trial"][:,:,3]>0)
metrics["source_display_bbox"]=bbox(arr["source_display"][:,:,3]>0)
metrics["official_bbox"]=bbox(arr["official"][:,:,3]>0)
# top-vs-bottom offset for leftmost stroke in halves of glyph, indicative only
def slant_measure(a):
 alpha=a[y0:y1,x0:x1,3]>0
 ys=np.where(alpha.any(axis=1))[0]
 if not len(ys):return None
 top=ys[:max(1,len(ys)//5)]
 bottom=ys[-max(1,len(ys)//5):]
 return {"top_left_median":float(np.median([np.where(alpha[y])[0].min() for y in top])),
 "bottom_left_median":float(np.median([np.where(alpha[y])[0].min() for y in bottom]))}
metrics["source_whole_phrase_slant_diagnostic_only"]=slant_measure(arr["source_display"])
metrics["trial_whole_phrase_slant_diagnostic_only"]=slant_measure(arr["trial"])
# separate direct independently decoded saved full-res panel no producer-contact
for bg,name in [((150,150,150),"GRAY"),((255,255,255),"WHITE"),((0,0,0),"BLACK")]:
 labels=["SOURCE","OFFICIAL","CLEAN","LETTERING","PERSISTED"]
 values=["source_display","official","clean","glyph","trial"]
 frames=[]
 for key in values:
  crop=Image.fromarray(arr[key][y0:y1,x0:x1])
  base=Image.new("RGBA",crop.size,bg+(255,));base.alpha_composite(crop);frames.append(base.convert("RGB"))
 w1=x1-x0;hh=y1-y0
 allpane=Image.new("RGB",(w1*len(frames),hh+27),bg);d=ImageDraw.Draw(allpane)
 for i,(title,im) in enumerate(zip(labels,frames)):
  allpane.paste(im,(i*w1,27));d.text((i*w1+4,5),title,fill=(255,255,255) if name=="BLACK" else (0,0,0))
 allpane.save(out/f"C2_Q012_DIRECT_PERSISTED_{name}_100.png")
 if name=="WHITE":
  for pc in [75,50]:
   allpane.resize((int(allpane.width*pc/100),int(allpane.height*pc/100)),Image.Resampling.LANCZOS).save(out/f"C2_Q012_DIRECT_PERSISTED_{name}_{pc}.png")
rawimg=Image.fromarray(raw).crop((x0,h-y1,x1,h-y0))
rawimg.save(out/"C2_Q012_SAVED_RAW_NATIVE.png")
Image.fromarray(arr["trial"][y0:y1,x0:x1]).save(out/"C2_Q012_SAVED_FLIPY_NATIVE.png")
meta={k:{"path":str(v.relative_to(r)),"sha256":sha(v),"size":list(Image.open(v).size)} for k,v in files.items()}
data={"review_id":"C2-Q012-A244-20261011-NEW-SHA-FIRST","queue_index":12,"producer":"A244","files":meta,"metrics":metrics,"scope":"One unpromoted new persisted 1024x256 DDS; source 256x64 canonical source only visible through labeled display-only 4x PNG, cannot assert English original DDS SHA independently","evidence":[str(f.relative_to(r)) for f in sorted(out.glob("*.png"))]}
(out/"C2_Q012_A244_MACHINE.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"metrics":metrics,"hashes":{k:meta[k]["sha256"] for k in ["source_display","official","trial","clean","glyph"]}},ensure_ascii=False))
