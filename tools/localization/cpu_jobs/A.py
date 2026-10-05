#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION31"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A_prod31"); work.mkdir(parents=True,exist_ok=True)
source=work/"37759842_HD.dds"; atlasp=work/"4x_37759842_1024x1024_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="eeecec9ecd494270932ce97a6c38dfd05205eb24"
ATLAS_BLOB_SHA1="581d42b49da9b882f2a54cdfef7675d147afacaa"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_37759842_1024x1024_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); parts=d.split(); m=parts[0]
    for p in parts[1:]: m=ImageChops.lighter(m,p)
    return bmask(m)
def flatten(im):
    z=Image.new("RGBA",im.size,(90,90,90,255)); z.alpha_composite(im); return z.convert("RGB")

sb=source.read_bytes(); ab=atlasp.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob drift",blobsha(sb)))
if blobsha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob drift",blobsha(ab)))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(4096,4096,16384,1) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb)))
rgbm=(pf[4],pf[5],pf[6])
if pf[3]!=32: raise RuntimeError(("bpp",pf))
if rgbm==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif rgbm==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("masks",rgbm))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8"))
regions={int(r["idx"]):r for r in atlas["regions"]}
if len(regions)!=87: raise RuntimeError(("atlas count",len(regions)))

# Physical target binding established from A30 numbered canonical-HD atlas review.
# Duplicate sprites intentionally map to the same reviewed semantic translation.
SPECS={
 2:(["예"],"orange_blue","plate","full"), 3:(["아니오"],"orange_blue","plate","full"),
 4:(["타임 어택","모드","15코스","연속"],"white_dark","plate","continuous"),
 5:(["아웃런","모드","15코스","연속"],"white_dark","plate","continuous"),
 6:(["타임 어택","모드"],"orange_blue","plate","mode"), 7:(["하트 어택","모드"],"orange_blue","plate","mode"),
 8:(["아웃런","모드"],"orange_blue","plate","mode"), 9:(["타임 어택","모드"],"orange_blue","plate","mode"),
 10:(["하트 어택","모드"],"orange_blue","plate","mode"), 11:(["아웃런","모드"],"orange_blue","plate","mode"),
 29:(["무작위"],"white_random","plate","random"),
 43:(["예"],"orange_blue","plate","yesno_small"), 44:(["아니오"],"orange_blue","plate","yesno_small"),
 45:(["타임 어택","모드","15코스","연속"],"white_dark","plate","continuous_small"),
 46:(["아웃런","모드","15코스","연속"],"white_dark","plate","continuous_small"),
 47:(["타임 어택","모드"],"orange_blue","plate","mode_small"), 48:(["하트 어택","모드"],"orange_blue","plate","mode_small"),
 49:(["아웃런","모드"],"orange_blue","plate","mode_small"), 50:(["타임 어택","모드"],"orange_blue","plate","mode_small"),
 51:(["하트 어택","모드"],"orange_blue","plate","mode_small"), 52:(["아웃런","모드"],"orange_blue","plate","mode_small"),
 59:(["조작이 어려운 차량입니다."],"white_red_help","text","text"),
 60:(["상급자용"],"red_white_help","text","text"),
 61:(["참가자를 기다리는 중입니다."],"cream_help","text","text"),
 62:(["참가 접수가 종료되었습니다."],"cream_help","text","text"),
 63:(["잠시 기다려 주세요."],"cream_help","text","text"),
 64:(["수동","변속"],"orange_redplate","plate","transmission"),
 65:(["자동","변속"],"yellow_greenplate","plate","transmission"),
 66:(["실제","플레이어","전용"],"orange_yellowplate","plate","realplayer"),
 82:(["수동"],"red_glow","text","text"),
 83:(["상급자용: 조작이 어려운 차량입니다."],"white_red_help","text","text"),
 84:(["상급자용: 기어 변속이 필요합니다."],"white_red_help","text","text"),
 85:(["튜닝"],"red_glow","text","text"),
}
if len(SPECS)!=33: raise RuntimeError(("target count",len(SPECS)))

# Protected canonical content deliberately excluded:
# idx0/1 & 41/42 MT/AT icon badges, idx12-28/30-40/54-58/67-81 Ferrari/model/song/logo art,
# idx37/38/53/86 non-text/decorative plates/lines.
PROTECTED_INDICES=sorted(set(regions)-set(SPECS))

def roi_for(idx,w,h,kind):
    if kind=="full": return (int(.13*w),int(.18*h),int(.87*w),int(.70*h))
    if kind=="continuous": return (int(.07*w),int(.16*h),int(.61*w),int(.83*h))
    if kind=="mode": return (int(.08*w),int(.12*h),int(.60*w),int(.62*h))
    if kind=="random": return (int(.16*w),int(.11*h),int(.67*w),int(.35*h))
    if kind=="yesno_small": return (int(.15*w),int(.16*h),int(.84*w),int(.68*h))
    if kind=="continuous_small": return (int(.08*w),int(.13*h),int(.64*w),int(.85*h))
    if kind=="mode_small": return (int(.08*w),int(.10*h),int(.61*w),int(.62*h))
    if kind=="transmission": return (int(.07*w),int(.08*h),int(.73*w),int(.72*h))
    if kind=="realplayer": return (int(.08*w),int(.10*h),int(.79*w),int(.84*h))
    return (0,0,w,h)

def core_detect(crop,style,kind):
    a=np.asarray(crop,dtype=np.uint8)
    rgb=a[:,:,:3].astype(np.int16); al=a[:,:,3]
    r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
    h,w=al.shape
    x0,y0,x1,y1=roi_for(0,w,h,kind)
    roi=np.zeros((h,w),bool); roi[y0:y1,x0:x1]=True
    if style in ("orange_blue","orange_redplate"):
        m=(r>165)&(g>65)&(g<205)&(b<125)&((r-g)>35)&roi&(al>40)
    elif style=="yellow_greenplate":
        m=(r>165)&(g>125)&(b<130)&roi&(al>40)
    elif style=="orange_yellowplate":
        m=(r>150)&(g<180)&(b<125)&((r-g)>25)&roi&(al>40)
    elif style in ("white_dark","white_random"):
        mx=np.maximum.reduce([r,g,b]); mn=np.minimum.reduce([r,g,b])
        m=(mn>150)&((mx-mn)<75)&roi&(al>40)
    else:
        m=(al>0)&roi
    # Remove tiny specks and retain glyph-scale connected components only.
    lab,n=ndimage.label(m)
    keep=np.zeros_like(m)
    for k in range(1,n+1):
        yy,xx=np.where(lab==k)
        if len(xx)>=18:
            keep[yy,xx]=True
    if keep.sum()<40: raise RuntimeError(("core detect",style,kind,int(m.sum()),int(keep.sum())))
    return keep,roi

def nearest_inpaint_rgba(arr,mask):
    if not mask.any(): return arr.copy()
    # nearest unmasked source pixel; suitable for the flat/gradient selector plates.
    _,inds=ndimage.distance_transform_edt(mask,return_indices=True)
    outa=arr.copy()
    yy,xx=np.where(mask)
    outa[yy,xx]=arr[inds[0,yy,xx],inds[1,yy,xx]]
    return outa

source_text_mask=Image.new("L",(W,H),0)
source_core_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
clean=src.copy()
rows=[]
masks={}
cores={}
for idx,(lines,style,mode,kind) in SPECS.items():
    r=regions[idx]; x,y,w,h=map(int,r["rect"]); crop=src.crop((x,y,x+w,y+h))
    if mode=="text":
        core=(np.asarray(crop.getchannel("A"))>0)
        effect=core.copy()
    else:
        core,roi=core_detect(crop,style,kind)
        # Effect halo/shadow around source glyph core, clipped to semantic text ROI.
        dil=11 if min(w,h)>=240 else 8
        effect=ndimage.binary_dilation(core,iterations=dil)&roi
    yy,xx=np.where(effect)
    if len(xx)==0: raise RuntimeError(("empty effect",idx))
    eb=[x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1]
    cy,cx=np.where(core)
    cb=[x+int(cx.min()),y+int(cy.min()),x+int(cx.max())+1,y+int(cy.max())+1]
    em=Image.new("L",(W,H),0); em.paste(Image.fromarray((effect*255).astype(np.uint8)),(x,y))
    cm=Image.new("L",(W,H),0); cm.paste(Image.fromarray((core*255).astype(np.uint8)),(x,y))
    source_text_mask=ImageChops.lighter(source_text_mask,em)
    source_core_mask=ImageChops.lighter(source_core_mask,cm)
    ImageDraw.Draw(allowed).rectangle((eb[0],eb[1],eb[2]-1,eb[3]-1),fill=255)
    masks[idx]=em; cores[idx]=cm
    if mode=="text":
        c=np.asarray(crop).copy(); c[effect]=0
    else:
        c=nearest_inpaint_rgba(np.asarray(crop),effect)
    clean.paste(Image.fromarray(c.astype(np.uint8),"RGBA"),(x,y))
    rows.append({"idx":idx,"source_effect_bbox":eb,"source_core_bbox":cb,
                 "source_width":eb[2]-eb[0],"source_height":eb[3]-eb[1],
                 "korean_lines":lines,"style":style,"mode":mode,"kind":kind,
                 "source_effect_pixels":int(effect.sum()),"source_core_pixels":int(core.sum())})

# Static clean-plate gate.
sp=out/"37759842_HD_SOURCE_READABLE.png"; cp=out/"37759842_HD_CLEAN_PLATE.png"
smp=out/"37759842_HD_SOURCE_TEXT_MASK.png"; scp=out/"37759842_HD_SOURCE_CORE_MASK.png"
ap=out/"37759842_HD_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); source_core_mask.save(scp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
pp=out/"37759842_HD_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--report",str(out/"A31_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A31_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
clean_diff=dmask(src,clean)
clean_outside=count(ImageChops.multiply(clean_diff,ImageOps.invert(source_text_mask)))
if clean_outside: raise RuntimeError(("clean outside source mask",clean_outside))

def resolve_font():
    pats=["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Black","Noto Sans CJK KR"]
    for install in (False,True):
        for pat in pats:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" in spec:
                fp,ix=spec.rsplit("|",1)
                if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
                    return fp,int(ix or 0),pat
        if not install:
            subprocess.run(["sudo","apt-get","update","-qq"],check=True)
            subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    raise RuntimeError("Noto CJK font unavailable")
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def palette(style):
    return {
      "orange_blue":((244,148,25,255),(25,35,55,255),(8,12,18,205)),
      "white_dark":((235,235,230,255),(30,30,35,255),(5,5,8,205)),
      "white_random":((245,245,245,255),(25,35,55,255),(8,12,18,205)),
      "white_red_help":((242,242,238,255),(22,29,48,255),(168,32,40,170)),
      "red_white_help":((225,45,50,255),(250,250,245,255),(25,25,32,190)),
      "cream_help":((248,235,184,255),(36,42,70,255),(10,12,18,190)),
      "orange_redplate":((245,147,25,255),(88,20,18,255),(30,8,8,190)),
      "yellow_greenplate":((250,224,50,255),(25,75,25,255),(8,30,8,190)),
      "orange_yellowplate":((221,94,25,255),(92,45,12,255),(40,20,8,160)),
      "red_glow":((205,45,48,255),(25,31,66,255),(248,248,240,190)),
    }[style]

def shear(im,amount):
    if amount<=0:return im
    w,h=im.size; k=amount/max(1,h-1)
    return im.transform((w+amount+3,h),Image.Transform.AFFINE,(1,k,-amount,0,1,0),resample=Image.Resampling.BICUBIC)

def build_layer(lines,style,bw,bh):
    fill,edge,shadow=palette(style)
    # Preserve source line count; fit a shared font size across all lines.
    target_w=int(bw*0.88); target_h=int(bh*0.82)
    if style=="red_glow": target_w=int(bw*0.90); target_h=int(bh*0.78)
    for fs in range(max(18,int(bh/max(1,len(lines))*0.78)),13,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        stroke=max(2,min(7,int(round(fs*0.055))))
        gap=max(1,int(round(fs*0.08)))
        boxes=[font.getbbox(t,stroke_width=stroke) for t in lines]
        widths=[b[2]-b[0] for b in boxes]; heights=[b[3]-b[1] for b in boxes]
        cw=max(widths)+stroke*8+20; ch=sum(heights)+gap*(len(lines)-1)+stroke*8+20
        base=Image.new("RGBA",(cw,ch),(0,0,0,0)); dr=ImageDraw.Draw(base)
        yy=stroke*4+8
        for t,bx,lh in zip(lines,boxes,heights):
            tw=bx[2]-bx[0]; tx=stroke*4+8+(max(widths)-tw)//2
            dr.text((tx-bx[0]+3,yy-bx[1]+4),t,font=font,fill=shadow,stroke_width=stroke,stroke_fill=edge)
            dr.text((tx-bx[0],yy-bx[1]),t,font=font,fill=fill,stroke_width=stroke,stroke_fill=edge)
            yy+=lh+gap
        if style=="red_glow":
            alpha=base.getchannel("A")
            glow=alpha.filter(ImageFilter.GaussianBlur(max(3,fs//12)))
            gl=Image.new("RGBA",base.size,(248,248,240,0)); gl.putalpha(glow.point(lambda v:min(150,v)))
            gl.alpha_composite(base); base=gl
        base=shear(base,max(2,int(fs*0.08)))
        bb=base.getchannel("A").getbbox()
        if not bb: continue
        base=base.crop(bb)
        # Source sprites are wide/low. Widen the Korean block after fitting height.
        if base.height>target_h:
            nw=max(1,int(round(base.width*target_h/base.height)))
            base=base.resize((nw,target_h),Image.Resampling.LANCZOS)
        desired=min(target_w,bw-8)
        if base.width<desired:
            base=base.resize((desired,base.height),Image.Resampling.LANCZOS)
        if base.width<=bw-6 and base.height<=bh-6:
            return base,fs,stroke
    raise RuntimeError(("cannot fit",lines,style,bw,bh))

final=clean.copy(); target_masks={}
for row in rows:
    ob=row["source_effect_bbox"]; bw,bh=ob[2]-ob[0],ob[3]-ob[1]
    layer,fs,stroke=build_layer(row["korean_lines"],row["style"],bw,bh)
    tx=ob[0]+(bw-layer.width)//2; ty=ob[1]+(bh-layer.height)//2
    lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
    lb=list(tm.getbbox() or ())
    contain=len(lb)==4 and lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]
    sizeok=contain and (lb[2]-lb[0])<=bw and (lb[3]-lb[1])<=bh
    if not (contain and sizeok): raise RuntimeError(("bbox fail",row["idx"],ob,lb))
    final.paste(layer,(tx,ty),lm)
    target_masks[row["idx"]]=tm
    row.update({"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
                "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
                "font_size":fs,"stroke_px":stroke,"font_pattern":FONT_PATTERN})

# Encode exact DDS structure/header/raw mirror_y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("DDS header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("DDS decoded roundtrip drift")
dp=out/"37759842_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)

# Exhaustive decoded-pixel gates.
subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),
                "--report",str(out/"A31_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A31_FINAL_MASK_VALIDATION.json").read_text())
diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=bmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")))
alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
# Atlas target regions are disjoint. Prove overlap/touch cheaply from localized bounding boxes
# instead of O(N^2) full-4096 mask multiplications.
lbs={r["idx"]:r["localized_bbox"] for r in rows}
keys=sorted(lbs); overlap=0; touch=0
for i in range(len(keys)):
    a=lbs[keys[i]]
    for j in range(i+1,len(keys)):
        b=lbs[keys[j]]
        if max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3]):
            overlap=1
        if max(a[0]-1,b[0]-1) < min(a[2]+1,b[2]+1) and max(a[1]-1,b[1]-1) < min(a[3]+1,b[3]+1):
            touch=1
# Build one union then dilate once; avoids 33 full-frame morphology passes.
target_union=Image.new("L",(W,H),0)
for tm in target_masks.values(): target_union=ImageChops.lighter(target_union,tm)
guard=target_union.filter(ImageFilter.MaxFilter(5))
same=ImageOps.invert(dmask(src,decoded))
residue=count(ImageChops.multiply(source_core_mask,ImageChops.multiply(same,ImageOps.invert(guard))))
clean_same=ImageOps.invert(dmask(src,clean))
clean_source_core_unchanged=count(ImageChops.multiply(source_core_mask,clean_same))
allbbox=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows)
status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and clean_outside==0 and outside==0 and alpha_out==0
        and protected_changed==0 and overlap==0 and touch==0 and residue==0 and clean_source_core_unchanged==0 and allbbox)

# Compact controller visual evidence: full SOURCE/CLEAN/FINAL at 1/4 plus one contact card per target.
thumbs=[]
for im in (src,clean,decoded):
    q=flatten(im).resize((1024,1024),Image.Resampling.LANCZOS); thumbs.append(q)
sheet=Image.new("RGB",(3072,1024),(90,90,90))
for i,q in enumerate(thumbs): sheet.paste(q,(i*1024,0))
sheet.save(out/"A31_SOURCE_CLEAN_FINAL_QUARTER.jpg",quality=94)

cards=[]
for row in rows:
    ob=row["source_effect_bbox"]; pad=18
    box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad))
    ims=[flatten(z.crop(box)) for z in (src,clean,decoded)]
    maxh=180
    scaled=[]
    for q in ims:
        sc=min(1.0,maxh/max(1,q.height)); scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+16; ch=max(q.height for q in scaled)+26
    card=Image.new("RGB",(cw,ch),(230,230,230)); cd=ImageDraw.Draw(card)
    cd.text((4,4),f"idx {row['idx']}  {' / '.join(row['korean_lines'])}  SOURCE | CLEAN | FINAL",fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,26)); xx+=q.width+8
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
contacts=Image.new("RGB",(cw,ch),(225,225,225)); yy=0
for c in cards: contacts.paste(c,(0,yy)); yy+=c.height+3
contacts.save(out/"A31_TARGET_CONTACTS.jpg",quality=94)
flatten(decoded_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A31_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"index":95,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
                      "path":"Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"},
 "atlas_provenance":{"git_blob_sha1":ATLAS_BLOB_SHA1,"regions":87},
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":CANDIDATE_SHA,
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "binding":{"physical_localized_targets":len(rows),"reviewed_semantic_strings":20,
            "localized_indices":sorted(SPECS),"protected_indices":PROTECTED_INDICES,
            "preserve_original":"song titles/music credits, Ferrari/model names, MT/AT icon badges, logos and non-text decorative art"},
 "rows":rows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "machine_checks":{"clean_changed_outside_source_text_mask":clean_outside,"clean_source_core_pixels_unchanged":clean_source_core_unchanged,
                   "decoded_changed_outside_source_effect_bboxes":outside,"alpha_changed_outside_source_effect_bboxes":alpha_out,
                   "protected_visible_pixels_changed":protected_changed,"localized_overlap_pixels":overlap,"localized_1px_touch_pixels":touch,
                   "source_core_residue_pixels":residue},
 "all_33_bbox_size_positive_margin_pass":allbbox,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A31_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A31_WORKER_REWORK_REQUIRED"}
(out/"A31_37759842_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":95,"asset":"37759842","candidate_sha256":CANDIDATE_SHA,
         "localized_physical_targets":len(rows),"semantic_strings":20,
         "bbox_size_positive_margin":"33/33 PASS" if allbbox else "FAIL",
         "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
         "changed_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
         "overlap":overlap,"touch":touch,"source_residue":residue,"clean_source_core_unchanged":clean_source_core_unchanged,
         "worker_status":report["status"],"runtime_validation":"UNTESTED",
         "report":"localization/graphics/role_A/20261005-A-PRODUCTION31/A31_37759842_REPORT.json"}
(wr/"A31_37759842.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
