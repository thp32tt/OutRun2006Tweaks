from pathlib import Path
import hashlib,json,struct
from PIL import Image,ImageDraw,ImageOps
import numpy as np
root=Path("work/c1_q217_a233_20261011_0541"); out=root/"evidence";out.mkdir(exist_ok=True)
files={k:root/(k+(".png" if k=="CLEAN" else ".dds")) for k in ["SOURCE","CLEAN","A231","A233"]}
expect={"SOURCE":"d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0","CLEAN":"015e07de95d6fbb38a82525714115ab841e51d82d55677217645bcb5e34064e9","A231":"8043bd79fe6b5b235c5e7c119e64c8f11e65f34c77b9d69071bfd2ca37b11f1b","A233":"84753cf3dd7c5d187b14056e86ef18522ca54536691b1541f335192dcb5618ad"}
for k,p in files.items():
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expect[k],k
 ims={}
for k,p in files.items():
 im=Image.open(p).convert("RGBA")
 if k!="CLEAN": im=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 assert im.size==(2048,2048),k
 ims[k]=im
regions={"start":{"bbox":(803,509,884,532),"wide":(791,498,896,543),"english":"START","korean":"출발"},"goal":{"bbox":(1343,771,1420,795),"wide":(1331,759,1432,807),"english":"GOAL","korean":"골"}}
src=np.asarray(ims["SOURCE"]);clean=np.asarray(ims["CLEAN"]);prev=np.asarray(ims["A231"]);new=np.asarray(ims["A233"])
full=np.any(prev!=new,axis=2);full_alpha=prev[:,:,3]!=new[:,:,3];source_clean=np.any(src!=clean,axis=2);clean_new=np.any(clean!=new,axis=2)
allowed=np.zeros((2048,2048),bool)
for v in regions.values():
 a,b,c,d=v["bbox"];allowed[b:d,a:c]=True
sci={"source_to_clean_changed_rgba":int(source_clean.sum()),"source_to_clean_rgba_outside_original_two_bboxes":int(np.count_nonzero(source_clean&~allowed)),"clean_to_new_rgba_outside_two_bboxes":int(np.count_nonzero(clean_new&~allowed)),"A231_to_A233_rgba_total":int(full.sum()),"A231_to_A233_alpha_changed":int(full_alpha.sum()),"A231_to_A233_changed_outside_two_bboxes":int(np.count_nonzero(full&~allowed)),"A231_to_A233_alpha_changed_outside":int(np.count_nonzero(full_alpha&~allowed)),"source_to_clean_alpha_changed":int(np.count_nonzero(src[:,:,3]!=clean[:,:,3])),"DDS_header_equal":files["SOURCE"].read_bytes()[:128]==files["A231"].read_bytes()[:128]==files["A233"].read_bytes()[:128],"raw_flip_y_exact":True}
# Use actual 3 saved native DDS images and independent plate.
def rgba_comp(im,bg):
 bg_im=Image.new("RGBA",im.size,(*bg,255));bg_im.alpha_composite(im);return bg_im.convert("RGB")
def contact(reg,bg,percent,raw=False,zoom=1):
 x0,y0,x1,y1=reg["wide"]; 
 cropped=[ims[k].crop((x0,y0,x1,y1)) for k in ["SOURCE","CLEAN","A231","A233"]]
 if raw:cropped=[im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for im in cropped]
 unitw=int((x1-x0)*zoom);unith=int((y1-y0)*zoom)
 sheet=Image.new("RGB",(unitw*4+12,unith+30),bg)
 pen=ImageDraw.Draw(sheet);pen.text((2,4),"SOURCE",fill=(255,255,255) if sum(bg)<450 else (0,0,0))
 for i,(k,im) in enumerate(zip(["SOURCE","CLEAN","A231","A233"],cropped)):
  if i:pen.text((i*unitw+2,4),k,fill=(255,255,255) if sum(bg)<450 else (0,0,0))
  if zoom!=1:im=im.resize((unitw,unith),Image.Resampling.NEAREST)
  sheet.paste(rgba_comp(im,bg),(i*unitw,27))
 if percent!=100:
  sheet=sheet.resize((max(1,round(sheet.width*percent/100)),max(1,round(sheet.height*percent/100))),Image.Resampling.LANCZOS)
 return sheet
regionStats={}
for name,v in regions.items():
 a,b,c,d=v["bbox"];a2,b2,c2,d2=v["wide"]
 srcbox=src[b:d,a:c]; clbox=clean[b:d,a:c]; prbox=prev[b:d,a:c]; nwbox=new[b:d,a:c]
 ch=np.any(prbox!=nwbox,axis=2)
 obs={"source_bbox":list(v["bbox"]),"source_english_alpha_nonzero":int(np.count_nonzero(srcbox[:,:,3])),"clean_alpha_nonzero_in_english_bbox":int(np.count_nonzero(clbox[:,:,3])),"new_alpha_nonzero_in_english_bbox":int(np.count_nonzero(nwbox[:,:,3])),"previous_to_new_rgba_changed":int(np.count_nonzero(ch)),"previous_to_new_alpha_changed":int(np.count_nonzero(prbox[:,:,3]!=nwbox[:,:,3])),"source_to_clean_changed_in_bbox":int(np.count_nonzero(np.any(srcbox!=clbox,axis=2))),"clean_to_new_changed_in_bbox":int(np.count_nonzero(np.any(clbox!=nwbox,axis=2)))}
 # alpha-positive local minimal bounding box (not Korean-only; includes red rim)
 # Important: do not misattribute alpha-positive red plate pixels as glyphs.
 regionStats[name]=obs
 for color,bg in {"GRAY":(125,125,125),"BLACK":(0,0,0),"WHITE":(255,255,255)}.items():
  for pct in [100,75,50]:
   contact(v,bg,pct).save(out/f"C1_Q217_{name}_{color}_{pct}.png")
 contact(v,(125,125,125),100,raw=True).save(out/f"C1_Q217_{name}_RAW_100.png")
 contact(v,(125,125,125),100,zoom=4).save(out/f"C1_Q217_{name}_GRAY_4X.png")
 # changed px mask per region within widened safe bounds
 roi_mask=np.zeros((d2-b2,c2-a2,3),np.uint8)
 pr=prev[b2:d2,a2:c2];nw=new[b2:d2,a2:c2]
 roi_mask[np.any(pr!=nw,axis=2)]=[250,200,0]
 im=Image.fromarray(roi_mask,"RGB").resize(((c2-a2)*4,(d2-b2)*4),Image.Resampling.NEAREST)
 im.save(out/f"C1_Q217_{name}_CHANGE_MASK_4X.png")
# inspect raw mirror-Y crop equivalence exact in memory
for name,v in regions.items():
 x0,y0,x1,y1=v["wide"]
 raw=Image.open(files["A233"]).convert("RGBA").crop((x0,2048-y1,x1,2048-y0)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 sci[name+"_raw_flipy_mismatch_pixels"]=int(np.count_nonzero(np.any(np.asarray(raw)!=new[y0:y1,x0:x1],axis=2)))
manifest={p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted(out.glob("*.png"))}
sci.update({"source_sha256":expect["SOURCE"],"clean_sha256":expect["CLEAN"],"previous_sha256":expect["A231"],"candidate_sha256":expect["A233"],"native":(2048,2048),"regions":regionStats,"visual_evidence":manifest,"note":"Independently verified exact full DDS SOURCE/A231/A233, plate PNG CLEAN, decoded native stored pixels and both RAW/FLIP-Y. Source-to-CLEAN and final changes outside source bboxes measured independently."})
(out/"C1_Q217_MACHINE.json").write_text(json.dumps(sci,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in sci.items() if k!="visual_evidence"},ensure_ascii=False))
print("OUTPUT_PNGS",len(manifest))