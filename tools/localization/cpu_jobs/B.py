#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION68"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
index=228
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b68")
work.mkdir(exist_ok=True)
dds=work/"a.dds"
atlas=work/"a.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_E7F6E9B7_512x512_atlas.json",atlas)

sb=dds.read_bytes()
ab=atlas.read_bytes()
def blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b):
    return hashlib.sha256(b).hexdigest()
def bmask(m):
    return m.point(lambda v:255 if v else 0)
def count(m):
    return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")

if blob(sb)!="87ff6635b287982d1dd2089f9bf9183df8a1e3ea":
    raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="17334e7e52c6f9f1848f0753eb22e35e2f04b1af":
    raise RuntimeError(("atlas blob drift",blob(ab)))

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
masks=(pf[4],pf[5],pf[6])
if (W,H,pitch,mips)!=(2048,2048,8192,1) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,len(sb)))
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode:
    raise RuntimeError(("rawmode",masks))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

specs=[
    (12,"coast 2 coast","코스트 2 코스트"),
    (11,"car select","차량 선택"),
    (10,"license select","라이선스 선택"),
    (9,"game lobby","게임 로비"),
    (8,"main menu","메인 메뉴"),
    (7,"multiplayer","멀티플레이"),
    (6,"music select","음악 선택"),
    (5,"options","옵션"),
    (4,"network","네트워크"),
    (3,"rankings","랭킹"),
    (2,"game select","게임 선택"),
    (1,"mode select","모드 선택"),
    (0,"race select","레이스 선택"),
]
if sorted(i for i,_,_ in specs)!=list(range(13)):
    raise RuntimeError("semantic map must cover all 13 cells")

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
rgba_samples=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    a=bmask(cell.getchannel("A"))
    bb=a.getbbox()
    if not bb:
        raise RuntimeError(("empty source cell",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),a),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    px=cell.load()
    for yy in range(ch):
        for xx in range(cw):
            r,g,b,aa=px[xx,yy]
            if aa>=96:
                rgba_samples.append((r,g,b,aa))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob})

if len(rgba_samples)<1000:
    raise RuntimeError(("style samples",len(rgba_samples)))

lums=sorted((0.2126*r+0.7152*g+0.0722*b,r,g,b,a) for r,g,b,a in rgba_samples)
def med_color(slice_):
    vals=lums[slice_]
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(1,5))
n=len(lums)
dark=med_color(slice(0,max(1,n//5)))
mid=med_color(slice(n//3,max(n//3+1,2*n//3)))
bright=med_color(slice(max(0,4*n//5),n))
OUTLINE=tuple(min(v,72) for v in dark[:3])+(255,)
SHADOW=tuple(min(v,48) for v in dark[:3])+(200,)
FILL_TOP=tuple(max(190,min(248,v)) for v in bright[:3])+(255,)
FILL_BOTTOM=tuple(max(120,min(205,v)) for v in mid[:3])+(255,)

source_visible=bmask(src.getchannel("A"))
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
if count(protected):
    raise RuntimeError(("unexpected protected visible pixels",count(protected)))

clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_mask)
cleanprot=ImageChops.multiply(source_visible,ImageOps.invert(source_mask))

sp=out/"E7F6_SOURCE_READABLE.png"
cp=out/"E7F6_CLEAN_PLATE.png"
smp=out/"E7F6_SOURCE_TEXT_MASK.png"
ap=out/"E7F6_ALLOWED_BBOX_MASK.png"
pp=out/"E7F6_PROTECTED_VISIBLE_MASK.png"
cpp=out/"E7F6_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap); protected.save(pp); cleanprot.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),"--report",str(out/"B68_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B68_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS":
    raise RuntimeError(("clean",cleanrep))

def getfont():
    def pick():
        for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black"]:
            try:
                s=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception:
                s=""
            if "|" in s:
                fp,ix=s.rsplit("|",1)
                if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
                    return fp,int(ix or 0),pat
        return None
    g=pick()
    if g:
        return g
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    g=pick()
    if not g:
        raise RuntimeError("font")
    return g

FONT,FI,FPAT=getfont()
SHEAR=0.12
STROKE=5
SHADOW_DX=4
SHADOW_DY=5
MARGIN=4

def shear_mask(mask, shear=SHEAR):
    w,h=mask.size
    extra=int(math.ceil(abs(shear)*h))+4
    outm=mask.transform((w+extra,h),Image.Transform.AFFINE,(1,-shear,0,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=outm.getbbox()
    return outm.crop(bb) if bb else outm

def render_label(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI)
    tmp=Image.new("L",(8,8),0)
    tb=ImageDraw.Draw(tmp).textbbox((0,0),text,font=f,stroke_width=0)
    pad=STROKE+SHADOW_DX+12
    w=max(8,tb[2]-tb[0]+pad*2)
    h=max(8,tb[3]-tb[1]+pad*2)
    fill=Image.new("L",(w,h),0)
    outer=Image.new("L",(w,h),0)
    pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(fill).text(pos,text,font=f,fill=255)
    ImageDraw.Draw(outer).text(pos,text,font=f,fill=255,stroke_width=STROKE,stroke_fill=255)
    fill=shear_mask(fill)
    outer=shear_mask(outer)
    ow=max(fill.width,outer.width)+SHADOW_DX+6
    oh=max(fill.height,outer.height)+SHADOW_DY+6
    fc=Image.new("L",(ow,oh),0); oc=Image.new("L",(ow,oh),0)
    fc.paste(fill,(2,2)); oc.paste(outer,(2,2))
    sh=Image.new("L",(ow,oh),0); sh.paste(oc,(SHADOW_DX,SHADOW_DY))
    rgba=Image.new("RGBA",(ow,oh),(0,0,0,0))
    rgba.paste(SHADOW,(0,0),sh)
    rgba.paste(OUTLINE,(0,0),oc)
    grad=Image.new("RGBA",(ow,oh),(0,0,0,0))
    gp=grad.load()
    den=max(1,oh-1)
    for yy in range(oh):
        t=yy/den
        c=tuple(int(round(FILL_TOP[k]*(1-t)+FILL_BOTTOM[k]*t)) for k in range(3))+(255,)
        for xx in range(ow):
            gp[xx,yy]=c
    rgba.paste(grad,(0,0),fc)
    bb=rgba.getchannel("A").getbbox()
    return rgba.crop(bb) if bb else rgba

FS=None
for fs in range(118,30,-1):
    ok=True
    for r in rows:
        ob=r["original_bbox"]
        aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
        lay=render_label(r["korean"],fs)
        if lay.width>aw-2*MARGIN or lay.height>ah-2*MARGIN:
            ok=False
            break
    if ok:
        FS=fs
        break
if FS is None:
    raise RuntimeError("shared fit")

final=clean.copy()
targets=[]
outrows=[]
for r in rows:
    ob=r["original_bbox"]
    aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    lay=render_label(r["korean"],FS)
    pos=(ob[0]+MARGIN,ob[1]+max(MARGIN,(ah-lay.height)//2))
    if pos[0]+lay.width>ob[2]-MARGIN:
        pos=(ob[2]-MARGIN-lay.width,pos[1])
    if pos[1]+lay.height>ob[3]-MARGIN:
        pos=(pos[0],ob[3]-MARGIN-lay.height)
    final.alpha_composite(lay,pos)
    lm=Image.new("L",(W,H),0)
    lm.paste(bmask(lay.getchannel("A")),pos)
    lb=list(lm.getbbox())
    if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]):
        raise RuntimeError(("margin",r["region_idx"],ob,lb))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah:
        raise RuntimeError(("size ceiling",r["region_idx"],ob,lb))
    if count(ImageChops.multiply(lm,protected)):
        raise RuntimeError(("protected overlap",r["region_idx"]))
    targets.append((r["region_idx"],lm))
    outrows.append({
        **r,
        "localized_bbox":lb,
        "source_width":aw,"source_height":ah,
        "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
        "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "font_file":Path(FONT).name,"font_face_index":FI,"font_size":FS,
        "stroke_width":STROKE,"shadow_offset":[SHADOW_DX,SHADOW_DY],"shear":SHEAR,
        "fill_top_rgba":FILL_TOP,"fill_bottom_rgba":FILL_BOTTOM,
        "outline_rgba":OUTLINE,"shadow_rgba":SHADOW,
        "rework_status":"B68_NEW_EXACT_HD_CANDIDATE"
    })

ov=0
touch=[]
for i in range(len(targets)):
    for j in range(i+1,len(targets)):
        a=targets[i][1]; b=targets[j][1]
        x=count(ImageChops.multiply(a,b))
        n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        ov+=x
        if x or n:
            touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch:
    raise RuntimeError(("overlap",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
csha=sha(payload)
if payload[:128]!=sb[:128]:
    raise RuntimeError("header")

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox():
    raise RuntimeError("roundtrip")
fp=out/"E7F6_FINAL_DECODED_READABLE.png"
dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B68_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B68_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets:
    target=ImageChops.lighter(target,m)
same=ImageOps.invert(diff)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),same))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or ov or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,ov,touch))
target.save(out/"E7F6_TARGET_TEXT_MASK.png")

cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    c=Image.new("RGB",(1024,1052),"white")
    c.paste(z,(0,28))
    ImageDraw.Draw(c).text((5,5),label,fill="black")
    cards.append(c)
sheet=Image.new("RGB",(1024,3156),"white")
for i,c in enumerate(cards):
    sheet.paste(c,(0,i*1052))
sheet.save(out/"B68_E7F6_SOURCE_CLEAN_FINAL.jpg",quality=96)

contacts=[]
for r in outrows:
    ob=r["original_bbox"]
    p=8
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    cw=sum(z.width for z in ims)+12
    ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),"white")
    xx=0
    for z in ims:
        c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white")
yy=0
for c in contacts:
    rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B68_E7F6_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2104),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    rr.paste(z,(0,i*1052+28))
    ImageDraw.Draw(rr).text((5,i*1052+5),label,fill="black")
rr.save(out/"B68_E7F6_RAW_COMPARE.jpg",quality=96)

report={
    "schema_version":1,"role":"B","run":run,"index":index,"asset":asset,
    "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
    "source_sha256":sha(sb),
    "semantic_binding":{str(i):en for i,en,_ in specs},
    "translations":{str(i):ko for i,_,ko in specs},
    "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
    "shared_source_style":{"family":"silver techno menu-name","font_file":Path(FONT).name,"font_face_index":FI,"font_size":FS,"shear":SHEAR,"stroke_width":STROKE,"shadow_offset":[SHADOW_DX,SHADOW_DY],"fill_top_rgba":FILL_TOP,"fill_bottom_rgba":FILL_BOTTOM,"outline_rgba":OUTLINE,"shadow_rgba":SHADOW},
    "rows":outrows,
    "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
    "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"overlap":ov,"touch_pairs":touch},
    "candidate_sha256":csha,
    "candidate_path":str(candidate.relative_to(repo)),
    "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
    "RUNTIME_VALIDATION":"UNTESTED",
    "status":"B_PRODUCTION68_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B68_E7F6_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={
    "run":run,"index":index,"asset":"E7F6E9B7","source_sha256":sha(sb),"candidate_sha256":csha,
    "bbox_size_positive_margin":"13/13","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
    "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"overlap":ov,"touch_pairs":len(touch),
    "worker_status":report["status"],"runtime_validation":"UNTESTED",
    "report":f"localization/graphics/role_B/{run}/B68_E7F6_REPORT.json"
}
(wr/"B68_E7F6E9B7.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
