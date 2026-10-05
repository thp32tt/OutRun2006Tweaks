#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION93-EBE401C8"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBE401C8_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/EBE401C8_512x256.dds"
source_sha="29b87a5c8a652fda0e107291bfa410ba492f44d4cc9c9ccefd55de26fc674b34"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported",w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{
      "width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,
      "masks":[hex(x) for x in masks],"raw_mode":mode}

def write_dds(header,readable,p,mode):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def ensure_font():
    q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",q))
    return q

srcp=Path("/tmp/a93_ebe_source.dds")
urllib.request.urlretrieve(source_url,srcp)
if sha(srcp)!=source_sha: raise RuntimeError(("source drift",sha(srcp)))
header,src,meta=load_dds(srcp)
if (meta["width"],meta["height"],meta["raw_mode"])!=(2048,1024,"BGRA"):
    raise RuntimeError(("structure",meta))

sa=np.asarray(src)
alpha=sa[:,:,3]>0
# Exact windows are non-overlapping and contain only the intended source glyph/effect family.
defs=[
 {"key":"help_online","source":"Play OutRun Online with Friends or other players!","korean":"아웃런 온라인에서 친구나 다른 플레이어와 함께 플레이하세요!","window":[0,340,1510,460],"family":"gray_help"},
 {"key":"help_lan","source":"Join or Create a LAN game of OutRun!","korean":"아웃런 LAN 게임에 참가하거나 만드세요!","window":[0,500,1200,620],"family":"gray_help"},
 {"key":"online_big","source":"ONLINE","korean":"온라인","window":[0,845,700,1024],"family":"red_big"},
 {"key":"online_small","source":"ONLINE","korean":"온라인","window":[1240,920,1660,1024],"family":"gray_small"},
]
for r in defs:
    x0,y0,x1,y1=r["window"]
    m=np.zeros_like(alpha); m[y0:y1,x0:x1]=alpha[y0:y1,x0:x1]
    bb=bbox_mask(m)
    if not bb: raise RuntimeError(("missing source row",r["key"]))
    r["original_bbox"]=bb
    r["source_mask"]=m

# Assert known preserved LAN rows are outside all target masks.
preserve_windows={"lan_big":[0,670,370,850],"lan_small":[1240,750,1480,870]}
for name,(x0,y0,x1,y1) in preserve_windows.items():
    if int(alpha[y0:y1,x0:x1].sum())==0: raise RuntimeError(("missing preserved LAN",name))

source_text_mask=np.zeros_like(alpha)
for r in defs: source_text_mask|=r["source_mask"]
protected=np.logical_and(alpha,~source_text_mask)
clean_arr=sa.copy()
clean_arr[source_text_mask]=0
clean=Image.fromarray(clean_arr,"RGBA")

FONT=ensure_font()
def source_colors(r):
    m=r["source_mask"]; px=sa[m]
    vis=px[px[:,3]>0]
    if len(vis)<20: raise RuntimeError(("few pixels",r["key"]))
    lum=vis[:,:3].mean(axis=1)
    if r["family"]=="red_big":
        main=vis[(vis[:,0] > vis[:,1]*1.8) & (vis[:,0] > vis[:,2]*1.5) & (vis[:,3]>100)]
        shadow=vis[~((vis[:,0] > vis[:,1]*1.8) & (vis[:,0] > vis[:,2]*1.5))]
    else:
        cut=np.percentile(lum,55)
        main=vis[(lum>=cut)&(vis[:,3]>80)]
        shadow=vis[lum<cut]
    if len(main)<10: main=vis[vis[:,3]>128]
    if len(shadow)<10: shadow=vis
    fill=tuple(int(x) for x in np.median(main,axis=0))
    sh=tuple(int(x) for x in np.median(shadow,axis=0))
    fill=(fill[0],fill[1],fill[2],255)
    sh=(sh[0],sh[1],sh[2],max(120,min(230,sh[3])))
    return fill,sh

def render_crop(text,size,fill,shadow,family):
    font=ImageFont.truetype(FONT,size,index=1)
    pad=max(20,size//2); shadow_off=max(2,round(size*(0.045 if family=="gray_help" else 0.055)))
    stroke=max(1,round(size*0.018))
    tmp=Image.new("RGBA",(2400,400),(0,0,0,0)); d=ImageDraw.Draw(tmp)
    box=d.textbbox((pad,pad),text,font=font,stroke_width=stroke)
    d.text((pad+shadow_off,pad+shadow_off),text,font=font,fill=shadow,stroke_width=stroke,stroke_fill=shadow)
    d.text((pad,pad),text,font=font,fill=fill,stroke_width=stroke,stroke_fill=shadow)
    bb=tmp.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty render",text))
    return tmp.crop(bb),{"font_size":size,"shadow_offset":shadow_off,"stroke_width":stroke}

# Shared gray-help size must fit both source rows.
help_rows=[r for r in defs if r["family"]=="gray_help"]
help_size=None
for size in range(64,25,-1):
    ok=True
    for r in help_rows:
        fill,sh=source_colors(r); crop,_=render_crop(r["korean"],size,fill,sh,r["family"])
        x0,y0,x1,y1=r["original_bbox"]
        if crop.width > (x1-x0-4) or crop.height > (y1-y0-4): ok=False; break
    if ok: help_size=size; break
if help_size is None: raise RuntimeError("help text cannot fit")

final=clean.copy()
allowed=np.zeros_like(alpha)
render_masks=[]
rows=[]
for r in defs:
    x0,y0,x1,y1=r["original_bbox"]; sw=x1-x0; shh=y1-y0
    allowed[y0:y1,x0:x1]=1
    fill,shadow=source_colors(r)
    if r["family"]=="gray_help":
        size=help_size
    else:
        start=max(20,int(shh*0.94))
        size=None
        for s in range(start,17,-1):
            crop,_=render_crop(r["korean"],s,fill,shadow,r["family"])
            if crop.width <= sw-4 and crop.height <= shh-4:
                size=s; break
        if size is None: raise RuntimeError(("cannot fit",r["key"]))
    glyph,sty=render_crop(r["korean"],size,fill,shadow,r["family"])
    px=x0+2
    py=y0+(shh-glyph.height)//2
    if px+glyph.width>=x1 or py<=y0 or py+glyph.height>=y1:
        raise RuntimeError(("positive margin fail",r["key"],glyph.size,r["original_bbox"],(px,py)))
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
    gm=np.asarray(layer.getchannel("A"))>0
    if int(np.logical_and(gm,protected).sum())!=0: raise RuntimeError(("protected overlap",r["key"]))
    final.alpha_composite(layer)
    render_masks.append(gm)
    lb=bbox_mask(gm)
    rows.append({
      "key":r["key"],"source":r["source"],"korean":r["korean"],"family":r["family"],
      "original_bbox":r["original_bbox"],"localized_bbox":lb,
      "source_width":sw,"source_height":shh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
      "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Black","font_size":size,"fill_rgba":list(fill),"shadow_rgba":list(shadow),
      **sty,"alignment":"source-left+2 / vertical-center","render_resolution":"native_2048x1024"
    })

fa=np.asarray(final)
changed=np.any(sa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(sa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_union=np.zeros_like(alpha)
for m in render_masks: render_union|=m
render_protected=int(np.logical_and(render_union,protected).sum())
# Every original source-text pixel in the target rows must be removed unless covered by new Korean glyphs.
residue=int(np.logical_and(source_text_mask, np.logical_and(np.all(fa==sa,axis=2), ~render_union)).sum())
# Final outside new glyphs inside target bboxes must equal clean plate.
clean_residue=0
ca=np.asarray(clean)
for r,m in zip(rows,render_masks):
    x0,y0,x1,y1=r["original_bbox"]
    diff=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    local=m[y0:y1,x0:x1]
    clean_residue+=int(np.logical_and(diff,~local).sum())
# Pairwise localized overlap and 1px touch.
overlap=[]; touch=[]
for i in range(len(render_masks)):
  for j in range(i+1,len(render_masks)):
    a=render_masks[i]; b=render_masks[j]
    ov=int(np.logical_and(a,b).sum())
    if ov: overlap.append([i,j,ov])
    dil=np.zeros_like(a)
    for dy in (-1,0,1):
      for dx in (-1,0,1):
        ys=slice(max(0,dy),a.shape[0]+min(0,dy)); xs=slice(max(0,dx),a.shape[1]+min(0,dx))
        sy=slice(max(0,-dy),a.shape[0]-max(0,dy)); sx=slice(max(0,-dx),a.shape[1]-max(0,dx))
        dil[ys,xs]|=a[sy,sx]
    t=int(np.logical_and(dil,b).sum())
    if t: touch.append([i,j,t])
if any([outside,alpha_out,protected_changed,render_protected,residue,clean_residue]) or overlap or touch:
    raise RuntimeError(("QA",outside,alpha_out,protected_changed,render_protected,residue,clean_residue,overlap,touch))

new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("DDS roundtrip")

# Evidence.
src.save(out/"A93_SOURCE_READABLE.png")
clean.save(out/"A93_CLEAN_PLATE.png")
decoded.save(out/"A93_FINAL_READABLE.png")
Image.fromarray((source_text_mask*255).astype(np.uint8),"L").save(out/"A93_SOURCE_TEXT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"A93_PROTECTED_MASK.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"A93_ALLOWED_BBOX_MASK.png")

def composite(im):
    bg=Image.new("RGBA",im.size,(240,240,240,255)); bg.alpha_composite(im); return bg.convert("RGB")
cards=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; pad=12
    crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    panels=[composite(x).crop(crop) for x in (src,clean,decoded)]
    W=max(p.width for p in panels); H=max(p.height for p in panels)
    card=Image.new("RGB",(W*3+16,H+30),"white"); dd=ImageDraw.Draw(card)
    dd.text((4,4),r["key"]+" | SOURCE | CLEAN | FINAL",fill="black")
    for k,p in enumerate(panels): card.paste(p,(k*(W+8),30))
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)+6*(len(cards)-1)
sheet=Image.new("RGB",(cw,ch),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
sheet.thumbnail((3000,3600),Image.Resampling.LANCZOS)
sheet.save(out/"A93_SOURCE_CLEAN_FINAL_CONTACTS.jpg",quality=97)

for label,a,b in [
  ("READABLE",src,decoded),
  ("RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
]:
    aa=composite(a); bb=composite(b)
    sh=Image.new("RGB",(aa.width+bb.width+8,max(aa.height,bb.height)+28),"white")
    ImageDraw.Draw(sh).text((4,4),"SOURCE | FINAL",fill="black")
    sh.paste(aa,(0,28)); sh.paste(bb,(aa.width+8,28)); sh.thumbnail((2600,1800),Image.Resampling.LANCZOS)
    sh.save(out/f"A93_{label}_SOURCE_FINAL.jpg",quality=95)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":231,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
   "source_sha256":source_sha,"source_url":source_url},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "transcription_correction":{
   "prior_segment_count":2,"corrected_segment_count":4,
   "added_source_lines":[defs[0]["source"],defs[1]["source"]],
   "preserved_original":["LAN (large)","LAN (small)"],
   "localized_physical_rows":4
 },
 "candidate_sha256":new_sha,"candidate_path":str(candidate.relative_to(repo)),
 "rows":rows,
 "machine_qa":{
   "bbox_size_positive_margin":"4/4 PASS",
   "changed_pixels":int(changed.sum()),"changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
   "render_protected_overlap_pixels":render_protected,
   "source_exact_residue_pixels":residue,"clean_plate_residue_outside_korean_glyphs":clean_residue,
   "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch,"dds_roundtrip":"PASS",
   "preserved_LAN_rows":"PIXEL_EXACT_BY_OUTSIDE_SCOPE"
 },
 "visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"A93_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A93_EBE401C8_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A93_EBE401C8.json").write_text(json.dumps({
 "run":run,"queue_index":231,"asset":"EBE401C8","candidate_sha256":new_sha,
 "localized_physical_rows":4,"transcription_correction":"ADD_2_EXPLANATORY_SOURCE_LINES",
 "bbox_size_positive_margin":"4/4 PASS","machine_qa":report["machine_qa"],
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":str((out/"A93_EBE401C8_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A93_DONE",new_sha,[(r["key"],r["original_bbox"],r["localized_bbox"],r["font_size"]) for r in rows])
