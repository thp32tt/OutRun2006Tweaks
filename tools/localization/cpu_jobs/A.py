#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION94-FF514CEB"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds"
source_sha="570fff6b71962f56b2f3d09993191a18989a80420b1963c4cccd1620b192907a"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not dds")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4: raise RuntimeError(("unsupported",w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    elif masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,"masks":[hex(x) for x in masks],"raw_mode":mode}
def write_dds(h,im,p,mode):
    payload=h+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode); Path(p).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def bbox_mask(m):
    ys,xs=np.nonzero(m); return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font_path():
    q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",q))
    return q
def comp(im):
    bg=Image.new("RGBA",im.size,(240,240,240,255)); bg.alpha_composite(im); return bg.convert("RGB")

srcp=Path("/tmp/a94_ff_source.dds"); urllib.request.urlretrieve(source_url,srcp)
if sha(srcp)!=source_sha: raise RuntimeError(("source drift",sha(srcp)))
header,src,meta=load_dds(srcp)
if (meta["width"],meta["height"],meta["raw_mode"])!=(2048,2048,"BGRA"): raise RuntimeError(("structure",meta))
sa=np.asarray(src); alpha=sa[:,:,3]>0

defs=[
 ("small_create","CREATE GAME","게임 만들기","gray_title",[0,740,570,855]),
 ("small_custom","CUSTOM GAME","커스텀 게임","gray_title",[0,840,570,940]),
 ("small_quick","QUICK GAME","빠른 게임","gray_title",[0,935,570,1030]),
 ("help_create","Create a game and invite your friends!","게임을 만들고 친구를 초대하세요!","gray_help",[0,1015,1200,1120]),
 ("help_custom","Specify what gametype you'd like to play!","플레이할 게임 유형을 설정하세요!","gray_help",[0,1175,1320,1280]),
 ("help_quick","Jump into a quick game of OutRun!","빠른 아웃런 게임에 참가하세요!","gray_help",[0,1335,1100,1440]),
 ("big_create","CREATE GAME","게임 만들기","red_big",[0,1490,1320,1680]),
 ("big_quick","QUICK GAME","빠른 게임","red_big",[0,1670,1150,1865]),
 ("big_custom","CUSTOM GAME","커스텀 게임","red_big",[0,1870,1335,2048]),
]
rows0=[]
for key,source,korean,family,window in defs:
    x0,y0,x1,y1=window; m=np.zeros_like(alpha); m[y0:y1,x0:x1]=alpha[y0:y1,x0:x1]
    bb=bbox_mask(m)
    if not bb: raise RuntimeError(("missing",key))
    rows0.append({"key":key,"source":source,"korean":korean,"family":family,"window":window,"original_bbox":bb,"source_mask":m})

# Non-target artwork/tokens remain protected by the global source-visible mask outside exact target windows.

source_mask=np.zeros_like(alpha)
for r in rows0: source_mask|=r["source_mask"]
protected=np.logical_and(alpha,~source_mask)
clean_a=sa.copy(); clean_a[source_mask]=0; clean=Image.fromarray(clean_a,"RGBA")
FONT=font_path()

def colors(r):
    vis=sa[r["source_mask"]]; vis=vis[vis[:,3]>0]
    lum=vis[:,:3].mean(axis=1)
    if r["family"]=="red_big":
        sel=(vis[:,0]>vis[:,1]*1.8)&(vis[:,0]>vis[:,2]*1.5)&(vis[:,3]>100)
        main=vis[sel]; shadow=vis[~sel]
    else:
        cut=np.percentile(lum,55); main=vis[(lum>=cut)&(vis[:,3]>80)]; shadow=vis[lum<cut]
    if len(main)<10: main=vis[vis[:,3]>128]
    if len(shadow)<10: shadow=vis
    f=np.median(main,axis=0).astype(int); s=np.median(shadow,axis=0).astype(int)
    return (int(f[0]),int(f[1]),int(f[2]),255),(int(s[0]),int(s[1]),int(s[2]),max(120,min(230,int(s[3]))))

def render(text,size,fill,shadow,family):
    font=ImageFont.truetype(FONT,size,index=1); pad=max(20,size//2)
    off=max(2,round(size*(0.05 if family!="gray_help" else 0.045))); stroke=max(1,round(size*0.018))
    im=Image.new("RGBA",(2600,440),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((pad+off,pad+off),text,font=font,fill=shadow,stroke_width=stroke,stroke_fill=shadow)
    d.text((pad,pad),text,font=font,fill=fill,stroke_width=stroke,stroke_fill=shadow)
    bb=im.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty",text))
    return im.crop(bb),{"font_size":size,"shadow_offset":off,"stroke_width":stroke}

# Preserve shared source-family cadence per family by choosing a common font size.
family_size={}
for fam in ["gray_title","gray_help","red_big"]:
    grp=[r for r in rows0 if r["family"]==fam]
    start=min(150,max(20,min(r["original_bbox"][3]-r["original_bbox"][1] for r in grp)-4))
    chosen=None
    for size in range(start,17,-1):
        ok=True
        for r in grp:
            f,s=colors(r); g,_=render(r["korean"],size,f,s,fam)
            x0,y0,x1,y1=r["original_bbox"]
            if g.width>x1-x0-4 or g.height>y1-y0-4: ok=False; break
        if ok: chosen=size; break
    if chosen is None: raise RuntimeError(("no shared fit",fam))
    family_size[fam]=chosen

final=clean.copy(); allowed=np.zeros_like(alpha); render_masks=[]; rows=[]
for r in rows0:
    x0,y0,x1,y1=r["original_bbox"]; sw=x1-x0; shh=y1-y0; allowed[y0:y1,x0:x1]=1
    fill,shadow=colors(r); g,sty=render(r["korean"],family_size[r["family"]],fill,shadow,r["family"])
    px=x0+2; py=y0+(shh-g.height)//2
    if px+g.width>=x1 or py<=y0 or py+g.height>=y1: raise RuntimeError(("margin",r["key"],g.size,r["original_bbox"],(px,py)))
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py)); gm=np.asarray(layer.getchannel("A"))>0
    if int(np.logical_and(gm,protected).sum()): raise RuntimeError(("protected overlap",r["key"]))
    final.alpha_composite(layer); render_masks.append(gm); lb=bbox_mask(gm)
    rows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"family":r["family"],
      "original_bbox":r["original_bbox"],"localized_bbox":lb,"source_width":sw,"source_height":shh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Black","font_size":family_size[r["family"]],"fill_rgba":list(fill),"shadow_rgba":list(shadow),
      **sty,"alignment":"source-left+2 / vertical-center","render_resolution":"native_2048x2048"})

fa=np.asarray(final); ca=np.asarray(clean); changed=np.any(sa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum()); alpha_out=int(np.logical_and(sa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_union=np.zeros_like(alpha)
for m in render_masks: render_union|=m
render_protected=int(np.logical_and(render_union,protected).sum())
residue=int(np.logical_and(source_mask,np.logical_and(np.all(fa==sa,axis=2),~render_union)).sum())
clean_residue=0
for r,m in zip(rows,render_masks):
    x0,y0,x1,y1=r["original_bbox"]; diff=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    clean_residue+=int(np.logical_and(diff,~m[y0:y1,x0:x1]).sum())
overlap=[]; touch=[]
for i in range(len(render_masks)):
  for j in range(i+1,len(render_masks)):
    a=render_masks[i]; b=render_masks[j]; ov=int(np.logical_and(a,b).sum())
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

new_sha=write_dds(header,final,candidate,meta["raw_mode"]); dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox(): raise RuntimeError("roundtrip")

src.save(out/"A94_SOURCE_READABLE.png"); clean.save(out/"A94_CLEAN_PLATE.png"); decoded.save(out/"A94_FINAL_READABLE.png")
Image.fromarray((source_mask*255).astype(np.uint8),"L").save(out/"A94_SOURCE_TEXT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"A94_PROTECTED_MASK.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"A94_ALLOWED_BBOX_MASK.png")
cards=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; pad=10; crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ps=[comp(x).crop(crop) for x in (src,clean,decoded)]; W=max(p.width for p in ps); H=max(p.height for p in ps)
    c=Image.new("RGB",(W*3+16,H+28),"white"); d=ImageDraw.Draw(c); d.text((4,4),r["key"]+" | SOURCE | CLEAN | FINAL",fill="black")
    for k,p in enumerate(ps): c.paste(p,(k*(W+8),28))
    cards.append(c)
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)+5*(len(cards)-1); sheet=Image.new("RGB",(cw,ch),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+5
sheet.thumbnail((3200,5200),Image.Resampling.LANCZOS); sheet.save(out/"A94_SOURCE_CLEAN_FINAL_CONTACTS.jpg",quality=97)
for label,a,b in [("READABLE",src,decoded),("RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]:
    aa=comp(a); bb=comp(b); sh=Image.new("RGB",(aa.width+bb.width+8,max(aa.height,bb.height)+28),"white")
    ImageDraw.Draw(sh).text((4,4),"SOURCE | FINAL",fill="black"); sh.paste(aa,(0,28)); sh.paste(bb,(aa.width+8,28))
    sh.thumbnail((2600,2600),Image.Resampling.LANCZOS); sh.save(out/f"A94_{label}_SOURCE_FINAL.jpg",quality=95)

report={"schema_version":1,"role":"A","run":run,"queue_index":237,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","source_sha256":source_sha,"source_url":source_url},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "candidate_sha256":new_sha,"candidate_path":str(candidate.relative_to(repo)),
 "conceptual_segments":6,"localized_physical_rows":9,"shared_family_font_sizes":family_size,"protected_unrelated_token":"K1/right-side cluster pixel exact",
 "rows":rows,
 "machine_qa":{"bbox_size_positive_margin":"9/9 PASS","changed_pixels":int(changed.sum()),"changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,"protected_changed_pixels":protected_changed,"render_protected_overlap_pixels":render_protected,
   "source_exact_residue_pixels":residue,"clean_plate_residue_outside_korean_glyphs":clean_residue,
   "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch,"dds_roundtrip":"PASS"},
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","status":"A94_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"A94_FF514CEB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A94_FF514CEB.json").write_text(json.dumps({"run":run,"queue_index":237,"asset":"FF514CEB","candidate_sha256":new_sha,
 "localized_physical_rows":9,"bbox_size_positive_margin":"9/9 PASS","machine_qa":report["machine_qa"],"worker_status":report["status"],
 "runtime_validation":"UNTESTED","report":str((out/"A94_FF514CEB_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n")
print("A94_DONE",new_sha,family_size)
