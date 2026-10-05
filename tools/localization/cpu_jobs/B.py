#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-INGAME172-IGR010-STAGE-HEART-TALLY"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
clean_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_CLEAN_PLATE.png"
protected_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_PROTECTED_MASK.png"

INPUT_SHA="a2785ce88703b9997b1a80b9e7cc624508463fd62671d3dc920d41d78444785f"
SOURCE_SHA="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
CLEAN_SHA="bc25fc34d95b0d9977ca4af5f8df6c590a654e91f6890f621be18cc6785027ee"
PROTECTED_SHA="0d95f62263989b1e1371bdff67844a42b47db55199d345f452c65aca9008a56e"
STAGE_BB=[455,245,690,350]
OLD_STAGE_BB=[461,249,685,345]
KOREAN="스테이지"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported dds",w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{
      "width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,
      "masks":[hex(x) for x in masks],"raw_mode":mode
    }

def write_dds(header,readable,p,mode):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def font_path(style="Bold"):
    q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",style,q))
    return q

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def sample_palette(src,bb):
    a=np.asarray(src,dtype=np.uint8)
    x0,y0,x1,y1=bb
    q=a[y0:y1,x0:x1,:]
    rgb=q[:,:,:3].reshape(-1,3); al=q[:,:,3].reshape(-1)
    rgb=rgb[al>32]
    if len(rgb)<100: raise RuntimeError("stage source palette too small")
    lum=rgb.mean(axis=1)
    yellow=rgb[(rgb[:,0]>160)&(rgb[:,1]>110)&(rgb[:,2]<140)]
    navy=rgb[(rgb[:,2]>rgb[:,0]*0.8)&(lum<90)]
    pale=rgb[(lum>170)&((rgb.max(axis=1)-rgb.min(axis=1))<95)]
    def med(arr,default):
        return tuple(int(x) for x in (np.median(arr,axis=0) if len(arr) else np.array(default)))+(255,)
    return {
      "face":med(yellow,(250,205,25)),
      "inner":med(navy,(5,15,70)),
      "outer":med(pale,(240,240,235))
    }

def shear_rgba(im,amount):
    if amount<=0: return im
    add=int(round(amount*im.height))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def render_candidate(fontfile,palette,bw,bh,margin=6,shear=0.16):
    for fs in range(76,31,-1):
        f=ImageFont.truetype(fontfile,fs)
        probe=Image.new("RGBA",(700,180),(0,0,0,0))
        d=ImageDraw.Draw(probe)
        tb=d.textbbox((0,0),KOREAN,font=f,stroke_width=5)
        base=Image.new("RGBA",(tb[2]-tb[0]+30,tb[3]-tb[1]+30),(0,0,0,0))
        bd=ImageDraw.Draw(base)
        xy=(15-tb[0],15-tb[1])
        # Source family: pale outer rim, dark navy inner keyline, yellow face.
        bd.text(xy,KOREAN,font=f,fill=palette["face"],stroke_width=5,stroke_fill=palette["outer"])
        bd.text(xy,KOREAN,font=f,fill=palette["face"],stroke_width=3,stroke_fill=palette["inner"])
        gb=base.getchannel("A").getbbox()
        if not gb: continue
        glyph=base.crop(gb)
        glyph=shear_rgba(glyph,shear)
        gb2=glyph.getchannel("A").getbbox()
        if gb2: glyph=glyph.crop(gb2)
        if glyph.width<=bw-2*margin and glyph.height<=bh-2*margin:
            return glyph,fs
    raise RuntimeError("no natural-advance stage fit")

def comp(im,bg=(82,82,82,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

def labeled(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30))
    ImageDraw.Draw(c).text((5,6),label,fill="black")
    return c

if sha(candidate)!=INPUT_SHA: raise RuntimeError(("candidate drift",sha(candidate),INPUT_SHA))
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(source),SOURCE_SHA))
if sha(clean_path)!=CLEAN_SHA: raise RuntimeError(("clean drift",sha(clean_path),CLEAN_SHA))
if sha(protected_path)!=PROTECTED_SHA: raise RuntimeError(("protected drift",sha(protected_path),PROTECTED_SHA))

header,src,meta=load_dds(source)
ch,old,cmeta=load_dds(candidate)
if header!=ch or meta!=cmeta: raise RuntimeError(("structure drift",meta,cmeta))
clean=Image.open(clean_path).convert("RGBA")
protected=np.asarray(Image.open(protected_path).convert("L"))>0
if clean.size!=src.size or protected.shape!=(src.height,src.width): raise RuntimeError("evidence size drift")

x0,y0,x1,y1=STAGE_BB; bw=x1-x0; bh=y1-y0
allowed=np.zeros((src.height,src.width),bool); allowed[y0:y1,x0:x1]=True
if np.logical_and(protected,allowed).sum()!=0:
    raise RuntimeError(("stage bbox intersects protected mask",int(np.logical_and(protected,allowed).sum())))

palette=sample_palette(src,STAGE_BB)
font=font_path("Bold")
glyph,fs=render_candidate(font,palette,bw,bh,margin=6,shear=0.16)

final=old.copy()
# Exact established clean plate only inside Stage source-effect bbox; preserves A85 and all other rows.
final.paste(clean.crop(tuple(STAGE_BB)),(x0,y0))
px=x0+(bw-glyph.width)//2
py=y0+(bh-glyph.height)//2
layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
render=np.asarray(layer.getchannel("A"))>0
final.alpha_composite(layer)
lb=bbox_mask(render)
if lb is None: raise RuntimeError("empty stage render")
if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1):
    raise RuntimeError(("positive margin fail",lb,STAGE_BB))
if lb[2]-lb[0]>bw or lb[3]-lb[1]>bh:
    raise RuntimeError(("size ceiling fail",lb,STAGE_BB))

oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
changed=np.any(oa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
prot_changed=int(np.logical_and(changed,protected).sum())
render_prot=int(np.logical_and(render,protected).sum())
if outside or alpha_out or prot_changed or render_prot:
    raise RuntimeError(("scope fail",outside,alpha_out,prot_changed,render_prot))

new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("dds roundtrip fail")

# Evidence masks.
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"B172_STAGE_EDIT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"B172_PROTECTED_MASK.png")
target_clean=old.copy(); target_clean.paste(clean.crop(tuple(STAGE_BB)),(x0,y0))
target_clean.save(out/"B172_STAGE_CLEAN.png")
decoded.save(out/"B172_FINAL_READABLE.png")

# Visual contacts: source / old squeezed row / clean / new natural-advance row.
pad=28
crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
cards=[
 labeled("SOURCE Stage",src,crop,4),
 labeled("OLD Korean xscale=0.7028",old,crop,4),
 labeled("CLEAN",target_clean,crop,4),
 labeled("B172 natural advance",decoded,crop,4)
]
W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(W,H),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.save(out/"B172_STAGE_SOURCE_OLD_CLEAN_FINAL_4X.jpg",quality=97)

# Family contact includes Ranking / Stage / Rank and right-hand heart tally art.
family_crop=(90,105,4070,1020)
co=labeled("A85 BEFORE",old,family_crop,1)
cn=labeled("B172 AFTER",decoded,family_crop,1)
fam=Image.new("RGB",(max(co.width,cn.width),co.height+cn.height+8),"white")
fam.paste(co,(0,0)); fam.paste(cn,(0,co.height+8)); fam.thumbnail((2200,1300),Image.Resampling.LANCZOS)
fam.save(out/"B172_STAGE_HEART_TALLY_FAMILY_CONTACT.jpg",quality=96)

ro=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_crop=(90,2048-1020,4070,2048-105)
co=labeled("A85 RAW",ro,raw_crop,1); cn=labeled("B172 RAW",rf,raw_crop,1)
raw=Image.new("RGB",(max(co.width,cn.width),co.height+cn.height+8),"white")
raw.paste(co,(0,0)); raw.paste(cn,(0,co.height+8)); raw.thumbnail((2200,1300),Image.Resampling.LANCZOS)
raw.save(out/"B172_RAW_FAMILY_CONTACT.jpg",quality=96)

# Exact preservation outside Stage bbox, including A85 OUTRUN MILES rows and numeric/heart tally art.
stage_changed=int(changed.sum())
report={
 "schema_version":1,
 "role":"B",
 "run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "user_ingame_regression":["IGR-010","스크린샷(153).png"],
 "screen":"STAGE_HEART_TALLY_OVERLAY",
 "owner_lane":"B",
 "priority":"P1",
 "mapping":{
   "status":"EXACT_GRAPHICS_A064_STAGE_PLUS_PROTECTED_TALLY_ART",
   "domain":"GRAPHICS",
   "queue_index":60,
   "asset":rel,
   "localized_binding":{"source":"Stage","korean":KOREAN,"source_effect_bbox":STAGE_BB},
   "protected_screen_components":["stage numeral/player marker sprites","heart icon","x /8 tally glyphs/numerals"],
   "runtime_text_required":False,
   "runtime_table_evidence":"runtime_ko.tsv contains only unrelated stage phrases (IDs 195/381 전체 스테이지, 1123 스테이지 주행, 1133 unlock guidance); no Stage <number> / heart-tally localized runtime row exists.",
   "provenance":"A064 B84 readable atlas visibly contains Ranking/Stage/Rank together with the heart x /8 tally HUD art. The user screenshot regression is therefore the baked Stage sprite plus protected numeric/icon art, not a Korean runtime-overlay string."
 },
 "regression_cause":{
   "producer_origin":"B84",
   "historical_stage_font_size":80,
   "historical_horizontal_scale":0.7028,
   "historical_localized_bbox":OLD_STAGE_BB,
   "later_preservation":"B_RECOVERY02 preserved the row byte-exact; B_RECOVERY09 re-applied it pixel-exact after clean-plate correction; A85 modified OUTRUN MILES only and kept Stage unchanged.",
   "numeric_false_negative":"Prior bbox/overlap static PASS did not catch the in-game compressed/hierarchy/readability defect.",
   "user_screenshot_override":True
 },
 "material_fix":{
   "input_candidate_sha256":INPUT_SHA,
   "candidate_sha256":new_sha,
   "source_sha256":SOURCE_SHA,
   "source_file":str(source.relative_to(repo)),
   "clean_plate":str(clean_path.relative_to(repo)),
   "changed_row":"Stage -> 스테이지",
   "method":"replace only exact Stage source-effect bbox with established clean plate; fresh native-resolution Noto Sans CJK KR Bold render at natural horizontal advance, source-derived yellow/navy/pale family, 0.16 right shear; preserve all other candidate pixels exact",
   "font":"Noto Sans CJK KR Bold",
   "font_size":fs,
   "horizontal_scale":1.0,
   "shear":0.16,
   "palette_rgba":palette,
   "old_localized_bbox":OLD_STAGE_BB,
   "new_localized_bbox":lb,
   "source_size":[bw,bh],
   "new_localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
   "delta_left":lb[0]-x0,
   "delta_right":x1-lb[2],
   "delta_top":lb[1]-y0,
   "delta_bottom":y1-lb[3]
 },
 "static_qa":{
   "containment":"PASS",
   "size_ceiling":"PASS",
   "positive_margin":"PASS",
   "changed_pixels":stage_changed,
   "changed_pixels_outside_stage_bbox":outside,
   "alpha_changed_outside_stage_bbox":alpha_out,
   "protected_changed_pixels":prot_changed,
   "render_protected_overlap_pixels":render_prot,
   "header_128_exact":True,
   "raw_orientation":"mirror_y",
   "all_non_stage_candidate_pixels_preserved_exact":True,
   "a85_outrun_miles_rows_preserved_exact":True,
   "heart_tally_art_preserved_exact":True,
   "status":"PASS"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"B172_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B172_IGR010_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/B172_IGR010.json").write_text(json.dumps({
 "role":"B","run":run,"regression":"IGR-010","queue_index":60,"asset":rel,
 "input_sha256":INPUT_SHA,"candidate_sha256":new_sha,
 "report":str((out/"B172_IGR010_REPORT.json").relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B172_DONE",new_sha,"font_size",fs,"bbox",lb,"palette",palette)
