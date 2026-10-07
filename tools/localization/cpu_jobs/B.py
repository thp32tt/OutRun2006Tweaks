#!/usr/bin/env python3
# B236: material Total Rank rework batch q32/q34/q36(+q38 exact alias).
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
from scipy import ndimage

repo=Path.cwd()
RUN="20261007-B236-BATCH-Q032-Q034-Q036-TOTAL-RANK"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

FONT_INDEX=1
def locate_font():
    cs=[
      Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
      Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"),
      Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    p=next((x for x in cs if x.exists()),None)
    if p:return p
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    p=next((x for x in cs if x.exists()),None)
    if not p: raise RuntimeError("Noto CJK font unavailable")
    return p
FONT=locate_font()

def sha(b):return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4: raise RuntimeError(("unsupported DDS",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode,"masks":masks}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),bool);x0,y0,x1,y1=bb;m[y0:y1,x0:x1]=True;return m
def changed(a,b):return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255));z.alpha_composite(im);return z.convert("RGB")
def fresh_text(text,target_w,target_h,font_size,stroke,slant=.30,ss=4):
    font=ImageFont.truetype(str(FONT),font_size*ss,index=FONT_INDEX)
    d=ImageDraw.Draw(Image.new("L",(1,1)));tb=d.textbbox((0,0),text,font=font,stroke_width=stroke*ss)
    pad=96*ss
    layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
    ImageDraw.Draw(layer).text((pad-tb[0],pad-tb[1]),text,font=font,fill=(255,255,255,255),
        stroke_width=stroke*ss,stroke_fill=(8,16,57,255))
    layer=layer.crop(layer.getbbox())
    extra=int(math.ceil(abs(slant)*layer.height))+40*ss
    tr=layer.transform((layer.width+extra,layer.height),Image.Transform.AFFINE,
        (1,-slant,extra//3,0,1,0),resample=Image.Resampling.BICUBIC)
    tr=tr.crop(tr.getbbox())
    return tr.resize((target_w,target_h),Image.Resampling.LANCZOS)

def glyph_mask_clean(base, old_bbox):
    # Remove only existing Korean white/navy glyph/effect pixels, never the whole plate bbox.
    a=np.array(base)
    x0,y0,x1,y1=old_bbox
    crop=a[y0:y1,x0:x1]
    rgb=crop[:,:,:3].astype(np.int16); al=crop[:,:,3]
    white=(al>20)&(rgb.min(axis=2)>145)
    navy=(al>20)&(rgb[:,:,0]<75)&(rgb[:,:,1]<90)&(rgb[:,:,2]<145)
    m=white|navy
    m=ndimage.binary_dilation(m,iterations=2)
    if m.sum()<200: raise RuntimeError(("glyph mask too small",m.sum(),old_bbox))
    # nearest intact-pixel reconstruction restricted to glyph-shaped holes
    _,inds=ndimage.distance_transform_edt(m,return_indices=True)
    fixed=crop.copy()
    yy,xx=np.nonzero(m)
    fixed[yy,xx]=crop[inds[0,yy,xx],inds[1,yy,xx]]
    out=base.copy(); out.paste(Image.fromarray(fixed,"RGBA"),(x0,y0))
    return out,int(m.sum())

jobs=[
 {
  "idx":32,"key":"DCC7B488","asset":"textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",
  "before":"9e0b5dcd66b1aaeb031f60090d3c8f919cc59f7c6f8860602bcbc9990eb87867",
  "source_sha":"ecd0607fd021b6aa0c78700bffa05f70546a4d37da6182edc4a35bc41ab5ee4e",
  "source_png":"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_SOURCE_READABLE.png",
  "authoritative_clean":"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_CLEAN_PLATE.png",
  "rows":[{"bbox":[547,164,1065,248],"old_bbox":[658,168,952,243],"size":[468,74],"font":75,"stroke":3}]
 },
 {
  "idx":34,"key":"B7E25BAD","asset":"textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",
  "before":"590f868ac4b99addf1bf41a87de29498584b770e54649809f8398bb699aad467",
  "source_sha":"3d5539326e4c75877457f946622c561aa20557520007dfd5851f7fe9f2056023",
  "source_png":"localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_SOURCE_READABLE.png",
  "authoritative_clean":"localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_CLEAN_PLATE.png",
  "rows":[{"bbox":[2021,1179,2556,1281],"old_bbox":[2140,1192,2437,1268],"size":[486,92],"font":90,"stroke":4}]
 },
 {
  "idx":36,"key":"06AB5CEE","asset":"textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds",
  "alias_asset":"textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds",
  "before":"e3854f79be83cdd5fac7e9af91ab8f2beb9707000a7c6abbc564c2ca443fa553",
  "source_sha":"cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a",
  "source_png":"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_SOURCE_READABLE.png",
  "authoritative_clean":None,
  "rows":[
    {"bbox":[1829,3227,2364,3329],"old_bbox":[1948,3240,2245,3316],"size":[486,92],"font":90,"stroke":4},
    {"bbox":[594,1622,1128,1724],"old_bbox":[712,1635,1009,1711],"size":[486,92],"font":90,"stroke":4},
    {"bbox":[2266,1643,2785,1728],"old_bbox":[2378,1648,2672,1723],"size":[468,75],"font":76,"stroke":3}
  ]
 }
]
summary=[]
for J in jobs:
    p=repo/"localization/graphics/hd_candidates"/J["asset"]
    b=p.read_bytes()
    if sha(b)!=J["before"]:raise RuntimeError(("candidate drift",J["idx"],sha(b),J["before"]))
    raw,old,meta=decode(b)
    if meta["mips"]!=1:raise RuntimeError(("unexpected mip",J["idx"],meta))
    source=Image.open(repo/J["source_png"]).convert("RGBA")
    if source.size!=old.size:raise RuntimeError(("source size mismatch",J["idx"],source.size,old.size))
    if J["authoritative_clean"]:
        clean=Image.open(repo/J["authoritative_clean"]).convert("RGBA")
        if clean.size!=old.size:raise RuntimeError("clean size")
        # Use only the exact source effect bbox from the independently C-approved clean.
        base=old.copy()
        for R in J["rows"]:
            bb=R["bbox"];base.paste(clean.crop(tuple(bb)),(bb[0],bb[1]))
        clean_mode="C_APPROVED_EXACT_BBOX_CLEAN"
        masked=0
    else:
        base=old.copy();masked=0
        # A144 already performed the user-requested plate restoration; remove only its Korean glyph/effect.
        for R in J["rows"]:
            base,n=glyph_mask_clean(base,R["old_bbox"]);masked+=n
        clean_mode="A144_PLATE_PLUS_GLYPH_MASK_LOCAL_NEAREST_RECONSTRUCTION"
    clean=base
    old_np=np.asarray(old); clean_np=np.asarray(clean)
    final=clean.copy()
    allowed=np.zeros((meta["h"],meta["w"]),bool); layers=[]; rows_out=[]
    for n,R in enumerate(J["rows"]):
        x0,y0,x1,y1=R["bbox"];sw,sh=x1-x0,y1-y0;allowed|=rectmask(meta["h"],meta["w"],R["bbox"])
        layer=fresh_text("종합 랭킹",R["size"][0],R["size"][1],R["font"],R["stroke"])
        px=x0+(sw-layer.width)//2;py=y0+(sh-layer.height)//2
        tmp=Image.new("RGBA",final.size,(0,0,0,0));tmp.alpha_composite(layer,(px,py));final.alpha_composite(tmp)
        lm=np.asarray(tmp.getchannel("A"))>0;layers.append(lm);lb=bbox(lm)
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        if min(margins)<2:raise RuntimeError(("margin",J["idx"],n,margins))
        rows_out.append({"region":n,"source":"Total Rank","korean":"종합 랭킹","original_bbox":R["bbox"],
          "localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
          "margins":margins,"width_ratio":round((lb[2]-lb[0])/sw,4),"font_file":FONT.name,
          "font_index":FONT_INDEX,"font_size":R["font"],"stroke_width":R["stroke"],"readable_right_slant":0.30,
          "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    for a in range(len(layers)):
      for c in range(a+1,len(layers)):
        if np.count_nonzero(layers[a]&layers[c]):raise RuntimeError(("overlap",J["idx"],a,c))
    fa=np.asarray(final)
    blast=int(np.count_nonzero(changed(old_np,fa)&~allowed))
    ablast=int(np.count_nonzero((old_np[:,:,3]!=fa[:,:,3])&~allowed))
    if blast or ablast:raise RuntimeError(("blast",J["idx"],blast,ablast))
    fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=b[:128]+fraw.tobytes("raw",meta["mode"])
    p.write_bytes(payload)
    pb=p.read_bytes();after=sha(pb)
    praw,persisted,pmeta=decode(pb)
    if pb[:128]!=b[:128] or pmeta!=meta or ImageChops.difference(persisted,final).getbbox():
        raise RuntimeError(("persist",J["idx"]))
    if J.get("alias_asset"):
        ap=repo/"localization/graphics/hd_candidates"/J["alias_asset"]
        if sha(ap.read_bytes())!=J["before"]:raise RuntimeError(("alias drift",sha(ap.read_bytes())))
        ap.write_bytes(pb)
    # compact but decisive visual evidence
    src_rgb,old_rgb,cl_rgb,fin_rgb=map(comp,(source,old,clean,persisted))
    focus_union=[min(r["bbox"][0] for r in J["rows"]),min(r["bbox"][1] for r in J["rows"]),
                 max(r["bbox"][2] for r in J["rows"]),max(r["bbox"][3] for r in J["rows"])]
    pad=60;crop=(max(0,focus_union[0]-pad),max(0,focus_union[1]-pad),min(meta["w"],focus_union[2]+pad),min(meta["h"],focus_union[3]+pad))
    cards=[]
    for lab,im in [("SOURCE",src_rgb),("A144 OLD",old_rgb),("CLEAN",cl_rgb),("B236 FINAL",fin_rgb)]:
        c=im.crop(crop)
        maxw=900
        if c.width>maxw:c=c.resize((maxw,round(c.height*maxw/c.width)),Image.Resampling.LANCZOS)
        z=Image.new("RGB",(c.width,c.height+30),(18,18,18));z.paste(c,(0,30));ImageDraw.Draw(z).text((6,7),lab,fill="white");cards.append(z)
    sheet=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(15,15,15));xx=0
    for c in cards:sheet.paste(c,(xx,0));xx+=c.width
    sheet.save(out/f"B236_Q{J['idx']:03d}_{J['key']}_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=95,subsampling=0)
    # raw overview, scaled
    sr=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rr=praw
    w=900
    srgb=comp(sr).resize((w,round(sr.height*w/sr.width)),Image.Resampling.LANCZOS)
    frgb=comp(rr).resize(srgb.size,Image.Resampling.LANCZOS)
    rp=Image.new("RGB",(w*2,srgb.height+30),(15,15,15));rp.paste(srgb,(0,30));rp.paste(frgb,(w,30))
    ImageDraw.Draw(rp).text((6,7),"SOURCE RAW | B236 RAW",fill="white")
    rp.save(out/f"B236_Q{J['idx']:03d}_{J['key']}_RAW.jpg","JPEG",quality=93,subsampling=0)
    report={"schema_version":2,"role":"B","run":RUN,"queue_index":J["idx"],"asset":J["asset"],
      "execution_backend":"GITHUB_ACTIONS_FALLBACK_AFTER_CHATGPT_LOCAL_GITHUB_DNS_BLOCKED; N100_AUXILIARY_REVIEW_ONLY",
      "trigger":"USER_PRE_INGAME_TOTAL_RANK_UNDERSIZED_CURRENT_A144_VISUAL_FALSE_NEGATIVE",
      "source_sha256":J["source_sha"],"before_candidate_sha256":J["before"],"candidate_sha256":after,
      "clean_mode":clean_mode,"glyph_mask_pixels_removed":masked,"construction":f"fresh native-HD {FONT.name} KR face index1, white/navy source family, readable-right shear 0.30, ~90% source width",
      "rows":rows_out,"machine_qa":{"rows":f"{len(rows_out)}/{len(rows_out)} PASS","changed_pixels_outside_exact_source_bboxes":blast,
        "alpha_changes_outside_exact_source_bboxes":ablast,"localized_pair_overlap":0,"header_128_exact":True,
        "mip_count":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"},
      "ordered_generation_gate":{"1_plate_restoration":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","2_slant_direction":"PASS_RIGHT_0.30",
        "3_no_undersizing":"PASS_NEAR_90_PERCENT_SOURCE_WIDTH","4_source_faithful_weight_effect":"PASS_WHITE_NAVY",
        "5_no_clipping":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_BLAST_OUTSIDE_SOURCE_BOXES",
        "7_flip_y_raw":"EVIDENCE_WRITTEN","8_immediate_readability":"PENDING_CONTROLLER"},
      "controller_visual_qa":"PENDING_CONTROLLER","status":"B236_WORKER_STATIC_PASS_PENDING_CONTROLLER_FRESH_C_C3",
      "RUNTIME_VALIDATION":"UNTESTED","forbidden_domains_touched":[]}
    (out/f"B236_Q{J['idx']:03d}_{J['key']}_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/f"B236_Q{J['idx']:03d}_{J['key']}.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":J["idx"],"candidate_sha256":after,
      "status":report["status"],"report":str((out/f"B236_Q{J['idx']:03d}_{J['key']}_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if J.get("alias_asset"):
        (wr/"B236_Q038_6AB5CEE.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":38,"alias_of_queue_index":36,
          "candidate_sha256":after,"status":"B236_ALIAS_EXACT_BYTES_PENDING_CONTROLLER_FRESH_C_C3","report":str((out/f"B236_Q{J['idx']:03d}_{J['key']}_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary.append({"index":J["idx"],"after":after,"rows":rows_out,"clean_mode":clean_mode})
print(json.dumps(summary,ensure_ascii=False))
