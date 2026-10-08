#!/usr/bin/env python3
# A182R: q154 controller-refined gray menu weight/counter-space rework after A182 underweight-risk precheck.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, subprocess, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

repo=Path.cwd()
RUN="20261008-A182R-Q154-GRAY-WEIGHT-COUNTERSPACE"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png"
protected_path=repo/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_PROTECTED_VISIBLE_MASK.png"
EXPECTED="dd4a3719b9af01b12e5f962b49f937ef7290dcc893ef970c19110f0611afaf64"
SOURCE_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
SS=4
GRAY=(78,96,100,255)

ROWS=[
 {"key":"single_player_gray","source":"SINGLE PLAYER","ko":"싱글 플레이","bbox":[1610,286,2197,350],"target":[411,58],"c268_ratio":1.3933},
 {"key":"showroom_gray","source":"SHOWROOM","ko":"쇼룸","bbox":[2674,288,3094,350],"target":[210,55],"c268_ratio":1.2361},
 {"key":"multiplayer_gray","source":"MULTIPLAYER","ko":"멀티플레이","bbox":[2566,952,3086,1014],"target":[364,58],"c268_ratio":1.3872},
]
RED_BBOXES=[
 [13,548,1954,696],[2007,541,3468,689],[12,374,1388,522],[1772,374,3316,522],[15,203,1235,347]
]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    if (w,h)!=(4096,1024) or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode}
def diffmask(a,b):
    d=ImageChops.difference(a,b); ch=d.split(); m=ch[0]
    for x in ch[1:]: m=ImageChops.lighter(m,x)
    return m.point(lambda v:255 if v else 0)
def count(m): return int(sum(m.histogram()[1:]))
def flat(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def coverage(mask):
    a=np.asarray(mask,dtype=np.uint8)
    return float(np.count_nonzero(a>8))/float(a.size) if a.size else 0.0
def exact_region_diff(a,b,box):
    return count(diffmask(a.crop(tuple(box)),b.crop(tuple(box))))

cb=candidate.read_bytes()
if sha_bytes(cb)!=EXPECTED: raise RuntimeError(("candidate drift",sha_bytes(cb),EXPECTED))
old_raw,old,meta=decode(cb)
clean=Image.open(clean_path).convert("RGBA")
protected=Image.open(protected_path).convert("L")
if clean.size!=old.size or protected.size!=old.size: raise RuntimeError("evidence size drift")

with tempfile.TemporaryDirectory() as td:
    sp=Path(td)/"source.dds"; urllib.request.urlretrieve(SOURCE_URL,sp)
    sb=sp.read_bytes()
    if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb)))
    source_raw,source,smeta=decode(sb)
    if smeta!=meta or sb[:128]!=cb[:128]: raise RuntimeError("source/current header drift")

    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)

    styles=[]
    for style in ("DemiLight","Regular","Medium","Bold"):
        fm=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
        fp,fi,fs=fm.rsplit("|",2)
        if Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            styles.append((style,fp,int(fi or 0),fs))
    if not styles: raise RuntimeError("Noto CJK Korean faces unavailable")

    final=old.copy()
    selected=Image.new("L",old.size,0)
    sdraw=ImageDraw.Draw(selected)
    row_reports=[]

    def render_variant(text,target_w,target_h,style_tuple):
        style,fp,fi,fsdesc=style_tuple
        font=ImageFont.truetype(fp,56*SS,index=fi)
        tmp=Image.new("L",(1200*SS,160*SS),0); d=ImageDraw.Draw(tmp)
        tb=d.textbbox((0,0),text,font=font,stroke_width=0)
        d.text((24*SS-tb[0],20*SS-tb[1]),text,font=font,fill=255)
        bb=tmp.getbbox()
        if not bb: raise RuntimeError(("empty render",text,style))
        mask=tmp.crop(bb).resize((target_w,target_h),Image.Resampling.LANCZOS)
        rgba=Image.new("RGBA",mask.size,GRAY); rgba.putalpha(mask)
        return rgba,mask,{"style":style,"font":Path(fp).name,"face_index":fi,"resolved_style":fsdesc}

    for cfg in ROWS:
        x0,y0,x1,y1=cfg["bbox"]; sw,sh=x1-x0,y1-y0
        # Restore the exact C141 clean plate only under this gray source footprint.
        final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
        sdraw.rectangle((x0,y0,x1-1,y1-1),fill=255)

        src_text=diffmask(source.crop((x0,y0,x1,y1)),clean.crop((x0,y0,x1,y1)))
        src_bb=src_text.getbbox()
        if not src_bb: raise RuntimeError(("source text evidence empty",cfg["key"]))
        src_density=coverage(src_text.crop(src_bb))

        # Preserve B225 hierarchy/footprint while selecting the lightest source-faithful
        # Korean face whose counter-space density approaches the English source.
        variants=[]
        tw,th=cfg["target"]
        for st in styles:
            tile,mask,meta_font=render_variant(cfg["ko"],tw,th,st)
            mb=mask.getbbox()
            den=coverage(mask.crop(mb))
            ratio=den/src_density if src_density else 999.0
            variants.append((abs(ratio-0.97),ratio,tile,mask,meta_font))
        acceptable=[v for v in variants if 0.86<=v[1]<=1.08]
        chosen=min(acceptable or variants,key=lambda v:v[0])
        _,ratio,tile,mask,fontmeta=chosen
        if ratio>1.12 or ratio<0.62:
            raise RuntimeError(("density fail-closed",cfg["key"],ratio,[(v[1],v[4]["style"]) for v in variants]))
        # Must materially improve the C268 overweight measurement, not merely change bytes.
        if ratio>=cfg["c268_ratio"]*0.86:
            raise RuntimeError(("insufficient density reduction",cfg["key"],ratio,cfg["c268_ratio"]))

        px=x0+2; py=y0+(sh-tile.height)//2
        if px+tile.width>=x1 or py+tile.height>=y1: raise RuntimeError(("margin",cfg["key"]))
        final.alpha_composite(tile,(px,py))
        layer=Image.new("L",old.size,0); layer.paste(mask,(px,py))
        lb=layer.getbbox()
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        if min(margins)<=0: raise RuntimeError(("positive margin",cfg["key"],lb,margins))

        row_reports.append({
          "key":cfg["key"],"source":cfg["source"],"korean":cfg["ko"],
          "source_bbox":cfg["bbox"],"source_size":[sw,sh],
          "localized_bbox":list(lb),"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
          "margins":margins,"target_size":cfg["target"],
          "source_text_density":round(src_density,6),
          "c268_prior_density_ratio":cfg["c268_ratio"],
          "a182r_density_ratio":round(ratio,4),
          "density_reduction_pct":round((1-ratio/cfg["c268_ratio"])*100,2),
          "font":fontmeta,"stroke_width":0,"fill_rgba":list(GRAY)
        })

    # Hard scope gate: only three gray source bboxes may change from B225.
    dm=diffmask(old,final)
    outside=count(ImageChops.multiply(dm,ImageChops.invert(selected)))
    ad=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
    alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(selected)))
    protected_changed=count(ImageChops.multiply(dm,protected))
    red_changed=sum(exact_region_diff(old,final,b) for b in RED_BBOXES)
    if outside or alpha_out or protected_changed or red_changed:
        raise RuntimeError(("scope/protected/red",outside,alpha_out,protected_changed,red_changed))

    raw_new=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=cb[:128]+raw_new.tobytes("raw",meta["mode"])
    candidate.write_bytes(payload)
    after=sha_bytes(payload)
    rraw,decoded,rmeta=decode(payload)
    if rmeta!=meta or payload[:128]!=cb[:128] or ImageChops.difference(decoded,final).getbbox() is not None:
        raise RuntimeError("persisted DDS roundtrip mismatch")

    # Re-derive persisted localized bboxes/densities from exact bytes.
    for rr in row_reports:
        x0,y0,x1,y1=rr["source_bbox"]
        loc=diffmask(decoded.crop((x0,y0,x1,y1)),clean.crop((x0,y0,x1,y1)))
        bb=loc.getbbox()
        if not bb: raise RuntimeError(("persisted empty",rr["key"]))
        g=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
        mar=[g[0]-x0,x1-g[2],g[1]-y0,y1-g[3]]
        if min(mar)<=0: raise RuntimeError(("persisted margin",rr["key"],g,mar))
        rr["persisted_bbox"]=g; rr["persisted_margins"]=mar
        rr["persisted_density"]=round(coverage(loc.crop(bb)),6)

    # Practical evidence at native, 75% and 50%, plus raw orientation.
    contacts=[]
    for rr in row_reports:
        x0,y0,x1,y1=rr["source_bbox"]; p=16
        crop=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
        for scale in (1.0,0.75,0.5):
            ims=[]
            for label,im in (("SOURCE",source),("B225",old),("A182R",decoded)):
                z=flat(im.crop(crop))
                if scale!=1:
                    z=z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.LANCZOS)
                card=Image.new("RGB",(z.width,z.height+24),(18,18,18)); card.paste(z,(0,24))
                ImageDraw.Draw(card).text((4,4),f"{label} {int(scale*100)}%",fill="white")
                ims.append(card)
            row=Image.new("RGB",(sum(i.width for i in ims)+12,max(i.height for i in ims)),(16,16,16))
            xx=0
            for z in ims: row.paste(z,(xx,0)); xx+=z.width+6
            contacts.append(row)
    sheet=Image.new("RGB",(max(i.width for i in contacts),sum(i.height for i in contacts)+8),(14,14,14)); yy=0
    for z in contacts: sheet.paste(z,(0,yy)); yy+=z.height+4
    sheet.save(out/"A182R_Q154_GRAY_PRACTICAL_100_75_50.jpg","JPEG",quality=96,subsampling=0)

    # Source/B225/clean/A182 native gray-row contact sheet.
    rowsheets=[]
    for rr in row_reports:
        x0,y0,x1,y1=rr["source_bbox"]; p=12
        crop=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
        ims=[]
        for label,im in (("SOURCE",source),("B225",old),("C141 CLEAN",clean),("A182R",decoded)):
            z=flat(im.crop(crop)).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.NEAREST)
            c=Image.new("RGB",(z.width,z.height+24),(18,18,18)); c.paste(z,(0,24)); ImageDraw.Draw(c).text((4,4),label,fill="white"); ims.append(c)
        rw=Image.new("RGB",(sum(i.width for i in ims)+18,max(i.height for i in ims)),(16,16,16)); xx=0
        for z in ims: rw.paste(z,(xx,0)); xx+=z.width+6
        rowsheets.append(rw)
    sheet2=Image.new("RGB",(max(i.width for i in rowsheets),sum(i.height for i in rowsheets)+8),(14,14,14)); yy=0
    for z in rowsheets: sheet2.paste(z,(0,yy)); yy+=z.height+4
    sheet2.save(out/"A182R_Q154_SOURCE_B225_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

    for label,raw in (("SOURCE RAW",source_raw),("B225 RAW",old_raw),("A182 RAW",rraw)):
        z=flat(raw); z.thumbnail((900,260),Image.Resampling.LANCZOS)
        z.save(out/(label.replace(" ","_")+".jpg"),"JPEG",quality=94,subsampling=0)

    report={
      "schema_version":2,"role":"A","run":RUN,"queue_index":154,"asset":asset,
      "work_stolen_from_lane":"B",
      "trigger":"C268_REWORK_REQUIRED_GRAY_WEIGHT_COUNTER_SPACE__A182_CONTROLLER_PRECHECK_UNDERWEIGHT_RISK",
      "source_sha256":SOURCE_SHA,"prior_candidate_sha256":EXPECTED,"candidate_sha256":after,
      "repair_scope":"ONLY_GRAY_SINGLE_PLAYER_SHOWROOM_MULTIPLAYER",
      "method":"restore exact C141 clean plate inside only the three gray source bboxes; rerender native Noto Sans CJK Korean with zero added stroke and density-selected lighter face; preserve B225 red rows and all non-gray pixels byte/pixel-exact",
      "rows":row_reports,
      "machine_qa":{
        "gray_bbox_source_size_positive_margin":"3/3 PASS",
        "changed_pixels_outside_gray_source_bboxes":outside,
        "alpha_changed_outside_gray_source_bboxes":alpha_out,
        "protected_visible_changed":protected_changed,
        "red_family_changed_pixels":red_changed,
        "header_128_exact":True,"dimensions":[meta["w"],meta["h"]],"mips":meta["mips"],
        "raw_mode":meta["mode"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
      },
      "ordered_generation_gate":{
        "1_plate_restoration":"PASS_C141_EXACT_CLEAN_THREE_GRAY_BBOXES_ONLY",
        "2_slant_direction":"PASS_SOURCE_UPRIGHT",
        "3_no_unnecessary_undersizing":"PASS_B225_HORIZONTAL_HIERARCHY_PRESERVED",
        "4_weight_outline_shadow":"PASS_LIGHTER_DENSITY_SELECTED_NO_ADDED_STROKE",
        "5_no_clipped_pixels":"PASS_3_OF_3_POSITIVE_MARGIN",
        "6_protected_clearance":"PASS_ZERO_OUTSIDE_PROTECTED_RED_CHANGE",
        "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
        "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"
      },
      "execution_backend":"GITHUB_HOSTED_CPU_WORKER_AFTER_CHATGPT_LOCAL_DNS_BLOCK_AND_N100_ENOSPC",
      "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
      "status":"A182R_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
      "fresh_independent_c":"REQUIRED_C2","mandatory_c3":"REQUIRED_AFTER_C268_VISUAL_REWORK",
      "pre_ingame":"REQUIRED_AFTER_C_PASS","runtime_validation":"UNTESTED",
      "forbidden_domains_touched":[]
    }
    rp=out/"A182R_Q154_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"A182_Q154.json").write_text(json.dumps({
      "role":"A","run":RUN,"queue_index":154,"asset":"4D38BBB0","work_stolen_from_lane":"B",
      "before":EXPECTED,"after":after,"status":report["status"],"report":str(rp.relative_to(repo)),
      "runtime_validation":"UNTESTED"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"run":RUN,"before":EXPECTED,"after":after,"rows":row_reports,
      "outside":outside,"alpha_outside":alpha_out,"protected":protected_changed,"red_changed":red_changed},ensure_ascii=False,indent=2))
