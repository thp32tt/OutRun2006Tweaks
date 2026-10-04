#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261004-A-PRODUCTION12"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wout=repo/"localization/graphics/worker_results"; wout.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A_prod12"); work.mkdir(parents=True,exist_ok=True)
source=work/"43B07A77_HD.dds"; atlas=work/"4x_43B07A77_512x64_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175"
BLOB="ca95f45529f841405c89bf0c00be25abcc0b5802"
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",source)
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_route_cvt_Exst/4x_43B07A77_512x64_atlas.json",atlas)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(2048,256,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(pf)
if len(sb)!=2097280: raise RuntimeError(len(sb))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

aj=json.loads(atlas.read_text(encoding="utf-8")); rr=aj["regions"][0]; x,y,cw,ch=rr["rect"]; cell=[x,y,x+cw,y+ch]
bb=readable.crop(tuple(cell)).getchannel("A").getbbox()
if not bb: raise RuntimeError("empty source text")
ob=[cell[0]+bb[0],cell[1]+bb[1],cell[0]+bb[2],cell[1]+bb[3]]

def count(m): return sum(m.histogram()[1:])
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

srcmask=Image.new("L",(W,H),0)
local=readable.crop(tuple(cell)).getchannel("A").point(lambda v:255 if v else 0)
srcmask.paste(local,(cell[0],cell[1]))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
protected=ImageChops.multiply(balpha(readable),ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(balpha(readable),ImageOps.invert(srcmask))
clean=readable.copy(); clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),srcmask)

sp=out/"43B07A77_HD_SOURCE_READABLE.png"; cp=out/"43B07A77_HD_CLEAN_PLATE.png"
smp=out/"43B07A77_HD_SOURCE_TEXT_MASK.png"; ap=out/"43B07A77_HD_ALLOWED_TEXT_REGION_MASK.png"
pp=out/"43B07A77_HD_PROTECTED_VISIBLE_MASK.png"; cpp=out/"43B07A77_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
readable.save(sp); clean.save(cp); srcmask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),"--report",str(out/"A_PRODUCTION12_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION12_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError("clean fail")

def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    return subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT=resolve_font()

def shear(m,s):
    w,h=m.size; k=s/max(1,h-1)
    return m.transform((w+s+4,h),Image.Transform.AFFINE,(1,k,-s,0,1,0),resample=Image.Resampling.BICUBIC)

def gradient(size):
    w,h=size; im=Image.new("RGBA",size); px=im.load()
    top=(252,250,255,255); mid=(255,231,220,255); bot=(246,162,101,255)
    for yy in range(h):
        t=yy/max(1,h-1)
        if t<.42: u=t/.42; a,b=top,mid
        else: u=(t-.42)/.58; a,b=mid,bot
        c=tuple(int(round(a[k]+(b[k]-a[k])*u)) for k in range(4))
        for xx in range(w): px[xx,yy]=c
    return im

def render(text):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(205,ah),45,-1):
        font=ImageFont.truetype(FONT,fs); ow=max(7,fs//15); iw=max(3,fs//30); pad=28
        tb=font.getbbox(text,stroke_width=ow); cw=tb[2]-tb[0]+pad*2; ch=tb[3]-tb[1]+pad*2
        masks={}
        for name,sw in [("outer",ow),("inner",iw),("fill",0)]:
            m=Image.new("L",(cw,ch),0); d=ImageDraw.Draw(m); d.text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
            masks[name]=shear(m,max(10,fs//5))
        union=ImageChops.lighter(masks["outer"],masks["inner"]); union=ImageChops.lighter(union,masks["fill"]); ub=union.getbbox()
        masks={k:v.crop(ub) for k,v in masks.items()}; mw=max(v.width for v in masks.values()); mh=max(v.height for v in masks.values())
        sx,sy=max(4,fs//30),max(6,fs//24)
        if mw+sx>aw-12 or mh+sy>ah-12: continue
        layer=Image.new("RGBA",(mw+sx,mh+sy),(0,0,0,0))
        sm=Image.new("L",layer.size,0); sm.paste(masks["outer"],(sx,sy)); layer.paste(Image.new("RGBA",layer.size,(8,8,15,210)),(0,0),sm)
        mm=Image.new("L",layer.size,0); mm.paste(masks["outer"],(0,0)); layer.paste(Image.new("RGBA",layer.size,(245,246,252,255)),(0,0),mm)
        mm=Image.new("L",layer.size,0); mm.paste(masks["inner"],(0,0)); layer.paste(Image.new("RGBA",layer.size,(25,30,45,255)),(0,0),mm)
        fm=Image.new("L",layer.size,0); fm.paste(masks["fill"],(0,0)); layer.paste(gradient(layer.size),(0,0),fm)
        lb=layer.getchannel("A").getbbox(); layer=layer.crop(lb)
        if layer.width<=aw-12 and layer.height<=ah-12:
            tx=ob[0]+(aw-layer.width)//2; ty=ob[1]+(ah-layer.height)//2
            return layer,(tx,ty),fs
    raise RuntimeError("fit")

layer,(tx,ty),fs=render("게임 오버"); lm=layer.getchannel("A").point(lambda v:255 if v else 0)
final=clean.copy(); final.paste(layer,(tx,ty),lm)
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cb=sb[:128]+raw_final.tobytes("raw","RGBA"); candidate.write_bytes(cb); csha=sha(candidate)
if cb[:128]!=sb[:128]: raise RuntimeError("header")
decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA"); decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
dp=out/"43B07A77_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A_PRODUCTION12_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION12_FINAL_MASK_VALIDATION.json").read_text())

diff=dmask(readable,decoded); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha=count(ImageChops.multiply(ImageChops.difference(readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected)); residue=count(ImageChops.multiply(balpha(clean),srcmask))
db=decoded.crop(tuple(cell)).getchannel("A").getbbox(); loc=[cell[0]+db[0],cell[1]+db[1],cell[0]+db[2],cell[1]+db[3]]
ok=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]

def gray(im):
    bg=Image.new("RGBA",im.size,(100,100,100,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W, H*3),(60,60,60)); sheet.paste(gray(readable),(0,0)); sheet.paste(gray(clean),(0,H)); sheet.paste(gray(decoded),(0,H*2)); sheet.save(out/"A_PRODUCTION12_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=94)
gray(decoded_raw).save(out/"A_PRODUCTION12_FINAL_RAW_GRAY.jpg",quality=94)
cx1=max(0,ob[0]-24); cy1=max(0,ob[1]-24); cx2=min(W,ob[2]+24); cy2=min(H,ob[3]+24)
a=gray(readable.crop((cx1,cy1,cx2,cy2))); b=gray(decoded.crop((cx1,cy1,cx2,cy2)))
contact=Image.new("RGB",(a.width+b.width+20,max(a.height,b.height)),(225,225,225)); contact.paste(a,(0,0)); contact.paste(b,(a.width+20,0)); contact.save(out/"A_PRODUCTION12_ROW_CONTACT.jpg",quality=94)

status=cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and outside==0 and alpha==0 and prot==0 and residue==0 and ok
report={"schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),"index":89,"asset":asset_rel,
"source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":SOURCE_SHA,"path":"Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds","classification":"authoritative high-resolution source; stale filename suffix, DDS header 2048x256 RGBA32"},
"source_sha256":SOURCE_SHA,"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
"structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
"translation":{"source":"Game Over","korean":"게임 오버"},"original_bbox":ob,"localized_bbox":loc,"delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],"containment":"PASS" if ok else "FAIL","font_size":fs,
"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bbox":outside,"alpha_changed_pixels_outside_original_bbox":alpha,"protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue},
"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED","status":"A_PRODUCTION12_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_PRODUCTION12_WORKER_REWORK_REQUIRED"}
(out/"A_PRODUCTION12_43B07A77_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"43B07A77","index":89,"source_sha256":SOURCE_SHA,"candidate_sha256":csha,"source_dimensions":[W,H],"format":"RGBA32","bbox_pass":"1/1" if ok else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"changed_pixels_outside_original_bbox":outside,"alpha_changed_pixels_outside_original_bbox":alpha,"protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261004-A-PRODUCTION12/A_PRODUCTION12_43B07A77_REPORT.json"}
(wout/"A_PRODUCTION12_43B07A77.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
