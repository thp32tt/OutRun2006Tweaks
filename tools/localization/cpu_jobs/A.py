#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261008-A193-Q225-NATIVE-BLACK-FAMILY"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/E3C455FA_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E3C455FA_512x256.dds"
source_sha="a0c8c67f88dfdc93385b821452f0175a6a951c238f5f3d8b012afa113ef37fc9"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not dds")
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
def write_dds(h,im,p,mode):
    payload=h+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    Path(p).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font_path():
    # A95R was textually labeled 'Black' but may have selected a Regular TTC
    # when the Black file was not installed. Never silently accept a fallback.
    import glob
    candidates=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not candidates:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
        candidates=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not candidates: raise RuntimeError("true Noto Sans CJK Black TTC unavailable (no Regular fallback)")
    return candidates[0]


# Fail closed: C1 already rejected this exact persisted candidate SHA.
OLD_REJECTED_SHA="37b8236f06fcec8c8c64c1076f9bf0f3c8c56ea3638b8a4582a513a40bbcb18d"
if not candidate.is_file() or sha(candidate)!=OLD_REJECTED_SHA:
    raise RuntimeError("q225 candidate SHA moved since source-family rejection; abort stale role A job")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","225","--require-safe-rerender"],capture_output=True,text=True)
print("A193 triage",triage.stdout,flush=True)
if triage.returncode!=0 or "MATERIAL_REWORK" not in triage.stdout:
    raise RuntimeError(("q225 triage blocked",triage.returncode,triage.stdout,triage.stderr))

srcp=Path("/tmp/a193_source.dds"); urllib.request.urlretrieve(source_url,srcp)
if sha(srcp)!=source_sha: raise RuntimeError(("source drift",sha(srcp)))
header,src,meta=load_dds(srcp)
if (meta["width"],meta["height"],meta["raw_mode"])!=(2048,1024,"RGBA"):
    raise RuntimeError(("structure",meta))
sa=np.asarray(src); alpha=sa[:,:,3]>0
lab,n=ndimage.label(alpha); objs=ndimage.find_objects(lab)
components=[]
for i,sl in enumerate(objs,1):
    if sl is None: continue
    y,x=sl; area=int((lab[sl]==i).sum())
    components.append((i,area,(.5*(x.start+x.stop),.5*(y.start+y.stop))))

rows=[
 {"key":"game_lobby","source":"GAME LOBBY","korean":"게임 로비","family":"dark_big","window":[0,0,600,100],"method":"component","cap":5000},
 {"key":"game_list","source":"GAME LIST","korean":"게임 목록","family":"dark_big","window":[930,100,1420,230],"method":"component","cap":5000},
 {"key":"setup","source":"SETUP","korean":"설정","family":"white_big","window":[940,490,1260,580],"method":"component","cap":5000},
 {"key":"course_type","source":"COURSE TYPE","korean":"코스 유형","family":"dark_small","window":[920,690,1320,755],"method":"rgb","rgb":[66,70,71]},
 {"key":"course","source":"COURSE","korean":"코스","family":"dark_small","window":[920,755,1200,810],"method":"rgb","rgb":[66,70,71]},
 {"key":"car_type","source":"CAR TYPE","korean":"차량 유형","family":"dark_small","window":[920,805,1230,860],"method":"rgb","rgb":[66,70,71]},
 {"key":"catch_up","source":"CATCH-UP","korean":"추격 보정","family":"dark_small","window":[920,860,1250,915],"method":"rgb","rgb":[66,70,71]},
 {"key":"collision","source":"COLLISION","korean":"충돌","family":"dark_small","window":[920,915,1250,965],"method":"rgb","rgb":[66,70,71]},
 {"key":"players","source":"PLAYERS","korean":"플레이어","family":"dark_small","window":[920,965,1200,1020],"method":"rgb","rgb":[66,70,71]},
]
for r in rows:
    x0,y0,x1,y1=r["window"]
    if r["method"]=="component":
        ids=[i for i,area,(cx,cy) in components if area<=r["cap"] and x0<=cx<x1 and y0<=cy<y1]
        m=np.isin(lab,ids); r["component_ids"]=ids
    else:
        target=np.array(r["rgb"],dtype=np.int16)
        sub=sa[y0:y1,x0:x1]
        d=np.max(np.abs(sub[:,:,:3].astype(np.int16)-target),axis=2)
        local=(d==0)&(sub[:,:,3]>0)
        m=np.zeros_like(alpha); m[y0:y1,x0:x1]=local
        r["rgb_exact_source_pixels"]=int(local.sum())
    bb=bbox_mask(m)
    if not bb: raise RuntimeError(("missing source row",r["key"]))
    r["source_mask"]=m; r["original_bbox"]=bb

# Explicit controller-found defect guard: each small row must include the leading source glyph at x=960.
for r in rows:
    if r["family"]=="dark_small" and r["original_bbox"][0]!=960:
        raise RuntimeError(("leading glyph not captured",r["key"],r["original_bbox"]))

source_mask=np.zeros_like(alpha)
for r in rows: source_mask|=r["source_mask"]
protected=alpha&~source_mask
clean_arr=sa.copy(); clean_arr[source_mask]=0
clean=Image.fromarray(clean_arr,"RGBA")
FONT=font_path()

def main_color(r):
    px=sa[r["source_mask"]]; px=px[px[:,3]>160]
    if len(px)<10: px=sa[r["source_mask"]]
    med=np.median(px[:,:3],axis=0).astype(int)
    return (int(med[0]),int(med[1]),int(med[2]),255)
def render(text,size,fill):
    f=ImageFont.truetype(FONT,size,index=1)
    pad=max(16,size//3); im=Image.new("RGBA",(2200,360),(0,0,0,0))
    ImageDraw.Draw(im).text((pad,pad),text,font=f,fill=fill)
    bb=im.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty render",text))
    return im.crop(bb)

fam_size={}
for fam in ["dark_big","white_big","dark_small"]:
    grp=[r for r in rows if r["family"]==fam]
    start=min(90,max(18,min(r["original_bbox"][3]-r["original_bbox"][1] for r in grp)-3))
    chosen=None
    for size in range(start,15,-1):
        ok=True
        for r in grp:
            g=render(r["korean"],size,main_color(r)); x0,y0,x1,y1=r["original_bbox"]
            if g.width>x1-x0-4 or g.height>y1-y0-4: ok=False; break
        if ok: chosen=size; break
    if chosen is None: raise RuntimeError(("family fit",fam))
    fam_size[fam]=chosen

final=clean.copy(); allowed=np.zeros_like(alpha); render_masks=[]; rows_out=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; sw=x1-x0; sh=y1-y0; allowed[y0:y1,x0:x1]=1
    fill=main_color(r); size=fam_size[r["family"]]; g=render(r["korean"],size,fill)
    px=x0+2; py=y0+(sh-g.height)//2
    if px+g.width>=x1 or py<=y0 or py+g.height>=y1:
        raise RuntimeError(("positive margin",r["key"],g.size,r["original_bbox"],(px,py)))
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py))
    gm=np.asarray(layer.getchannel("A"))>0
    if int((gm&protected).sum()): raise RuntimeError(("protected overlap",r["key"]))
    final.alpha_composite(layer); render_masks.append(gm); lb=bbox_mask(gm)
    rows_out.append({
      "key":r["key"],"source":r["source"],"korean":r["korean"],"family":r["family"],
      "mask_method":r["method"],"original_bbox":r["original_bbox"],"localized_bbox":lb,
      "source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"NotoSansCJK-Black.ttc / KR face index=1","font_size":size,"fill_rgba":list(fill),
      "alignment":"source-left+2 / vertical-center","render_resolution":"native_2048x1024"
    })

fa=np.asarray(final); ca=np.asarray(clean); changed=np.any(sa!=fa,axis=2)
outside=int((changed&~allowed).sum())
alpha_out=int(((sa[:,:,3]!=fa[:,:,3])&~allowed).sum())
protected_changed=int((changed&protected).sum())
ru=np.zeros_like(alpha)
for m in render_masks: ru|=m
render_protected=int((ru&protected).sum())
source_residue=int((source_mask&np.all(fa==sa,axis=2)&~ru).sum())
clean_residue=0
for r,m in zip(rows_out,render_masks):
    x0,y0,x1,y1=r["original_bbox"]
    diff=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    clean_residue+=int((diff&~m[y0:y1,x0:x1]).sum())
# Strong regression gate for the six small rows: no original exact RGB family may survive outside new Korean glyphs.
small_source_family_residue=0
for source_r,out_r,gm in zip(rows,rows_out,render_masks):
    if source_r["family"]!="dark_small": continue
    x0,y0,x1,y1=source_r["window"]; target=np.array([66,70,71],dtype=np.int16)
    sub=fa[y0:y1,x0:x1]; exact=np.all(sub[:,:,:3].astype(np.int16)==target,axis=2)&(sub[:,:,3]>0)
    local_render=gm[y0:y1,x0:x1]
    small_source_family_residue+=int((exact&~local_render).sum())
overlap=[]; touch=[]
for i in range(len(render_masks)):
    for j in range(i+1,len(render_masks)):
        ov=int((render_masks[i]&render_masks[j]).sum())
        if ov: overlap.append([i,j,ov])
        t=int((ndimage.binary_dilation(render_masks[i],structure=np.ones((3,3),bool))&render_masks[j]).sum())
        if t: touch.append([i,j,t])
if any([outside,alpha_out,protected_changed,render_protected,source_residue,clean_residue,small_source_family_residue]) or overlap or touch:
    raise RuntimeError(("QA",outside,alpha_out,protected_changed,render_protected,source_residue,clean_residue,small_source_family_residue,overlap,touch))

new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("DDS roundtrip")

src.save(out/"A193_SOURCE_READABLE.png"); clean.save(out/"A193_CLEAN_PLATE.png"); decoded.save(out/"A193_FINAL_READABLE.png")
Image.fromarray((source_mask*255).astype(np.uint8),"L").save(out/"A193_SOURCE_TEXT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"A193_PROTECTED_MASK.png")
cards=[]
for r in rows_out:
    x0,y0,x1,y1=r["original_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    panels=[]
    for im in (src,clean,decoded):
        bg=Image.new("RGBA",im.size,(240,240,240,255)); bg.alpha_composite(im); panels.append(bg.convert("RGB").crop(crop))
    W=max(p.width for p in panels); H=max(p.height for p in panels)
    card=Image.new("RGB",(W*3+16,H+26),"white"); d=ImageDraw.Draw(card); d.text((4,3),r["key"]+" | SOURCE | CLEAN | FINAL",fill="black")
    for k,p in enumerate(panels): card.paste(p,(k*(W+8),26))
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)+4*(len(cards)-1)
sheet=Image.new("RGB",(cw,ch),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((3400,5000),Image.Resampling.LANCZOS); sheet.save(out/"A193_SOURCE_CLEAN_FINAL_CONTACTS.jpg",quality=97)
def comp(im):
    bg=Image.new("RGBA",im.size,(240,240,240,255)); bg.alpha_composite(im); return bg.convert("RGB")
for label,a,b in [("READABLE",src,decoded),("RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]:
    aa=comp(a); bb=comp(b); sh=Image.new("RGB",(aa.width+bb.width+8,max(aa.height,bb.height)+28),"white")
    ImageDraw.Draw(sh).text((4,4),"SOURCE | FINAL",fill="black"); sh.paste(aa,(0,28)); sh.paste(bb,(aa.width+8,28))
    sh.thumbnail((3000,1900),Image.Resampling.LANCZOS); sh.save(out/f"A193_{label}_SOURCE_FINAL.jpg",quality=95)

 
# Post-encode native practical-scale review evidence, not claim of source-family PASS.
for scale in (100,75,50):
    w=max(1,decoded.width*scale//100); h=max(1,decoded.height*scale//100)
    source_v=comp(src).resize((w,h),Image.Resampling.LANCZOS)
    final_v=comp(decoded).resize((w,h),Image.Resampling.LANCZOS)
    sh=Image.new("RGB",(w*2+8,h+26),"white")
    ImageDraw.Draw(sh).text((4,4),f"A193 native persisted DDS SOURCE / FINAL {scale}%",fill="black")
    sh.paste(source_v,(0,26));sh.paste(final_v,(w+8,26))
    sh.save(out/f"A193_PRACTICAL_{scale}.jpg",quality=93)

qa={
 "bbox_size_positive_margin":"9/9 PASS","changed_pixels":int(changed.sum()),
 "changed_outside_source_bboxes":outside,"alpha_changed_outside_source_bboxes":alpha_out,
 "protected_changed_pixels":protected_changed,"render_protected_overlap_pixels":render_protected,
 "source_exact_residue_pixels":source_residue,"clean_plate_residue_outside_korean_glyphs":clean_residue,
 "small_row_source_rgb_residue_outside_korean_glyphs":small_source_family_residue,
 "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch,"dds_roundtrip":"PASS",
 "controller_defect_regression_guard":"ALL_6_SMALL_ROWS_CAPTURE_LEADING_SOURCE_GLYPH_AT_X960","black_font_path":str(FONT),"black_font_file_required":True
}
report={
 "schema_version":1,"role":"A","run":run,"queue_index":225,"asset":asset_rel,
 "supersedes_candidate_sha256":OLD_REJECTED_SHA,
 "rework_reason":"A95 controller visual QA found leading Latin source-glyph fragments on six small lobby labels because connected-component masking joined the first glyph to adjacent UI; A193 uses exact source RGB isolation for those rows.",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","source_sha256":source_sha,"source_url":source_url},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "candidate_sha256":new_sha,"candidate_path":str(candidate.relative_to(repo)),
 "font_file_verified":str(FONT),"font_method":"explicit NotoSansCJK-Black.ttc index=1, no Regular fallback",
 "conceptual_segments":9,"localized_physical_rows":9,"shared_family_font_sizes":fam_size,
 "rows":rows_out,"machine_qa":qa,"visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED","status":"A193_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A193_E3C455FA_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A193_E3C455FA.json").write_text(json.dumps({
 "run":run,"queue_index":225,"asset":"E3C455FA","candidate_sha256":new_sha,
 "supersedes_candidate_sha256":report["supersedes_candidate_sha256"],
 "localized_physical_rows":9,"machine_qa":qa,"worker_status":report["status"],
 "runtime_validation":"UNTESTED","report":str((out/"A193_E3C455FA_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A193_DONE",new_sha,fam_size,[r["original_bbox"] for r in rows_out[3:]])
