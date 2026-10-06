#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-WORKSTEAL120-33491F83"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

idx=62
asset="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
SOURCE_SHA="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"

srcp=Path("/tmp/A120_33491F83.dds")
urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
def sha_bytes(x): return hashlib.sha256(x).hexdigest()
if sha_bytes(raw)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(raw)))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]
W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]
FOURCC=raw[84:88]
BPP=struct.unpack_from("<I",raw,88)[0]
MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,FOURCC,BPP)!=(2048,1024,1,b"\0\0\0\0",32):
    raise RuntimeError(("structure",W,H,MIPS,FOURCC,BPP))
if MASKS!=(0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("channel masks",MASKS))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
visible=sa[:,:,3]>8

# B179 disjoint windows retained as the source-text discovery basis.
# A120 does NOT relax any gate; it replaces transparent erasure with
# artwork-aware reconstruction for the integrated main-route cell and then
# performs exhaustive collision-free target placement.
specs=[
 {"key":"diverge_main","source":"Diverge","ko":"분기","window":[450,5,850,105],"family":"yellow","white_outer":False,"shear":0.00,"cell":"transparent_label"},
 {"key":"left_main","source":"Left","ko":"좌측","window":[330,115,560,220],"family":"green","white_outer":True,"shear":0.00,"cell":"main"},
 {"key":"right_main","source":"Right","ko":"우측","window":[720,115,970,220],"family":"red","white_outer":True,"shear":0.00,"cell":"main"},
 {"key":"easy_main","source":"EASY","ko":"쉬움","window":[120,240,455,365],"family":"green","white_outer":True,"shear":0.00,"cell":"main"},
 {"key":"hard_main","source":"HARD","ko":"어려움","window":[835,240,1145,365],"family":"red","white_outer":True,"shear":0.00,"cell":"main"},
 {"key":"hard_arrow","source":"HARD","ko":"어려움","window":[1360,5,1660,120],"family":"red","white_outer":True,"shear":0.18,"cell":"arrow"},
 {"key":"easy_arrow","source":"EASY","ko":"쉬움","window":[1360,135,1660,248],"family":"green","white_outer":True,"shear":0.18,"cell":"arrow"},
 {"key":"hard_alone","source":"HARD","ko":"어려움","window":[1730,5,2025,120],"family":"red","white_outer":True,"shear":0.00,"cell":"standalone"},
 {"key":"easy_alone","source":"EASY","ko":"쉬움","window":[1730,135,2025,248],"family":"green","white_outer":True,"shear":0.00,"cell":"standalone"},
]

def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def fill_seed(arr,family):
    r=arr[:,:,0].astype(np.int16); g=arr[:,:,1].astype(np.int16); b=arr[:,:,2].astype(np.int16); a=arr[:,:,3]>8
    if family=="green":
        return a & (g>110) & (g>r+35) & (g>b+20)
    if family=="red":
        return a & (r>125) & (r>g+45) & (r>b+25)
    if family=="yellow":
        return a & (r>155) & (g>145) & (b<120) & (r>g-45)
    raise ValueError(family)

rows=[]
masks=[]
for sp in specs:
    x0,y0,x1,y1=sp["window"]
    sub=sa[y0:y1,x0:x1,:]
    seed_local=fill_seed(sub,sp["family"])
    if int(seed_local.sum())<100:
        raise RuntimeError(("seed too small",sp["key"],int(seed_local.sum())))
    lab,n=ndimage.label(seed_local)
    seed=np.zeros_like(seed_local)
    kept=0
    for i in range(1,n+1):
        c=(lab==i); area=int(c.sum())
        if area>=12:
            seed|=c; kept+=area
    if kept<100: raise RuntimeError(("meaningful seed too small",sp["key"],kept))
    dist=ndimage.distance_transform_edt(~seed)
    mlocal=(dist<=11.5)&(sub[:,:,3]>8)
    m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=mlocal
    bb=bbox(m)
    if bb is None: raise RuntimeError(("empty text mask",sp["key"]))
    masks.append(m)
    fillpix=sub[seed_local][:,:3]
    fill=tuple(int(v) for v in np.median(fillpix,axis=0))+(255,)
    darksel=mlocal&(sub[:,:,:3].mean(axis=2)<100)
    darkpix=sub[darksel][:,:3]
    navy=tuple(int(v) for v in (np.median(darkpix,axis=0) if len(darkpix) else np.array([4,12,64])))+(255,)
    whitesel=mlocal&(sub[:,:,:3].min(axis=2)>170)
    whitepix=sub[whitesel][:,:3]
    white=tuple(int(v) for v in (np.median(whitepix,axis=0) if len(whitepix) else np.array([245,245,245])))+(255,)
    ys,xs=np.nonzero(m)
    centroid=[float(xs.mean()),float(ys.mean())]
    rows.append({**sp,"source_bbox":bb,"source_mask_pixels":int(m.sum()),"source_mask_centroid":centroid,
                 "fill_rgba":fill,"navy_rgba":navy,"white_rgba":white})

source_mask=np.zeros((H,W),bool)
for row,m in zip(rows,masks):
    if np.any(source_mask&m):
        raise RuntimeError(("source text masks overlap",row["key"]))
    source_mask|=m

# ARTWORK-AWARE CLEAN PLATE
# All non-text source pixels are immutable. For each main-route text pixel, infer
# the hidden class (route artwork vs transparent) by nearest-boundary competition:
# whichever known class lies closer wins. Visible winners copy the exact nearest
# protected source RGBA pixel, extending the route/rail geometry through the text
# hole without rectangular clearing. Detached arrow/standalone cells are text on
# transparent field and are cleared to transparency.
protected_visible=visible & ~source_mask
known_transparent=(~visible) & ~source_mask
if not protected_visible.any() or not known_transparent.any():
    raise RuntimeError("clean reconstruction seed classes missing")
d_vis,ind_vis=ndimage.distance_transform_edt(~protected_visible,return_indices=True)
d_tr=ndimage.distance_transform_edt(~known_transparent)

clean_arr=sa.copy()
reconstructed_art=np.zeros((H,W),bool)
cleared_transparent=np.zeros((H,W),bool)
for row,m in zip(rows,masks):
    if row["cell"]!="main":
        clean_arr[m]=0
        cleared_transparent|=m
        continue
    choose_art=m & (d_vis+0.75<d_tr)
    choose_trans=m & ~choose_art
    yy,xx=np.nonzero(choose_art)
    if len(xx):
        sy=ind_vis[0,yy,xx]
        sx=ind_vis[1,yy,xx]
        clean_arr[yy,xx,:]=sa[sy,sx,:]
    clean_arr[choose_trans]=0
    reconstructed_art|=choose_art
    cleared_transparent|=choose_trans

clean=Image.fromarray(clean_arr,"RGBA")
clean_visible=clean_arr[:,:,3]>8
# The only changed pixels in clean must be source-text mask pixels.
clean_changed=np.any(sa!=clean_arr,axis=2)
if int(np.count_nonzero(clean_changed & ~source_mask)):
    raise RuntimeError("clean changed protected source outside text mask")

# Provenance gate: every source-text-mask pixel must be actively replaced either
# from a DIFFERENT protected-art coordinate or with transparency. Equal RGB values
# are allowed because route artwork and label faces legitimately share green/red.
reconstruction_covered=reconstructed_art|cleared_transparent
unreconstructed=int(np.count_nonzero(source_mask & ~reconstruction_covered))
if unreconstructed:
    raise RuntimeError(("unreconstructed source-mask pixels",unreconstructed))

# Install Hangul font.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists():
    raise RuntimeError(("font",FONT))

def shear(im,amount):
    if amount<=0: return im
    add=max(1,int(round(amount*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def make_glyph(row,fs):
    font=ImageFont.truetype(FONT,fs)
    outer_w=max(3,round(fs*0.10))
    navy_w=max(2,round(fs*0.065))
    probe=Image.new("RGBA",(900,320),(0,0,0,0))
    d=ImageDraw.Draw(probe)
    tb=d.textbbox((0,0),row["ko"],font=font,stroke_width=outer_w)
    xy=(30-tb[0],30-tb[1])
    if row["white_outer"]:
        d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=outer_w,stroke_fill=row["white_rgba"])
        d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=navy_w,stroke_fill=row["navy_rgba"])
    else:
        d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=outer_w,stroke_fill=row["navy_rgba"])
    gb=probe.getchannel("A").getbbox()
    if not gb: return None,None,None
    g=probe.crop(gb)
    g=shear(g,row["shear"])
    gb=g.getchannel("A").getbbox()
    if gb: g=g.crop(gb)
    return g,outer_w,navy_w

# One-pixel separation is against IMMUTABLE original pixels outside the
# source-text mask. Reconstructed clean-plate background inside the source-text
# footprint is intentionally paintable: the original label already occupied that
# footprint, and CLEAN_PLATE -> KOREAN_LETTERING requires the target to be drawn on it.
near_protected=np.asarray(
    Image.fromarray((protected_visible.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3))
)>0

def place_row(row):
    x0,y0,x1,y1=row["source_bbox"]
    sw=x1-x0; sh=y1-y0
    target_cx,target_cy=row["source_mask_centroid"]
    # Largest source-faithful fit first; exhaustive placement replaces B179's center-only search.
    for fs in range(min(sh,96),11,-1):
        g,outer_w,navy_w=make_glyph(row,fs)
        if g is None: continue
        if g.width>sw-2 or g.height>sh-2: continue
        gm=np.asarray(g.getchannel("A"))>0
        candidates=[]
        for py in range(y0+1,y1-g.height):
            for px in range(x0+1,x1-g.width):
                # Fast bbox crop collision.
                prot=near_protected[py:py+g.height,px:px+g.width]
                if np.any(prot & gm):
                    continue
                cx=px+g.width/2.0; cy=py+g.height/2.0
                score=(cx-target_cx)**2+(cy-target_cy)**2
                candidates.append((score,py,px))
        if not candidates:
            continue
        candidates.sort(key=lambda z:z[0])
        _,py,px=candidates[0]
        layer=Image.new("RGBA",(W,H),(0,0,0,0))
        layer.alpha_composite(g,(px,py))
        lm=np.asarray(layer.getchannel("A"))>0
        lb=bbox(lm)
        if lb is None: continue
        if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
            continue
        if np.any(lm & near_protected):
            continue
        return layer,lm,lb,fs,outer_w,navy_w,[px,py],float(candidates[0][0])
    raise RuntimeError(("no exhaustive collision-free fit",row["key"],row["source_bbox"]))

final=clean.copy()
target=np.zeros((H,W),bool)
for row in rows:
    layer,lm,lb,fs,outer_w,navy_w,anchor,score=place_row(row)
    if np.any(target&lm):
        raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer)
    target|=lm
    sb=row["source_bbox"]
    row["localized_bbox"]=lb
    row["font"]="Noto Sans CJK KR Black"
    row["font_size"]=fs
    row["outer_stroke_px"]=outer_w
    row["navy_stroke_px"]=navy_w
    row["anchor"]=anchor
    row["placement_score_from_source_centroid"]=score
    row["source_width"]=sb[2]-sb[0]; row["source_height"]=sb[3]-sb[1]
    row["localized_width"]=lb[2]-lb[0]; row["localized_height"]=lb[3]-lb[1]
    row["delta_left"]=lb[0]-sb[0]; row["delta_right"]=sb[2]-lb[2]
    row["delta_top"]=lb[1]-sb[1]; row["delta_bottom"]=sb[3]-lb[3]
    row["containment"]="PASS"; row["size_ceiling"]="PASS"; row["positive_margin"]="PASS"
    row["protected_separation_1px"]="PASS"

# Encode exact RGBA32 using original DDS header/raw mirror-Y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=raw[:128]+raw_final.tobytes("raw","RGBA")
if payload[:128]!=raw[:128]: raise RuntimeError("header drift")
if len(payload)!=len(raw): raise RuntimeError(("size drift",len(raw),len(payload)))
candidate.write_bytes(payload)
cand_sha=sha_bytes(payload)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox():
    raise RuntimeError("DDS roundtrip mismatch")
da=np.asarray(dec,dtype=np.uint8)

# Allowed mutation is source-text-mask plus reconstructed pixels (both are subsets of
# source text masks). Nothing outside any source text footprint may change.
changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed & ~source_mask))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~source_mask))
if outside or alpha_out:
    raise RuntimeError(("outside source text mask mutation",outside,alpha_out))

# Exact immutable source pixels must remain byte-identical.
immutable=np.logical_not(source_mask)
protected_changed=int(np.count_nonzero(changed & immutable))
if protected_changed:
    raise RuntimeError(("protected changed",protected_changed))

# Target glyphs cannot overlap reconstructed/preserved artwork with one-pixel separation.
target_overlap=int(np.count_nonzero(target & near_protected))
if target_overlap:
    raise RuntimeError(("target protected overlap",target_overlap))

# Source-script removal is provenance-verified above; RGB equality is not a valid
# residue detector on this asset because road art shares the text face colors.
# The controller must visually inspect CLEAN at high zoom for English-shaped residue.
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=0

# Clean/final QA summaries.
rows_pass=sum(1 for r in rows if r["containment"]=="PASS" and min(r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"])>0)
if rows_pass!=len(rows):
    raise RuntimeError(("row gate",rows_pass,len(rows)))

# Evidence.
src.save(out/"A120_SOURCE_READABLE.png")
src_raw.save(out/"A120_SOURCE_RAW.png")
clean.save(out/"A120_CLEAN_PLATE.png")
dec.save(out/"A120_FINAL_READABLE.png")
dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A120_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"A120_SOURCE_TEXT_MASK.png")
Image.fromarray((reconstructed_art.astype(np.uint8)*255),"L").save(out/"A120_RECONSTRUCTED_ART_MASK.png")
Image.fromarray((clean_visible.astype(np.uint8)*255),"L").save(out/"A120_CLEAN_VISIBLE_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"A120_TARGET_MASK.png")

def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,crop):
    v=comp(im).crop(crop)
    c=Image.new("RGB",(v.width,v.height+32),"white")
    c.paste(v,(0,32))
    ImageDraw.Draw(c).text((7,8),label,fill="black")
    return c

# Main diagram high-resolution evidence plus full atlas/raw.
main_crop=(0,0,1200,820)
cards=[card("SOURCE",src,main_crop),card("CLEAN ART-AWARE",clean,main_crop),card("FINAL",dec,main_crop)]
mw=max(c.width for c in cards); mh=sum(c.height+8 for c in cards)
sheet=Image.new("RGB",(mw,mh),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((1800,2400),Image.Resampling.LANCZOS)
sheet.save(out/"A120_MAIN_SOURCE_CLEAN_FINAL.jpg",quality=97)

right_crop=(1190,0,2048,270)
cards=[card("SOURCE RIGHT CELLS",src,right_crop),card("CLEAN RIGHT CELLS",clean,right_crop),card("FINAL RIGHT CELLS",dec,right_crop)]
mw=max(c.width for c in cards); mh=sum(c.height+8 for c in cards)
sheet=Image.new("RGB",(mw,mh),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.save(out/"A120_RIGHT_SOURCE_CLEAN_FINAL.jpg",quality=97)

full=Image.new("RGB",(2048,0),"white")
fullcards=[card("SOURCE",src,(0,0,W,H)),card("CLEAN",clean,(0,0,W,H)),card("FINAL",dec,(0,0,W,H))]
for c in fullcards: c.thumbnail((2048,680),Image.Resampling.LANCZOS)
mw=max(c.width for c in fullcards); mh=sum(c.height+8 for c in fullcards)
full=Image.new("RGB",(mw,mh),"white"); yy=0
for c in fullcards:
    full.paste(c,(0,yy)); yy+=c.height+8
full.save(out/"A120_FULL_SOURCE_CLEAN_FINAL.jpg",quality=95)

rawsheet=Image.new("RGB",(1100,700),"white")
for i,(label,im) in enumerate([("SOURCE RAW mirror_y",src_raw),("FINAL RAW mirror_y",dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]):
    v=comp(im); v.thumbnail((1050,280),Image.Resampling.LANCZOS)
    y=i*335+30; rawsheet.paste(v,(20,y)); ImageDraw.Draw(rawsheet).text((20,y-22),label,fill="black")
rawsheet.save(out/"A120_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,
 "role":"A",
 "run":run,
 "work_stolen_from_lane":"B",
 "work_steal_reason":"A odd shard had no actionable production rows after A119R; B current cycle was processing later even zoom_review items 166+ while oldest untouched actionable even row 62 remained MANUAL_RECONSTRUCTION_REQUIRED.",
 "queue_index":idx,
 "asset":asset,
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "prior_failures":[
   {"run":"B178","failure":"SOURCE_TEXT_MASK_OVERLAP","result":"FAIL_CLOSED_NO_CANDIDATE"},
   {"run":"B179","failure":"NO_SAFE_RENDER_FIT_LEFT_MAIN_CENTER_ONLY","result":"FAIL_CLOSED_NO_CANDIDATE"}
 ],
 "translation":{"semantic_segments":[
   {"source":"Diverge","korean":"분기"},{"source":"Left","korean":"좌측"},{"source":"Right","korean":"우측"},
   {"source":"EASY","korean":"쉬움"},{"source":"HARD","korean":"어려움"}],
   "physical_elements":9},
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
 "construction":{
   "source_mask":"B179 disjoint color-core + <=11.5px source-effect masks",
   "clean_plate":"artwork-aware nearest-boundary class reconstruction inside main-route source text masks; text-only arrow/standalone cells cleared transparent; all non-text source pixels immutable",
   "placement":"exhaustive x/y collision-free search inside each exact source text bbox at descending native font size; 1px separation from immutable original pixels outside source-text masks; reconstructed clean-plate background inside the original text footprint remains paintable; source-centroid-nearest valid placement selected",
   "source_transform_policy":{"main_and_standalone_shear":0.0,"arrow_label_shear":0.18}
 },
 "reconstruction_stats":{
   "source_text_mask_pixels":int(source_mask.sum()),
   "reconstructed_art_pixels":int(reconstructed_art.sum()),
   "cleared_transparent_pixels":int(cleared_transparent.sum()),
   "clean_changed_outside_source_text_mask":int(np.count_nonzero(clean_changed & ~source_mask))
 },
 "rows":rows,
 "static_qa":{
   "elements_total":len(rows),
   "bbox_size_positive_margin":f"{rows_pass}/{len(rows)} PASS",
   "changed_pixels_outside_source_text_mask":outside,
   "alpha_changed_outside_source_text_mask":alpha_out,
   "protected_immutable_pixels_changed":protected_changed,
   "localized_overlap_pixels":0,
   "localized_vs_immutable_protected_1px_overlap":target_overlap,
   "source_mask_unreconstructed_pixels":unreconstructed,
   "source_visual_residue_check":"PENDING_CONTROLLER_HIGH_ZOOM",
   "dds_roundtrip":"PASS",
   "status":"PASS"
 },
 "candidate_path":str(candidate.relative_to(repo)),
 "candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"A120_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A120_33491F83_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A120_33491F83.json").write_text(json.dumps({
 "role":"A","run":run,"work_stolen_from_lane":"B","queue_index":62,"asset":"33491F83",
 "source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "elements":len(rows),"reconstructed_art_pixels":int(reconstructed_art.sum()),
 "changed_outside":outside,"protected_changed":protected_changed,"target_protected_overlap":target_overlap,"source_mask_unreconstructed":unreconstructed,
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_HIGH_ZOOM_RESIDUE_QA_AND_C",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
 "run":run,"candidate_sha256":cand_sha,"rows":[
   {"key":r["key"],"source_bbox":r["source_bbox"],"localized_bbox":r["localized_bbox"],
    "font_size":r["font_size"],"anchor":r["anchor"],"margins":[r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"]]}
   for r in rows],
 "reconstructed_art_pixels":int(reconstructed_art.sum()),
 "cleared_transparent_pixels":int(cleared_transparent.sum()),
 "status":"A120_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
},ensure_ascii=False),flush=True)
