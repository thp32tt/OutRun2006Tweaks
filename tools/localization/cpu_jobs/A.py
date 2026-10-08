#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261008-A195-Q237-FLAT-EFFECT-RECONSTRUCTION"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds"
source_sha="570fff6b71962f56b2f3d09993191a18989a80420b1963c4cccd1620b192907a"

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
    # Never accept the Regular TTC fallback that weakened older Korean UI.
    import glob
    options=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not options:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
        options=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not options: raise RuntimeError("No real NotoSansCJK-Black.ttc")
    return options[0]


# C1 q237 REWORK: reconstruct single-face source-type lettering, never reuse displaced
# bevel/shadow method. All nine windows and exact English source are pinned to A94.
REJECTED_SHA="acbf42d5f8f45ee6227bb0f81a770687bba680916c828f773095b64dbc63e5a3"
if not candidate.is_file() or sha(candidate)!=REJECTED_SHA:
    raise RuntimeError("q237 changed after C1 review; refuse stale overwrite")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","237","--require-safe-rerender"],capture_output=True,text=True)
print("A195 TRIAGE",triage.stdout,flush=True)
if triage.returncode!=0 or '"MATERIAL_REWORK"' not in triage.stdout:
    raise RuntimeError(("unsafe rerender",triage.stdout,triage.stderr))
srcp=Path("/tmp/a195_ff514ceb_source.dds")
urllib.request.urlretrieve(source_url,srcp)
if sha(srcp)!=source_sha: raise RuntimeError(("source SHA drift",sha(srcp)))
header,src,meta=load_dds(srcp)
if (meta["width"],meta["height"],meta["raw_mode"],meta["mips"])!=(2048,2048,"BGRA",1):
    raise RuntimeError(("invalid canonical source DDS",meta))
# Use the *lossless authored A94 clean plate* rather than inventing a new
# rectangular background patch. Verify plate removal independently.
clean_path=repo/"localization/graphics/role_A/20261006-A-PRODUCTION94-FF514CEB/A94_CLEAN_PLATE.png"
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError("A94 plate size mismatch")
sa=np.asarray(src); ca=np.asarray(clean)
alpha=sa[:,:,3]>0
defs=[
  {"key":"small_create","source":"CREATE GAME","korean":"게임 만들기","family":"gray_title","original_bbox":[14,775,536,838]},
  {"key":"small_custom","source":"CUSTOM GAME","korean":"커스텀 게임","family":"gray_title","original_bbox":[12,863,521,926]},
  {"key":"small_quick","source":"QUICK GAME","korean":"빠른 게임","family":"gray_title","original_bbox":[13,951,469,1018]},
  {"key":"help_create","source":"Create a game and invite your friends!","korean":"게임을 만들고 친구를 초대하세요!","family":"gray_help","original_bbox":[8,1015,1160,1101]},
  {"key":"help_custom","source":"Specify what gametype you'd like to play!","korean":"플레이할 게임 유형을 설정하세요!","family":"gray_help","original_bbox":[0,1175,1263,1272]},
  {"key":"help_quick","source":"Jump into a quick game of OutRun!","korean":"빠른 아웃런 게임에 참가하세요!","family":"gray_help","original_bbox":[4,1344,1047,1419]},
  {"key":"big_create","source":"CREATE GAME","korean":"게임 만들기","family":"red_big","original_bbox":[17,1517,1243,1662]},
  {"key":"big_quick","source":"QUICK GAME","korean":"빠른 게임","family":"red_big","original_bbox":[17,1695,1086,1849]},
  {"key":"big_custom","source":"CUSTOM GAME","korean":"커스텀 게임","family":"red_big","original_bbox":[15,1894,1260,2040]}
]
allowed=np.zeros(alpha.shape,dtype=bool)
for r in defs:
    x0,y0,x1,y1=r["original_bbox"]
    allowed[y0:y1,x0:x1]=True
changed_plate=np.any(sa!=ca,axis=2)
source_text_mask=np.logical_and(changed_plate,alpha)
outside_plate=int(np.logical_and(changed_plate,~allowed).sum())
plate_unchanged_source=int(np.logical_and(alpha,np.logical_and(allowed,~changed_plate)).sum())
plate_alpha_residue=int(np.logical_and(ca[:,:,3]>0,np.logical_and(source_text_mask,allowed)).sum())
if outside_plate or plate_alpha_residue:
    raise RuntimeError(("PLATE_ONLY failure",outside_plate,plate_alpha_residue))
# A94 authored clean may include overlapping bbox windows; don't assume every
# transparent pixel was English. Confirm all truly removed opaque source pixels.
removed_alpha=int(np.logical_and(source_text_mask,ca[:,:,3]==0).sum())
if removed_alpha<=5000: raise RuntimeError(("no validated source removal",removed_alpha))
protected=np.logical_and(alpha,~source_text_mask)
FONT=ensure_font()
def source_face(r):
    x0,y0,x1,y1=r["original_bbox"]
    aa=sa[y0:y1,x0:x1].reshape(-1,4)
    pix=aa[aa[:,3]>=220]
    if r["family"]=="red_big":
        pix=pix[(pix[:,0]>pix[:,1]*1.7)&(pix[:,0]>pix[:,2]*1.7)]
    if len(pix)<30: raise RuntimeError(("source color insufficient",r["key"],len(pix)))
    rr=np.median(pix[:,:3],axis=0).astype(int)
    if r["family"]=="red_big" and not (rr[0]>rr[1]*1.7 and rr[0]>rr[2]*1.7):
        raise RuntimeError(("not original red",r["key"],rr.tolist()))
    return tuple(int(v) for v in rr)+(255,)
def glyph_crop(text,size,color):
    font=ImageFont.truetype(FONT,size,index=1)
    temp=Image.new("RGBA",(3000,500),(0,0,0,0))
    ImageDraw.Draw(temp).text((30,50),text,font=font,fill=color,stroke_width=0)
    bb=temp.getchannel("A").getbbox()
    if not bb or min(bb[0],bb[1],temp.width-bb[2],temp.height-bb[3])<3:
        raise RuntimeError(("clipped glyph temp",text,size,bb))
    return temp.crop(bb)
final=clean.copy()
render_masks=[]
rows=[]
for r in defs:
    x0,y0,x1,y1=r["original_bbox"]; sw=x1-x0; shh=y1-y0
    fill=source_face(r)
    # One pure native Korean glyph face: no glow, stroke, offset shadow,
    # semitransparent text-crop rectangle or arbitrary width stretch.
    nominal={"gray_title":60,"gray_help":78,"red_big":146}[r["family"]]
    size=None
    for pt in range(nominal,34,-1):
        crop=glyph_crop(r["korean"],pt,fill)
        if crop.width<=sw-4 and crop.height<=shh-4:
            size=pt
            break
    if size is None: raise RuntimeError(("source bbox too small",r["key"]))
    crop=glyph_crop(r["korean"],size,fill)
    px=x0+2; py=y0+(shh-crop.height)//2
    if px+crop.width>=x1 or py<=y0 or py+crop.height>=y1:
        raise RuntimeError(("glyph boundary",r["key"],(px,py),crop.size))
    layer=Image.new("RGBA",src.size,(0,0,0,0))
    layer.alpha_composite(crop,(px,py))
    gm=np.asarray(layer.getchannel("A"))>0
    if int(np.logical_and(gm,protected).sum()):
        raise RuntimeError(("protected overlap",r["key"]))
    final.alpha_composite(layer)
    render_masks.append(gm)
    bb=bbox_mask(gm)
    rows.append({
        "key":r["key"],"source":r["source"],"korean":r["korean"],"family":r["family"],
        "original_bbox":r["original_bbox"],"localized_bbox":bb,
        "source_width":sw,"source_height":shh,
        "localized_width":bb[2]-bb[0],"localized_height":bb[3]-bb[1],
        "delta_left":bb[0]-x0,"delta_right":x1-bb[2],"delta_top":bb[1]-y0,"delta_bottom":y1-bb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "font":"NotoSansCJK-Black.ttc index 1","font_size":size,"fill_rgba":list(fill),
        "stroke_width":0,"shadow_offset":0,"effect":"SOURCE_FLAT_FACE_ONLY",
        "alignment":"source-left+2 / native vertical center","render_resolution":"2048x2048"
    })
fa=np.asarray(final)
changed=np.any(sa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(sa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_union=np.zeros_like(alpha)
for m in render_masks: render_union|=m
render_protected=int(np.logical_and(render_union,protected).sum())
residue=int(np.logical_and(source_text_mask,np.logical_and(np.all(fa==sa,axis=2),~render_union)).sum())
# Composite-only: changed CLEAN->FINAL pixels must be inside transparent Korean glyph masks.
composite_diff=np.any(ca!=fa,axis=2)
clean_residue=int(np.logical_and(composite_diff,~render_union).sum())
overlap=[];touch=[]
for i in range(len(render_masks)):
    for j in range(i+1,len(render_masks)):
        a=render_masks[i]; b=render_masks[j]
        ov=int(np.logical_and(a,b).sum())
        if ov: overlap.append([i,j,ov])
        dil=np.zeros_like(a)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ys=slice(max(0,dy),a.shape[0]+min(0,dy))
                xs=slice(max(0,dx),a.shape[1]+min(0,dx))
                sy=slice(max(0,-dy),a.shape[0]-max(0,dy))
                sx=slice(max(0,-dx),a.shape[1]-max(0,dx))
                dil[ys,xs]|=a[sy,sx]
        n=int(np.logical_and(dil,b).sum())
        if n: touch.append([i,j,n])
if any((outside,alpha_out,protected_changed,render_protected,residue,clean_residue)) or overlap or touch:
    raise RuntimeError(("stage8 or 1px QA failed",outside,alpha_out,protected_changed,render_protected,residue,clean_residue,overlap,touch))
new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("persisted DDS roundtrip failure")
# Evidence.
src.save(out/"A195_SOURCE_READABLE.png")
clean.save(out/"A195_CLEAN_PLATE.png")
decoded.save(out/"A195_FINAL_READABLE.png")
Image.fromarray((source_text_mask*255).astype(np.uint8),"L").save(out/"A195_SOURCE_TEXT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"A195_PROTECTED_MASK.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"A195_ALLOWED_BBOX_MASK.png")

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
sheet.save(out/"A195_SOURCE_CLEAN_FINAL_CONTACTS.jpg",quality=97)

for label,a,b in [
  ("READABLE",src,decoded),
  ("RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
]:
    aa=composite(a); bb=composite(b)
    sh=Image.new("RGB",(aa.width+bb.width+8,max(aa.height,bb.height)+28),"white")
    ImageDraw.Draw(sh).text((4,4),"SOURCE | FINAL",fill="black")
    sh.paste(aa,(0,28)); sh.paste(bb,(aa.width+8,28)); sh.thumbnail((2600,1800),Image.Resampling.LANCZOS)
    sh.save(out/f"A195_{label}_SOURCE_FINAL.jpg",quality=95)

# Preserve native practical presentation evidence derived from persisted DDS.
for scale in (100,75,50):
    new_w=decoded.width*scale//100;new_h=decoded.height*scale//100
    aa=composite(src).resize((new_w,new_h),Image.Resampling.LANCZOS)
    bb=composite(decoded).resize((new_w,new_h),Image.Resampling.LANCZOS)
    pane=Image.new("RGB",(new_w*2+8,new_h+26),"white")
    ImageDraw.Draw(pane).text((4,4),f"A195 SOURCE / FINAL {scale}%",fill="black")
    pane.paste(aa,(0,26));pane.paste(bb,(new_w+8,26))
    pane.save(out/f"A195_PRACTICAL_{scale}.jpg",quality=95)


report={
 "schema_version":1,"role":"A","run":run,"queue_index":237,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "source_sha256":source_sha,"source_url":source_url},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_clean_provenance":"localization/graphics/role_A/20261006-A-PRODUCTION94-FF514CEB/A94_CLEAN_PLATE.png",
 "source_clean_plate":{"removed_source_opaque_pixels":removed_alpha,"changed_outside_target_bboxes":outside_plate,
 "source_alpha_unchanged_inside_bboxes":plate_unchanged_source,"alpha_residue_under_removed_letters":plate_alpha_residue,
 "gate":"MACHINE_PASS_VISUAL_CONTROLLER_PENDING"},
 "composite_only":{"clean_to_final_outside_glyph_effect_pixels":clean_residue,
 "glyph_effect_method":"native transparent glyph only","gate":"MACHINE_PASS_VISUAL_CONTROLLER_PENDING"},
 "candidate_sha256":new_sha,"candidate_path":str(candidate.relative_to(repo)),
 "localized_physical_rows":len(rows),"rows":rows,
 "machine_qa":{"bbox_size_positive_margin":str(len(rows))+"/"+str(len(rows))+" PASS",
 "changed_pixels":int(changed.sum()),"changed_outside_source_bboxes":outside,
 "alpha_changed_outside_source_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
 "render_protected_overlap_pixels":render_protected,
 "source_exact_residue_pixels":residue,"clean_plate_residue_outside_korean_glyphs":clean_residue,
 "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch,
 "dds_roundtrip":"PASS"},
 "independent_c":"PENDING","C3":"PENDING","visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "RUNTIME_VALIDATION":"UNTESTED","verified_font_path":FONT,
 "supersedes_rejected_sha256":REJECTED_SHA,
 "rework_reason":"C1 q237 rejected invented displaced pink/red bevel and gray edging; rebuilt all nine from verified A94 clean with flat English palette/native Black glyph and zero added shadow/stroke.",
 "status":"A195_WORKER_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_AND_C"
}
(out/"A195_FF514CEB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A195_FF514CEB.json").write_text(json.dumps({
 "run":run,"queue_index":237,"asset":"FF514CEB",
 "candidate_sha256":new_sha,"localized_physical_rows":len(rows),
 "bbox_size_positive_margin":str(len(rows))+"/"+str(len(rows))+" PASS",
 "machine_qa":report["machine_qa"],"worker_status":report["status"],
 "runtime_validation":"UNTESTED","report":str((out/"A195_FF514CEB_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A195_MACHINE_DONE",new_sha,[(r["key"],r["original_bbox"],r["localized_bbox"],r["font_size"]) for r in rows],flush=True)
