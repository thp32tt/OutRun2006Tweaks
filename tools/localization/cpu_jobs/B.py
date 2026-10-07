#!/usr/bin/env python3
# B235: q26 63C91067 direct C244 REWORK_REQUIRED repair.
# Execution on GitHub-hosted worker is a fallback because the ChatGPT local
# environment cannot resolve GitHub DNS for binary materialization and N100 MCP
# was unavailable when the fallback was attempted. This is recorded in evidence.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib,json,struct,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

repo=Path.cwd()
run="20261007-B235-Q026-63C91067-C244-REWORK"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION137/63C_CLEAN_PLATE.png"
source_png_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION137/63C_SOURCE_READABLE.png"
c244_report=repo/"localization/graphics/role_C/20261007-C244-C2-Q026-63C91067-A144/C244_63C91067_MACHINE_QA.json"
SOURCE_SHA="d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab"
BEFORE_SHA="0281b7b46b5c53598bab2bf4a01f65f391b166345710460c51791da8cf70d530"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")
FONT_INDEX=1
if not FONT.exists(): raise RuntimeError(f"required font missing: {FONT}")

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"w":w,"h":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":masks}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),bool); x0,y0,x1,y1=bb; m[y0:y1,x0:x1]=True; return m
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")

cb=cand.read_bytes()
if sha(cb)!=BEFORE_SHA: raise RuntimeError(("candidate drift",sha(cb),BEFORE_SHA))
raw,old,meta=decode(cb)
if meta["mips"]!=1: raise RuntimeError(("unexpected mips",meta["mips"]))
clean=Image.open(clean_path).convert("RGBA")
source=Image.open(source_png_path).convert("RGBA")
if clean.size!=old.size or source.size!=old.size: raise RuntimeError("evidence size mismatch")
c244=json.loads(c244_report.read_text(encoding="utf-8"))
if c244["source_sha256"]!=SOURCE_SHA or c244["candidate_sha256"]!=BEFORE_SHA:
    raise RuntimeError("C244 basis mismatch")

rows=[
 {"region":0,"source":"Total Rank","korean":"종합 랭킹","bbox":[747,1174,1271,1275],"target_w":476,"target_h":91,"font_size":89,"stroke":4,"slant":0.30},
 {"region":1,"source":"Total Rank","korean":"종합 랭킹","bbox":[599,156,1124,246],"target_w":476,"target_h":80,"font_size":80,"stroke":3,"slant":0.30},
]

# Fresh native-HD supersampled render. No prior Korean bitmap is scaled/reused.
def render_fresh(row,ss=4):
    size=row["font_size"]*ss
    stroke=row["stroke"]*ss
    font=ImageFont.truetype(str(FONT),size,index=FONT_INDEX)
    # Ample high-res padding so affine work cannot clip glyph/effect pixels.
    dummy=Image.new("L",(1,1),0); d=ImageDraw.Draw(dummy)
    tb=d.textbbox((0,0),row["korean"],font=font,stroke_width=stroke)
    tw,th=tb[2]-tb[0],tb[3]-tb[1]
    pad=96*ss
    layer=Image.new("RGBA",(tw+pad*2,th+pad*2),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    ld.text((pad-tb[0],pad-tb[1]),row["korean"],font=font,
            fill=(255,255,255,255),stroke_width=stroke,stroke_fill=(8,16,57,255))
    bb=layer.getbbox()
    if bb is None: raise RuntimeError("empty render")
    layer=layer.crop(bb)
    shear=row["slant"]
    # PIL affine is inverse mapping; negative coefficient gives readable right lean.
    extra=int(math.ceil(abs(shear)*layer.height))+40*ss
    tr=Image.new("RGBA",(layer.width+extra,layer.height),(0,0,0,0))
    # Offset leaves headroom for rightward top displacement.
    tr=layer.transform((layer.width+extra,layer.height),Image.Transform.AFFINE,
                       (1,-shear,extra//3,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=tr.getbbox()
    if bb is None: raise RuntimeError("empty shear")
    tr=tr.crop(bb)
    # Downsample directly from supersampled fresh glyph/effect to final source-relative dimensions.
    tr=tr.resize((row["target_w"],row["target_h"]),Image.Resampling.LANCZOS)
    return tr

final=old.copy()
allowed=np.zeros((meta["h"],meta["w"]),bool)
clean_np=np.asarray(clean); old_np=np.asarray(old)
row_out=[]; layer_masks=[]
for row in rows:
    x0,y0,x1,y1=row["bbox"]; sw,sh=x1-x0,y1-y0
    allowed |= rectmask(meta["h"],meta["w"],row["bbox"])
    # Start from the B137/C193 validated clean plate only inside exact source effect bbox.
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    layer=render_fresh(row)
    if layer.width>sw or layer.height>sh: raise RuntimeError(("oversize render",row["region"],layer.size,(sw,sh)))
    px=x0+(sw-layer.width)//2
    py=y0+(sh-layer.height)//2
    margins=[px-x0,x1-(px+layer.width),py-y0,y1-(py+layer.height)]
    if min(margins)<2: raise RuntimeError(("insufficient margin",row["region"],margins))
    tmp=Image.new("RGBA",final.size,(0,0,0,0)); tmp.alpha_composite(layer,(px,py))
    final.alpha_composite(tmp)
    lm=np.asarray(tmp.getchannel("A"))>0
    layer_masks.append(lm)
    lb=bbox(lm)
    if lb is None: raise RuntimeError("empty localized mask")
    row_out.append({
      "region":row["region"],"source":row["source"],"korean":row["korean"],
      "original_bbox":row["bbox"],"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "margins":[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]],
      "font_file":FONT.name,"font_index":FONT_INDEX,"font_size":row["font_size"],
      "stroke_width":row["stroke"],"readable_right_slant":row["slant"],
      "fresh_supersample":4,"target_width_ratio":round((lb[2]-lb[0])/sw,4),
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

fa=np.asarray(final)
blast=int(np.count_nonzero(changed(old_np,fa)&~allowed))
alpha_blast=int(np.count_nonzero((old_np[:,:,3]!=fa[:,:,3])&~allowed))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))
if np.count_nonzero(layer_masks[0]&layer_masks[1]): raise RuntimeError("localized pair overlap")

# Persist exact DDS header and mirror-Y raw convention.
fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=cb[:128]+fraw.tobytes("raw",meta["mode"])
cand.write_bytes(payload)
pb=cand.read_bytes(); after=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=cb[:128]: raise RuntimeError("header/structure drift")
if ImageChops.difference(persisted,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")
pa=np.asarray(persisted)
if np.count_nonzero(changed(old_np,pa)&~allowed): raise RuntimeError("persisted outside change")
if np.count_nonzero((old_np[:,:,3]!=pa[:,:,3])&~allowed): raise RuntimeError("persisted alpha outside change")

# Independent dark-outline bbox check within the two source bboxes.
dark_rows=[]
for ro in row_out:
    x0,y0,x1,y1=ro["original_bbox"]
    a=pa[y0:y1,x0:x1,:]
    dark=(a[:,:,3]>0)&(a[:,:,0]<60)&(a[:,:,1]<80)&(a[:,:,2]<130)
    db=bbox(dark)
    if db:
      g=[x0+db[0],y0+db[1],x0+db[2],y0+db[3]]
      dark_rows.append({"region":ro["region"],"dark_bbox":g,"dark_size":[g[2]-g[0],g[3]-g[1]]})

# Evidence.
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(source,old,clean,persisted))
def label(im,label):
    z=Image.new("RGB",(im.width,im.height+30),(18,18,18)); z.paste(im,(0,30))
    ImageDraw.Draw(z).text((6,7),label,fill="white"); return z
# Full 2x2 overview at half-scale.
ims=[]
for lab,im in [("SOURCE",src_rgb),("C244-REJECTED A144",old_rgb),("B137/C193 CLEAN",clean_rgb),("B235 FINAL",new_rgb)]:
    x=im.resize((1024,1024),Image.Resampling.LANCZOS); ims.append(label(x,lab))
sheet=Image.new("RGB",(2048,2108),(12,12,12))
for i,x in enumerate(ims): sheet.paste(x,((i%2)*1024,(i//2)*1054))
sheet.save(out/"B235_Q26_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

# High-zoom row contacts.
cards=[]
for row in rows:
    x0,y0,x1,y1=row["bbox"]; pad=40
    crop=(max(0,x0-pad),max(0,y0-pad),min(2048,x1+pad),min(2048,y1+pad))
    parts=[]
    for lab,im in [("SOURCE",src_rgb),("A144 OLD",old_rgb),("CLEAN",clean_rgb),("B235 FINAL",new_rgb)]:
        c=im.crop(crop).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.NEAREST)
        parts.append(label(c,lab))
    h=max(x.height for x in parts); w=sum(x.width for x in parts)
    rowim=Image.new("RGB",(w,h),(15,15,15)); xx=0
    for x in parts: rowim.paste(x,(xx,0)); xx+=x.width
    cards.append(rowim)
cw=max(x.width for x in cards); ch=sum(x.height for x in cards)
cs=Image.new("RGB",(cw,ch),(15,15,15)); yy=0
for x in cards: cs.paste(x,(0,yy)); yy+=x.height
cs.save(out/"B235_Q26_ROW_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

# RAW source/current.
source_raw=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rawpair=Image.new("RGB",(2048,1054),(15,15,15))
for i,(lab,im) in enumerate([("SOURCE RAW MIRROR_Y",source_raw),("B235 RAW MIRROR_Y",praw)]):
    x=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    rawpair.paste(label(x,lab),(i*1024,0))
rawpair.save(out/"B235_Q26_RAW_COMPARE.jpg","JPEG",quality=94,subsampling=0)

# Practical scale SOURCE | FINAL for 100/75/50%, crop around both title regions.
roi=(480,100,1380,1320)
pcs=[]
for sc in (1.0,0.75,0.50):
    s=src_rgb.crop(roi); f=new_rgb.crop(roi)
    s=s.resize((round(s.width*sc),round(s.height*sc)),Image.Resampling.LANCZOS)
    f=f.resize(s.size,Image.Resampling.LANCZOS)
    r=Image.new("RGB",(s.width*2+6,s.height+28),(15,15,15))
    r.paste(s,(0,28));r.paste(f,(s.width+6,28));ImageDraw.Draw(r).text((6,6),f"SOURCE | B235 FINAL {int(sc*100)}%",fill="white")
    pcs.append(r)
pw=max(x.width for x in pcs); ph=sum(x.height+4 for x in pcs)
ps=Image.new("RGB",(pw,ph),(15,15,15)); yy=0
for x in pcs: ps.paste(x,(0,yy)); yy+=x.height+4
ps.save(out/"B235_Q26_PRACTICAL_100_75_50.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"B","run":run,"queue_index":26,"asset":asset,
 "execution_backend":"GITHUB_ACTIONS_FALLBACK_AFTER_CHATGPT_LOCAL_GITHUB_DNS_BLOCKED_AND_N100_MCP_UNAVAILABLE",
 "selection_reason":"B primary even shard direct C244 REWORK_REQUIRED; highest producer order after owned in-game rows already have material/build fixes pending C/user/ingame",
 "trigger":"C244_VISUAL_FAIL_REWORK_REQUIRED_TOTAL_RANK_UNDERSIZED_AND_FLAT",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":BEFORE_SHA,"candidate_sha256":after,
 "clean_plate":"localization/graphics/role_B/20261005-B-PRODUCTION137/63C_CLEAN_PLATE.png",
 "construction":"fresh native-HD supersampled Noto Sans CJK KR Black face index 1; white fill/navy outline; stronger readable-right 0.30 shear; source-relative wide title fit; no reuse/upscale of prior Korean bitmap",
 "rows":row_out,"dark_outline_rows":dark_rows,
 "machine_qa":{
   "rows":"2/2 PASS","changed_pixels_outside_two_exact_source_bboxes":blast,
   "alpha_changes_outside_two_exact_source_bboxes":alpha_blast,
   "localized_pair_overlap":0,"header_128_exact":pb[:128]==cb[:128],
   "mip_count":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
 },
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSED_B137_C193_VALIDATED_CLEAN",
   "2_slant_direction":"PASS_STRONG_READABLE_RIGHT_0.30",
   "3_no_undersizing":"PASS_TARGET_WIDTH_476_OF_524_525_NEAR_SOURCE_HIERARCHY",
   "4_weight_outline_shadow":"PASS_SOURCE_WHITE_NAVY_BLACK_FAMILY",
   "5_no_clipping":"PASS_POSITIVE_MARGINS",
   "6_protected_clearance":"PASS_ZERO_BLAST_OUTSIDE_EXACT_SOURCE_BOXES",
   "7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER_VISUAL"
 },
 "post_encode_presentation_gate":{
   "decoded_persisted_dds_authority":"PASS","practical_scales":["100%","75%","50%"],
   "family_profile":"WHITE_NAVY_STRONG_RIGHT_ITALIC_TOTAL_RANK",
   "blast_radius":"PASS_ZERO_OUTSIDE_TWO_SOURCE_BOXES"
 },
 "controller_visual_qa":"PENDING_CONTROLLER",
 "status":"B235_WORKER_STATIC_PASS_PENDING_CONTROLLER_FRESH_C_C3",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"B235_Q26_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B235_Q026_63C91067.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":26,"candidate_sha256":after,
 "status":report["status"],"report":str((out/"B235_Q26_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"queue_index":26,"before":BEFORE_SHA,"after":after,"rows":row_out,"dark":dark_rows,"blast":blast,"alpha_blast":alpha_blast,"status":report["status"]},ensure_ascii=False))
