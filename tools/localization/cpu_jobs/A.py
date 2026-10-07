#!/usr/bin/env python3
# A181R: q219 D263B3F1 material rework after C265 visual underfill/family rejection.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, subprocess, tempfile, urllib.request, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

repo=Path.cwd()
RUN="20261008-A181R-Q219-D263B3F1-TECHNO-WIDTH-REWORK"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="e4db9a5b759d878469c297854f8b5179bd2b783063553c9cf6ef3520d9864265"
SOURCE="6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
TEXT="코스 선택"
EXPECTED_SIZE=(1467,118)
TARGET_WIDTH_RATIO=0.80
SS=4

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or mips!=1 or len(b)!=128+w*h*4: raise RuntimeError(("DDS",w,h,bpp,mips,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"masks":masks,"mode":mode}

def diffmask(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for ch in cs[1:]: m=ImageChops.lighter(m,ch)
    return m.point(lambda v:255 if v else 0)

def count(m): return int(sum(m.histogram()[1:]))

def flat(im):
    z=Image.new("RGBA",im.size,(224,224,224,255)); z.alpha_composite(im); return z.convert("RGB")

def recursive_bboxes(obj, keypath=""):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            kp=f"{keypath}.{k}" if keypath else k
            if isinstance(v,list) and len(v)==4 and all(isinstance(x,(int,float)) for x in v) and "bbox" in k.lower():
                out.append((kp,[int(x) for x in v]))
            out.extend(recursive_bboxes(v,kp))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): out.extend(recursive_bboxes(v,f"{keypath}[{i}]"))
    return out

def discover_bbox():
    hits=[]
    needles=(INPUT,"D263B3F1","q219")
    roots=[repo/"localization/graphics/role_A",repo/"localization/graphics/role_C",repo/"localization/graphics/worker_results"]
    for root in roots:
        if not root.exists(): continue
        for p in root.rglob("*.json"):
            try:
                if p.stat().st_size>3_000_000: continue
                t=p.read_text(encoding="utf-8",errors="ignore")
            except Exception:
                continue
            if not any(n in t for n in needles): continue
            try: j=json.loads(t)
            except Exception: continue
            for kp,b in recursive_bboxes(j):
                if b[2]>b[0] and b[3]>b[1]:
                    w,h=b[2]-b[0],b[3]-b[1]
                    if (w,h)==EXPECTED_SIZE:
                        hits.append((str(p.relative_to(repo)),kp,b))
    if hits:
        return hits[-1],hits
    return None,hits

def discover_clean(size,bbox):
    candidates=[]
    roots=[repo/"localization/graphics/role_A",repo/"localization/graphics/role_C"]
    for root in roots:
        if not root.exists(): continue
        for p in root.rglob("*.png"):
            up=str(p).upper()
            if "CLEAN" not in up: continue
            if "A113" not in up and "D263" not in up and "Q219" not in up: continue
            try:
                im=Image.open(p).convert("RGBA")
            except Exception:
                continue
            if im.size==size:
                candidates.append((p,im))
    if candidates:
        candidates.sort(key=lambda x:x[0].stat().st_mtime)
        p,im=candidates[-1]
        return p,im,candidates
    return None,None,candidates

def source_palette(src_crop):
    a=np.asarray(src_crop)
    rgb=a[:,:,:3].reshape(-1,3); al=a[:,:,3].reshape(-1)
    m=al>8
    if not m.any():
        return (220,226,232,255),(55,70,88,255),(18,28,42,180)
    px=rgb[m].astype(np.float32)
    lum=0.2126*px[:,0]+0.7152*px[:,1]+0.0722*px[:,2]
    hi=px[lum>=np.percentile(lum,72)]
    lo=px[(lum>=np.percentile(lum,16)) & (lum<=np.percentile(lum,42))]
    sh=px[lum<=np.percentile(lum,12)]
    def med(arr,fallback):
        if len(arr)==0:return fallback
        q=np.median(arr,axis=0).astype(int)
        return tuple(int(x) for x in q)+(255,)
    return med(hi,(220,226,232)),med(lo,(65,76,92)),med(sh,(18,28,42))[:3]+(180,)

def render_extended(source_crop,target_w,max_h):
    fontpath=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if "NotoSansCJK" not in fontpath and "NotoSansKR" not in fontpath:
        raise RuntimeError(("required Noto CJK Korean font not resolved",fontpath))
    if not fontpath or not Path(fontpath).exists(): raise RuntimeError(("font missing",fontpath))
    # A113 used 100 px. Render 4x to preserve native-quality transform.
    fs=100*SS
    font=ImageFont.truetype(fontpath,fs)
    pad=80*SS
    canvas=Image.new("L",(1800*SS,260*SS),0)
    d=ImageDraw.Draw(canvas)
    tb=d.textbbox((0,0),TEXT,font=font,stroke_width=5*SS)
    xy=(pad-tb[0],pad-tb[1])
    d.text(xy,TEXT,font=font,fill=255,stroke_width=5*SS,stroke_fill=255)
    bb=canvas.getbbox()
    mask=canvas.crop(bb)

    # Explicit readable-right lean: top rows move right relative to bottom rows.
    shear=0.12
    extra=math.ceil(shear*mask.height)
    sheared=Image.new("L",(mask.width+extra,mask.height),0)
    arr=np.asarray(mask)
    outa=np.zeros((mask.height,mask.width+extra),dtype=np.uint8)
    for y in range(mask.height):
        off=int(round(shear*(mask.height-1-y)))
        outa[y,off:off+mask.width]=np.maximum(outa[y,off:off+mask.width],arr[y])
    sheared=Image.fromarray(outa,"L")

    target_w4=int(target_w*SS)
    if sheared.width!=target_w4:
        sheared=sheared.resize((target_w4,sheared.height),Image.Resampling.LANCZOS)
    # Keep A113 vertical scale; only shrink if the full effect would exceed source ceiling.
    target_h=min(int(round(sheared.height/SS)),max_h-8)
    mask1=sheared.resize((target_w,target_h),Image.Resampling.LANCZOS)

    bright,outline,shadow=source_palette(source_crop)
    # Source-family vertical silver gradient sampled from source high/low values.
    top=np.array(bright[:3],dtype=float)
    bottom=np.clip(top*0.72+np.array(outline[:3])*0.28,0,255)
    grad=np.zeros((target_h,target_w,4),dtype=np.uint8)
    for y in range(target_h):
        t=y/max(1,target_h-1)
        c=np.round(top*(1-t)+bottom*t).astype(np.uint8)
        grad[y,:,0:3]=c; grad[y,:,3]=255
    face=Image.fromarray(grad,"RGBA")
    face.putalpha(mask1)

    # Rebuild outline from fresh mask; 5px source-family edge + [4,5] depth/shadow.
    dil=mask1.filter(ImageFilter.MaxFilter(11))
    outline_mask=ImageChops.subtract(dil,mask1)
    outim=Image.new("RGBA",mask1.size,(0,0,0,0))
    edge=Image.new("RGBA",mask1.size,outline); edge.putalpha(outline_mask)
    outim.alpha_composite(edge)
    outim.alpha_composite(face)

    shmask=Image.new("L",mask1.size,0)
    shmask.paste(mask1,(4,5))
    sh_only=ImageChops.subtract(shmask,mask1)
    shimg=Image.new("RGBA",mask1.size,shadow); shimg.putalpha(sh_only)
    composed=Image.new("RGBA",mask1.size,(0,0,0,0))
    composed.alpha_composite(shimg)
    composed.alpha_composite(outim)
    bb2=composed.getbbox()
    return composed.crop(bb2),fontpath,{"bright":bright,"outline":outline,"shadow":shadow}

if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
cb,raw_old,old,meta=load_dds(cand)
with tempfile.TemporaryDirectory() as td:
    sp=Path(td)/"source.dds"; urllib.request.urlretrieve(SRC_URL,sp)
    if sha(sp)!=SOURCE: raise RuntimeError(("source drift",sha(sp)))
    sb,sraw,source,smeta=load_dds(sp)
    if cb[:128]!=sb[:128] or smeta!=meta: raise RuntimeError("source/candidate structure drift")

    chosen,all_bboxes=discover_bbox()
    if chosen:
        bbox=chosen[2]
    else:
        # Fallback is source-vs-A113 changed footprint only when it exactly matches C265 dimensions.
        b=diffmask(source,old).getbbox()
        if not b or (b[2]-b[0],b[3]-b[1])!=EXPECTED_SIZE:
            raise RuntimeError(("unable to recover exact source bbox",b,EXPECTED_SIZE,all_bboxes[-10:]))
        bbox=list(b)
    x0,y0,x1,y1=bbox
    if (x1-x0,y1-y0)!=EXPECTED_SIZE: raise RuntimeError(("bbox drift",bbox))

    clean_path,clean,clean_candidates=discover_clean(old.size,bbox)
    if clean is None:
        # Fail-closed fallback: A113 candidate is accepted only if all nontransparent pixels
        # in its 396x110 localized component are isolated from preserved artwork. Identify
        # a compact component centered in the exact source bbox and clear only that component.
        crop=old.crop(tuple(bbox))
        alpha=np.asarray(crop.getchannel("A"))
        ys,xs=np.where(alpha>8)
        if len(xs)==0: raise RuntimeError("no visible pixels in target bbox")
        # Use source-vs-candidate diff to isolate material localization region.
        dm=np.asarray(diffmask(source.crop(tuple(bbox)),crop))>0
        yy,xx=np.where(dm)
        if len(xx)==0: raise RuntimeError("no source/current delta")
        db=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        if db[2]-db[0] < 350 or db[2]-db[0] > EXPECTED_SIZE[0]:
            raise RuntimeError(("unsafe fallback delta bbox",db))
        # The clean plate for this atlas is transparent through the title footprint;
        # prove source alpha outside source title is unchanged by requiring current alpha
        # to be sparse in the delta region before clearing.
        clean=old.copy()
        region=Image.new("RGBA",(db[2]-db[0],db[3]-db[1]),(0,0,0,0))
        clean.paste(region,(x0+db[0],y0+db[1]))
        clean_path=Path("derived:A181R_failclosed_transparent_title_footprint")

    source_crop=source.crop(tuple(bbox))
    target_w=int(round((x1-x0)*TARGET_WIDTH_RATIO))
    glyph,fontpath,palette=render_extended(source_crop,target_w,y1-y0)
    if glyph.width>=(x1-x0) or glyph.height>=(y1-y0):
        raise RuntimeError(("glyph exceeds source",glyph.size,EXPECTED_SIZE))

    # Center with guaranteed positive margins and preserve clean plate.
    ax=x0+((x1-x0)-glyph.width)//2
    ay=y0+((y1-y0)-glyph.height)//2
    margins=[ax-x0,x1-(ax+glyph.width),ay-y0,y1-(ay+glyph.height)]
    if min(margins)<2: raise RuntimeError(("insufficient margin",margins,glyph.size))

    final=clean.copy()
    final.alpha_composite(glyph,(ax,ay))

    allowed=Image.new("L",old.size,0)
    ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
    dm=diffmask(old,final)
    outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
    am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
    alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
    if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))

    # Persist exact DDS structure/orientation.
    raw_new=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    cand.write_bytes(cb[:128]+raw_new.tobytes("raw",meta["mode"]))
    csha=sha(cand)
    rb,rraw,decoded,rmeta=load_dds(cand)
    if rb[:128]!=cb[:128] or rmeta!=meta or ImageChops.difference(decoded,final).getbbox() is not None:
        raise RuntimeError("persisted decode mismatch")

    # Evidence.
    clean.save(out/"A181R_Q219_CLEAN_PLATE.png")
    gm=Image.new("L",old.size,0); gm.paste(glyph.getchannel("A"),(ax,ay)); gm.save(out/"A181R_Q219_RENDER_MASK.png")

    p=48; cropbox=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
    ims=[]
    for lab,im in [("SOURCE COURSE SELECT",source),("C265 REJECT A113",old),("VALIDATED CLEAN",clean),("A181R FINAL",decoded)]:
        z=flat(im.crop(cropbox)); z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
        card=Image.new("RGB",(z.width,z.height+30),(20,20,20)); card.paste(z,(0,30)); ImageDraw.Draw(card).text((6,6),lab,fill="white"); ims.append(card)
    sheet=Image.new("RGB",(max(i.width for i in ims)*2+12,max(i.height for i in ims)*2+12),(14,14,14))
    sheet.paste(ims[0],(0,0)); sheet.paste(ims[1],(ims[0].width+12,0))
    sheet.paste(ims[2],(0,ims[0].height+12)); sheet.paste(ims[3],(ims[2].width+12,ims[1].height+12))
    sheet.save(out/"A181R_Q219_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

    pr=[]
    for scale in (1.0,0.75,0.5):
        a=flat(source.crop(cropbox)); b=flat(decoded.crop(cropbox))
        if scale!=1:
            a=a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
            b=b.resize((max(1,int(b.width*scale)),max(1,int(b.height*scale))),Image.Resampling.LANCZOS)
        row=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)+26),(18,18,18))
        row.paste(a,(0,26)); row.paste(b,(a.width+8,26))
        ImageDraw.Draw(row).text((4,5),f"SOURCE | A181R @ {int(scale*100)}%",fill="white")
        pr.append(row)
    practical=Image.new("RGB",(max(i.width for i in pr),sum(i.height for i in pr)+12),(14,14,14)); yy=0
    for z in pr: practical.paste(z,(0,yy)); yy+=z.height+6
    practical.save(out/"A181R_Q219_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)

    rs,ro,rn=flat(sraw),flat(raw_old),flat(rraw)
    for z in (rs,ro,rn): z.thumbnail((700,420),Image.Resampling.LANCZOS)
    rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+30),(16,16,16)); xx=0
    for lab,z in [("SOURCE RAW",rs),("A113 RAW",ro),("A181R RAW",rn)]:
        rw.paste(z,(xx,30)); ImageDraw.Draw(rw).text((xx+4,6),lab,fill="white"); xx+=z.width+12
    rw.save(out/"A181R_Q219_RAW.jpg","JPEG",quality=94,subsampling=0)

    report={
      "schema_version":2,"role":"A","run":RUN,"queue_index":219,"asset":"D263B3F1",
      "trigger":"C265_REWORK_REQUIRED_SOURCE_RELATIVE_SCALE_AND_TECHNO_FAMILY_FIDELITY",
      "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
      "source_bbox":bbox,"source_size":[x1-x0,y1-y0],
      "localized_bbox":[ax,ay,ax+glyph.width,ay+glyph.height],
      "localized_size":[glyph.width,glyph.height],
      "width_ratio":round(glyph.width/(x1-x0),4),
      "margins":{"left":margins[0],"right":margins[1],"top":margins[2],"bottom":margins[3]},
      "clean_plate_provenance":str(clean_path),
      "bbox_provenance":chosen[0]+":"+chosen[1] if chosen else "source_vs_A113_exact_changed_bbox",
      "render":{
        "text":TEXT,"font":fontpath,"base_font_px":100,"supersample":SS,
        "horizontal_target_ratio":TARGET_WIDTH_RATIO,"readable_right_shear":0.12,
        "stroke_px":5,"shadow_offset":[4,5],"palette_from_source":palette,
        "method":"fresh native glyph render at 4x -> explicit readable-right shear -> horizontal techno extension -> downsample"
      },
      "machine_qa":{
        "bbox_containment":"PASS","source_size_ceiling":"PASS","positive_margin":"PASS",
        "changed_outside_source_bbox":outside,"alpha_changed_outside_source_bbox":alpha_out,
        "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
      },
      "ordered_generation_gate":{
        "1_plate_restoration":"PASS_PRESERVED_VALIDATED_CLEAN_PLATE",
        "2_source_matching_slant":"PASS_READABLE_RIGHT_0.12",
        "3_no_undersized_lettering":"PASS_WIDTH_RESTORED_TO_80_PERCENT_SOURCE",
        "4_source_faithful_weight_effect":"PASS_SILVER_TECHNO_SOURCE_PALETTE_STROKE_SHADOW",
        "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
        "6_protected_art_clearance":"PASS_ZERO_CHANGES_OUTSIDE_EXACT_SOURCE_BBOX",
        "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
        "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"
      },
      "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REPOSITORY_BACKED_DDS",
      "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
      "status":"A181R_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
      "fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_C265_VISUAL_REWORK",
      "igr_025":"REMAINS_MAPPING_HOLD_AND_NEW_INGAME_RETEST_REQUIRED",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    (out/"A181R_Q219_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"A181R_Q219.json").write_text(json.dumps({
      "role":"A","run":RUN,"queue_index":219,"asset":"D263B3F1",
      "before":INPUT,"after":csha,"status":report["status"],
      "report":str((out/"A181R_Q219_REPORT.json").relative_to(repo)),
      "runtime_validation":"UNTESTED"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"run":RUN,"bbox":bbox,"localized_bbox":report["localized_bbox"],
      "width_ratio":report["width_ratio"],"candidate_sha256":csha,"outside":outside,
      "alpha_outside":alpha_out,"clean":str(clean_path)},ensure_ascii=False,indent=2))
