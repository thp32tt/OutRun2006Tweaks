#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION79-C05"\n# A79 rerun marker: worker compute passed; retry persistence after concurrent branch push.
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/C05E67EF_128x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a78_c05"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/C05E67EF_128x64.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_C05E67EF_128x64_atlas.json",atlas)
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

if blob(sb)!="6109bf8757aff5aeb11654e94356e303ed2179d4": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="d59e6fed81902cbadb2aa962d30e2eafa230669f": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(512,256) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# A77 controller contact review established physical order:
# idx0 GOAL E, 1 GOAL D, 2 GOAL C, 3 GOAL B, 4 GOAL A, 5 15CON.
specs={0:("GOAL E","골 E"),1:("GOAL D","골 D"),2:("GOAL C","골 C"),3:("GOAL B","골 B"),4:("GOAL A","골 A"),5:("15con.","15코스")}

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
for idx in range(6):
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    a=bmask(cell.getchannel("A"))
    bb=a.getbbox()
    if not bb: raise RuntimeError(("empty source",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),a),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    vals=[]; px=cell.load()
    for yy in range(bb[1],bb[3]):
        for xx in range(bb[0],bb[2]):
            if a.getpixel((xx,yy)):
                r,g,b,aa=px[xx,yy]
                if aa>=96: vals.append((r,g,b,aa))
    if not vals: raise RuntimeError(("no color samples",idx))
    med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
    rows.append({"region_idx":idx,"source":specs[idx][0],"korean":specs[idx][1],"cell":[x,y,cw,ch],
                 "original_bbox":ob,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"source_median_rgba":med})

# Text-only transparent atlas: clear the exact source glyph/effect alpha footprint.
clean=src.copy()
clean_px=clean.load()
for yy in range(H):
    for xx in range(W):
        if source_mask.getpixel((xx,yy)):
            clean_px[xx,yy]=(0,0,0,0)

sp=out/"A79_C05_SOURCE_READABLE.png"; cp=out/"A79_C05_CLEAN_PLATE.png"
smp=out/"A79_C05_SOURCE_TEXT_MASK.png"; ap=out/"A79_C05_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(source_mask))
pp=out/"A79_C05_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A79_C05_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A79_C05_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)

def render_native(text,fs,fill):
    f=ImageFont.truetype(FONT,fs,index=FI)
    dr=ImageDraw.Draw(Image.new("L",(8,8),0))
    bb=dr.textbbox((0,0),text,font=f)
    a=Image.new("L",(max(8,bb[2]-bb[0]+8),max(8,bb[3]-bb[1]+8)),0)
    ImageDraw.Draw(a).text((4-bb[0],4-bb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("render empty",text,fs))
    a=a.crop(ab)
    rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a)
    return rgba

# Preserve one shared source family size across all six labels at native HD resolution.
# A78 nearest-neighbor quarter-scale rendering is intentionally superseded because controller
# self-QA found visibly pixelated Hangul compared with the anti-aliased source.
chosen=None
for fs in range(64,8,-1):
    ok=True
    for r in rows:
        lay=render_native(r["korean"],fs,r["source_median_rgba"])
        if lay.width>r["source_width"]-4 or lay.height>r["source_height"]-4:
            ok=False; break
    if ok:
        chosen=fs; break
if chosen is None: raise RuntimeError("shared family fit")

final=clean.copy()
targets=[]
outrows=[]
for r in rows:
    ob=r["original_bbox"]; fill=r["source_median_rgba"]
    lay=render_native(r["korean"],chosen,fill)
    # Source labels are left aligned within their physical text bbox.
    px=ob[0]+2
    py=ob[1]+(r["source_height"]-lay.height)//2
    if not(px>ob[0] and py>ob[1] and px+lay.width<ob[2] and py+lay.height<ob[3]):
        raise RuntimeError(("placement",r["region_idx"],ob,[px,py,px+lay.width,py+lay.height],chosen))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py))
    lb=list(lm.getbbox()); targets.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","native_font_size_px":chosen,"pixel_scale":1,
      "horizontal_scale":1.0,"tracking_px_average":0.0,"alignment":"left","font_file":Path(FONT).name,
      "font_face_index":FI,"font_style":FSTYLE,"fill_rgba":[fill[0],fill[1],fill[2],255]})

overlap=0; touch=[]
for i in range(len(targets)):
    for j in range(i+1,len(targets)):
        a=targets[i][1]; b=targets[j][1]
        x=count(ImageChops.multiply(a,b))
        n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        overlap+=x
        if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))

target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A79_C05_FINAL_DECODED_READABLE.png"; dec.save(fp)
target.save(out/"A79_C05_TARGET_TEXT_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A79_C05_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A79_C05_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
candidate_vs_clean_outside_target=count(ImageChops.multiply(dmask(clean,dec),ImageOps.invert(target)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or render_outside or candidate_vs_clean_outside_target or overlap or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,render_outside,candidate_vs_clean_outside_target,overlap,touch))

cards=[]
for r in outrows:
    ob=r["original_bbox"]; cr=(max(0,ob[0]-6),max(0,ob[1]-6),min(W,ob[2]+6),min(H,ob[3]+6))
    ims=[comp(z).crop(cr).resize(((cr[2]-cr[0])*3,(cr[3]-cr[1])*3),Image.Resampling.NEAREST) for z in (src,clean,dec)]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+30),"white")
    xx=0
    for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]} native_fs={chosen}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A79_C05_TARGET_CONTACTS.jpg",quality=98)

rawcmp=Image.new("RGB",(W*2,H+30),"white")
for i,(label,im) in enumerate([("SOURCE_RAW",raw_src),("FINAL_RAW",raw_dec)]):
    z=comp(im); rawcmp.paste(z,(i*W,30)); ImageDraw.Draw(rawcmp).text((i*W+4,5),label,fill="black")
rawcmp.save(out/"A79_C05_RAW_COMPARE.jpg",quality=98)

report={"schema_version":1,"role":"A","run":run,"index":215,"asset":asset,
 "readiness_tier":"A77_ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "physical_binding":{"0":"GOAL E","1":"GOAL D","2":"GOAL C","3":"GOAL B","4":"GOAL A","5":"15con."},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "font":{"file":Path(FONT).name,"face_index":FI,"style":FSTYLE,"shared_native_font_size_px":chosen,"pixel_scale":1,"horizontal_scale":1.0,"artificial_tracking_px":0.0},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
   "render_outside_target":render_outside,"candidate_vs_clean_outside_korean_target":candidate_vs_clean_outside_target,
   "localized_overlap":overlap,"localized_touch_pairs":touch},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"A79_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"A79_C05E67EF_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A79_C05E67EF.json").write_text(json.dumps({
 "run":run,"index":215,"asset":"C05E67EF","source_sha256":sha(sb),"candidate_sha256":sha(payload),
 "physical_rows":6,"bbox_size_positive_margin":"6/6 PASS","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_outside,
 "candidate_vs_clean_outside_target":candidate_vs_clean_outside_target,"overlap":overlap,"touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A79_C05E67EF_REPORT.json"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"index":215,"asset":"C05E67EF","candidate_sha256":sha(payload),"native_font_size_px":chosen,"status":report["status"]},ensure_ascii=False))
