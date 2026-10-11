from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import numpy as np,hashlib,json
root=Path.cwd()
out=root/"localization/graphics/role_C/20261011-C2-Q060-PSD-V02-SOURCE-FIDELITY"
out.mkdir(parents=True,exist_ok=True)
pd=root/"localization/graphics/source_psd_upstream/A064FDFC/872dd766_A064FDFC_1024x512-v02.psd"
src=root/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
manifest=root/"localization/graphics/plate_library/entries/6144f03e47650e55909abcfea820b451afa12e5f489bba2c747ef89334a8309a.json"
conf=json.loads(manifest.read_text())
mask_path=root/conf["removal"]["path"]
clean_path=root/conf["clean"]["path"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for label,p,exp in [("PSD",pd,"cb03eb03f6515da0453c0e70d316a89955fa6da9690833354b869145c97a8024"),("SOURCE",src,"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"),("MASK",mask_path,conf["removal"]["sha256"]),("CLEAN",clean_path,conf["clean"]["sha256"])]:
 assert sha(p)==exp,(label,sha(p),exp)
psd=Image.open(pd).convert("RGBA")
dds=Image.open(src).convert("RGBA")
clean=Image.open(clean_path).convert("RGBA")
mask=Image.open(mask_path)
print("SIZES",psd.size,dds.size,clean.size,mask.size,"MASKMODE",mask.mode)
assert psd.size==dds.size==clean.size==(4096,2048)
mr=np.asarray(mask.convert("L"))
ym,xm=np.nonzero(mr>0)
bb=[int(xm.min()),int(ym.min()),int(xm.max()+1),int(ym.max()+1)] if len(xm) else None
# full-canvas source vs merged PSD, and clean approved provenance candidate check
psd_a=np.asarray(psd)
ddraw=np.asarray(dds)
dc=np.asarray(clean)
# accurate readable transform
read=np.flipud(ddraw)
pixel=np.any(psd_a!=read,axis=2)
raw_diff=np.any(psd_a!=ddraw,axis=2)
alpha=psd_a[:,:,3]!=read[:,:,3]
src_clean=np.any(read!=dc,axis=2)
outside_mask=int(np.count_nonzero(src_clean & ~(mr>0)))
metrics={"psd_vs_canonical_readable_rgba_diff":int(pixel.sum()),"psd_vs_canonical_readable_alpha_diff":int(alpha.sum()),"psd_vs_canonical_raw_rgba_diff":int(raw_diff.sum()),"total_pixels":4096*2048,
"psd_vs_canonical_readable_equal":bool(not pixel.any()),"source_vs_legacy_clean_changed":int(src_clean.sum()),"source_vs_legacy_clean_changed_outside_removal_mask":outside_mask,
"source_vs_legacy_clean_alpha_changed":int(np.count_nonzero(read[:,:,3]!=dc[:,:,3])),"removal_mask_nonzero":int((mr>0).sum()),"removal_mask_bbox":bb,
"source_sha256":sha(src),"psd_sha256":sha(pd),"existing_clean_sha256":sha(clean_path),"removal_sha256":sha(mask_path)}
# visible ROI includes exact source removal mask, padded 40px
x0=max(0,bb[0]-40); y0=max(0,bb[1]-40); x1=min(4096,bb[2]+40);y1=min(2048,bb[3]+40)
roi=(x0,y0,x1,y1)
def matte(im,bg=(160,160,160)):
 b=Image.new("RGBA",im.size,bg+(255,));b.alpha_composite(im);return b.convert("RGB")
frames=[("PSD MERGED",matte(psd.crop(roi))),("ENGLISH DDS FLIPY",matte(Image.fromarray(read[y0:y1,x0:x1]))),("EXISTING CLEAN",matte(clean.crop(roi)))]
cw,ch=x1-x0,y1-y0
pane=Image.new("RGB",(cw*3,ch+25),(160,160,160));draw=ImageDraw.Draw(pane)
for i,(name,img) in enumerate(frames):
 pane.paste(img,(i*cw,25));draw.text((i*cw+4,3),name,fill=(0,0,0))
pane.save(out/"C2_Q060_PSD_SOURCE_CLEAN_ROI_NATIVE.png")
pane.resize((pane.width//2,pane.height//2),Image.Resampling.LANCZOS).save(out/"C2_Q060_PSD_SOURCE_CLEAN_ROI_50.png")
# entire 4096x2048, downscaled QA navigational overview only
overview=Image.new("RGB",(1200,200), (145,145,145))
small=[matte(im.resize((400,200),Image.Resampling.LANCZOS)) for im in [psd,Image.fromarray(read),clean]]
for i,im in enumerate(small):overview.paste(im,(i*400,0))
overview.save(out/"C2_Q060_PSD_SOURCE_CLEAN_ATLAS_OVERVIEW.png")
# avoid false claims: PSD mismatch means cannot qualify PSD as source
result={"review_id":"C2-Q060-PSD-CANONICAL-FIRST","source_base_head":"d3f6f4930","queue_index":60,"source":str(src.relative_to(root)),
"psd":str(pd.relative_to(root)),"existing_clean":str(clean_path.relative_to(root)),"removal_mask":str(mask_path.relative_to(root)),
"metrics":metrics,"readable_roi":list(roi),"evidence":[str(x.relative_to(root)) for x in out.glob("*.png")],
"status":"INDEPENDENT_PSD_SOURCE_FIDELITY_MEASURED_NOT_PLATE_APPROVAL","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C2_Q060_PSD_CANONICAL_MACHINE.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
print(json.dumps(metrics,ensure_ascii=False))
