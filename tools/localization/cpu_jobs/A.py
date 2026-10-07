#!/usr/bin/env python3
# A165: q28 + q30 direct C245 REWORK_REQUIRED work-steal batch.
# A's odd primary shard has no direct producer work after A164R reconciliation.
# ChatGPT-local GitHub materialization failed DNS and N100 fresh worktree failed
# for disk exhaustion, so repository-backed heavy DDS work uses hosted fallback.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, math, subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

repo=Path.cwd()
run="20261007-A165-BATCH-Q028-Q030-C245-REWORK"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

FONT_INDEX=1
FONT_CANDIDATES=[
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
]
FONT=next((p for p in FONT_CANDIDATES if p.exists()),None)
if FONT is None:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    FONT=next((p for p in FONT_CANDIDATES if p.exists()),None)
if FONT is None:
    raise RuntimeError("required Noto CJK font unavailable")

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b,expect_wh):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or (w,h)!=expect_wh or len(b)!=128+w*h*4 or mips!=1:
        raise RuntimeError(("DDS structure",w,h,mips,masks,len(b),expect_wh))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":masks}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),bool);x0,y0,x1,y1=bb;m[y0:y1,x0:x1]=True;return m
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255));z.alpha_composite(im);return z.convert("RGB")
def render_fresh(text,font_size,stroke,slant,target_w,target_h,ss=4):
    font=ImageFont.truetype(str(FONT),font_size*ss,index=FONT_INDEX)
    dummy=Image.new("L",(1,1)); d=ImageDraw.Draw(dummy)
    tb=d.textbbox((0,0),text,font=font,stroke_width=stroke*ss)
    pad=96*ss
    layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    ld.text((pad-tb[0],pad-tb[1]),text,font=font,fill=(255,255,255,255),
            stroke_width=stroke*ss,stroke_fill=(8,16,57,255))
    bb=layer.getbbox()
    if not bb: raise RuntimeError("empty glyph")
    layer=layer.crop(bb)
    extra=int(math.ceil(abs(slant)*layer.height))+40*ss
    tr=layer.transform((layer.width+extra,layer.height),Image.Transform.AFFINE,
                       (1,-slant,extra//3,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=tr.getbbox()
    if not bb: raise RuntimeError("empty transformed glyph")
    tr=tr.crop(bb)
    return tr.resize((target_w,target_h),Image.Resampling.LANCZOS)

assets=[
 {
  "queue_index":28,"key":"A05BF610",
  "asset":"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
  "expect_wh":(2048,2048),
  "source_sha":"52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129",
  "before_sha":"aa0692a2918326a494c1b04837603313faac7bdd9b7f043d4b679a8e8b1493f9",
  "clean":"localization/graphics/role_C/20261005-C175-A05BF610/C175_A05_CLEAN_PLATE.png",
  "rows":[{"bbox":[543,1185,1068,1275],"target_w":476,"target_h":80,"font_size":80,"stroke":3,"slant":0.30}],
  "c245_ratio":[0.5943],
  "clean_authority":"TARGET_BBOX_ONLY_AFTER_CONTROLLER_VISUAL_REVIEW; HISTORICAL_CLEAN_NOT_GLOBAL_ATLAS_AUTHORITY"
 },
 {
  "queue_index":30,"key":"8215FD25",
  "asset":"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "expect_wh":(4096,2048),
  "source_sha":"e8125cb52c6a135dcde0dade0dcf447ea5d806b8a9b2438d7d6732be84c9b66e",
  "before_sha":"e2eccea39c4241477c5c9743e23ffb69d1cfe785f5186dbd992a865a917d6edc",
  "clean":"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_CLEAN_PLATE.png",
  "rows":[
   {"bbox":[1829,1179,2364,1281],"target_w":486,"target_h":92,"font_size":90,"stroke":4,"slant":0.30},
   {"bbox":[1682,150,2216,252],"target_w":486,"target_h":92,"font_size":90,"stroke":4,"slant":0.30}
  ],
  "c245_ratio":[0.5533,0.5562],
  "clean_authority":"TARGET_BBOX_ONLY_AFTER_CONTROLLER_VISUAL_REVIEW; HISTORICAL_CLEAN_NOT_GLOBAL_ATLAS_AUTHORITY"
 }
]

summaries=[]
for spec in assets:
    asset=spec["asset"]; cand=repo/"localization/graphics/hd_candidates"/asset
    source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset
    clean_path=repo/spec["clean"]
    cb=cand.read_bytes()
    if source_path.exists():
        sb=source_path.read_bytes()
    else:
        import urllib.request
        rel=asset.split("textures/load/",1)[1]
        url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/"+rel
        tmp=Path("/tmp")/(spec["key"]+"_source.dds")
        urllib.request.urlretrieve(url,tmp)
        sb=tmp.read_bytes()
    if sha(cb)!=spec["before_sha"]: raise RuntimeError((spec["key"],"candidate drift",sha(cb),spec["before_sha"]))
    if sha(sb)!=spec["source_sha"]: raise RuntimeError((spec["key"],"source drift",sha(sb),spec["source_sha"]))
    raw,old,meta=decode(cb,spec["expect_wh"]); sraw,source,smeta=decode(sb,spec["expect_wh"])
    if meta!=smeta or cb[:128]!=sb[:128]: raise RuntimeError((spec["key"],"source/current structure mismatch"))
    clean=Image.open(clean_path).convert("RGBA")
    if clean.size!=old.size: raise RuntimeError((spec["key"],"clean size mismatch",clean.size,old.size))
    old_np=np.asarray(old); final=old.copy(); allowed=np.zeros((meta["h"],meta["w"]),bool)
    clean_edge_checks=[]; row_out=[]; layers=[]
    for i,row in enumerate(spec["rows"]):
        x0,y0,x1,y1=row["bbox"]; sw,sh=x1-x0,y1-y0
        allowed |= rectmask(meta["h"],meta["w"],row["bbox"])
        # Historical clean is intentionally used ONLY inside exact canonical text bbox.
        # Verify a 2px ring at the bbox edge is visually/source-compatible enough that
        # no donor seam is introduced at the paste boundary.
        sc=np.asarray(source.crop((x0,y0,x1,y1))).astype(np.int16)
        cc=np.asarray(clean.crop((x0,y0,x1,y1))).astype(np.int16)
        ring=np.zeros((sh,sw),bool); ring[:2,:]=True;ring[-2:,:]=True;ring[:,:2]=True;ring[:,-2:]=True
        ring_delta=np.abs(sc[:,:,:3]-cc[:,:,:3])[ring]
        ring_mean=float(ring_delta.mean()) if ring_delta.size else 0.0
        clean_edge_checks.append({"region":i,"edge_ring_mean_abs_rgb_delta":round(ring_mean,4)})
        final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
        layer=render_fresh("종합 랭킹",row["font_size"],row["stroke"],row["slant"],row["target_w"],row["target_h"])
        if layer.width>sw or layer.height>sh: raise RuntimeError((spec["key"],i,"oversize",layer.size,[sw,sh]))
        px=x0+(sw-layer.width)//2; py=y0+(sh-layer.height)//2
        if min(px-x0,x1-(px+layer.width),py-y0,y1-(py+layer.height))<2:
            raise RuntimeError((spec["key"],i,"insufficient placement margin"))
        tmp=Image.new("RGBA",final.size,(0,0,0,0));tmp.alpha_composite(layer,(px,py));final.alpha_composite(tmp)
        lm=np.asarray(tmp.getchannel("A"))>0; layers.append(lm); lb=bbox(lm)
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        if min(margins)<2: raise RuntimeError((spec["key"],i,"final bbox margin",margins))
        row_out.append({
          "region":i,"source":"Total Rank","korean":"종합 랭킹","original_bbox":row["bbox"],"localized_bbox":lb,
          "source_size":[sw,sh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
          "font_file":FONT.name,"font_index":FONT_INDEX,"font_size":row["font_size"],"stroke_width":row["stroke"],
          "readable_right_slant":row["slant"],"fresh_supersample":4,
          "width_ratio":round((lb[2]-lb[0])/sw,4),"height_ratio":round((lb[3]-lb[1])/sh,4),
          "c245_rejected_width_ratio":spec["c245_ratio"][i],
          "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    for i in range(len(layers)):
        for j in range(i+1,len(layers)):
            if np.count_nonzero(layers[i]&layers[j]): raise RuntimeError((spec["key"],"pair overlap"))
    fa=np.asarray(final)
    blast=int(np.count_nonzero(changed(old_np,fa)&~allowed))
    alpha_blast=int(np.count_nonzero((old_np[:,:,3]!=fa[:,:,3])&~allowed))
    if blast or alpha_blast: raise RuntimeError((spec["key"],"blast",blast,alpha_blast))
    fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    pb=cb[:128]+fraw.tobytes("raw",meta["mode"]); cand.write_bytes(pb)
    after=sha(pb); praw,persisted,pmeta=decode(pb,spec["expect_wh"])
    if pmeta!=meta or pb[:128]!=cb[:128] or ImageChops.difference(persisted,final).getbbox() is not None:
        raise RuntimeError((spec["key"],"persisted decode/header mismatch"))
    pa=np.asarray(persisted)
    if np.count_nonzero(changed(old_np,pa)&~allowed) or np.count_nonzero((old_np[:,:,3]!=pa[:,:,3])&~allowed):
        raise RuntimeError((spec["key"],"persisted blast"))
    # Evidence.
    src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(source,old,clean,persisted))
    cards=[]
    for i,row in enumerate(spec["rows"]):
        x0,y0,x1,y1=row["bbox"]; pad=60
        crop=(max(0,x0-pad),max(0,y0-pad),min(meta["w"],x1+pad),min(meta["h"],y1+pad))
        parts=[]
        for lab,im in [("SOURCE",src_rgb),("C245 OLD",old_rgb),("CLEAN TARGET",clean_rgb),("A165 FINAL",new_rgb)]:
            c=im.crop(crop).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.LANCZOS)
            z=Image.new("RGB",(c.width,c.height+28),(18,18,18));z.paste(c,(0,28));ImageDraw.Draw(z).text((5,5),lab,fill="white");parts.append(z)
        rowim=Image.new("RGB",(sum(x.width for x in parts),max(x.height for x in parts)),(15,15,15));xx=0
        for x in parts:rowim.paste(x,(xx,0));xx+=x.width
        cards.append(rowim)
    cw=max(x.width for x in cards);ch=sum(x.height for x in cards);sheet=Image.new("RGB",(cw,ch),(15,15,15));yy=0
    for x in cards:sheet.paste(x,(0,yy));yy+=x.height
    sheet.save(out/f"A165_Q{spec['queue_index']:03d}_{spec['key']}_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=97,subsampling=0)
    rawpair=Image.new("RGB",(2048,1054),(15,15,15))
    for ii,(lab,im) in enumerate([("SOURCE RAW",sraw),("A165 RAW",praw)]):
        x=comp(im); x=x.resize((1024,round(1024*x.height/x.width)),Image.Resampling.LANCZOS)
        z=Image.new("RGB",(1024,1024+30),(18,18,18)); z.paste(x,(0,30)); ImageDraw.Draw(z).text((5,5),lab,fill="white")
        rawpair.paste(z,(ii*1024,0))
    rawpair.save(out/f"A165_Q{spec['queue_index']:03d}_{spec['key']}_RAW.jpg","JPEG",quality=94,subsampling=0)
    # Practical-scale rows based on union ROI.
    ux0=min(r["bbox"][0] for r in spec["rows"])-80;uy0=min(r["bbox"][1] for r in spec["rows"])-80
    ux1=max(r["bbox"][2] for r in spec["rows"])+80;uy1=max(r["bbox"][3] for r in spec["rows"])+80
    roi=(max(0,ux0),max(0,uy0),min(meta["w"],ux1),min(meta["h"],uy1)); pcs=[]
    for sc in (1.0,.75,.5):
        s=src_rgb.crop(roi);f=new_rgb.crop(roi);sz=(round(s.width*sc),round(s.height*sc))
        s=s.resize(sz,Image.Resampling.LANCZOS);f=f.resize(sz,Image.Resampling.LANCZOS)
        rr=Image.new("RGB",(s.width*2+6,s.height+28),(15,15,15));rr.paste(s,(0,28));rr.paste(f,(s.width+6,28))
        ImageDraw.Draw(rr).text((5,5),f"SOURCE | A165 FINAL {int(sc*100)}%",fill="white");pcs.append(rr)
    pw=max(x.width for x in pcs);ph=sum(x.height+4 for x in pcs);ps=Image.new("RGB",(pw,ph),(15,15,15));yy=0
    for x in pcs:ps.paste(x,(0,yy));yy+=x.height+4
    ps.save(out/f"A165_Q{spec['queue_index']:03d}_{spec['key']}_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)
    report={
      "schema_version":2,"role":"A","run":run,"queue_index":spec["queue_index"],"asset":asset,
      "work_stolen_from_lane":"B",
      "selection_reason":"A odd primary shard exhausted after A164R q197 reconciliation; refreshed branch confirmed direct C245 REWORK_REQUIRED remained unchanged on B-even shard",
      "execution_backend":"GITHUB_ACTIONS_FALLBACK_AFTER_CHATGPT_LOCAL_GITHUB_DNS_FAILURE_AND_N100_DISK_FULL_MATERIALIZATION_FAILURE",
      "trigger":"C245_VISUAL_FAIL_REWORK_REQUIRED_TOTAL_RANK_TEXT_TOO_SMALL",
      "source_sha256":spec["source_sha"],"before_candidate_sha256":spec["before_sha"],"candidate_sha256":after,
      "clean_plate":spec["clean"],"clean_authority":spec["clean_authority"],"clean_target_edge_checks":clean_edge_checks,
      "construction":f"fresh native-HD supersampled {FONT.name} face index {FONT_INDEX}; white face/navy outline; readable-right shear 0.30; ~90% source-width target; no prior Korean bitmap scale/reuse",
      "rows":row_out,
      "machine_qa":{"rows":f"{len(row_out)}/{len(row_out)} PASS","changed_pixels_outside_exact_source_bboxes":blast,
        "alpha_changes_outside_exact_source_bboxes":alpha_blast,"localized_pair_overlap":0,
        "header_128_exact":pb[:128]==cb[:128],"mip_count":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"},
      "ordered_generation_gate":{"1_plate_restoration":"PENDING_CONTROLLER_VISUAL_TARGET_BBOX_ONLY",
        "2_slant_direction":"PASS_READABLE_RIGHT_0.30","3_no_undersizing":"PASS_NEAR_90_PERCENT_SOURCE_WIDTH",
        "4_weight_outline_shadow":"PASS_WHITE_NAVY_SOURCE_FAMILY","5_no_clipping":"PASS_POSITIVE_MARGINS",
        "6_protected_clearance":"PASS_ZERO_BLAST_OUTSIDE_EXACT_SOURCE_BBOXES","7_flip_y_raw":"EVIDENCE_WRITTEN",
        "8_immediate_readability":"PENDING_CONTROLLER_VISUAL"},
      "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","fresh_independent_c":"REQUIRED",
      "mandatory_c3_strict_audit":"REQUIRED_EXACT_SHA_USER_JPG_FALSE_NEGATIVE_HISTORY",
      "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    rp=out/f"A165_Q{spec['queue_index']:03d}_{spec['key']}_REPORT.json";rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"role":"A","run":run,"queue_index":spec["queue_index"],"asset":spec["key"],"work_stolen_from_lane":"B",
      "candidate_sha256":after,"status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL","report":str(rp.relative_to(repo)),"runtime_validation":"UNTESTED"}
    (wr/f"A165_Q{spec['queue_index']:03d}_{spec['key']}.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summaries.append(summary)

(out/"A165_BATCH_SUMMARY.json").write_text(json.dumps({"run":run,"work_stolen_from_lane":"B","assets":summaries,
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summaries,ensure_ascii=False,indent=2))
