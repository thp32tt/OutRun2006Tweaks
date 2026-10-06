#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
repo=Path.cwd(); run="20261006-A-DIAG105-590A"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
def dec(p):
 b=p.read_bytes(); h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; pf=struct.unpack_from("<8I",b,76); m=(pf[4],pf[5],pf[6])
 mode="RGBA" if m==(0xff,0xff00,0xff0000) else "BGRA"
 return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp=Path("/tmp/a105"); tmp.mkdir(exist_ok=True)
for name in ["590A4724_512x512.dds","C075FB49_512x512.dds"]:
 urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/"+name,tmp/name)
t=dec(tmp/"590A4724_512x512.dds"); s=dec(tmp/"C075FB49_512x512.dds")
clean=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_CLEAN_PLATE.png").convert("RGBA")
final=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_FINAL_READABLE.png").convert("RGBA")
dst=(1400,1960,1824,2048)
cells=[(50,(864,1624,1288,1712)),(51,(1288,1712,1712,1800)),(52,(864,1712,1288,1800))]
tc=np.asarray(t.crop(dst))
stats=[]
for idx,b in cells:
 sc=np.asarray(s.crop(b))
 stats.append({"template_cell":idx,"diff_pixels":int(np.count_nonzero(np.any(tc!=sc,axis=2))),
               "mean_abs_rgba":float(np.abs(tc.astype(np.int16)-sc.astype(np.int16)).mean())})
# labeled contact: target source + each template SOURCE/CLEAN/FINAL
panels=[]
labels=[]
panels.append(t.crop(dst)); labels.append("590A TARGET SOURCE")
for idx,b in cells:
 for kind,im in [("SRC",s),("CLEAN",clean),("FINAL",final)]:
  panels.append(im.crop(b)); labels.append(f"C075 cell{idx} {kind}")
scale=3
sheet=Image.new("RGB",(424*scale*2+12, (88*scale+30)*5),"white")
d=ImageDraw.Draw(sheet)
for n,(im,lab) in enumerate(zip(panels,labels)):
 row=n//2; col=n%2; z=Image.new("RGBA",im.size,(235,235,235,255)); z.alpha_composite(im)
 z=z.convert("RGB").resize((424*scale,88*scale),Image.Resampling.NEAREST)
 x=col*(424*scale+12); y=row*(88*scale+30)
 d.text((x+4,y+3),lab,fill="black"); sheet.paste(z,(x,y+26))
sheet.save(out/"A105_590A_TEMPLATE_CONTACTS.jpg",quality=94,optimize=True)
# small 151 proof
src151=Image.open(repo/"localization/graphics/role_A/20261006-A-PROBE103-ZOOM103151153/A103_4668C688_READABLE.png").convert("RGBA")
z=Image.new("RGBA",src151.size,(235,235,235,255)); z.alpha_composite(src151); z=z.convert("RGB"); z.thumbnail((800,800),Image.Resampling.LANCZOS)
z.save(out/"A105_4668C688_SMALL_PROOF.jpg",quality=75,optimize=True)
rep={"schema_version":1,"role":"A","run":run,"target":"590A4724","target_cell":[1400,1960,424,88],"c075_template_stats":stats,"status":"DIAGNOSTIC_COMPLETE"}
(out/"A105_DIAG.json").write_text(json.dumps(rep,indent=2)+"\n")
(wr/"A105_DIAG.json").write_text(json.dumps({"run":run,"stats":stats,"status":"DIAGNOSTIC_COMPLETE"},indent=2)+"\n")
print(json.dumps(rep),flush=True)
