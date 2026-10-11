from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageChops
import numpy as np,hashlib,json
root=Path.cwd()
p=root/"localization/graphics/source_psd_upstream/FD90AA9/68e32365_FD90AA9_1024x1024.psd"
s=root/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
folder=root/"localization/graphics/role_C/20261011-C2-Q121-PSD-V02-ENGLISH-CANONICAL-COMPARISON"
folder.mkdir(parents=True,exist_ok=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
roi=(3460,365,3760,470)
psd=Image.open(p).convert("RGBA")
src=Image.open(s).convert("RGBA")
# compare PSD raw and mirrorY source in readable coord
source_readable=ImageOps.flip(src)
a=np.asarray(psd.crop(roi),dtype=np.int16)
b=np.asarray(source_readable.crop(roi),dtype=np.int16)
c=np.asarray(src.crop(roi),dtype=np.int16)
metrics={}
for tag,x in [("DDS_READABLE_FLIPY",b),("DDS_RAW_UNFLIPPED",c)]:
 pix=np.any(a!=x,axis=2)
 alph=(a[:,:,3]!=x[:,:,3])
 metrics[tag]={"different_RGBA_pixels":int(np.count_nonzero(pix)),"different_alpha_pixels":int(np.count_nonzero(alph)),
 "mean_abs_RGBA":float(np.mean(np.abs(a-x))),"PSD_nonzero_alpha":int(np.count_nonzero(a[:,:,3])),"DDS_nonzero_alpha":int(np.count_nonzero(x[:,:,3])),
 "equal":bool(np.array_equal(a,x))}
# compare alpha shape for source readable against PSD
for name,z in [("PSD_FULL",psd),("CANONICAL_DDS_FLIPY",source_readable),("CANONICAL_DDS_RAW",src)]:
 im=z.crop(roi)
 im.save(folder/f"C2_Q121_{name}_ROI_NATIVE.png")
# neutral bg pane
panels=[]
for k,im in [("PSD composite",psd.crop(roi)),("canonical FLIPY",source_readable.crop(roi)),("canonical RAW",src.crop(roi))]:
 matte=Image.new("RGBA",im.size,(140,140,140,255));matte.alpha_composite(im)
 panels.append((k,matte.convert("RGB")))
cw=roi[2]-roi[0];ch=roi[3]-roi[1]
out=Image.new("RGB",(cw*3,ch+26),(150,150,150))
d=ImageDraw.Draw(out)
for i,(k,im) in enumerate(panels):
 out.paste(im,(cw*i,26));d.text((cw*i+3,4),k,fill=(0,0,0))
out.save(folder/"C2_Q121_PSD_vs_CANONICAL_ROI_COMPARE.png")
report={"queue_index":121,"source_psd_path":str(p.relative_to(root)),"canonical_game_dds_path":str(s.relative_to(root)),"source_psd_sha256":sha(p),"canonical_dds_sha256":sha(s),"source_size":list(psd.size),"roi_readable":list(roi),"metrics":metrics,"claim":"PIL PSD merged composite compared to exact canonical English DDS, two orientations. Does not imply selected English layer or CLEAN approved. Source-only evidence.","evidence":[str(x.relative_to(root)) for x in folder.glob("*.png")]}
(folder/"C2_Q121_PSD_TO_CANONICAL_FIRSTHAND.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"psd_sha256":report["source_psd_sha256"],"source_sha256":report["canonical_dds_sha256"],"metrics":metrics},ensure_ascii=False))
