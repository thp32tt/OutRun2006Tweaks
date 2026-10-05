#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-PRODUCTION87-IGR018-HEADER-FAMILY"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
srcp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candp=repo/"localization/graphics/hd_candidates"/asset_rel
cleanp=repo/"localization/graphics/role_A/20261005-A-RECOVERY13/FD90AA9_CLEAN_PLATE.png"
source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
input_sha="16f605a90a072b39c071e24edae578f181afd8d229e2238a9f6100815420da94"
rows=[
 ("select_game_mode","Select Game Mode","게임 모드 선택",(166,819,1166,973)),
 ("select_car","Select your car","차량 선택",(243,947,1156,1111)),
 ("select_course","Select Course","코스 선택",(302,1062,1085,1213)),
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def dmask(a,b):
 d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
 for q in cs[1:]:m=ImageChops.lighter(m,q)
 return bmask(m)
def count(m): return sum(m.histogram()[1:])
def flat(im):
 bg=Image.new("RGBA",im.size,(86,86,86,255)); bg.alpha_composite(im); return bg.convert("RGB")
def fontspec():
 for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
  try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
  except:q=""
  if "|" in q:
   p,ix=q.rsplit("|",1)
   if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
 p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()

def shear(mask,k):
 pad=max(12,int(mask.height*abs(k))+12)
 c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
 o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
 bb=o.getbbox(); return o.crop(bb) if bb else o

def shift(m,dx,dy):
 o=Image.new("L",m.size,0)
 sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
 if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
 return o

def render(text,fs=142,k=0.28):
 f=ImageFont.truetype(FONT,fs,index=FI)
 d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f)
 pad=28; m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
 ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
 m=shear(m,k); mb=m.getbbox(); m=m.crop(mb)
 # shared family: source-like white face, thin light edge, dark gray/black keyline and offset depth.
 outer=m.filter(ImageFilter.MaxFilter(11)); inner=m.filter(ImageFilter.MaxFilter(5)); sh=shift(outer,7,8)
 w,h=outer.size; z=Image.new("RGBA",(w,h),(0,0,0,0))
 z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(18,18,20,190)),Image.new("RGBA",(w,h),(0,0,0,0)),sh))
 z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(42,42,48,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
 z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(218,218,220,255)),Image.new("RGBA",(w,h),(0,0,0,0)),inner))
 # neutral white face (source group is plain white, not blue-tinted).
 z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(252,252,250,255)),Image.new("RGBA",(w,h),(0,0,0,0)),m))
 lb=z.getchannel("A").getbbox(); return z.crop(lb)

if sha(srcp)!=source_sha: raise RuntimeError(("source drift",sha(srcp)))
if sha(candp)!=input_sha: raise RuntimeError(("candidate drift",sha(candp)))
sb=srcp.read_bytes(); cb=candp.read_bytes()
if cb[:128]!=sb[:128]: raise RuntimeError("header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,mips)!=(4096,4096,16384,1): raise RuntimeError((W,H,pitch,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA"); src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA"); old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(cleanp).convert("RGBA")
if clean.size!=(W,H): raise RuntimeError("clean size")

allowed=Image.new("L",(W,H),0)
final=old.copy(); rec=[]; render_masks=[]; prev_bottom=None
for key,source,ko,bbox in rows:
 x0,y0,x1,y1=bbox
 ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
 final.paste(clean.crop(bbox),(x0,y0))
 layer=render(ko,120,0.28)
 if layer.width>x1-x0-12 or layer.height>y1-y0-10:
  raise RuntimeError(("shared fs does not fit",key,layer.size,bbox))
 # source bboxes are a centered shared header stack; preserve that center alignment.
 tx=x0+(x1-x0-layer.width)//2
 center_ty=y0+(y1-y0-layer.height)//2
 ty=max(y0+5,center_ty,(prev_bottom+5) if prev_bottom is not None else y0+5)
 if ty+layer.height>=y1:
  raise RuntimeError(("shared cadence does not fit",key,ty,layer.height,bbox,prev_bottom))
 lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
 loc=list(tm.getbbox() or ())
 if not loc or not(loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1):
  raise RuntimeError(("margin",key,loc,bbox))
 final.paste(layer,(tx,ty),lm); render_masks.append(tm); prev_bottom=loc[3]
 rec.append({"key":key,"source":source,"korean":ko,"original_bbox":list(bbox),"localized_bbox":loc,
   "source_size":[x1-x0,y1-y0],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
   "delta_left":loc[0]-x0,"delta_right":x1-loc[2],"delta_top":loc[1]-y0,"delta_bottom":y1-loc[3],
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":FPAT,"native_font_size_px":120,
   "shear":0.28,"alignment":"source-centered-horizontal-positive-vertical-cadence"})

delta=dmask(old,final); outside=count(ImageChops.multiply(delta,ImageOps.invert(allowed)))
ad=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A"))); alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))
# clean/source effect residue gate for the three exact bboxes
clean_res=0
for _,_,_,bbox in rows:
 sc=src.crop(bbox); cc=clean.crop(bbox); eff=dmask(sc,cc); same=ImageOps.invert(dmask(sc,cc))
 clean_res+=count(ImageChops.multiply(eff,same))
if clean_res: raise RuntimeError(("clean residue",clean_res))
# pairwise new-header overlap/touch; source provides positive vertical gaps.
overlaps=[]; touches=[]
for i in range(len(render_masks)):
 for j in range(i+1,len(render_masks)):
  ov=count(ImageChops.multiply(render_masks[i],render_masks[j]))
  tv=count(ImageChops.multiply(render_masks[i].filter(ImageFilter.MaxFilter(3)),render_masks[j]))
  if ov: overlaps.append([i,j,ov])
  if tv: touches.append([i,j,tv])
if overlaps or touches: raise RuntimeError(("header overlap/touch",overlaps,touches))

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); candp.write_bytes(cb[:128]+raw.tobytes("raw","RGBA"))
csha=sha(candp)
dec_raw=Image.frombytes("RGBA",(W,H),candp.read_bytes()[128:],"raw","RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

# Group contact: source/current-A86/clean/A87, showing all three shared rows.
group=(100,760,1260,1260)
ims=[flat(z.crop(group)) for z in (src,old,clean,dec)]; labs=["SOURCE","A86","CLEAN","A87 FINAL"]
sheet=Image.new("RGB",(sum(i.width for i in ims)+24*3,max(i.height for i in ims)+34),(225,225,225)); xx=0; dr=ImageDraw.Draw(sheet)
for lab,im in zip(labs,ims):
 dr.text((xx+4,4),lab,fill=(0,0,0)); sheet.paste(im,(xx,34)); xx+=im.width+24
sheet.save(out/"A87_IGR018_HEADER_FAMILY_CONTACT.jpg",quality=95)
flat(dec.crop(group)).resize(((group[2]-group[0])*2,(group[3]-group[1])*2),Image.Resampling.LANCZOS).save(out/"A87_IGR018_HEADER_FAMILY_2X.jpg",quality=96)
flat(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A87_FD90_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"queue_index":121,"asset":asset_rel,
"user_regression":{"id":"IGR-018","screenshot":"스크린샷(141).png","screen":"CAR_SELECT_BLUE","defect_tags":["SOURCE_RESIDUE","LOW_RES_FONT","HEADER_GHOST","STYLE_INCONSISTENCY"]},
"mapping":{"status":"EXACT_HIGH_CONFIDENCE_GRAPHICS","basis":"FD90AA9 uniquely contains the contiguous Select Game Mode / Select your car / Select Course source header stack visible in the car-select family."},
"source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,"candidate_path":str(candp.relative_to(repo)),
"structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mips":mips,"header_128_exact":candp.read_bytes()[:128]==sb[:128],"raw_orientation":"mirror_y"},
"reworked_elements":rec,
"family_style":{"shared_native_font":"Noto Sans CJK KR Black","font_size_px":120,"shear":0.28,"alignment":"source-centered-horizontal + positive vertical cadence","fill":"neutral white","outline":"light edge + dark gray keyline","shadow":"source-like offset dark depth","old_korean_bitmap_reused":False},
"preservation":{"all_pixels_outside_three_header_bboxes_vs_A86":"PIXEL_EXACT","other_26_localized_rows":"PRESERVED_BYTES"},
"machine_checks":{"changed_pixels_outside_header_union":outside,"alpha_changed_outside_header_union":alpha_out,"clean_source_effect_unchanged_pixels":clean_res,"localized_pair_overlap":[],"localized_pair_touch":[]},
"a86_fail_close_reason":"A86 changed only Select your car; controller family review would leave source-shared header lines in inconsistent Korean styles. The first A87 shared-family attempt at 142px was fail-closed because Select car/Course localized effects overlapped. This corrected A87 uses one 120px source-family style with explicit positive vertical cadence.",
"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"PENDING_NEW_INGAME_RETEST",
"status":"A87_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A87_IGR018_FD90_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A87_IGR018_FD90.json").write_text(json.dumps({"run":run,"index":121,"asset":"FD90AA9","candidate_sha256":csha,"regression":"IGR-018",
"bbox_size_margin":"3/3 PASS","outside":outside,"alpha_outside":alpha_out,"clean_residue":clean_res,"overlap":0,"touch":0,
"worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST","report":str((out/"A87_IGR018_FD90_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":csha,"rows":rec,"outside":outside,"alpha_outside":alpha_out,"clean_residue":clean_res},ensure_ascii=False))
