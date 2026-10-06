#!/usr/bin/env python3
# B212: manual PRE_INGAME visual QA rework for selector-mode family q102/q104/q116.
# Fixes weak/upright readable slant while preserving exact source bbox ceilings,
# validated transparent clean plates, native-HD DXT5 structure and protected pixels.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261006-B-MANUALQA212-SELECTOR-SLANT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

ASSETS=[
 {
  "index":102,"key":"571E78F3",
  "rel":"textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
  "clean":"localization/graphics/role_C/20261004-1720-C91/C91_571E78F3_CLEAN_PLATE.png",
  "source_sha":"17ee051e59d23c741c9df428dccd3ee2f7863c19a038f02db250001f44b6c121",
  "before_sha":"c4f33f3d98b6d5873d8bb6438d5e649fdaa12c114ed8d34d22a7405d448fc186",
  "prior_c":"C91_PIXEL_VISUAL_PASS_PENDING_INGAME_HIGH_RISK_EDGE_TOUCH",
  "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/030_q102_571E78F3.jpg",
  "rows":[
   {"key":"time_attack_mode","source":"Time Attack Mode","korean":"타임 어택 모드",
    "sprite_cell":[380,8,1340,140],"source_bbox":[395,15,1330,140],"old_bbox":[532,16,1246,140],"lean":0.14},
   {"key":"continuous_15","source":"15 Continuous Course","korean":"15코스 연속",
    "sprite_cell":[500,132,1612,252],"source_bbox":[520,132,1590,245],"old_bbox":[832,132,1277,241],"lean":0.14}
  ]
 },
 {
  "index":104,"key":"62BEBF33",
  "rel":"textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "clean":"localization/graphics/role_C/20261004-1720-C91/C91_62BEBF33_CLEAN_PLATE.png",
  "source_sha":"f0a8491585dd4f225c4707b63bd61ae43869cb9d243d9de881258add023c06e2",
  "before_sha":"687ecaad8db7478f4964b11d082f86b21091507bef564cfde3adfb4a1a625e7d",
  "prior_c":"C91_PIXEL_VISUAL_PASS_PENDING_INGAME",
  "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/031_q104_62BEBF33.jpg",
  "rows":[
   {"key":"outrun_mode","source":"OutRun Mode","korean":"아웃런 모드",
    "sprite_cell":[380,44,1372,208],"source_bbox":[392,52,1357,201],"old_bbox":[576,56,1172,197],"lean":0.16}
  ]
 },
 {
  "index":116,"key":"E3FD08BE",
  "rel":"textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "clean":"localization/graphics/role_C/20261004-1720-C91/C91_E3FD08BE_CLEAN_PLATE.png",
  "source_sha":"ebc2d866597955c6e802de65eff2d07e048f66b4ae2770fffd86b81b61fd5845",
  "before_sha":"3fbf7b03834549de10277947043ca8dd15d05fd729cd8441174b74581b532c9f",
  "prior_c":"C91_PIXEL_VISUAL_PASS_PENDING_INGAME",
  "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/035_q116_E3FD08BE.jpg",
  "rows":[
   {"key":"heart_attack_mode","source":"Heart Attack Mode","korean":"하트 어택 모드",
    "sprite_cell":[380,44,1640,208],"source_bbox":[393,54,1628,200],"old_bbox":[648,56,1372,196],"lean":0.16}
  ]
 }
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dds_meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    if fourcc!=b"DXT5": raise RuntimeError(("expected DXT5",str(p),fourcc))
    need=128+((w+3)//4)*((h+3)//4)*16
    if mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DXT5 layout",str(p),w,h,mips,len(b),need))
    return b,{"width":w,"height":h,"mips":mips,"fourcc":"DXT5","bytes":len(b)}

def decode_readable(p):
    return Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def bool_bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def rect_bool(size,boxes):
    W,H=size
    m=np.zeros((H,W),dtype=bool)
    for x0,y0,x1,y1 in boxes: m[y0:y1,x0:x1]=True
    return m

def visible_diff_counts(a,b,allowed):
    aa=np.asarray(a,dtype=np.uint8); bb=np.asarray(b,dtype=np.uint8)
    diff=np.any(aa!=bb,axis=2)
    visible=(aa[:,:,3]>0)|(bb[:,:,3]>0)
    return {
      "changed":int(diff.sum()),
      "visible_outside":int(np.logical_and(np.logical_and(diff,visible),~allowed).sum()),
      "alpha_outside":int(np.logical_and(aa[:,:,3]!=bb[:,:,3],~allowed).sum()),
      "bbox":bool_bbox(diff)
    }

def right_lean(tile,amount):
    # Readable-orientation transform: top rows move right relative to bottom rows.
    # Integer row translation avoids affine resampling/crop damage; DXT5 recompression happens only once after placement.
    shift=max(1,int(np.ceil(amount*max(1,tile.height-1))))
    pad=shift+8
    src=Image.new("RGBA",(tile.width+2*pad,tile.height),(0,0,0,0))
    src.alpha_composite(tile,(pad,0))
    dst=Image.new("RGBA",src.size,(0,0,0,0))
    for y in range(src.height):
        dx=int(round(amount*(src.height-1-y)))
        row=src.crop((0,y,src.width,y+1))
        dst.alpha_composite(row,(dx,y))
    bb=dst.getchannel("A").getbbox()
    if not bb: raise RuntimeError("empty leaned glyph")
    return dst.crop(bb)

def flatten(im,bg=(104,104,104,255)):
    c=Image.new("RGBA",im.size,bg); c.alpha_composite(im)
    return c.convert("RGB")

def save_contact(spec,source,before,final,raw=False):
    s=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else source
    o=before.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else before
    n=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else final
    cards=[]
    for row in spec["rows"]:
        bbox=list(row["source_bbox"])
        if raw:
            x0,y0,x1,y1=bbox
            bbox=[x0,source.height-y1,x1,source.height-y0]
        x0,y0,x1,y1=bbox
        pad=24
        crop=(max(0,x0-pad),max(0,y0-pad),min(source.width,x1+pad),min(source.height,y1+pad))
        ims=[]
        for im in (s,o,n):
            v=flatten(im.crop(crop))
            v=v.resize((v.width*2,v.height*2),Image.Resampling.NEAREST)
            ims.append(v)
        W=sum(i.width for i in ims)+12; H=max(i.height for i in ims)+34
        card=Image.new("RGB",(W,H),(28,28,28)); d=ImageDraw.Draw(card); x=0
        for lab,im in zip(("SOURCE","OLD","B212"),ims):
            d.text((x+4,5),lab,fill="white")
            card.paste(im,(x,32)); x+=im.width+6
        cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+6*(len(cards)-1)
    sheet=Image.new("RGB",(W,H),(20,20,20)); y=0
    for c in cards:
        sheet.paste(c,(0,y)); y+=c.height+6
    suffix="RAW" if raw else "READABLE"
    sheet.save(out/f'B212_{spec["key"]}_SOURCE_OLD_NEW_{suffix}.jpg',"JPEG",quality=95,subsampling=0)

if not Path("/usr/bin/nvcompress").exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","libnvtt-bin"],check=True)
nvcompress=Path("/usr/bin/nvcompress")
if not nvcompress.exists(): raise RuntimeError("nvcompress unavailable")

results=[]
for spec in ASSETS:
    source_path=repo/spec["source"]
    cand_path=repo/"localization/graphics/hd_candidates"/spec["rel"]
    clean_path=repo/spec["clean"]
    if sha(source_path)!=spec["source_sha"]: raise RuntimeError((spec["key"],"source SHA drift",sha(source_path)))
    if sha(cand_path)!=spec["before_sha"]: raise RuntimeError((spec["key"],"candidate SHA drift",sha(cand_path)))
    sb,smeta=dds_meta(source_path); cb,cmeta=dds_meta(cand_path)
    if sb[:128]!=cb[:128] or smeta!=cmeta: raise RuntimeError((spec["key"],"header/structure drift"))
    source=decode_readable(source_path)
    before=decode_readable(cand_path)
    clean=Image.open(clean_path).convert("RGBA")
    if source.size!=before.size or source.size!=clean.size: raise RuntimeError((spec["key"],"dimension mismatch"))
    W,H=source.size
    allowed=rect_bool(source.size,[r["source_bbox"] for r in spec["rows"]])

    # Reconstruct from the C91-validated clean plate first, then relayer the native-HD Korean raster.
    final=before.copy()
    row_reports=[]
    for row in spec["rows"]:
        cell=tuple(row["sprite_cell"])
        final.paste(clean.crop(cell),(cell[0],cell[1]))
        old_bbox=tuple(row["old_bbox"])
        crop=before.crop(old_bbox)
        ab=crop.getchannel("A").getbbox()
        if not ab: raise RuntimeError((spec["key"],row["key"],"empty old glyph"))
        crop=crop.crop(ab)
        leaned=right_lean(crop,float(row["lean"]))
        sbx=row["source_bbox"]; sw=sbx[2]-sbx[0]; sh=sbx[3]-sbx[1]
        if leaned.width>sw or leaned.height>sh:
            fit=min(sw/leaned.width,sh/leaned.height)
            if fit>=1: raise RuntimeError("unexpected fit state")
            leaned=leaned.resize((max(1,int(leaned.width*fit)),max(1,int(leaned.height*fit))),Image.Resampling.LANCZOS)
            bb=leaned.getchannel("A").getbbox()
            if bb: leaned=leaned.crop(bb)
        px=sbx[0]+(sw-leaned.width)//2
        py=sbx[1]+(sh-leaned.height)//2
        if px<sbx[0] or py<sbx[1] or px+leaned.width>sbx[2] or py+leaned.height>sbx[3]:
            raise RuntimeError((spec["key"],row["key"],"lean fit escape",leaned.size,sbx))
        layer=Image.new("RGBA",final.size,(0,0,0,0)); layer.alpha_composite(leaned,(px,py)); final.alpha_composite(layer)
        row_reports.append({
          "key":row["key"],"source":row["source"],"korean":row["korean"],
          "source_bbox":row["source_bbox"],"prior_localized_bbox":row["old_bbox"],
          "precompress_localized_bbox":[px,py,px+leaned.width,py+leaned.height],
          "readable_added_right_lean":row["lean"],
          "source_size":[sw,sh],"precompress_size":[leaned.width,leaned.height]
        })

    # Recompress only once, then copy back only BC3 blocks intersecting original source bboxes.
    raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    tmp_png=Path("/tmp")/f'B212_{spec["key"]}_raw.png'
    tmp_dds=Path("/tmp")/f'B212_{spec["key"]}_nv.dds'
    raw_final.save(tmp_png)
    subprocess.run([str(nvcompress),"-bc3","-nomips",str(tmp_png),str(tmp_dds)],
                   check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    tb,tmeta=dds_meta(tmp_dds)
    if tmeta["width"]!=W or tmeta["height"]!=H: raise RuntimeError((spec["key"],"nvcompress size drift"))
    arr_target=np.asarray(raw_final,dtype=np.int16)
    arr_dec=np.asarray(Image.open(tmp_dds).convert("RGBA"),dtype=np.int16)
    mae=float(np.mean(np.abs(arr_target-arr_dec)))
    mae_flip=float(np.mean(np.abs(arr_target-np.flipud(arr_dec))))
    if mae_flip+0.5<mae: raise RuntimeError((spec["key"],"nvcompress orientation inversion",mae,mae_flip))

    out_bytes=bytearray(cb); bw=(W+3)//4; bh=(H+3)//4
    patch_blocks=set()
    for row in spec["rows"]:
        x0,y0,x1,y1=row["source_bbox"]
        # readable y -> raw mirror-y block coordinates
        ry0=H-y1; ry1=H-y0
        bx0=max(0,x0//4); bx1=min(bw,(x1+3)//4)
        by0=max(0,ry0//4); by1=min(bh,(ry1+3)//4)
        for by in range(by0,by1):
            for bx in range(bx0,bx1): patch_blocks.add((bx,by))
    for bx,by in patch_blocks:
        off=128+(by*bw+bx)*16
        out_bytes[off:off+16]=tb[off:off+16]
    cand_path.write_bytes(out_bytes)
    after_sha=sha(cand_path)

    fb,fmeta=dds_meta(cand_path)
    if fb[:128]!=sb[:128] or fmeta!=smeta: raise RuntimeError((spec["key"],"final header/structure drift"))
    decoded=decode_readable(cand_path)
    gates=visible_diff_counts(source,decoded,allowed)
    if gates["visible_outside"] or gates["alpha_outside"]:
        raise RuntimeError((spec["key"],"outside source bbox",gates))

    changed_blocks=0; outside_patch=0
    for by in range(bh):
        for bx in range(bw):
            off=128+(by*bw+bx)*16
            if cb[off:off+16]!=fb[off:off+16]:
                changed_blocks+=1
                if (bx,by) not in patch_blocks: outside_patch+=1
    if outside_patch: raise RuntimeError((spec["key"],"compressed collateral",outside_patch))

    # Post-BC3 row containment/size checks from each isolated sprite cell.
    alpha=np.asarray(decoded.getchannel("A"))>0
    for row,rr in zip(spec["rows"],row_reports):
        cx0,cy0,cx1,cy1=row["sprite_cell"]
        local=np.zeros_like(alpha); local[cy0:cy1,cx0:cx1]=alpha[cy0:cy1,cx0:cx1]
        lb=bool_bbox(local)
        if not lb: raise RuntimeError((spec["key"],row["key"],"empty postcompress"))
        ob=row["source_bbox"]; lw=lb[2]-lb[0]; lh=lb[3]-lb[1]; sw=ob[2]-ob[0]; sh=ob[3]-ob[1]
        contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
        sizeok=lw<=sw and lh<=sh
        if not (contain and sizeok): raise RuntimeError((spec["key"],row["key"],"bbox fail",ob,lb))
        rr.update({
          "localized_bbox":lb,"localized_size":[lw,lh],
          "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
          "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
          "containment":"PASS","size_ceiling":"PASS",
          "edge_touch_high_risk":any(v==0 for v in [lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]])
        })

    save_contact(spec,source,before,decoded,False)
    save_contact(spec,source,before,decoded,True)

    report={
      "schema_version":1,"role":"B","run":"B212","queue_index":spec["index"],"asset":spec["rel"],
      "trigger":"B_MANUAL_PRE_INGAME_CONTROLLER_REVIEW_SELECTOR_FAMILY",
      "review_jpg":spec["review_jpg"],"prior_c_status":spec["prior_c"],
      "defects":["WRONG_OR_WEAK_SLANT_DIRECTION","SOURCE_TRANSFORM_FIDELITY_MISMATCH"],
      "source_sha256":spec["source_sha"],"before_sha256":spec["before_sha"],"candidate_sha256":after_sha,
      "method":"exact native-HD DXT5 + inherited C91 validated clean plate -> isolate current native-HD Korean raster -> integer scanline readable right-lean correction -> relayer inside exact source bbox -> BC3 scratch recompress -> patch only source-bbox-intersecting blocks -> decoded strict QA",
      "rows":row_reports,
      "qa":{
        "visible_changed_pixels_outside_source_bboxes":gates["visible_outside"],
        "alpha_changed_pixels_outside_source_bboxes":gates["alpha_outside"],
        "header_128_exact_canonical":True,
        "changed_blocks_outside_patch_set":outside_patch,
        "changed_blocks_vs_prior_candidate":changed_blocks,
        "nvcompress_mae_raw_rgba":mae,
        "nvcompress_mae_if_flipped":mae_flip,
        "readable_source_old_new_visual_review":"PENDING_CONTROLLER",
        "raw_source_old_new_visual_review":"PENDING_CONTROLLER",
        "ordered_gate":{
          "plate_restoration":"PASS_INHERITED_C91_VALIDATED_CLEAN_PLATE",
          "source_matching_slant_direction":"REWORKED_PENDING_CONTROLLER_VISUAL",
          "no_unnecessary_undersizing":"UNCHANGED_NATIVE_HEIGHT_WITHIN_SOURCE_BBOX_CEILING",
          "weight_outline_shadow":"PRESERVED_FROM_PRIOR_NATIVE_HD_KOREAN_EFFECT_RASTER",
          "clipping":"PASS_MACHINE_CONTAINMENT",
          "protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX",
          "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
          "immediate_readability":"PENDING_CONTROLLER"
        }
      },
      "runtime_validation":"UNTESTED",
      "status":"B212_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
      "no_vr_ffb_dx11_dxvk_work":True
    }
    rp=out/f'B212_{spec["key"]}_REPORT.json'
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/f'B212_{spec["key"]}.json').write_text(json.dumps({
      "role":"B","run":"B212","queue_index":spec["index"],"asset":spec["rel"],
      "candidate_sha256":after_sha,"report":str(rp.relative_to(repo)),
      "status":report["status"],"runtime_validation":"UNTESTED"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    results.append({"index":spec["index"],"key":spec["key"],"before":spec["before_sha"],"after":after_sha,"rows":row_reports})

summary={
  "schema_version":1,"role":"B","run":"B212",
  "scope":"manual PRE_INGAME English-original comparison review; selector mode family q102/q104/q116 weak readable slant correction",
  "assets":results,
  "runtime_validation":"UNTESTED",
  "status":"B212_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
  "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B212_SELECTOR_FAMILY_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
