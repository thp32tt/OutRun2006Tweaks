#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd(); run="20261006-B-PRODUCTION178-33491F83"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
srcp=Path("/tmp/B178_33491F83.dds"); urllib.request.urlretrieve(url,srcp)
SOURCE_SHA="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw=srcp.read_bytes()
if sha(srcp)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(srcp)))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]; W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]; FOURCC=raw[84:88]; BPP=struct.unpack_from("<I",raw,88)[0]
MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,FOURCC,BPP)!=(2048,1024,1,b"\0\0\0\0",32): raise RuntimeError(("structure",W,H,MIPS,FOURCC,BPP))
if MASKS!=(0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("masks",MASKS))
src=Image.open(srcp).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); alpha=sa[:,:,3]>8

# Exact atlas cells from upstream 4x_33491F83_512x256_atlas.json.
atlas_cells=[
 [4,4,1196,812],[1204,4,1708,124],[1204,132,1708,252],[1716,4,2036,124],[1716,132,2036,252]
]
# Coarse text-only controller windows. Main diagram windows exclude arrows/cones/road where possible.
specs=[
 {"key":"diverge_main","source":"Diverge","ko":"분기","window":[450,5,850,120],"family":"yellow","white_outer":False},
 {"key":"left_main","source":"Left","ko":"좌측","window":[330,100,560,230],"family":"green","white_outer":True},
 {"key":"right_main","source":"Right","ko":"우측","window":[720,100,970,230],"family":"red","white_outer":True},
 {"key":"easy_main","source":"EASY","ko":"쉬움","window":[120,225,455,365],"family":"green","white_outer":True},
 {"key":"hard_main","source":"HARD","ko":"어려움","window":[835,225,1145,365],"family":"red","white_outer":True},
 {"key":"hard_arrow","source":"HARD","ko":"어려움","window":[1360,5,1660,120],"family":"red","white_outer":True},
 {"key":"easy_arrow","source":"EASY","ko":"쉬움","window":[1360,135,1660,248],"family":"green","white_outer":True},
 {"key":"hard_alone","source":"HARD","ko":"어려움","window":[1730,5,2025,120],"family":"red","white_outer":True},
 {"key":"easy_alone","source":"EASY","ko":"쉬움","window":[1730,135,2025,248],"family":"green","white_outer":True},
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

rows=[]; masks=[]
for sp in specs:
    x0,y0,x1,y1=sp["window"]; sub=sa[y0:y1,x0:x1,:]
    seed_local=fill_seed(sub,sp["family"])
    if int(seed_local.sum())<100: raise RuntimeError(("seed too small",sp["key"],int(seed_local.sum())))
    # Keep text fill components; coarse windows avoid the same-colour arrows/road.
    lab,n=ndimage.label(seed_local)
    comps=[]
    for i in range(1,n+1):
        c=(lab==i); area=int(c.sum())
        if area>=12: comps.append((area,c))
    if not comps: raise RuntimeError(("no seed components",sp["key"]))
    seed=np.zeros_like(seed_local)
    # Text letters can be separate components; keep all meaningful components in the text window.
    for area,c in comps: seed|=c
    # Grow from fill through nearby visible pixels to capture navy/white outline + AA,
    # but cap growth to 14px so unrelated road/arrow art cannot bridge in.
    grow=ndimage.binary_dilation(seed,iterations=14)
    mlocal=grow & (sub[:,:,3]>8)
    # Require every kept pixel to be close to seed; this rejects a background component
    # that merely enters the window away from the lettering.
    dist=ndimage.distance_transform_edt(~seed)
    mlocal &= (dist<=14.5)
    m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=mlocal
    bb=bbox(m)
    if bb is None: raise RuntimeError(("empty mask",sp["key"]))
    masks.append(m)
    fillpix=sub[seed_local][:,:3]
    fill=tuple(int(v) for v in np.median(fillpix,axis=0))+(255,)
    darkpix=sub[mlocal & (sub[:,:,:3].mean(axis=2)<100)][:,:3]
    navy=tuple(int(v) for v in (np.median(darkpix,axis=0) if len(darkpix) else np.array([4,12,64])))+(255,)
    whitepix=sub[mlocal & (sub[:,:,:3].min(axis=2)>170)][:,:3]
    white=tuple(int(v) for v in (np.median(whitepix,axis=0) if len(whitepix) else np.array([245,245,245])))+(255,)
    rows.append({**sp,"source_bbox":bb,"source_mask_pixels":int(m.sum()),"fill_rgba":fill,"navy_rgba":navy,"white_rgba":white})

source_mask=np.zeros((H,W),bool)
for m in masks:
    if np.any(source_mask&m): raise RuntimeError("source text masks overlap")
    source_mask|=m

# Preserve every source-visible pixel not explicitly identified as source text.
protected_visible=alpha & ~source_mask
clean_arr=sa.copy(); clean_arr[source_mask]=0
clean=Image.fromarray(clean_arr,"RGBA")
if np.count_nonzero(np.asarray(clean.getchannel("A"))[source_mask]>0): raise RuntimeError("clean source residue")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def shear(im,amount):
    if amount<=0:return im
    add=int(round(amount*im.height))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def render_text(row):
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0
    for fs in range(max(18,sh),15,-1):
        font=ImageFont.truetype(FONT,fs)
        probe=Image.new("RGBA",(max(600,sw*3),max(240,sh*3)),(0,0,0,0)); d=ImageDraw.Draw(probe)
        # Source family: coloured face, navy keyline, and white outer rim except Diverge.
        outer_w=max(3,round(fs*0.10))
        navy_w=max(2,round(fs*0.065))
        tb=d.textbbox((0,0),row["ko"],font=font,stroke_width=outer_w)
        xy=(24-tb[0],24-tb[1])
        if row["white_outer"]:
            d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=outer_w,stroke_fill=row["white_rgba"])
            d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=navy_w,stroke_fill=row["navy_rgba"])
        else:
            d.text(xy,row["ko"],font=font,fill=row["fill_rgba"],stroke_width=outer_w,stroke_fill=row["navy_rgba"])
        gb=probe.getchannel("A").getbbox()
        if not gb: continue
        g=probe.crop(gb); g=shear(g,0.13)
        gb=g.getchannel("A").getbbox()
        if gb:g=g.crop(gb)
        if g.width>sw-4 or g.height>sh-4: continue
        px=x0+(sw-g.width)//2; py=y0+(sh-g.height)//2
        layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(g,(px,py))
        lm=np.asarray(layer.getchannel("A"))>0
        lb=bbox(lm)
        if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): continue
        # Hard zero-overlap with preserved source art, plus one-pixel separation.
        near=np.asarray(Image.fromarray((protected_visible.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
        if np.any(lm & near): continue
        return layer,lm,lb,fs
    raise RuntimeError(("no safe render fit",row["key"],row["source_bbox"]))

final=clean.copy(); target=np.zeros((H,W),bool)
for row in rows:
    layer,lm,lb,fs=render_text(row)
    if np.any(target&lm): raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer); target|=lm
    sbx=row["source_bbox"]; row["localized_bbox"]=lb; row["font"]="Noto Sans CJK KR Black"; row["font_size"]=fs; row["shear"]=0.13
    row["source_width"]=sbx[2]-sbx[0]; row["source_height"]=sbx[3]-sbx[1]
    row["localized_width"]=lb[2]-lb[0]; row["localized_height"]=lb[3]-lb[1]
    row["delta_left"]=lb[0]-sbx[0]; row["delta_right"]=sbx[2]-lb[2]; row["delta_top"]=lb[1]-sbx[1]; row["delta_bottom"]=sbx[3]-lb[3]
    row["containment"]="PASS"; row["size_ceiling"]="PASS"; row["positive_margin"]="PASS"; row["protected_separation_1px"]="PASS"

# Encode exact RGBA32 DDS with original header and raw mirror_y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=raw[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(payload)
cand_sha=sha(candidate)
dec=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")
da=np.asarray(dec,dtype=np.uint8)
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; allowed[y0:y1,x0:x1]=True
changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
protected_changed=int(np.count_nonzero(changed & protected_visible))
introduced=int(np.count_nonzero((da[:,:,3]>8)&(sa[:,:,3]<=8)&~allowed))
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_mask & (da[:,:,3]>8) & ~guard))
if outside or alpha_out or protected_changed or introduced or residue:
    raise RuntimeError(("static gate",outside,alpha_out,protected_changed,introduced,residue))

# Evidence.
src.save(out/"B178_SOURCE_READABLE.png"); clean.save(out/"B178_CLEAN_PLATE.png"); dec.save(out/"B178_FINAL_READABLE.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B178_SOURCE_TEXT_MASK.png")
Image.fromarray((protected_visible.astype(np.uint8)*255),"L").save(out/"B178_PROTECTED_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B178_TARGET_MASK.png")

def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1:v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30)); ImageDraw.Draw(c).text((5,6),label,fill="black"); return c

crop=(0,0,2048,420)
cards=[card("SOURCE",src,crop,1),card("CLEAN",clean,crop,1),card("FINAL",dec,crop,1)]
mw=max(c.width for c in cards); mh=sum(c.height for c in cards)+8*2
sheet=Image.new("RGB",(mw,mh),"white"); yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
sheet.thumbnail((2200,1600),Image.Resampling.LANCZOS); sheet.save(out/"B178_SOURCE_CLEAN_FINAL_TOP_CONTACT.jpg",quality=97)

full=Image.new("RGB",(2048,comp(src).height*3+68),"white")
yy=0
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
    c=card(label,im,(0,0,W,H),1); c.thumbnail((2048,700),Image.Resampling.LANCZOS); full.paste(c,(0,yy)); yy+=c.height+4
full=full.crop((0,0,2048,yy)); full.save(out/"B178_FULL_SOURCE_CLEAN_FINAL.jpg",quality=95)
rawsrc=Image.open(srcp).convert("RGBA"); rawfin=Image.open(candidate).convert("RGBA")
rs=Image.new("RGB",(2048,0+2*(H+30)+8),"white"); yy=0
for label,im in [("SOURCE_RAW",rawsrc),("FINAL_RAW",rawfin)]:
    c=card(label,im,(0,0,W,H),1); rs.paste(c,(0,yy)); yy+=c.height+8
rs.thumbnail((2200,1500),Image.Resampling.LANCZOS); rs.save(out/"B178_RAW_CONTACT.jpg",quality=95)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":62,"asset":asset,"readiness_tier":"B177_ZOOM_REVIEW_POSITIVE_TO_RENDER_SAME_INVOCATION",
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "atlas_cells":atlas_cells,
 "classification":{"semantic_segments":[{"source":"Diverge","korean":"분기"},{"source":"Left","korean":"좌측"},{"source":"Right","korean":"우측"},{"source":"EASY","korean":"쉬움"},{"source":"HARD","korean":"어려움"}],
   "physical_text_elements":9,
   "protected":["road/track geometry","direction arrows","traffic light/cones/barriers","all non-text artwork"],
   "translation_provenance":"Diverge/Left/Right wording follows historical EBEF6D20 established labels; EASY follows reviewed A064FDFC 쉬움; HARD paired as 어려움."},
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
 "rows":rows,
 "static_qa":{"elements_total":len(rows),"bbox_size_positive_margin":f"{len(rows)}/{len(rows)} PASS",
   "changed_outside_source_bboxes":outside,"alpha_changed_outside":alpha_out,
   "protected_visible_changed":protected_changed,"introduced_visible_outside":introduced,
   "source_residue_pixels":residue,"localized_overlap":0,"status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"B178_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B178_33491F83_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B178_33491F83.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":62,"asset":"33491F83","source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "report":str((out/"B178_33491F83_REPORT.json").relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B178_DONE",cand_sha,[(r["key"],r["source_bbox"],r["localized_bbox"]) for r in rows])
