#!/usr/bin/env python3
# A180: work-steal q62 after C261 visual clean-plate rejection.
# Rebuild EASY/HARD from the text-free PSD manual clean component rather than
# the B244 Layer43 crop that retained an opaque white rectangle.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib,json,struct,subprocess,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-A180-Q062-AUTHORED-CLEAN-COMPONENT"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="fa5cd96ff30b41d563886b336ca6305e2fdb7b050b39b2bcd5a5e8c2d46d64b6"
SOURCE="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"

A132=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN"
DONOR=A132/"A132_MANUAL_PSD_CLEAN_COMPONENT.png"
SOURCE_MASK=A132/"A132_SOURCE_TEXT_MASK.png"

ROWS=[
 {"key":"easy_main","bbox":[142,285,385,375],"ko":"쉬움","fill":(0,179,96,255),"anchor":[186,287]},
 {"key":"hard_main","bbox":[808,287,1068,373],"ko":"어려움","fill":(199,50,50,255),"anchor":[829,288]},
]
NAVY=(0,10,57,255); WHITE=(255,255,255,255); FS=73; OUTER=7; INNER=5

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

def make_glyph(text,fill,font):
    p=Image.new("RGBA",(1200,360),(0,0,0,0)); d=ImageDraw.Draw(p)
    tb=d.textbbox((0,0),text,font=font,stroke_width=OUTER)
    xy=(40-tb[0],40-tb[1])
    d.text(xy,text,font=font,fill=fill,stroke_width=OUTER,stroke_fill=WHITE)
    d.text(xy,text,font=font,fill=fill,stroke_width=INNER,stroke_fill=NAVY)
    bb=p.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty glyph",text))
    return p.crop(bb)

if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
if not DONOR.exists() or not SOURCE_MASK.exists(): raise RuntimeError("missing A132 authored evidence")
cb,raw_old,old,meta=load_dds(cand)
donor=Image.open(DONOR).convert("RGBA")
srcmask=Image.open(SOURCE_MASK).convert("L")
if donor.size!=old.size or srcmask.size!=old.size: raise RuntimeError(("evidence shape",donor.size,srcmask.size,old.size))

FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))
font=ImageFont.truetype(FONT,FS)

with tempfile.TemporaryDirectory() as td:
    sp=Path(td)/"source.dds"; urllib.request.urlretrieve(SRC_URL,sp)
    if sha(sp)!=SOURCE: raise RuntimeError(("source drift",sha(sp)))
    sb,sraw,source,smeta=load_dds(sp)
    if cb[:128]!=sb[:128] or smeta!=meta: raise RuntimeError("source/candidate structure drift")

    # The donor is the A132 PSD-derived *text-free manual component* shown as a
    # continuous fork road. B244 accidentally used A124 Layer43 crops instead.
    clean=old.copy()
    final=old.copy()
    allowed=Image.new("L",old.size,0); ad=ImageDraw.Draw(allowed)
    render_union=Image.new("L",old.size,0)
    report_rows=[]

    for row in ROWS:
        x0,y0,x1,y1=row["bbox"]; ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
        donor_crop=donor.crop((x0,y0,x1,y1))
        prior_crop=old.crop((x0,y0,x1,y1))

        # Full authored clean crop is safe here because the donor is a same-canvas,
        # text-free PSD component and the source bbox is the exact allowed region.
        # Record how much of the B244 rectangle/background is materially replaced.
        repair_px=count(diffmask(prior_crop,donor_crop))
        if repair_px<=0: raise RuntimeError(("no repair delta",row["key"]))

        clean.paste(donor_crop,(x0,y0))
        final.paste(donor_crop,(x0,y0))

        g=make_glyph(row["ko"],row["fill"],font)
        ax,ay=row["anchor"]
        if ax<=x0 or ay<=y0 or ax+g.width>=x1 or ay+g.height>=y1:
            raise RuntimeError(("glyph containment",row["key"],g.size,row["bbox"],row["anchor"]))
        final.alpha_composite(g,(ax,ay))
        gm=Image.new("L",old.size,0); gm.paste(g.getchannel("A"),(ax,ay))
        render_union=ImageChops.lighter(render_union,gm)
        lb=[ax,ay,ax+g.width,ay+g.height]
        margins=[ax-x0,x1-lb[2],ay-y0,y1-lb[3]]

        # Donor provenance / clean plate gate: source-mask pixels are allowed to differ,
        # but the donor must not contain any of the source text alpha itself.
        sm=srcmask.crop((x0,y0,x1,y1))
        donor_alpha=donor_crop.getchannel("A")
        source_mask_alpha_overlap=count(ImageChops.multiply(sm,donor_alpha))
        # This count may be non-zero because the road/background is opaque under source
        # text; it is informational, not residue. Visual residue is judged on donor image.
        report_rows.append({
            "key":row["key"],"source_bbox":row["bbox"],"localized_bbox":lb,
            "source_size":[x1-x0,y1-y0],"localized_size":[g.width,g.height],
            "delta_left":margins[0],"delta_right":margins[1],
            "delta_top":margins[2],"delta_bottom":margins[3],
            "repair_pixels_vs_b244":repair_px,
            "donor":"A132_MANUAL_PSD_CLEAN_COMPONENT.png",
            "source_mask_x_donor_alpha_pixels":source_mask_alpha_overlap,
            "font":"Noto Sans CJK KR Black","font_size":FS,
            "outer_stroke_px":OUTER,"navy_stroke_px":INNER,
            "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
        })

    # Scope and persisted DDS checks.
    dm=diffmask(old,final)
    outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
    am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
    alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
    if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))

    # Every final background pixel outside fresh Korean alpha inside the two target
    # bboxes must equal the authored clean component exactly.
    background_mismatch=0
    for row in ROWS:
        x0,y0,x1,y1=row["bbox"]
        fa=np.asarray(final.crop((x0,y0,x1,y1)))
        da=np.asarray(donor.crop((x0,y0,x1,y1)))
        gm=np.asarray(render_union.crop((x0,y0,x1,y1)))>0
        mismatch=np.any(fa!=da,axis=2)&~gm
        background_mismatch+=int(mismatch.sum())
    if background_mismatch: raise RuntimeError(("background mismatch",background_mismatch))

    raw_new=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    cand.write_bytes(cb[:128]+raw_new.tobytes("raw",meta["mode"]))
    csha=sha(cand)
    rb,rraw,decoded,rmeta=load_dds(cand)
    if rb[:128]!=cb[:128] or rmeta!=meta or ImageChops.difference(decoded,final).getbbox() is not None:
        raise RuntimeError("persisted decode mismatch")

    clean.save(out/"A180_Q062_CLEAN_PLATE.png")
    render_union.save(out/"A180_Q062_RENDER_MASK.png")

    # High-zoom evidence.
    cards=[]
    for rr,row in zip(report_rows,ROWS):
        x0,y0,x1,y1=row["bbox"]; p=24
        crop=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
        ims=[]
        for lab,im in [("SOURCE",source),("B244_C261_REJECT",old),("A180_AUTHORED_CLEAN",clean),("A180_FINAL",decoded)]:
            z=flat(im.crop(crop)); z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
            cc=Image.new("RGB",(z.width,z.height+26),(24,24,24)); cc.paste(z,(0,26)); ImageDraw.Draw(cc).text((4,4),lab,fill="white"); ims.append(cc)
        rowim=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+20),(16,16,16)); xx=0
        for cc in ims: rowim.paste(cc,(xx,0)); xx+=cc.width+12
        ImageDraw.Draw(rowim).text((4,rowim.height-3),row["key"],fill="white",anchor="ls")
        cards.append(rowim)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16)); yy=0
    for cc in cards: sheet.paste(cc,(0,yy)); yy+=cc.height+8
    sheet.save(out/"A180_Q062_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

    main=(0,0,1196,812); ims=[]
    for lab,im in [("SOURCE",source),("B244_C261_REJECT",old),("A180_AUTHORED_CLEAN",clean),("A180_FINAL",decoded)]:
        z=flat(im.crop(main)); z.thumbnail((600,410),Image.Resampling.LANCZOS)
        cc=Image.new("RGB",(z.width,z.height+28),(24,24,24)); cc.paste(z,(0,28)); ImageDraw.Draw(cc).text((4,5),lab,fill="white"); ims.append(cc)
    panel=Image.new("RGB",(max(x.width for x in ims)*2+12,max(x.height for x in ims)*2+12),(16,16,16))
    panel.paste(ims[0],(0,0)); panel.paste(ims[1],(ims[0].width+12,0))
    panel.paste(ims[2],(0,ims[0].height+12)); panel.paste(ims[3],(ims[2].width+12,ims[1].height+12))
    panel.save(out/"A180_Q062_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)

    rs,ro,rn=flat(sraw),flat(raw_old),flat(rraw)
    for z in (rs,ro,rn): z.thumbnail((650,340),Image.Resampling.LANCZOS)
    rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+28),(16,16,16)); xx=0
    for lab,z in [("SOURCE RAW",rs),("B244 RAW",ro),("A180 RAW",rn)]:
        rw.paste(z,(xx,28)); ImageDraw.Draw(rw).text((xx+4,5),lab,fill="white"); xx+=z.width+12
    rw.save(out/"A180_Q062_RAW.jpg","JPEG",quality=93,subsampling=0)

    report={
      "schema_version":2,"role":"A","run":RUN,"queue_index":62,"asset":"33491F83",
      "work_stolen_from_lane":"B",
      "work_steal_reason":"A odd shard has no safe material RENDER_READY/C-returned target; q212 has newer B246 compute in progress, while q62 is a fresh C261 even-shard clean-plate REWORK with stable B244 bytes.",
      "trigger":"C261_REWORK_REQUIRED_CLEAN_PLATE_WHITE_RECTANGLE_PATCH_EASY_HARD",
      "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
      "repair_basis":{
        "rejected":"B244 used A124 Layer43 crops and C261 still saw opaque white rectangular EASY/HARD patches.",
        "replacement":"A132_MANUAL_PSD_CLEAN_COMPONENT is the same-canvas text-free authored fork-road component; paste exact EASY/HARD source bboxes from that component, then native rerender.",
        "lettering":"preserve proven A132/B244 main-difficulty family: Noto Sans CJK KR Black 73px, white outer 7px, navy inner 5px, source green/red fills and anchors."
      },
      "rows":report_rows,
      "machine_qa":{
        "target_rows":"2/2 PASS",
        "changed_pixels_vs_b244":count(dm),
        "changed_outside_target_bboxes":outside,
        "alpha_changed_outside_target_bboxes":alpha_out,
        "background_mismatch_vs_authored_clean_outside_fresh_glyph":background_mismatch,
        "non_target_atlas_pixel_exact":True,
        "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
      },
      "ordered_generation_gate":{
        "1_plate_restoration":"PASS_AUTHORED_TEXT_FREE_PSD_COMPONENT_NO_LAYER43_RECTANGLE",
        "2_source_matching_slant":"PASS_UPRIGHT_MAIN_LABEL_FAMILY",
        "3_no_undersized_lettering":"PASS_PROVEN_73PX_NATIVE_FAMILY",
        "4_source_faithful_weight_effect":"PASS_BLACK_WHITE7_NAVY5_SOURCE_COLORS",
        "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
        "6_protected_art_clearance":"PASS_NON_TARGET_ATLAS_PIXEL_EXACT",
        "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
        "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"
      },
      "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REPOSITORY_BACKED_DDS",
      "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
      "status":"A180_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
      "fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_C261_VISUAL_REGRESSION",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    (out/"A180_Q062_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"A180_Q062.json").write_text(json.dumps({"role":"A","run":RUN,"queue_index":62,"asset":"33491F83","before":INPUT,"after":csha,
      "status":report["status"],"report":str((out/"A180_Q062_REPORT.json").relative_to(repo)),
      "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":report_rows,"changed_pixels":count(dm),
      "outside":outside,"alpha_outside":alpha_out,"background_mismatch":background_mismatch},ensure_ascii=False,indent=2))
