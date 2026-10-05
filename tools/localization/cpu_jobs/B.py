#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION80"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b80"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_FEF70E85_512x512_atlas.json",atlas)

sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="48fd896aaa8ff2f269b659771f2618ea6a8426d5": raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="750c9f48f00508161f195a1a2515321cbebdab88": raise RuntimeError(("atlas blob drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# B79 controller binding: canonical stage rows are reverse atlas order 13..0.
specs=[
 (0,"INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),
 (1,"WATERFALLS","워터폴스"),
 (2,"TULIP GARDEN","튤립 가든"),
 (3,"SUNNY BEACH","서니 비치"),
 (4,"SNOW MOUNTAIN","스노 마운틴"),
 (5,"SKYSCRAPERS","스카이스크레이퍼스"),
 (6,"PALM BEACH","팜 비치"),
 (7,"NATIONAL PARK","내셔널 파크"),
 (8,"MILKY WAY","밀키 웨이"),
 (9,"METROPOLIS","메트로폴리스"),
 (10,"LOST CITY","로스트 시티"),
 (11,"LEGEND","레전드"),
 (12,"JUNGLE","정글"),
 (13,"IMPERIAL AVENUE","임페리얼 애비뉴"),
]
protected_ids=[14]  # REVERSED remains original; not present in reviewed translation segments.

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
rgb_samples=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    lm=bmask(cell.getchannel("A"))
    bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty source row",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    pix=cell.load()
    for yy in range(ch):
      for xx in range(cw):
        r,g,b,a=pix[xx,yy]
        if a>=200: rgb_samples.append((r,g,b,a))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(lm)})

if len(rgb_samples)<1000: raise RuntimeError(("style sample too small",len(rgb_samples)))
fill=tuple(int(round(statistics.median(v[k] for v in rgb_samples))) for k in range(4))
fill=(fill[0],fill[1],fill[2],255)

# Clear exact source alpha footprint while preserving hidden RGB.
clean=src.copy()
ca=clean.getchannel("A")
ca.paste(0,(0,0,W,H),source_mask)
clean.putalpha(ca)

sp=out/"FEF_SOURCE_READABLE.png"; cp=out/"FEF_CLEAN_PLATE.png"; smp=out/"FEF_SOURCE_TEXT_MASK.png"; ap=out/"FEF_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
pp=out/"FEF_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"B80_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B80_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if "Black" not in Path(FONT).name and "Black" not in FSTYLE: raise RuntimeError(("heavy CJK face unavailable",font_line))

# Source is 4x pixel artwork. Render at native quarter scale and nearest-upsample.
def render_low(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI)
    p=Image.new("L",(8,8),0); bb=ImageDraw.Draw(p).textbbox((0,0),text,font=f)
    pad=2
    a=Image.new("L",(max(8,bb[2]-bb[0]+pad*2),max(8,bb[3]-bb[1]+pad*2)),0)
    ImageDraw.Draw(a).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("empty render",text))
    a=a.crop(ab)
    rgba=Image.new("RGBA",a.size,fill); rgba.putalpha(a)
    return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)

MARGIN=4
shared_fs=None
for fs in range(30,8,-1):
    ok=True
    for r in rows:
        ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
        lay=render_low(r["korean"],fs)
        if lay.width>aw-2*MARGIN or lay.height>ah-2*MARGIN:
            ok=False; break
    if ok:
        shared_fs=fs; break
if shared_fs is None: raise RuntimeError("shared stage font fit failed")

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    lay=render_low(r["korean"],shared_fs)
    # Source family is right-aligned inside each row.
    px=ob[2]-MARGIN-lay.width
    py=ob[1]+(ah-lay.height)//2
    px=max(ob[0]+MARGIN,px); py=max(ob[1]+MARGIN,min(py,ob[3]-MARGIN-lay.height))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py))
    lb=list(lm.getbbox())
    if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]):
        raise RuntimeError(("positive margin",r["region_idx"],ob,lb))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah:
        raise RuntimeError(("size ceiling",r["region_idx"],ob,lb))
    targets.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "lowres_font_size":shared_fs,"pixel_scale":4,"fill_rgba":fill,"alignment":"right",
      "rework_status":"B80_NEW_EXACT_HD_CANDIDATE"})

ov=0; touch=[]
for i in range(len(targets)):
  for j in range(i+1,len(targets)):
    a=targets[i][1]; b=targets[j][1]
    x=count(ImageChops.multiply(a,b)); n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
    ov+=x
    if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("overlap/touch",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128]: raise RuntimeError("header")
candidate.write_bytes(payload); csha=sha(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"FEF_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B80_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B80_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
final_alpha=bmask(dec.getchannel("A"))
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),final_alpha))
render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
# Explicit protected REVERSED cell exactness.
preserved={}
for idx in protected_ids:
    x,y,cw,ch=regions[idx]["rect"]
    preserved[str(idx)]=count(dmask(src.crop((x,y,x+cw,y+ch)),dec.crop((x,y,x+cw,y+ch))))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or render_outside or ov or touch or any(preserved.values()):
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,render_outside,ov,touch,preserved))
target.save(out/"FEF_TARGET_TEXT_MASK.png")

# Evidence.
full=Image.new("RGB",(1024,3*536),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST); full.paste(z,(0,i*536+24))
    ImageDraw.Draw(full).text((5,i*536+4),label,fill="black")
full.save(out/"B80_FEF_SOURCE_CLEAN_FINAL.jpg",quality=96)

cards=[]
for r in outrows:
    ob=r["original_bbox"]; p=12
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=max(1,min(2,900//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white")
    xx=0
    for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS)
sheet.save(out/"B80_FEF_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*536),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST); rr.paste(z,(0,i*536+24))
    ImageDraw.Draw(rr).text((5,i*536+4),label,fill="black")
rr.save(out/"B80_FEF_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"index":236,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"localized":{str(i):en for i,en,_ in specs},"translations":{str(i):ko for i,_,ko in specs},"protected":{"14":"REVERSED"}},
 "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"family":"dark condensed pixel stage labels","font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"shared_lowres_font_size":shared_fs,"pixel_scale":4,"fill_rgba":fill,"alignment":"right"},
 "rows":outrows,"preserved_regions_changed_pixels":preserved,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
   "exact_source_residue":residue,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION80_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B80_FEF_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":236,"asset":"FEF70E85","source_sha256":sha(sb),"candidate_sha256":csha,
 "localized_physical_elements":len(specs),"preserved_regions":len(protected_ids),
 "bbox_size_positive_margin":f"{len(specs)}/{len(specs)}","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
 "render_outside_target":render_outside,"preserved_regions_changed":sum(preserved.values()),"overlap":ov,"touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B80_FEF_REPORT.json"}
(wr/"B80_FEF70E85.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
