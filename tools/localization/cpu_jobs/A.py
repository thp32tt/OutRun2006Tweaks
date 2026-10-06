#!/usr/bin/env python3
import hashlib,json,math,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION113-D263-D103-DIAG"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
tmp=Path("/tmp/a113"); tmp.mkdir(exist_ok=True)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI=q.rsplit("|",1); FI=int(FI or 0)
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name: raise RuntimeError(("font",FONT,FI))

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im):
    bg=Image.new("RGBA",im.size,(235,235,235,255)); bg.alpha_composite(im); return bg.convert("RGB")
def dec(raw,expected):
    if sha(raw)!=expected: raise RuntimeError(("source drift",sha(raw),expected))
    H,W,pitch,depth,mips=struct.unpack_from("<5I",raw,12); pf=struct.unpack_from("<8I",raw,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or len(raw)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(raw)))
    rim=Image.frombytes("RGBA",(W,H),raw[128:],"raw",mode)
    return W,H,mips,mode,rim,rim.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def shear_mask(mask,k):
    pad=max(6,int(math.ceil(abs(k)*mask.height))+8); c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC); bb=o.getbbox()
    return o.crop(bb) if bb else o

# ---- D263 material production ----
p=tmp/"D263B3F1.dds"; urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds",p)
raw=p.read_bytes(); W,H,mips,mode,raw_src,src=dec(raw,"6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d")
atlas=json.loads(urllib.request.urlopen(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_D263B3F1_512x512_atlas.json").read().decode())
reg=next(x for x in atlas["regions"] if x["idx"]==2); x,y,cw,ch=reg["rect"]
cell=src.crop((x,y,x+cw,y+ch)); sm_local=bmask(cell.getchannel("A")); bb=sm_local.getbbox()
if not bb: raise RuntimeError("D263 header empty")
ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
source_mask=Image.new("L",(W,H),0); source_mask.paste(sm_local,(x,y))
clean=src.copy(); clean.paste(Image.new("RGBA",(cw,ch),(0,0,0,0)),(x,y),sm_local)
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
source_visible=bmask(src.getchannel("A")); protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
sp=out/"A113_D263_SOURCE_READABLE.png"; cp=out/"A113_D263_CLEAN_PLATE.png"; smp=out/"A113_D263_SOURCE_TEXT_MASK.png"; ap=out/"A113_D263_ALLOWED_BBOX_MASK.png"; pp=out/"A113_D263_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap); protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A113_D263_CLEAN_VALIDATION.json")],check=True)
cr=json.loads((out/"A113_D263_CLEAN_VALIDATION.json").read_text())
if cr["status"]!="PASS": raise RuntimeError(("D263 clean",cr))

SHEAR=.12; STROKE=5; SDX=4; SDY=5; MARGIN=4; TOP=(244,244,244,255); BOT=(134,134,134,255); OUTLINE=(2,2,2,255); SHADOW=(2,2,2,200)
def render_silver(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI); tb=ImageDraw.Draw(Image.new("L",(8,8),0)).textbbox((0,0),text,font=f)
    pad=STROKE+SDX+12; size=(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2)
    fill=Image.new("L",size,0); outer=Image.new("L",size,0); pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(fill).text(pos,text,font=f,fill=255); ImageDraw.Draw(outer).text(pos,text,font=f,fill=255,stroke_width=STROKE,stroke_fill=255)
    fill=shear_mask(fill,SHEAR); outer=shear_mask(outer,SHEAR)
    ow=max(fill.width,outer.width)+SDX+6; oh=max(fill.height,outer.height)+SDY+6
    fc=Image.new("L",(ow,oh),0); oc=Image.new("L",(ow,oh),0); fc.paste(fill,(2,2)); oc.paste(outer,(2,2))
    sh=Image.new("L",(ow,oh),0); sh.paste(oc,(SDX,SDY))
    rgba=Image.new("RGBA",(ow,oh),(0,0,0,0)); rgba.paste(SHADOW,(0,0),sh); rgba.paste(OUTLINE,(0,0),oc)
    grad=np.zeros((oh,ow,4),dtype=np.uint8)
    for yy in range(oh):
        t=yy/max(1,oh-1); grad[yy,:,]=[round(TOP[k]*(1-t)+BOT[k]*t) for k in range(4)]
    rgba.paste(Image.fromarray(grad,"RGBA"),(0,0),fc); rb=rgba.getchannel("A").getbbox()
    return rgba.crop(rb) if rb else rgba
aw,ah=ob[2]-ob[0],ob[3]-ob[1]
chosen=None
for fs in range(101,80,-1):
    lay=render_silver("코스 선택",fs)
    if lay.width<=aw-2*MARGIN and lay.height<=ah-2*MARGIN:
        chosen=(fs,lay); break
if not chosen: raise RuntimeError(("D263 no fit",ob))
fs,lay=chosen; px=ob[0]+MARGIN; py=ob[1]+max(MARGIN,(ah-lay.height)//2)
if py+lay.height>ob[3]-MARGIN: py=ob[3]-MARGIN-lay.height
final=clean.copy(); final.alpha_composite(lay,(px,py))
target=Image.new("L",(W,H),0); target.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(target.getbbox()); margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
if min(margins)<=0 or lb[2]-lb[0]>aw or lb[3]-lb[1]>ah: raise RuntimeError(("D263 bbox",ob,lb,margins))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=raw[:128]+raw_final.tobytes("raw",mode)
cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"; cand.parent.mkdir(parents=True,exist_ok=True); cand.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); decim=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decim,final).getbbox(): raise RuntimeError("D263 roundtrip")
fp=out/"A113_D263_FINAL_READABLE.png"; decim.save(fp); target.save(out/"A113_D263_RENDER_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A113_D263_FINAL_VALIDATION.json")],check=True)
fr=json.loads((out/"A113_D263_FINAL_VALIDATION.json").read_text())
diff=dmask(src,decim); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed))); alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),decim.getchannel("A"))),ImageOps.invert(allowed)))
same=ImageOps.invert(diff); residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),same))
if fr["status"]!="PASS" or outside or alphaout or residue: raise RuntimeError(("D263 gates",fr["status"],outside,alphaout,residue))
box=(max(0,ob[0]-12),max(0,ob[1]-12),min(W,ob[2]+12),min(H,ob[3]+12))
ims=[comp(z.crop(box)) for z in (src,clean,decim)]; ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+38),"white"); xx=0; ImageDraw.Draw(sheet).text((5,5),"D263 COURSE SELECT -> 코스 선택 | SOURCE CLEAN FINAL",fill="black")
for z in ims: sheet.paste(z,(xx,38)); xx+=z.width+8
sheet.save(out/"A113_D263_CONTACTS.jpg",quality=96,optimize=True)
rr=Image.new("RGB",(1000,1040),"white")
for i,(labn,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),labn,fill="black")
rr.save(out/"A113_D263_RAW_COMPARE.jpg",quality=92,optimize=True)
d263={"queue_index":219,"asset":"D263B3F1","source_sha256":sha(raw),"candidate_sha256":sha(payload),"classification":{"source":"COURSE SELECT","korean":"코스 선택"},"family_reference":"C144-approved B68 silver-techno menu-name family","style":{"font":Path(FONT).name,"face_index":FI,"font_size":fs,"shear":SHEAR,"stroke_width":STROKE,"shadow_offset":[SDX,SDY]},"row":{"original_bbox":ob,"localized_bbox":lb,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},"zero_pixel_gates":{"outside":outside,"alpha_outside":alphaout,"source_residue":residue,"overlap":0},"clean_validator":cr,"final_validator":fr,"candidate_path":str(cand.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"}

# ---- D103 diagnostic: identify the actual red START/GOAL sign components exactly ----
p=tmp/"D1039D6F.dds"; urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds",p)
drawraw=p.read_bytes(); DW,DH,dmips,dmode,draw_src,dsrc=dec(drawraw,"d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0")
sa=np.asarray(dsrc,dtype=np.uint8); r=sa[:,:,0].astype(np.int16); g=sa[:,:,1].astype(np.int16); b=sa[:,:,2].astype(np.int16); a=sa[:,:,3]>8
red=a&(r>155)&(r>g+60)&(r>b+40)&(g<125)
lab,n=ndimage.label(red); comps=[]
for i in range(1,n+1):
    c=(lab==i); area=int(c.sum())
    if area<150: continue
    yy,xx=np.nonzero(c); x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1); w=x1-x0; h=y1-y0
    if w<35 or h<8 or w>350 or h>150: continue
    bright=int(np.count_nonzero(a[y0:y1,x0:x1]&(r[y0:y1,x0:x1]>180)&(g[y0:y1,x0:x1]>120)&(b[y0:y1,x0:x1]>60)))
    comps.append({"label":i,"area":area,"bbox":[x0,y0,x1,y1],"w":w,"h":h,"aspect":round(w/max(1,h),3),"rectangularity":round(area/max(1,w*h),3),"bright":bright,"center":[round((x0+x1)/2,1),round((y0+y1)/2,1)]})
comps=sorted(comps,key=lambda z:z["area"],reverse=True)
ov=dsrc.copy(); dd=ImageDraw.Draw(ov)
for j,c in enumerate(comps[:40]):
    x0,y0,x1,y1=c["bbox"]; dd.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,255,255),width=3); dd.text((x0,max(0,y0-14)),str(j),fill=(0,0,0,255))
proof=comp(ov); proof.thumbnail((1800,1800),Image.Resampling.LANCZOS); proof.save(out/"A113_D103_RED_COMPONENT_DIAGNOSTIC.jpg",quality=94,optimize=True)
d103diag={"queue_index":217,"asset":"D1039D6F","source_sha256":sha(drawraw),"candidate_components":comps[:40],"status":"ONE_STAGE_TO_RENDER_COMPONENT_MAPPING_READY_FOR_CONTROLLER"}
(out/"A113_D103_DIAGNOSTIC.json").write_text(json.dumps(d103diag,indent=2)+"\n")

report={"schema_version":1,"role":"A","run":run,"D263B3F1":d263,"D1039D6F":d103diag,"status":"A113_D263_STATIC_PASS_D103_COMPONENT_DIAGNOSTIC_COMPLETE","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False}
(out/"A113_BATCH_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A113_D263_D103.json").write_text(json.dumps({"run":run,"D263_candidate_sha256":d263["candidate_sha256"],"D103_status":d103diag["status"],"report":f"localization/graphics/role_A/{run}/A113_BATCH_REPORT.json"},indent=2)+"\n")
print(json.dumps({"D263":d263,"D103_components":comps[:20]},ensure_ascii=False),flush=True)
