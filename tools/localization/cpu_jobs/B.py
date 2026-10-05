#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-INGAME165-30CF-TRANSMISSION-MODAL"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
old_sha="6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b"
source_sha="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
source=Path("/tmp/30CF0D_HD.dds"); urllib.request.urlretrieve(source_url,source)

clean_path=repo/"localization/graphics/role_A/20261005-A-PRODUCTION22/30CF0D_HD_CLEAN_PLATE.png"
protected_path=repo/"localization/graphics/role_A/20261005-A-PRODUCTION22/30CF0D_HD_PROTECTED_MASK.png"
clean_sha="b128a8fd82f3ccae6300511c22e63bf40e2938e114b8417aada19bbd49bc9098"
protected_sha="5eacc087baf5c569657611e72f3b8617e390366843f9a5c83ebddb0c000f02ac"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in [(source,source_sha),(candidate,old_sha),(clean_path,clean_sha),(protected_path,protected_sha)]:
    if not Path(p).exists() or sha(p)!=h: raise RuntimeError(("input drift",str(p),sha(p) if Path(p).exists() else None,h))

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if not (w==2048 and h==1024 and pitch==8192 and mips==1 and fourcc==b"\0\0\0\0" and bpp==32 and masks==(0xff0000,0xff00,0xff,0xff000000) and len(b)==128+w*h*4):
        raise RuntimeError(("DDS structure",w,h,pitch,mips,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","BGRA")
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,"masks":[hex(x) for x in masks],"raw_mode":"BGRA"}

def write_dds(header,readable,p):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA")
    Path(p).write_bytes(payload); return hashlib.sha256(payload).hexdigest()

def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def shear(im,s):
    add=int(np.ceil(abs(s)*(im.height-1)))+2
    z=im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-s,s*(im.height-1),0,1,0),resample=Image.Resampling.BICUBIC)
    b=z.getchannel("A").getbbox(); return z.crop(b) if b else z

def font_path():
    q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    return q
FONT=font_path()

header,src,meta=load_dds(source)
oh,old,ometa=load_dds(candidate)
if oh!=header or ometa!=meta: raise RuntimeError("candidate structure drift")
clean=Image.open(clean_path).convert("RGBA")
protected=np.asarray(Image.open(protected_path).convert("L"))>0
if clean.size!=src.size or protected.shape!=(1024,2048): raise RuntimeError("evidence size")

# Screenshot(147) exact mapping:
# visible 변속 방식 선택 / 자동 / 수동 / small 변속 방식 / AT / MT are all 30CF0D baked graphics.
# 788CE557 is therefore not the source of IGR-005; it stays linked to IGR-017.
# Preserve the four MANUAL/AUTOMATIC rows; rework only the two weak/overlong Korean labels.
targets=[
 {"key":"select_transmission","source":"SELECT TRANSMISSION","old":"변속 방식 선택","ko":"변속기 선택","bb":[5,67,868,130],"fs":60,"stroke":3,"slant":0.08,"fill":(250,250,250,255)},
 {"key":"transmission_small","source":"TRANSMISSION","old":"변속 방식","ko":"변속기","bb":[1288,96,1569,128],"fs":31,"stroke":1,"slant":0.04,"fill":(184,184,184,255)}
]
final=old.copy()
for t in targets:
    x0,y0,x1,y1=t["bb"]; final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))

rows=[]; render=np.zeros((1024,2048),bool)
for t in targets:
    x0,y0,x1,y1=t["bb"]; bw=x1-x0; bh=y1-y0
    chosen=None
    for fs in range(t["fs"],15,-1):
        f=ImageFont.truetype(FONT,fs)
        p=Image.new("RGBA",(1200,180),(0,0,0,0)); d=ImageDraw.Draw(p)
        tb=d.textbbox((0,0),t["ko"],font=f,stroke_width=t["stroke"])
        pos=(12-tb[0],12-tb[1])
        d.text(pos,t["ko"],font=f,fill=t["fill"],stroke_width=t["stroke"],stroke_fill=t["fill"])
        g=shear(p,t["slant"]); gb=g.getchannel("A").getbbox()
        if not gb: continue
        g=g.crop(gb)
        if g.width>bw-4 or g.height>bh-4: continue
        px=x0+(bw-g.width)//2; py=y0+(bh-g.height)//2
        gm=np.asarray(g.getchannel("A"))>0
        if np.any(gm & protected[py:py+g.height,px:px+g.width]): continue
        chosen=(g,px,py,fs); break
    if chosen is None: raise RuntimeError(("fit",t["key"]))
    g,px,py,fs=chosen
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py)); final.alpha_composite(layer)
    gm=np.asarray(layer.getchannel("A"))>0; render|=gm; lb=bbox(gm)
    if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("margin",t["key"],lb))
    rows.append({"key":t["key"],"source":t["source"],"old_korean":t["old"],"korean":t["ko"],
                 "original_bbox":t["bb"],"localized_bbox":lb,
                 "source_size":[bw,bh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
                 "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
                 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
                 "font":"Noto Sans CJK KR Black","font_size":fs,"stroke_width":t["stroke"],"slant":t["slant"],"alignment":"center"})

oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
changed=np.any(oa!=fa,axis=2)
allowed=np.zeros((1024,2048),bool)
for t in targets:
    x0,y0,x1,y1=t["bb"]; allowed[y0:y1,x0:x1]=1
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_protected=int(np.logical_and(render,protected).sum())
preserved=[[130,237,268,313],[1263,235,1401,313],[124,150,229,208],[1041,149,1157,214]]
preserved_diffs=[]
for b in preserved:
    x0,y0,x1,y1=b
    preserved_diffs.append(int(np.count_nonzero(np.any(oa[y0:y1,x0:x1]!=fa[y0:y1,x0:x1],axis=2))))
if outside or alpha_out or protected_changed or render_protected or any(preserved_diffs):
    raise RuntimeError(("scope",outside,alpha_out,protected_changed,render_protected,preserved_diffs))

new_sha=write_dds(header,final,candidate)
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox(): raise RuntimeError("roundtrip")

Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"B165_EDIT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"B165_PROTECTED_MASK.png")
tmp=Path("/tmp/b165"); tmp.mkdir(exist_ok=True)
old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),str(old_png),str(final_png),str(out/"B165_EDIT_MASK.png"),
                "--protected-mask",str(out/"B165_PROTECTED_MASK.png"),"--report",str(out/"B165_FINAL_MASK_VALIDATION.json")],check=True)

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def mk(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c

for name,crop in [("TITLE",(0,48,920,140)),("SUBTITLE",(1240,82,1610,138))]:
    cards=[mk(name+"_SOURCE",src,crop,2),mk(name+"_OLD",old,crop,2),mk(name+"_CLEAN",clean,crop,2),mk(name+"_B165",decoded,crop,2)]
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
    sh=Image.new("RGB",(W,H),"white"); yy=0
    for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
    sh.save(out/f"B165_{name}_SOURCE_OLD_CLEAN_FINAL_2X.jpg",quality=97)

for fn,a,b in [("B165_FULL_OLD_FINAL.jpg",old,decoded),("B165_RAW_OLD_FINAL.jpg",old.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]:
    ca=mk("OLD",a,(0,0,2048,1024)); cb=mk("B165_FINAL",b,(0,0,2048,1024))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white"); sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0))
    sh.thumbnail((2200,1200),Image.Resampling.LANCZOS); sh.save(out/fn,quality=94)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":137,"owner_lane":"B",
 "user_ingame_regression":["IGR-005","스크린샷(147).png"],
 "mapping":{"status":"EXACT_HIGH_CONFIDENCE_GRAPHICS","prior_suspected_queue_index":106,
   "prior_suspected_asset":"textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds",
   "exact_queue_index":137,"exact_asset":asset,
   "screenshot_visible_binding":["변속 방식 선택=SELECT TRANSMISSION","자동/수동=AUTOMATIC/MANUAL","small 변속 방식=TRANSMISSION","AT/MT badges=protected same-atlas artwork"],
   "conclusion":"All visible IGR-005 modal text/art is accounted for by 30CF0D baked graphics; runtime text is not needed for this visible defect. 788CE557 remains IGR-017 only."},
 "source_sha256":source_sha,"superseded_candidate_sha256":old_sha,"candidate_sha256":new_sha,
 "candidate_path":str(candidate.relative_to(repo)),
 "readiness_tier":"P0_MAPPING_RESOLVED_TO_RENDER_READY_AND_REWORKED_SAME_INVOCATION",
 "method":"Screenshot-to-atlas exact mapping; preserve MANUAL/AUTOMATIC x4 candidate pixels exact; restore validated A22 clean plate under title/subtitle; shorten overlong Korean 변속 방식 선택/변속 방식 to 변속기 선택/변속기 for readability and hierarchy; native Black render with source-relative slant; exact-header BGRA DDS.",
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "scope_qa":{"changed_pixels":int(changed.sum()),"changed_outside_target_bboxes":outside,"alpha_outside_target_bboxes":alpha_out,
   "protected_changed_pixels":protected_changed,"render_protected_overlap_pixels":render_protected,
   "manual_automatic_rows_changed_pixels":preserved_diffs,"status":"PASS"},
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"B165_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B165_30CF0D_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(out/"B165_STATIC_VALIDATION_SUMMARY.json").write_text(json.dumps({
 "source_sha256":source_sha,"candidate_sha256":new_sha,"mapping":"IGR-005_EXACT_TO_30CF0D_GRAPHICS",
 "rows":rows,"changed_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
 "render_protected_overlap":render_protected,"manual_automatic_rows_changed_pixels":preserved_diffs,
 "header_128_exact":True,"raw_orientation":"mirror_y","status":"PASS"
},ensure_ascii=False,indent=2)+"\n")
print("B165_DONE",new_sha,[(r["key"],r["localized_bbox"],r["font_size"]) for r in rows])
