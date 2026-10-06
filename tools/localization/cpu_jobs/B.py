#!/usr/bin/env python3
import hashlib, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION196-75C3586A-NAMES"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
cand.parent.mkdir(parents=True,exist_ok=True)

url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
expected="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
srcp=Path("/tmp/B196_75C3586A.dds")
urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
got=hashlib.sha256(raw).hexdigest()
if got!=expected: raise RuntimeError(("source sha drift",got,expected))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")

raw_im=Image.open(srcp).convert("RGBA")
src=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
H,W=sa.shape[:2]
if (W,H)!=(2048,2048): raise RuntimeError(("dimensions",W,H))

# B74's atlas metadata was correct; its controller conclusion was not.
# These four readable-orientation cells visibly contain the transcribed red labels.
specs=[
 {"key":"clarissa","source":"CLARISSA","ko":"클라리사","roi":[0,1676,580,1844]},
 {"key":"jennifer","source":"JENNIFER","ko":"제니퍼","roi":[580,1676,1040,1844]},
 {"key":"flagman4","source":"FLAGMAN 4","ko":"플래그맨 4","roi":[0,1844,1036,2008]},
 {"key":"holly","source":"HOLLY","ko":"홀리","roi":[1036,1844,1312,1956]},
]

def bbox(mask):
    yy,xx=np.nonzero(mask)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

source_masks=[]
rows=[]
clean_arr=sa.copy()
for sp in specs:
    x0,y0,x1,y1=sp["roi"]
    sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]>8
    # Red source lettering on a neutral gray strip. Include dark-red AA fringe,
    # while excluding neutral background and non-text cells outside these atlas ROIs.
    red=a & (r>65) & (r>g+28) & (r>b+28) & ((r-g)>35)
    # Retain meaningful connected-ish text by requiring horizontal/vertical neighborhood support.
    from scipy import ndimage
    red=ndimage.binary_closing(red,iterations=1)
    red=ndimage.binary_dilation(red,iterations=1) & a
    lab,n=ndimage.label(red)
    kept=np.zeros_like(red)
    comps=[]
    for i in range(1,n+1):
        cm=lab==i; ar=int(cm.sum())
        if ar<12: continue
        bb=bbox(cm)
        comps.append((ar,bb))
        kept|=cm
    if int(kept.sum())<120:
        raise RuntimeError(("source text mask too small",sp["key"],int(kept.sum()),comps))
    gm=np.zeros((H,W),bool); gm[y0:y1,x0:x1]=kept
    sb=bbox(gm)
    if sb is None: raise RuntimeError(("empty source bbox",sp["key"]))
    # The exact red/effect footprint must stay well inside its atlas cell.
    if sb[0]<x0 or sb[1]<y0 or sb[2]>x1 or sb[3]>y1:
        raise RuntimeError(("source bbox outside roi",sp["key"],sb,sp["roi"]))
    sw=sb[2]-sb[0]; sh=sb[3]-sb[1]
    if sw<40 or sh<25:
        raise RuntimeError(("implausible source bbox",sp["key"],sb))
    # Flat/near-flat neutral plate reconstruction: sample non-red neutral pixels
    # from the same ROI, favoring pixels adjacent to the text bbox.
    neutral=(~kept) & a
    nr=sub[:,:,0].astype(np.int16); ng=sub[:,:,1].astype(np.int16); nb=sub[:,:,2].astype(np.int16)
    neutral &= (np.maximum.reduce([nr,ng,nb])-np.minimum.reduce([nr,ng,nb])<28)
    q=sub[neutral]
    if len(q)<50:
        q=sub[(~kept)&a]
    if len(q)<50: raise RuntimeError(("no clean plate donors",sp["key"],len(q)))
    bg=np.median(q,axis=0).astype(np.uint8)
    # Rebuild only the actual source glyph/effect footprint.
    yy,xx=np.nonzero(gm)
    clean_arr[yy,xx]=bg
    source_masks.append(gm)
    rows.append({**sp,"source_bbox":sb,"source_text_pixels":int(gm.sum()),"background_rgba":[int(v) for v in bg],"components":comps})

source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
clean=Image.fromarray(clean_arr,"RGBA")
same_clean=np.all(clean_arr==sa,axis=2)
clean_residue=int(np.count_nonzero(source_mask & same_clean))
if clean_residue: raise RuntimeError(("clean source residue",clean_residue))

# Install a native CJK font on the hosted runner.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

final=clean.copy()
target=np.zeros((H,W),bool)
render_masks=[]
for row,sm in zip(rows,source_masks):
    sb=row["source_bbox"]; x0,y0,x1,y1=sb; sw=x1-x0; sh=y1-y0
    # Source fill median from the measured red mask, preserving the original red family.
    srcpix=sa[sm]
    fill=np.median(srcpix,axis=0).astype(np.uint8)
    fill=(int(fill[0]),int(fill[1]),int(fill[2]),int(fill[3]))
    chosen=None
    # Preserve upright/blocky family and source-left alignment with positive margins.
    for fs in range(max(8,sh),7,-1):
        font=ImageFont.truetype(FONT,fs)
        tmp=Image.new("RGBA",(sw,sh),(0,0,0,0))
        d=ImageDraw.Draw(tmp)
        # Measure exact glyph bbox at origin, then normalize to top-left.
        bb=d.textbbox((0,0),row["ko"],font=font,stroke_width=0)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        if tw>sw-4 or th>sh-4: continue
        px=2-bb[0]
        py=2-bb[1] + max(0,(sh-4-th)//2)
        d.text((px,py),row["ko"],font=font,fill=fill)
        lm=np.asarray(tmp.getchannel("A"))>0
        lb=bbox(lm)
        if lb is None: continue
        # Translate local bbox to full image.
        glb=[x0+lb[0],y0+lb[1],x0+lb[2],y0+lb[3]]
        if not (glb[0]>=x0+2 and glb[1]>=y0+2 and glb[2]<=x1-2 and glb[3]<=y1-2): continue
        chosen=(tmp,lm,glb,fs,fill)
        break
    if chosen is None: raise RuntimeError(("no render fit",row["key"],sb))
    tmp,lm,glb,fs,fill=chosen
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tmp,(x0,y0))
    glm=np.asarray(layer.getchannel("A"))>0
    if np.any(target&glm): raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer)
    target|=glm; render_masks.append(glm)
    row.update({
      "korean":row["ko"],"font":"Noto Sans CJK KR Black","font_size":fs,"fill_rgba":list(fill),
      "localized_bbox":glb,
      "source_width":sw,"source_height":sh,
      "localized_width":glb[2]-glb[0],"localized_height":glb[3]-glb[1],
      "delta_left":glb[0]-x0,"delta_right":x1-glb[2],"delta_top":glb[1]-y0,"delta_bottom":y1-glb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

# Allowed changed pixels are inside exact source glyph/effect bboxes only.
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; allowed[y0:y1,x0:x1]=True
fa=np.asarray(final,dtype=np.uint8)
changed=np.any(sa!=fa,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=fa[:,:,3]) & ~allowed))
introduced=int(np.count_nonzero((fa[:,:,3]>8)&(sa[:,:,3]<=8)&~allowed))
if outside or alpha_out or introduced:
    raise RuntimeError(("outside gate",outside,alpha_out,introduced))

# Source red/effect must be gone from the clean plate and from final outside Korean targets.
rr=fa[:,:,0].astype(np.int16); gg=fa[:,:,1].astype(np.int16); bb=fa[:,:,2].astype(np.int16)
red_final=(rr>65)&(rr>gg+28)&(rr>bb+28)&((rr-gg)>35)&(fa[:,:,3]>8)
guard=target
source_red_residue=int(np.count_nonzero(source_mask & ~guard & red_final))
if source_red_residue:
    raise RuntimeError(("final source red residue",source_red_residue))

# Exact RGBA32 DDS write preserving 128-byte header and raw mirror_y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=raw[:128]+raw_final.tobytes("raw","RGBA")
cand.write_bytes(payload)
dec_raw=Image.open(cand).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")
cand_sha=sha256(cand)

# Evidence.
src.save(out/"B196_SOURCE_READABLE.png")
clean.save(out/"B196_CLEAN_PLATE.png")
final.save(out/"B196_FINAL_READABLE.png")
raw_im.save(out/"B196_SOURCE_RAW.png")
raw_final.save(out/"B196_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B196_SOURCE_TEXT_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B196_TARGET_MASK.png")

cards=[]
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; pad=18
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",final)]:
        crop=im.crop(box).convert("RGB")
        scale=4
        crop=crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.NEAREST)
        card=Image.new("RGB",(crop.width,crop.height+28),"white"); card.paste(crop,(0,28))
        ImageDraw.Draw(card).text((6,7),f'{row["source"]}->{row["ko"]} {label}',fill="black")
        cards.append(card)
mw=max(c.width for c in cards); total=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(mw,total),"white"); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+8
sheet.thumbnail((1800,6000),Image.Resampling.LANCZOS)
sheet.save(out/"B196_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":176,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":url,"sha256":got},
 "b74_hold_resolution":"B74 region contact visibly contains all four red source labels. B196 uses the B74 atlas cells in readable orientation and derives exact red/effect bboxes from canonical source pixels; the prior SOURCE_TEXT_ABSENT conclusion is superseded.",
 "segments":[{"source":r["source"],"korean":r["ko"]} for r in rows],
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":1,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "static_qa":{
   "elements_total":4,"bbox_size_positive_margin":"4/4 PASS",
   "clean_source_residue":clean_residue,
   "changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,
   "introduced_visible_outside_source_bboxes":introduced,
   "final_source_red_residue_outside_targets":source_red_residue,
   "localized_overlap":0,
   "dds_roundtrip":"PASS","status":"PASS"
 },
 "candidate_sha256":cand_sha,
 "candidate_path":str(cand.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"B196_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B196_75C3586A_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B196_75C3586A.json").write_text(json.dumps({"role":"B","run":run,"queue_index":176,"asset":"75C3586A","candidate_sha256":cand_sha,"report":str(rp.relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B196_DONE",cand_sha,[(r["key"],r["source_bbox"],r["localized_bbox"],r["font_size"]) for r in rows])
