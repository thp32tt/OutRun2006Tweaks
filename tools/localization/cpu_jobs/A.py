#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,math
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION36"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A36"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
SOURCE_BLOB_SHA1="1e95df72109411fb1f9c398445db583ed31de2a1"
ATLAS_BLOB_SHA1="90b0122b7fdc44a553eff3f3e83278725ad0f24b"
source=work/"560FA536_HD.dds"; atlasp=work/"4x_560FA536_1024x1024_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_560FA536_1024x1024_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); ps=d.split(); m=ps[0]
    for p in ps[1:]: m=ImageChops.lighter(m,p)
    return bmask(m)
def flatten(im,bg=(88,88,88)):
    z=Image.new("RGBA",im.size,bg+(255,)); z.alpha_composite(im); return z.convert("RGB")

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
atlas=json.loads(ab.decode("utf-8")); regions={int(r["idx"]):r for r in atlas["regions"]}
if len(regions)!=48: raise RuntimeError(("atlas count",len(regions)))

# 12 reviewed semantics / 13 physical sprites. Song titles, OutRun2 and speed values are protected.
SPECS={
 11:{"lines":[[("튜닝","main")]],"kind":"plate_tuned"},
 12:{"lines":[[("일반","main")]],"kind":"plate_normal"},
 14:{"lines":[[("무작위","main")]],"kind":"plate_random"},
 21:{"lines":[[("초급자용","accent"),(" 차량입니다.","white")]],"kind":"expert_green"},
 22:{"lines":[[("중급자용","accent"),(" 차량입니다.","white")]],"kind":"expert_orange"},
 24:{"lines":[[("싱글 플레이 모드","accent"),("로 전환하려면","white")],
              [("시점 변경 버튼","accent"),("과 ","white"),("브레이크 페달","accent"),("을 동시에 누르세요.","white")]],"kind":"help_yellow"},
 31:{"lines":[[("이 모드를 플레이하려면 모든 플레이어가","accent")],
              [("동시에 참가해야 합니다.","accent")]],"kind":"warning"},
 32:{"lines":[[("대전 스페셜 코스","accent"),("가 선택되었습니다.","white")]],"kind":"versus"},
 33:{"lines":[[("타임 어택 모드","main")]],"kind":"plate_time_red"},
 34:{"lines":[[("타임 어택 모드","main")]],"kind":"plate_time_green"},
 36:{"lines":[[("최종 골까지의 거리가 ","white"),("매우 깁니다.","accent")]],"kind":"help_red"},
 37:{"lines":[[("15코스를 연속으로 달립니다.","white")]],"kind":"help_white"},
 44:{"lines":[[("스티어링 휠:","white")]],"kind":"steering"},
}
PROTECTED_INDICES=sorted(set(regions)-set(SPECS))
PROTECTED_TEXT={25:"song title",26:"song title",27:"song title",28:"song title",29:"song title",30:"song title",38:"OutRun2",45:"speed value",46:"speed value"}

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
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
    raise RuntimeError("Noto CJK unavailable")
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def plate_core(crop,kind):
    a=np.asarray(crop,dtype=np.uint8); rgb=a[:,:,:3].astype(np.int16); al=a[:,:,3]
    r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]; h,w=al.shape
    roi=np.zeros((h,w),bool)
    if kind in ("plate_tuned","plate_normal"): roi[int(.10*h):int(.52*h),int(.13*w):int(.92*w)]=True
    elif kind=="plate_random": roi[int(.08*h):int(.42*h),int(.16*w):int(.82*w)]=True
    elif kind.startswith("plate_time"): roi[int(.03*h):int(.92*h),int(.02*w):int(.98*w)]=True
    if kind=="plate_tuned":
        core=(r>205)&(g>85)&(g<225)&(b<100)&roi&(al>40)
    elif kind=="plate_normal":
        core=(r>180)&(g>180)&(b<175)&roi&(al>40)
    elif kind=="plate_random":
        core=(r>190)&(g>190)&(b>190)&roi&(al>40)
    else:
        core=(r>185)&(g>165)&(b<185)&roi&(al>40)
    lab,n=ndimage.label(core); keep=np.zeros_like(core)
    for k in range(1,n+1):
        yy,xx=np.where(lab==k)
        if len(xx)>=10: keep[yy,xx]=True
    if int(keep.sum())<80: raise RuntimeError(("plate core too small",kind,int(core.sum()),int(keep.sum())))
    return keep,roi

def clean_plate_crop(crop,effect,core,transparent):
    arr=np.asarray(crop).copy()
    if transparent:
        arr[effect]=0
        return Image.fromarray(arr.astype(np.uint8),"RGBA")
    _,inds=ndimage.distance_transform_edt(effect,return_indices=True)
    yy,xx=np.where(effect); arr[yy,xx]=arr[inds[0,yy,xx],inds[1,yy,xx]]
    # Re-sample core from outside a wider ring when byte-identical to source remains.
    same=core & np.all(arr==np.asarray(crop),axis=2)
    if same.any():
        wide=ndimage.binary_dilation(effect,iterations=14)
        _,inds2=ndimage.distance_transform_edt(wide,return_indices=True)
        sy,sx=np.where(same); arr[sy,sx]=np.asarray(crop)[inds2[0,sy,sx],inds2[1,sy,sx]]
    # Smooth only repaired RGB to avoid nearest-neighbor streaks on simple plate gradients.
    tmp=Image.fromarray(arr.astype(np.uint8),"RGBA")
    blur=tmp.filter(ImageFilter.GaussianBlur(10))
    ba=np.asarray(blur).copy()
    rgbmask=effect
    arr[rgbmask,:3]=ba[rgbmask,:3]
    # Strictly disambiguate any remaining source-core equal pixel without changing alpha.
    same=core & np.all(arr==np.asarray(crop),axis=2)
    sy,sx=np.where(same)
    for y,x in zip(sy.tolist(),sx.tolist()):
        px=arr[y,x].copy(); ch=int(np.argmin(px[:3])); px[ch]=px[ch]+1 if px[ch]<255 else px[ch]-1; arr[y,x]=px
    return Image.fromarray(arr.astype(np.uint8),"RGBA")

def source_masks(idx,crop,kind):
    a=np.asarray(crop)
    alpha=a[:,:,3]>0
    if kind.startswith("plate_"):
        core,roi=plate_core(crop,kind)
        dil=12 if crop.height>=120 else 8
        effect=ndimage.binary_dilation(core,iterations=dil)&roi
        return core,effect,False
    if kind=="warning":
        core=alpha.copy(); core[:,:int(crop.width*.17)]=False
        return core,core.copy(),True
    # These atlas rows are isolated transparent lettering/effects.
    return alpha.copy(),alpha.copy(),True

def palette(kind,role):
    # fill, stroke, shadow
    if kind=="plate_tuned": return ((255,158,24,255),(85,18,8,255),(20,8,6,220))
    if kind=="plate_normal": return ((255,244,112,255),(20,72,22,255),(8,20,8,220))
    if kind=="plate_random": return ((245,245,245,255),(12,45,95,255),(8,18,38,220))
    if kind=="expert_green":
        return (((46,225,48,255) if role=="accent" else (248,248,248,255)),(5,5,5,255),(250,250,250,180))
    if kind=="expert_orange":
        return (((245,132,18,255) if role=="accent" else (248,248,248,255)),(5,5,5,255),(250,250,250,180))
    if kind in ("help_yellow","warning","versus"):
        return (((252,190,25,255) if role=="accent" else (248,248,248,255)),(15,18,66,255),(5,6,24,210))
    if kind=="help_red":
        return (((225,52,58,255) if role=="accent" else (248,248,248,255)),(15,18,66,255),(5,6,24,210))
    if kind=="help_white":
        return ((248,248,248,255),(15,18,66,255),(5,6,24,210))
    if kind.startswith("plate_time"):
        return ((255,242,114,255),(70,55,18,255),(25,12,15,220))
    if kind=="steering":
        return ((248,248,248,255),(12,34,42,255),(5,16,20,190))
    return ((248,248,248,255),(20,20,20,255),(5,5,5,200))

def shear(im,amount):
    if amount<=0:return im
    w,h=im.size; k=amount/max(1,h-1)
    return im.transform((w+amount+3,h),Image.Transform.AFFINE,(1,k,-amount,0,1,0),resample=Image.Resampling.BICUBIC)

def line_width(font,segments,stroke,gap):
    total=0; hs=[]
    for txt,role in segments:
        b=font.getbbox(txt,stroke_width=stroke); total+=b[2]-b[0]; hs.append(b[3]-b[1])
    total+=gap*max(0,len(segments)-1)
    return total,max(hs or [1])

def build_layer(lines,kind,bw,bh):
    # Japanese expert labels intentionally use a much larger colored lead phrase
    # and a smaller white tail. Preserve that source-intentional hierarchy.
    if kind in ("expert_green","expert_orange"):
        accent_txt,accent_role=lines[0][0]
        tail_txt,tail_role=lines[0][1]
        for bigfs in range(max(30,int(bh*.86)),20,-1):
            smallfs=max(18,int(round(bigfs*.62)))
            big=ImageFont.truetype(FONT,bigfs,index=FONT_INDEX)
            small=ImageFont.truetype(FONT,smallfs,index=FONT_INDEX)
            sb=max(2,min(8,int(round(bigfs*.055))))
            ss=max(2,min(6,int(round(smallfs*.055))))
            bb1=big.getbbox(accent_txt,stroke_width=sb); bb2=small.getbbox(tail_txt,stroke_width=ss)
            w1=bb1[2]-bb1[0]; h1=bb1[3]-bb1[1]; w2=bb2[2]-bb2[0]; h2=bb2[3]-bb2[1]
            gap=max(5,int(bigfs*.06)); maxh=max(h1,h2)
            base=Image.new("RGBA",(w1+w2+gap+80,maxh+80),(0,0,0,0)); d=ImageDraw.Draw(base)
            x=30; y1=35+(maxh-h1); y2=35+(maxh-h2)
            f1,e1,sh1=palette(kind,accent_role); f2,e2,sh2=palette(kind,tail_role)
            d.text((x-bb1[0]+3,y1-bb1[1]+4),accent_txt,font=big,fill=sh1,stroke_width=sb,stroke_fill=e1)
            d.text((x-bb1[0],y1-bb1[1]),accent_txt,font=big,fill=f1,stroke_width=sb,stroke_fill=e1)
            x+=w1+gap
            d.text((x-bb2[0]+2,y2-bb2[1]+3),tail_txt,font=small,fill=sh2,stroke_width=ss,stroke_fill=e2)
            d.text((x-bb2[0],y2-bb2[1]),tail_txt,font=small,fill=f2,stroke_width=ss,stroke_fill=e2)
            alpha=base.getchannel("A"); glow=alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
            gl=Image.new("RGBA",base.size,(250,250,250,0)); gl.putalpha(glow.point(lambda v:min(190,v)))
            gl.alpha_composite(base); base=shear(gl,max(3,int(bigfs*.09)))
            bb=base.getchannel("A").getbbox()
            if not bb: continue
            base=base.crop(bb)
            target_w=int(bw*.94); target_h=int(bh*.90)
            if base.height>target_h:
                nw=max(1,int(round(base.width*target_h/base.height))); base=base.resize((nw,target_h),Image.Resampling.LANCZOS)
            if base.width>target_w:
                nh=max(1,int(round(base.height*target_w/base.width))); base=base.resize((target_w,nh),Image.Resampling.LANCZOS)
            if base.width<target_w:
                base=base.resize((target_w,base.height),Image.Resampling.LANCZOS)
            if base.width<=bw-4 and base.height<=bh-4:
                return base,bigfs,max(sb,ss)
        raise RuntimeError(("cannot fit expert",kind,bw,bh))

    nlines=len(lines)
    maxfs=max(18,int(bh/max(1,nlines)*.78))
    for fs in range(maxfs,13,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        stroke=max(2,min(8,int(round(fs*.06))))
        seggap=max(0,int(round(fs*.02)))
        linegap=max(1,int(round(fs*.10)))
        dims=[line_width(font,line,stroke,seggap) for line in lines]
        cw=max(w for w,h in dims)+stroke*10+30; ch=sum(h for w,h in dims)+linegap*(nlines-1)+stroke*12+30
        base=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(base)
        y=stroke*5+10
        for line,(lw,lh) in zip(lines,dims):
            x=stroke*5+15+(max(w for w,h in dims)-lw)//2
            for txt,role in line:
                fill,edge,shadow=palette(kind,role)
                b=font.getbbox(txt,stroke_width=stroke); tw=b[2]-b[0]
                d.text((x-b[0]+max(2,stroke//2),y-b[1]+max(2,stroke//2)),txt,font=font,fill=shadow,stroke_width=stroke,stroke_fill=edge)
                d.text((x-b[0],y-b[1]),txt,font=font,fill=fill,stroke_width=stroke,stroke_fill=edge)
                x+=tw+seggap
            y+=lh+linegap
        amt=max(2,int(fs*.10)) if kind!="steering" else max(2,int(fs*.08))
        base=shear(base,amt)
        bb=base.getchannel("A").getbbox()
        if not bb: continue
        base=base.crop(bb)
        target_h=max(1,int(bh*.84)); target_w=max(1,int(bw*.90))
        if kind in ("plate_tuned","plate_normal","plate_random"): target_w=int(bw*.84); target_h=int(bh*.78)
        if base.height>target_h:
            nw=max(1,int(round(base.width*target_h/base.height))); base=base.resize((nw,target_h),Image.Resampling.LANCZOS)
        if base.width>bw-6:
            nh=max(1,int(round(base.height*(bw-6)/base.width))); base=base.resize((bw-6,nh),Image.Resampling.LANCZOS)
        if base.width<target_w:
            base=base.resize((target_w,base.height),Image.Resampling.LANCZOS)
        if base.height<=bh-4 and base.width<=bw-4:
            return base,fs,stroke
    raise RuntimeError(("cannot fit",kind,bw,bh))

source_text_mask=Image.new("L",(W,H),0); source_core_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0); clean=src.copy(); rows=[]; cores={}
for idx,spec in SPECS.items():
    r=regions[idx]; x,y,w,h=map(int,r["rect"]); crop=src.crop((x,y,x+w,y+h))
    core,effect,transparent=source_masks(idx,crop,spec["kind"])
    yy,xx=np.where(effect); cy,cx=np.where(core)
    if not len(xx) or not len(cx): raise RuntimeError(("empty mask",idx))
    eb=[x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1]
    cb=[x+int(cx.min()),y+int(cy.min()),x+int(cx.max())+1,y+int(cy.max())+1]
    em=Image.new("L",(W,H),0); em.paste(Image.fromarray((effect*255).astype(np.uint8)),(x,y))
    cm=Image.new("L",(W,H),0); cm.paste(Image.fromarray((core*255).astype(np.uint8)),(x,y))
    source_text_mask=ImageChops.lighter(source_text_mask,em); source_core_mask=ImageChops.lighter(source_core_mask,cm); cores[idx]=cm
    ImageDraw.Draw(allowed).rectangle((eb[0],eb[1],eb[2]-1,eb[3]-1),fill=255)
    clean_crop=clean_plate_crop(crop,effect,core,transparent); clean.paste(clean_crop,(x,y))
    rows.append({"idx":idx,"kind":spec["kind"],"source_effect_bbox":eb,"source_core_bbox":cb,
                 "source_width":eb[2]-eb[0],"source_height":eb[3]-eb[1],
                 "source_effect_pixels":int(effect.sum()),"source_core_pixels":int(core.sum()),
                 "korean_lines":[[t for t,role in line] for line in spec["lines"]]})

sp=out/"560FA536_HD_SOURCE_READABLE.png"; cp=out/"560FA536_HD_CLEAN_PLATE.png"
smp=out/"560FA536_HD_SOURCE_TEXT_MASK.png"; scp=out/"560FA536_HD_SOURCE_CORE_MASK.png"
ap=out/"560FA536_HD_ALLOWED_BBOX_MASK.png"; pp=out/"560FA536_HD_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); source_core_mask.save(scp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed)); protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--report",str(out/"A36_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A36_CLEAN_PLATE_VALIDATION.json").read_text())
clean_diff=dmask(src,clean); clean_outside=count(ImageChops.multiply(clean_diff,ImageOps.invert(source_text_mask)))
clean_same=ImageOps.invert(dmask(src,clean)); clean_core_unchanged=count(ImageChops.multiply(source_core_mask,clean_same))
if cleanrep["status"]!="PASS" or clean_outside!=0 or clean_core_unchanged!=0:
    raise RuntimeError(("clean gate",cleanrep["status"],clean_outside,clean_core_unchanged))

final=clean.copy(); target_masks={}
for row in rows:
    idx=row["idx"]; spec=SPECS[idx]; ob=row["source_effect_bbox"]; bw,bh=ob[2]-ob[0],ob[3]-ob[1]
    layer,fs,stroke=build_layer(spec["lines"],spec["kind"],bw,bh)
    tx=ob[0]+(bw-layer.width)//2; ty=ob[1]+(bh-layer.height)//2
    lm=bmask(layer.getchannel("A")); lb0=lm.getbbox()
    tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty)); lb=list(tm.getbbox() or ())
    contain=len(lb)==4 and lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]
    sizeok=contain and lb[2]-lb[0]<=bw and lb[3]-lb[1]<=bh
    if not contain or not sizeok: raise RuntimeError(("bbox",idx,ob,lb))
    final.paste(layer,(tx,ty),lm); target_masks[idx]=tm
    row.update({"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
                "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
                "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_size":fs,"stroke_px":stroke,"font_pattern":FONT_PATTERN})

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header drift")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip")
dp=out/"560FA536_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)

subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A36_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A36_FINAL_MASK_VALIDATION.json").read_text())
diff=dmask(src,decoded); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=bmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A"))); alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
union=Image.new("L",(W,H),0)
for tm in target_masks.values(): union=ImageChops.lighter(union,tm)
guard=union.filter(ImageFilter.MaxFilter(5)); same=ImageOps.invert(dmask(src,decoded))
residue=count(ImageChops.multiply(source_core_mask,ImageChops.multiply(same,ImageOps.invert(guard))))
overlap=0; touch=0; lbs={r["idx"]:r["localized_bbox"] for r in rows}; keys=sorted(lbs)
for i in range(len(keys)):
  a=lbs[keys[i]]
  for j in range(i+1,len(keys)):
    b=lbs[keys[j]]
    if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]): overlap=1
    if max(a[0]-1,b[0]-1)<min(a[2]+1,b[2]+1) and max(a[1]-1,b[1]-1)<min(a[3]+1,b[3]+1): touch=1
for row in rows:
    row["clean_source_core_unchanged_pixels"]=count(ImageChops.multiply(cores[row["idx"]],clean_same))
    row["candidate_source_core_residue_pixels"]=count(ImageChops.multiply(cores[row["idx"]],ImageChops.multiply(same,ImageOps.invert(guard))))
allbbox=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows)
status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and clean_outside==0 and clean_core_unchanged==0 and outside==0 and alpha_out==0 and protected_changed==0 and residue==0 and overlap==0 and touch==0 and allbbox)

# Controller visual evidence.
thumbs=[flatten(z).resize((1024,1024),Image.Resampling.LANCZOS) for z in (src,clean,decoded)]
sheet=Image.new("RGB",(3072,1024),(90,90,90))
for i,q in enumerate(thumbs): sheet.paste(q,(i*1024,0))
sheet.save(out/"A36_SOURCE_CLEAN_FINAL_QUARTER.jpg",quality=94)

cards=[]
for row in rows:
    ob=row["source_effect_bbox"]; pad=18; box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad))
    ims=[flatten(z.crop(box)) for z in (src,clean,decoded)]; scaled=[]
    for q in ims:
        sc=min(1.0,220/max(1,q.height)); scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+16; ch=max(q.height for q in scaled)+30
    card=Image.new("RGB",(cw,ch),(230,230,230)); d=ImageDraw.Draw(card); d.text((4,4),f"idx {row['idx']} {row['kind']} SOURCE | CLEAN | FINAL",fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,30)); xx+=q.width+8
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards); contacts=Image.new("RGB",(cw,ch),(225,225,225)); yy=0
for c in cards: contacts.paste(c,(0,yy)); yy+=c.height+3
contacts.save(out/"A36_TARGET_CONTACTS.jpg",quality=95)
flatten(decoded_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A36_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"index":101,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA},
 "atlas_provenance":{"git_blob_sha1":ATLAS_BLOB_SHA1,"regions":48},
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":CANDIDATE_SHA,
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "binding":{"semantic_strings":12,"physical_localized_targets":13,"localized_indices":sorted(SPECS),"protected_indices":PROTECTED_INDICES,
            "protected_text_indices":PROTECTED_TEXT,"preserve_original":"song titles, OutRun2 product token, speed values and unrelated artwork"},
 "rows":rows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "machine_checks":{"clean_changed_outside_source_text_mask":clean_outside,"clean_source_core_pixels_unchanged":clean_core_unchanged,
                   "decoded_changed_outside_source_effect_bboxes":outside,"alpha_changed_outside_source_effect_bboxes":alpha_out,
                   "protected_visible_pixels_changed":protected_changed,"source_core_residue_pixels":residue,
                   "localized_overlap_pixels":overlap,"localized_1px_touch_pixels":touch},
 "all_13_bbox_size_positive_margin_pass":allbbox,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A36_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A36_WORKER_REWORK_REQUIRED"}
(out/"A36_560FA536_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":101,"asset":"560FA536","candidate_sha256":CANDIDATE_SHA,"semantic_strings":12,"localized_physical_targets":13,
 "bbox_size_positive_margin":"13/13 PASS" if allbbox else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "changed_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"source_residue":residue,
 "clean_source_core_unchanged":clean_core_unchanged,"overlap":overlap,"touch":touch,"worker_status":report["status"],
 "runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION36/A36_560FA536_REPORT.json"}
(wr/"A36_560FA536.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
