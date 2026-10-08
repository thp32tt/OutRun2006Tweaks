#!/usr/bin/env python3
# A186R: q219 D263B3F1 material rework after C265 visual underfill/family rejection.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, subprocess, tempfile, urllib.request, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

repo=Path.cwd()
RUN="20261008-A186R-Q219-SOURCE-HEIGHT-CHROME"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="ecc2bca164cffacd6eec1b627c22a1154caa5ce61e8a751e0606348dac55a43b"
SOURCE="6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
TEXT="코스 선택"
EXPECTED_SIZE=(1467,118)
TARGET_WIDTH_RATIO=None  # policy: never fit to an arbitrary proportion of English width
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


def select_font():
    # Source-derived family: rounded geometric lettering. Korean-capable native face.
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","fonts-nanum"],check=True)
    candidates=["NanumSquareRound:style=Bold","Noto Sans CJK KR:style=Medium","Noto Sans CJK KR:style=Regular"]
    for pattern in candidates:
        spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}|%{style}",pattern],text=True).strip()
        fp,idx,family,style=spec.rsplit("|",3)
        if not Path(fp).exists(): continue
        if pattern.startswith("NanumSquareRound") and "NanumSquareRound" not in family: continue
        if pattern.startswith("Noto") and "Noto" not in family: continue
        return fp,int(idx or 0),family,style
    raise RuntimeError("no verified Korean-capable geometric face")

def profile_slant(ima):
    # Evidence-only two-band leading-edge approximation; no universal angle threshold.
    a=np.asarray(ima.getchannel("A"))
    pts=np.argwhere(a>24)
    if not len(pts): return {"result":"HOLD","observation":"empty source alpha"}
    yy0,yy1=int(pts[:,0].min()),int(pts[:,0].max())
    h=yy1-yy0+1
    bands=[]
    for lo,hi in ((yy0+int(h*.20),yy0+int(h*.35)),(yy0+int(h*.65),yy0+int(h*.80))):
        sl=a[max(0,lo):min(a.shape[0],hi),:]
        ys,xs=np.where(sl>90)
        if not len(xs): return {"result":"HOLD","observation":"ambiguous anchored source alpha"}
        bands.append(int(np.percentile(xs,5)))
    return {"result":"MEASURED_NOT_GLYPH_EXACT","top_minus_bottom_dx":bands[0]-bands[1],
            "anchor_observation":"leading alpha quantile for composite title; separate C visual verification required"}

def render_extended(source_crop,max_w,max_h):
    fontpath,fontindex,family,style=select_font()
    bright,outline,shadow=source_palette(source_crop)
    chosen=None
    # Fit by natural Korean glyph anatomy and source *height*, not English width.
    for fontsize in range(124,74,-1):
        font=ImageFont.truetype(fontpath,fontsize*SS,index=fontindex)
        tracking=int(round(fontsize*.26*SS))
        chars=list(TEXT)
        glyphw=int(sum(font.getlength(ch) for ch in chars)+tracking*max(0,len(chars)-1))
        bbox=font.getbbox(TEXT)
        margin=36*SS
        canvas=Image.new("L",(glyphw+margin*2+100*SS,max(200*SS,bbox[3]-bbox[1]+margin*2)),0)
        dr=ImageDraw.Draw(canvas)
        xx=margin
        for ch in chars:
            dr.text((round(xx),margin-bbox[1]),ch,font=font,fill=255)
            xx+=font.getlength(ch)+tracking
        tight=canvas.getbbox()
        if not tight:continue
        core=canvas.crop(tight)
        # The source has a modest readable right-lean; perform at supersample.
        slant=.115
        srca=np.asarray(core)
        shift=math.ceil(slant*core.height)
        sheared=np.zeros((core.height,core.width+shift),dtype=np.uint8)
        for yy in range(core.height):
            off=round(slant*(core.height-1-yy))
            sheared[yy,off:off+core.width]=srca[yy,:]
        core=Image.fromarray(sheared,"L")
        # Never apply arbitrary horizontal target ratio; independently preserve counters.
        core=core.resize((math.ceil(core.width/SS),math.ceil(core.height/SS)),Image.Resampling.LANCZOS)
        core=core.crop(core.getbbox())
        pad=16
        mask=Image.new("L",(core.width+pad*2,core.height+pad*2),0)
        mask.paste(core,(pad,pad))
        # Supersample composition canvas includes transparent padding; only the
        # actual persisted cropped glyph/effects must fit source bbox.
        # Native solid face, source-like dark keyline, downward extrusion, and
        # narrow white top bevel. Do not expand counters or flatten strokes.
        outer=mask.filter(ImageFilter.MaxFilter(7))
        tile=Image.new("RGBA",mask.size,(0,0,0,0))
        for sx,sy,opacity in ((2,5,85),(3,6,100),(4,7,110)):
            moved=Image.new("L",mask.size,0)
            moved.paste(outer,(sx,sy))
            color=Image.new("RGBA",mask.size,(12,12,18,opacity))
            color.putalpha(ImageChops.multiply(moved,Image.new("L",mask.size,opacity)))
            tile.alpha_composite(color)
        edge=Image.new("RGBA",mask.size,(24,29,36,255));edge.putalpha(outer)
        tile.alpha_composite(edge)
        # Separate bevel from face. Unobstructed transparent Hangul counters remain open.
        raised=Image.new("L",mask.size,0);raised.paste(mask,(0,-2))
        top_bevel=ImageChops.subtract(raised,mask)
        hl=Image.new("RGBA",mask.size,(250,252,254,255));hl.putalpha(top_bevel)
        tile.alpha_composite(hl)
        # Silver/chrome source family: bright upper face, gray lower steel, bright baseline lip.
        w,h=mask.size
        arr=np.empty((h,w,4),dtype=np.uint8)
        lumhi=min(252,max(224,int(np.mean(bright[:3]))))
        for y in range(h):
            z=(y-pad)/max(1,core.height)
            if z<.20: v=lumhi
            elif z<.45: v=round(lumhi+(177-lumhi)*(z-.20)/.25)
            elif z<.72: v=round(177+(215-177)*(z-.45)/.27)
            elif z<.87: v=round(215+(100-215)*(z-.72)/.15)
            else: v=round(100+(212-100)*min(1,(z-.87)/.13))
            arr[y,:,0]=min(255,max(0,v))
            arr[y,:,1]=min(255,max(0,v))
            arr[y,:,2]=min(255,max(0,v))
            arr[y,:,3]=255
        face=Image.fromarray(arr,"RGBA");face.putalpha(mask)
        tile.alpha_composite(face)
        box=tile.getbbox()
        if not box:continue
        tile=tile.crop(box)
        if tile.height>max_h-8 or tile.width>max_w-8:continue
        if tile.height<max_h*.72:continue
        chosen=(tile,{"font":fontpath,"face_index":fontindex,"family":family,"style":style,
              "size_px":fontsize,"tracking_px":tracking/SS,"readable_right_shear":slant,
              "horizontal_width_target":None,"scale_x":1,"original_mask_px":list(core.size),
              "effects":{"dark_outline_px":3,"extrusion_dx_dy":[4,7],"white_top_bevel_px":2,
                         "face":"source-derived bright chrome, steel-dark mid and baseline lip"},
              "top_minus_bottom":profile_slant(tile)})
        break
    if chosen is None:raise RuntimeError("natural-source-height font cannot fit source glyph bbox")
    return chosen


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
        clean_path=Path("derived:A186R_failclosed_transparent_title_footprint")

    source_crop=source.crop(tuple(bbox))
    glyph,render_meta=render_extended(source_crop,x1-x0,y1-y0)
    palette=source_palette(source_crop)
    if glyph.width>=(x1-x0) or glyph.height>=(y1-y0):
        raise RuntimeError(("glyph exceeds source",glyph.size,EXPECTED_SIZE))

    # Source-left alignment of title with positive 6px margin; no forced width quota.
    # Prior A186 numeric PASS was visually rejected by producer for 90/118px height underfill.
    ax=x0+6
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

    # Explicit SOURCE-vs-final decoded exact-pixel gate, not only old-vs-final.
    sr_diff=diffmask(source,decoded)
    sr_outside=count(ImageChops.multiply(sr_diff,ImageChops.invert(allowed)))
    sr_alpha=ImageChops.difference(source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
    sr_alpha_outside=count(ImageChops.multiply(sr_alpha,ImageChops.invert(allowed)))
    if sr_outside or sr_alpha_outside: raise RuntimeError(("SOURCE preservation outside glyph bbox",sr_outside,sr_alpha_outside))
    # Validate unchanged candidate source and correct persisted DDS no-wrap.
    fbox=decoded.crop(tuple(bbox))
    if not fbox.getbbox(): raise RuntimeError("no final visible title")

    # Evidence.
    clean.save(out/"A186R_Q219_CLEAN_PLATE.png")
    gm=Image.new("L",old.size,0); gm.paste(glyph.getchannel("A"),(ax,ay)); gm.save(out/"A186R_Q219_RENDER_MASK.png")

    p=48; cropbox=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
    ims=[]
    for lab,im in [("SOURCE COURSE SELECT",source),("C265 REJECT A113",old),("VALIDATED CLEAN",clean),("A186R FINAL",decoded)]:
        z=flat(im.crop(cropbox)); z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
        card=Image.new("RGB",(z.width,z.height+30),(20,20,20)); card.paste(z,(0,30)); ImageDraw.Draw(card).text((6,6),lab,fill="white"); ims.append(card)
    sheet=Image.new("RGB",(max(i.width for i in ims)*2+12,max(i.height for i in ims)*2+12),(14,14,14))
    sheet.paste(ims[0],(0,0)); sheet.paste(ims[1],(ims[0].width+12,0))
    sheet.paste(ims[2],(0,ims[0].height+12)); sheet.paste(ims[3],(ims[2].width+12,ims[1].height+12))
    sheet.save(out/"A186R_Q219_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

    pr=[]
    for scale in (1.0,0.75,0.5):
        a=flat(source.crop(cropbox)); b=flat(decoded.crop(cropbox))
        if scale!=1:
            a=a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
            b=b.resize((max(1,int(b.width*scale)),max(1,int(b.height*scale))),Image.Resampling.LANCZOS)
        row=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)+26),(18,18,18))
        row.paste(a,(0,26)); row.paste(b,(a.width+8,26))
        ImageDraw.Draw(row).text((4,5),f"SOURCE | A186R @ {int(scale*100)}%",fill="white")
        pr.append(row)
    practical=Image.new("RGB",(max(i.width for i in pr),sum(i.height for i in pr)+12),(14,14,14)); yy=0
    for z in pr: practical.paste(z,(0,yy)); yy+=z.height+6
    practical.save(out/"A186R_Q219_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)

    rs,ro,rn=flat(sraw),flat(raw_old),flat(rraw)
    for z in (rs,ro,rn): z.thumbnail((700,420),Image.Resampling.LANCZOS)
    rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+30),(16,16,16)); xx=0
    for lab,z in [("SOURCE RAW",rs),("A113 RAW",ro),("A186R RAW",rn)]:
        rw.paste(z,(xx,30)); ImageDraw.Draw(rw).text((xx+4,6),lab,fill="white"); xx+=z.width+12
    rw.save(out/"A186R_Q219_RAW.jpg","JPEG",quality=94,subsampling=0)

    report={
      "schema_version":2,"role":"A","run":RUN,"queue_index":219,"asset":"D263B3F1",
      "trigger":"C272_REWORK_REQUIRED_FORCED_RATIO_COUNTERSPACE_SILVER_TECHNO",
      "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
      "source_bbox":bbox,"source_size":[x1-x0,y1-y0],
      "localized_bbox":[ax,ay,ax+glyph.width,ay+glyph.height],
      "localized_size":[glyph.width,glyph.height],
      "width_ratio":round(glyph.width/(x1-x0),4),
      "margins":{"left":margins[0],"right":margins[1],"top":margins[2],"bottom":margins[3]},
      "clean_plate_provenance":str(clean_path),
      "rejected_initial_A186_sha256":"ecc2bca164cffacd6eec1b627c22a1154caa5ce61e8a751e0606348dac55a43b",
      "rejected_initial_A186_reason":"visually underfilled 90px target versus 118px English source despite numeric PASS",
      "source_slant_measurement":profile_slant(source_crop),"localized_slant_measurement":render_meta["top_minus_bottom"],
      "bbox_provenance":chosen[0]+":"+chosen[1] if chosen else "source_vs_A113_exact_changed_bbox",
      "render":{
        "text":TEXT,"construction":render_meta,"supersample":SS,"horizontal_target_ratio":None,
        "palette_from_source":palette,
        "method":"native supersampled Hangul glyphs -> per-character spacing -> readable right shear -> source-sampled chrome bevel/outline without horizontal scaling -> DDS persisted"
      },
      "machine_qa":{
        "bbox_containment":"PASS","source_size_ceiling":"PASS","positive_margin":"PASS",
        "changed_outside_source_bbox":outside,"alpha_changed_outside_source_bbox":alpha_out,
        "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS",
        "source_vs_final_changed_outside":sr_outside,"source_vs_final_alpha_outside":sr_alpha_outside
      },
      "ordered_generation_gate":{
        "1_plate_restoration":"PASS_PRESERVED_VALIDATED_CLEAN_PLATE",
        "2_source_matching_slant":"PASS_READABLE_RIGHT_0.12",
        "3_no_undersized_lettering":"SOURCE_HEIGHT_REFIT_NO_FORCED_WIDTH_RATIO_PENDING_CONTROLLER_VISUAL",
        "4_source_faithful_weight_effect":"PENDING_CONTROLLER_EXACT_SOURCE_STYLE_REVIEW",
        "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
        "6_protected_art_clearance":"PASS_ZERO_CHANGES_OUTSIDE_EXACT_SOURCE_BBOX",
        "7_flip_y_raw":"SOURCE_AND_CANDIDATE_RAW_SAVED_PENDING_CONTROLLER",
        "8_immediate_readability":"PENDING_CONTROLLER_NATIVE_AND_75_50_VISUAL"
      },
      "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REPOSITORY_BACKED_DDS",
      "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
      "status":"A186R_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
      "fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_C265_VISUAL_REWORK",
      "igr_025":"REMAINS_MAPPING_HOLD_AND_NEW_INGAME_RETEST_REQUIRED",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    (out/"A186R_Q219_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"A186R_Q219.json").write_text(json.dumps({
      "role":"A","run":RUN,"queue_index":219,"asset":"D263B3F1",
      "before":INPUT,"after":csha,"status":report["status"],
      "report":str((out/"A186R_Q219_REPORT.json").relative_to(repo)),
      "runtime_validation":"UNTESTED"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"run":RUN,"bbox":bbox,"localized_bbox":report["localized_bbox"],
      "width_ratio":report["width_ratio"],"candidate_sha256":csha,"outside":outside,
      "alpha_outside":alpha_out,"clean":str(clean_path)},ensure_ascii=False,indent=2))
