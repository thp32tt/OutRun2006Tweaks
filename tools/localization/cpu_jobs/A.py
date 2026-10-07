#!/usr/bin/env python3
import os,hashlib,json,struct,subprocess
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261008-A176-Q121-TRANSPARENT-PLATE"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
srcp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
cand=repo/"localization/graphics/hd_candidates"/rel
SOURCE="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
INPUT="03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433"

rows=[
 ("select_game_mode","Select Game Mode","게임 모드 선택",(166,819,1166,973)),
 ("select_car","Select your car","차량 선택",(243,947,1156,1111)),
 ("select_course","Select Course","코스 선택",(302,1062,1085,1213)),
]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bmask(m):
    return m.point(lambda v:255 if v else 0)

def count(m):
    return sum(m.histogram()[1:])

def dmask(a,b):
    d=ImageChops.difference(a,b)
    cs=d.split()
    m=cs[0]
    for q in cs[1:]:
        m=ImageChops.lighter(m,q)
    return bmask(m)

def flat(im,bg=(86,86,86,255)):
    z=Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")

def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:
            q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:
            q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:
                return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1)
    return p,int(ix or 0),"Noto Sans CJK KR:style=Black"

FONT,FI,FPAT=fontspec()

def shear(mask,k):
    pad=max(12,int(mask.height*abs(k))+12)
    c=Image.new("L",(mask.width+pad*2,mask.height),0)
    c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,k,0,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox()
    return o.crop(bb) if bb else o

def shift(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy)
    sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:
        o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o

def render(text,fs=108,k=.28):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    bb=d.textbbox((0,0),text,font=f)
    pad=28
    m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
    ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    m=shear(m,k)
    m=m.crop(m.getbbox())
    outer=m.filter(ImageFilter.MaxFilter(11))
    inner=m.filter(ImageFilter.MaxFilter(5))
    sh=shift(outer,7,8)
    z=Image.new("RGBA",outer.size,(0,0,0,0))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(18,18,20,190)),Image.new("RGBA",outer.size,(0,0,0,0)),sh))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(42,42,48,255)),Image.new("RGBA",outer.size,(0,0,0,0)),outer))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(218,218,220,255)),Image.new("RGBA",outer.size,(0,0,0,0)),inner))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(252,252,250,255)),Image.new("RGBA",outer.size,(0,0,0,0)),m))
    return z.crop(z.getchannel("A").getbbox())

if sha(srcp)!=SOURCE:
    raise RuntimeError(("source drift",sha(srcp),SOURCE))
if sha(cand)!=INPUT:
    raise RuntimeError(("candidate drift",sha(cand),INPUT))

sb=srcp.read_bytes()
cb=cand.read_bytes()
if sb[:4]!=b"DDS " or cb[:128]!=sb[:128]:
    raise RuntimeError("header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,mips)!=(4096,4096,16384,1):
    raise RuntimeError((W,H,pitch,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# C255 proved the visible English ghosts are still alpha-visible. The header atlas
# cells are transparent-background text sprites, not opaque gray plates. Prior A171-
# A174 attempts treated the neutral QA background as authored plate color and created
# rectangular patches. Rebuild from the actual persisted alpha geometry instead.
allowed=Image.new("L",(W,H),0)
clean=old.copy()
final=old.copy()
clean_union=Image.new("L",(W,H),0)
stats=[]

for key,source,ko,bbox in rows:
    x0,y0,x1,y1=bbox
    ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
    oc=old.crop(bbox)
    sc=src.crop(bbox)
    oa=bmask(oc.getchannel("A"))
    sa=bmask(sc.getchannel("A"))
    area=(x1-x0)*(y1-y0)
    old_cov=count(oa)/area
    src_cov=count(sa)/area
    # A text-only transparent atlas region should be sparse. If not, fail closed
    # instead of erasing protected artwork.
    if old_cov>0.72 or src_cov>0.72:
        raise RuntimeError(("unsafe alpha coverage",key,old_cov,src_cov))
    rm=ImageChops.lighter(oa,sa)
    # clear only pixels belonging to current/source visible text/effects; transparent
    # atlas background remains transparent and no rectangular fill is introduced.
    cp=clean.crop(bbox)
    fp=final.crop(bbox)
    zero=Image.new("RGBA",cp.size,(0,0,0,0))
    cp.paste(zero,(0,0),rm)
    fp.paste(zero,(0,0),rm)
    clean.paste(cp,(x0,y0))
    final.paste(fp,(x0,y0))
    clean_union.paste(ImageChops.lighter(clean_union.crop(bbox),rm),(x0,y0))
    stats.append({"key":key,"source_alpha_coverage":round(src_cov,6),"prior_alpha_coverage":round(old_cov,6),"cleared_pixels":count(rm)})

# Clean plate must contain no visible alpha inside the exact three source header
# footprints after removing old/source layers. This is the source-art-aware
# transparent plate condition for these atlas cells.
clean_visible_by_row={}
for key,source,ko,bbox in rows:
    n=count(bmask(clean.crop(bbox).getchannel("A")))
    clean_visible_by_row[key]=n
    if n!=0:
        raise RuntimeError(("clean plate still visible in text-only header bbox",key,n))

rec=[]
render_masks=[]
for key,source,ko,bbox in rows:
    x0,y0,x1,y1=bbox
    layer=render(ko,108,.28)
    if layer.width>x1-x0-12 or layer.height>y1-y0-10:
        raise RuntimeError(("fit",key,layer.size,bbox))
    tx=x0+(x1-x0-layer.width)//2
    ty=y0+(y1-y0-layer.height)//2
    lm=bmask(layer.getchannel("A"))
    tm=Image.new("L",(W,H),0)
    tm.paste(lm,(tx,ty))
    loc=list(tm.getbbox() or ())
    if not loc or not(loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1):
        raise RuntimeError(("margin",key,loc,bbox))
    final.alpha_composite(layer,(tx,ty))
    render_masks.append(tm)
    rec.append({
      "key":key,"source":source,"korean":ko,
      "original_bbox":list(bbox),"localized_bbox":loc,
      "source_size":[x1-x0,y1-y0],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
      "delta_left":loc[0]-x0,"delta_right":x1-loc[2],
      "delta_top":loc[1]-y0,"delta_bottom":y1-loc[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":FPAT,"native_font_size_px":108,"shear":.28,
      "alignment":"source-centered-shared-header-family"
    })

overlaps=[]
touches=[]
for i in range(len(render_masks)):
    for j in range(i+1,len(render_masks)):
        ov=count(ImageChops.multiply(render_masks[i],render_masks[j]))
        tv=count(ImageChops.multiply(render_masks[i].filter(ImageFilter.MaxFilter(3)),render_masks[j]))
        if ov: overlaps.append([i,j,ov])
        if tv: touches.append([i,j,tv])
if overlaps or touches:
    raise RuntimeError(("overlap/touch",overlaps,touches))

diff=dmask(old,final)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
ad=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A")))
alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out:
    raise RuntimeError(("outside",outside,alpha_out))

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand.write_bytes(cb[:128]+raw.tobytes("raw","RGBA"))
csha=sha(cand)
db=cand.read_bytes()
dec_raw=Image.frombytes("RGBA",(W,H),db[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None:
    raise RuntimeError("roundtrip")

# Evidence: each row SOURCE | A138 PRIOR | TRUE CLEAN | A176 FINAL.
cards=[]
for key,source,ko,bbox in rows:
    x0,y0,x1,y1=bbox
    pad=28
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("A138 PRIOR",old),("A176 CLEAN",clean),("A176 FINAL",dec)]:
        z=flat(im.crop(crop))
        scale=min(1.0,640/max(1,z.width))
        if scale<1:
            z=z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.LANCZOS)
        cc=Image.new("RGB",(z.width,z.height+24),(24,24,24))
        cc.paste(z,(0,24))
        ImageDraw.Draw(cc).text((4,4),lab,fill="white")
        ims.append(cc)
    row=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+18),(16,16,16))
    xx=0
    for cc in ims:
        row.paste(cc,(xx,0)); xx+=cc.width+12
    ImageDraw.Draw(row).text((4,row.height-2),key,fill="white",anchor="ls")
    cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8*(len(cards)-1)),(16,16,16))
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.save(out/"A176_Q121_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

group=(100,760,1260,1260)
gims=[]
for lab,im in [("SOURCE",src),("A138 PRIOR",old),("A176 CLEAN",clean),("A176 FINAL",dec)]:
    z=flat(im.crop(group))
    z=z.resize((580,250),Image.Resampling.LANCZOS)
    cc=Image.new("RGB",(580,278),(24,24,24)); cc.paste(z,(0,28))
    ImageDraw.Draw(cc).text((4,5),lab,fill="white")
    gims.append(cc)
gs=Image.new("RGB",(580*4+36,278),(16,16,16)); xx=0
for cc in gims:
    gs.paste(cc,(xx,0)); xx+=592
gs.save(out/"A176_Q121_HEADER_FAMILY.jpg","JPEG",quality=96,subsampling=0)

sraw=flat(src_raw); fraw=flat(dec_raw)
sraw.thumbnail((1000,1000),Image.Resampling.LANCZOS)
fraw.thumbnail((1000,1000),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(sraw.width+fraw.width+12,max(sraw.height,fraw.height)+26),(16,16,16))
rw.paste(sraw,(0,26)); rw.paste(fraw,(sraw.width+12,26))
dr=ImageDraw.Draw(rw)
dr.text((4,4),"SOURCE RAW",fill="white")
dr.text((sraw.width+16,4),"A176 RAW",fill="white")
rw.save(out/"A176_Q121_RAW.jpg","JPEG",quality=94,subsampling=0)
clean.save(out/"A176_Q121_CLEAN.png")
clean_union.save(out/"A176_Q121_REMOVAL_MASK.png")

report={
 "schema_version":2,"role":"A","run":run,"queue_index":121,"asset":"FD90AA9",
 "regression":"IGR-018 / C255 visible English source residue double draw",
 "input_candidate_sha256":INPUT,"candidate_sha256":csha,"source_sha256":SOURCE,
 "construction":"transparent-atlas alpha-aware reconstruction: clear union of canonical-source and current visible alpha only inside the three exact source header bboxes; no opaque/gray rectangle fill; fresh native A138-family Korean rerender",
 "alpha_geometry":stats,"clean_visible_alpha_by_row":clean_visible_by_row,
 "rows":rec,
 "machine_qa":{
   "bbox_size_positive_margin":"3/3 PASS",
   "changed_outside_header_union":outside,
   "alpha_changed_outside_header_union":alpha_out,
   "localized_pair_overlap":overlaps,
   "localized_pair_touch_1px":touches,
   "header_128_exact":db[:128]==sb[:128],
   "persisted_decode":"PASS",
   "raw_orientation":"mirror_y"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "fresh_independent_c":"REQUIRED",
 "mandatory_c3":"REQUIRED_EXACT_SHA",
 "runtime_validation":"UNTESTED",
 "status":"A176_Q121_MACHINE_PASS_PENDING_CONTROLLER_VISUAL",
 "forbidden_domains_touched":[]
}
(out/"A176_Q121_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A176_Q121.json").write_text(json.dumps({
 "run":run,"index":121,"asset":"FD90AA9","before":INPUT,"after":csha,
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"candidate_sha256":csha,"alpha_geometry":stats,"rows":rec},ensure_ascii=False,indent=2))
