#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-INGAME90-IGR013-BRACKET-STAGE"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/6DC89C6E_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
old_sha="b406580d029118f5a3aa7de689389699dcb2cd0e4824c4f8d8c9075f0d9e4c26"
source_sha="2c08a6fc224d2263f8c7d4e97d1bd8cfe2fad060688ef5665f78791449510cb3"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/6DC89C6E_512x512.dds"
prior_report=repo/"localization/graphics/role_A/20261005-A-PRODUCTION62/A62_6DC89C6E_REPORT.json"
clean_path=repo/"localization/graphics/role_A/20261005-A-PRODUCTION62/A62_CLEAN_PLATE.png"
protected_path=repo/"localization/graphics/role_A/20261005-A-PRODUCTION62/A62_PROTECTED_VISIBLE_MASK.png"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{"width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,
      "masks":[hex(x) for x in masks],"raw_mode":mode}

def write_dds(header,readable,p,mode):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def font_path():
    q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",q))
    return q

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def comp(im,bg=(245,245,245,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

def make_contact(label,src,old,clean,final,bb,scale=3):
    x0,y0,x1,y1=bb; pad=18
    crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    cards=[]
    for name,im in [("SOURCE",src),("OLD_LOWRES4X",old),("CLEAN",clean),("A90_NATIVE",final)]:
        v=comp(im).crop(crop)
        if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
        c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26))
        ImageDraw.Draw(c).text((5,4),label+" "+name,fill="black")
        cards.append(c)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
    sh=Image.new("RGB",(W,H),"white"); yy=0
    for c in cards:
        sh.paste(c,(0,yy)); yy+=c.height+8
    return sh

if not candidate.exists() or sha(candidate)!=old_sha:
    raise RuntimeError(("candidate drift",sha(candidate) if candidate.exists() else None))
prior=json.loads(prior_report.read_text(encoding="utf-8"))
if prior.get("candidate_sha256")!=old_sha: raise RuntimeError("prior report drift")
if prior.get("index")!=173 or len(prior.get("rows",[]))!=21: raise RuntimeError("prior row binding drift")

source=Path("/tmp/a90_6dc_source.dds")
urllib.request.urlretrieve(source_url,source)
if sha(source)!=source_sha: raise RuntimeError(("source drift",sha(source)))
header,src,meta=load_dds(source)
oh,old,ometa=load_dds(candidate)
if header!=oh or meta!=ometa: raise RuntimeError(("structure drift",meta,ometa))
if (meta["width"],meta["height"],meta["raw_mode"])!=(2048,2048,"BGRA"):
    raise RuntimeError(("unexpected structure",meta))

clean=Image.open(clean_path).convert("RGBA")
protected=np.asarray(Image.open(protected_path).convert("L"))>0
if clean.size!=src.size or protected.shape!=(src.height,src.width):
    raise RuntimeError("evidence size drift")

FONT=font_path()
font=ImageFont.truetype(FONT,71,index=1)
final=old.copy()
allowed=np.zeros((src.height,src.width),bool)
render_masks=[]
rows=[]
for r in prior["rows"]:
    x0,y0,x1,y1=[int(v) for v in r["original_bbox"]]
    sw=x1-x0; sh=y1-y0
    allowed[y0:y1,x0:x1]=1
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    text=r["korean"]
    probe=Image.new("RGBA",(max(sw+200,1200),max(sh+80,240)),(0,0,0,0))
    d=ImageDraw.Draw(probe)
    tb=d.textbbox((0,0),text,font=font)
    fill=tuple(int(v) for v in r["source_median_rgba"])
    d.text((12-tb[0],12-tb[1]),text,font=font,fill=fill)
    gb=probe.getchannel("A").getbbox()
    if not gb: raise RuntimeError(("empty render",r["region_idx"]))
    glyph=probe.crop(gb)
    if glyph.width>=sw or glyph.height>=sh:
        raise RuntimeError(("native font does not fit",r["region_idx"],glyph.size,(sw,sh)))
    px=x0+2
    py=y0+(sh-glyph.height)//2
    if px+glyph.width>=x1 or py<=y0 or py+glyph.height>=y1:
        raise RuntimeError(("positive margin fail",r["region_idx"],(px,py,glyph.width,glyph.height),(x0,y0,x1,y1)))
    gm=np.asarray(glyph.getchannel("A"))>0
    if np.any(gm & protected[py:py+glyph.height,px:px+glyph.width]):
        raise RuntimeError(("protected overlap",r["region_idx"]))
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
    final.alpha_composite(layer)
    fullgm=np.asarray(layer.getchannel("A"))>0
    render_masks.append(fullgm)
    lb=bbox_mask(fullgm)
    rows.append({
      "region_idx":r["region_idx"],"source":r["source"],"korean":text,
      "original_bbox":[x0,y0,x1,y1],"localized_bbox":lb,
      "source_width":sw,"source_height":sh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
      "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Bold","font_size":71,
      "render_resolution":"native_2048x2048","old_lowres_font_size":r.get("lowres_font_size"),
      "old_pixel_scale":r.get("pixel_scale"),"upscaled_old_korean_reused":False,
      "fill_rgba":list(fill),"alignment":"left_source_bbox_plus_2px"
    })

# Pairwise overlap/touch.
overlap_pairs=[]; touch_pairs=[]
for i in range(len(render_masks)):
    a=render_masks[i]
    for j in range(i+1,len(render_masks)):
        b=render_masks[j]
        ov=int(np.logical_and(a,b).sum())
        if ov: overlap_pairs.append([i,j,ov])
        # 1px neighborhood touch
        ys,xs=np.nonzero(a)
        if len(xs):
            dil=np.zeros_like(a)
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    y0=max(0,dy); y1=a.shape[0]+min(0,dy)
                    x0=max(0,dx); x1=a.shape[1]+min(0,dx)
                    sy0=max(0,-dy); sy1=a.shape[0]-max(0,dy)
                    sx0=max(0,-dx); sx1=a.shape[1]-max(0,dx)
                    dil[y0:y1,x0:x1]|=a[sy0:sy1,sx0:sx1]
            t=int(np.logical_and(dil,b).sum())
            if t: touch_pairs.append([i,j,t])
if overlap_pairs or touch_pairs:
    raise RuntimeError(("localized overlap/touch",overlap_pairs,touch_pairs))

oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8)
changed=np.any(oa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_union=np.zeros_like(allowed)
for m in render_masks: render_union|=m
render_protected=int(np.logical_and(render_union,protected).sum())
# Inside each source bbox, final outside Korean glyph must equal the validated clean plate.
clean_residue=0
for r,m in zip(rows,render_masks):
    x0,y0,x1,y1=r["original_bbox"]
    local=m[y0:y1,x0:x1]
    diff=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    clean_residue+=int(np.logical_and(diff,~local).sum())
if any([outside,alpha_out,protected_changed,render_protected,clean_residue]):
    raise RuntimeError(("scope",outside,alpha_out,protected_changed,render_protected,clean_residue))

new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("DDS roundtrip")

Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"A90_6DC_EDIT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"A90_6DC_PROTECTED_MASK.png")
final.save(out/"A90_6DC_FINAL_READABLE.png")
old.save(out/"A90_6DC_OLD_LOWRES_READABLE.png")
# Reuse exact validated clean evidence but persist a run-local snapshot for audit.
clean.save(out/"A90_6DC_CLEAN_PLATE.png")

tmp=Path("/tmp/a90_6dc"); tmp.mkdir(exist_ok=True)
old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                str(old_png),str(final_png),str(out/"A90_6DC_EDIT_MASK.png"),
                "--protected-mask",str(out/"A90_6DC_PROTECTED_MASK.png"),
                "--report",str(out/"A90_6DC_FINAL_MASK_VALIDATION.json")],check=True)

# Screenshot-visible Sunny Beach contact plus whole family contacts.
sunny=next(r for r in rows if r["source"]=="SUNNY BEACH")
make_contact("IGR-013 SUNNY BEACH",src,old,clean,decoded,sunny["original_bbox"],4).save(out/"A90_IGR013_SUNNY_BEACH_SOURCE_OLD_CLEAN_FINAL_4X.jpg",quality=97)

contacts=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    crop=(max(0,x0-8),max(0,y0-6),min(src.width,x1+8),min(src.height,y1+6))
    s=comp(src).crop(crop); o=comp(old).crop(crop); c=comp(clean).crop(crop); f=comp(decoded).crop(crop)
    W=max(s.width,o.width,c.width,f.width); H=max(s.height,o.height,c.height,f.height)
    card=Image.new("RGB",(W*4+18,H+24),"white")
    dd=ImageDraw.Draw(card); dd.text((4,4),f"{r['region_idx']:02d} {r['source']} -> {r['korean']}",fill="black")
    for k,v in enumerate([s,o,c,f]): card.paste(v,(k*(W+6),24))
    contacts.append(card)
cw=max(c.width for c in contacts); ch=sum(c.height for c in contacts)+4*(len(contacts)-1)
sheet=Image.new("RGB",(cw,ch),"white"); yy=0
for c in contacts: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((2600,5200),Image.Resampling.LANCZOS)
sheet.save(out/"A90_6DC_21ROW_SOURCE_OLD_CLEAN_FINAL.jpg",quality=96)

for name,a,b in [("READABLE",old,decoded),("RAW",old.transpose(Image.Transpose.FLIP_TOP_BOTTOM),decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))]:
    caa=comp(a); cbb=comp(b)
    sh=Image.new("RGB",(caa.width+cbb.width+8,max(caa.height,cbb.height)+28),"white")
    ImageDraw.Draw(sh).text((4,4),"OLD LOWRES4X | A90 NATIVE",fill="black")
    sh.paste(caa,(0,28)); sh.paste(cbb,(caa.width+8,28)); sh.thumbnail((2200,2200),Image.Resampling.LANCZOS)
    sh.save(out/f"A90_6DC_{name}_OLD_FINAL.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":173,"asset":asset_rel,
 "user_ingame_regression":["IGR-013","스크린샷(158).png","C2C_BRACKET_SCREEN"],
 "mapping":{
   "status":"EXACT_MIXED_SPLIT_GRAPHICS_PLUS_RUNTIME_REFERENCE",
   "domain":"MIXED",
   "graphics":{
     "E7F6E9B7":{"queue_index":228,"visible":"top COAST 2 COAST metallic header","action":"PRESERVE_C144_NATIVE",
       "candidate_sha256":"6e880cb7614531a95b5dcc8cda311423b8a6cbeaf6b7f6c2d0fc5befcca6d607"},
     "6DC89C6E":{"queue_index":173,"visible":"bottom stage location label (screenshot shows SUNNY BEACH / 서니 비치)",
       "action":"REWORK_ALL_21_SHARED_STAGE_ROWS_NATIVE_HD"}
   },
   "runtime_text":{"id":1123,"korean":"스테이지 주행","visible":"center bracket detail box","action":"MAPPED_REFERENCE_NO_SOURCE_CHANGE",
      "reason":"string is semantically correct and screenshot defect targeted the raster stage-name lowres family; retain for new in-game retest"},
   "protected_screen_art":"character portrait, bracket tree/lines/circles, rank badge/icon and other UI artwork are outside the edited 6DC text atlas"
 },
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
   "source_sha256":source_sha},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "superseded_candidate_sha256":old_sha,"candidate_sha256":new_sha,
 "candidate_path":str(candidate.relative_to(repo)),
 "prior_lowres_defect":{"producer":"A62","shared_lowres_font_size":18,"pixel_scale":4,
   "user_visible_example":"SUNNY BEACH -> 서니 비치","numeric_prior_pass_overridden_by_user_ingame_evidence":True},
 "native_rework":{"shared_font":"Noto Sans CJK KR Bold","shared_font_size":71,"render_resolution":"2048x2048",
   "alignment":"left","fill_rgba":[79,97,101,255],"stage_name_policy":"CANONICAL_PHONETIC_TRANSLITERATION",
   "rows":rows},
 "machine_qa":{"bbox_size_positive_margin":f"{len(rows)}/{len(rows)} PASS",
   "changed_pixels":int(changed.sum()),"changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
   "render_protected_overlap_pixels":render_protected,"clean_plate_residue_outside_korean_glyphs":clean_residue,
   "localized_overlap_pairs":overlap_pairs,"localized_1px_touch_pairs":touch_pairs,"dds_roundtrip":"PASS"},
 "visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A90_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A90_IGR013_6DC89C6E_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A90_IGR013.json").write_text(json.dumps({
 "run":run,"regression":"IGR-013","queue_index":173,"asset":"6DC89C6E",
 "candidate_sha256":new_sha,"superseded_candidate_sha256":old_sha,
 "physical_rows_reworked":len(rows),"bbox_size_positive_margin":f"{len(rows)}/{len(rows)} PASS",
 "scope_qa":report["machine_qa"],"mapping":report["mapping"],
 "worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "report":str((out/"A90_IGR013_6DC89C6E_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n")
print("A90_DONE",new_sha,len(rows))
