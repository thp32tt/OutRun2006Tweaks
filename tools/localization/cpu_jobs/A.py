#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")

repo=Path.cwd()
run="20261005-A-PRODUCTION57"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a57"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_59A79158_256x512_atlas.json",atlas)

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

if blob(ab)!="bcd439152c3fe1b04b1374609db27244a4d0e9df":
    raise RuntimeError(("atlas blob drift",blob(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); flags,fourcc,bpp,rm,gm,bm,am=pf[1],pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode=None
if fourcc==0 and bpp==32:
    mode="RGBA" if (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(1024,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("unsupported structure",W,H,pitch,mips,fourcc,bpp,hex(rm),hex(gm),hex(bm),hex(am),len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlasj=json.loads(ab.decode())
regions={r["idx"]:r for r in atlasj["regions"]}
if sorted(regions)!=list(range(24)): raise RuntimeError(("region ids",sorted(regions)))

# Artwork-plan order is the reviewed stage-name order for this 24-row atlas.
translations=[
("Castle Wall","캐슬 월"),
("Casino Town","카지노 타운"),
("Cloudy Highland","클라우디 하이랜드"),
("Coniferous Forest","코니퍼러스 포레스트"),
("Deep Lake","딥 레이크"),
("Desert","데저트"),
("Floral Village","플로럴 빌리지"),
("Ghost Forest","고스트 포레스트"),
("Giant Statues","자이언트 스태추스"),
("Ice Scape","아이스스케이프"),
("Imperial Avenue","임페리얼 애비뉴"),
("Industrial Complex","인더스트리얼 컴플렉스"),
("Jungle","정글"),
("Legend","레전드"),
("Lost City","로스트 시티"),
("Metropolis","메트로폴리스"),
("Milky Way","밀키 웨이"),
("National Park","내셔널 파크"),
("Palm Beach","팜 비치"),
("Skyscrapers","스카이스크레이퍼스"),
("Snow Mountain","스노 마운틴"),
("Sunny Beach","서니 비치"),
("Tulip Garden","튤립 가든"),
("Waterfalls","워터폴스"),
]

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
for idx,(en,ko) in enumerate(translations):
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    lm=bmask(cell.getchannel("A"))
    bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty source row",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    px=[]
    arr=cell.load()
    for yy in range(ch):
      for xx in range(cw):
        r,g,b,a=arr[xx,yy]
        if a>=96: px.append((r,g,b,a))
    if not px: raise RuntimeError(("no source style sample",idx,en))
    med=tuple(int(round(statistics.median(v[k] for v in px))) for k in range(4))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,
                 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"source_mask_pixels":count(lm),
                 "source_median_rgba":[med[0],med[1],med[2],med[3]]})

# Text-only transparent atlas: clean plate is exact alpha removal of source glyph/effect footprint.
clean=src.copy()
ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
sp=out/"A57_SOURCE_READABLE.png"; cp=out/"A57_CLEAN_PLATE.png"; smp=out/"A57_SOURCE_TEXT_MASK.png"; ap=out/"A57_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
pp=out/"A57_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A57_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A57_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)

def render_low(text,fs,fill):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=0)
    pad=2
    a=Image.new("L",(max(8,bb[2]-bb[0]+pad*2),max(8,bb[3]-bb[1]+pad*2)),0)
    ImageDraw.Draw(a).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("empty render",text))
    a=a.crop(ab)
    rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a)
    return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    fill=r["source_median_rgba"]
    chosen=None
    for fs in range(max(8,ah//4+3),5,-1):
        lay=render_low(r["korean"],fs,fill)
        if lay.width<=aw-8 and lay.height<=ah-8:
            chosen=(fs,lay); break
    if chosen is None: raise RuntimeError(("fit failed",r["region_idx"],r["korean"],aw,ah))
    fs,lay=chosen
    # Preserve source element center inside its exact effect bbox.
    px=ob[0]+(aw-lay.width)//2; py=ob[1]+(ah-lay.height)//2
    if not(px>ob[0] and py>ob[1] and px+lay.width<ob[2] and py+lay.height<ob[3]):
        raise RuntimeError(("positive margin placement",r["region_idx"],ob,[px,py,px+lay.width,py+lay.height]))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py))
    lb=list(lm.getbbox())
    if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("bbox",r["region_idx"],ob,lb))
    targets.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","lowres_font_size":fs,
        "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"pixel_scale":4,
        "fill_rgba":[fill[0],fill[1],fill[2],255],"alignment":"source_bbox_center"})

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
candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A57_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A57_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A57_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
final_alpha=bmask(dec.getchannel("A"))
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),final_alpha))
render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or render_outside or ov or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,render_outside,ov,touch))
target.save(out/"A57_TARGET_TEXT_MASK.png")

# Readable contacts are mandatory controller evidence and also validate semantic row binding.
cards=[]
for r in outrows:
    ob=r["original_bbox"]; p=8
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=max(1,min(3,900//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),"white")
    xx=0
    for z in ims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS)
sheet.save(out/"A57_ROW_CONTACTS.jpg",quality=96)

full=Image.new("RGB",(768,3*536),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((256,512),Image.Resampling.NEAREST).resize((768,1536),Image.Resampling.NEAREST)
    crop=z.crop((0,0,768,512))
    full.paste(crop,(0,i*536+24)); ImageDraw.Draw(full).text((4,i*536+4),label,fill="black")
full.save(out/"A57_SOURCE_CLEAN_FINAL.jpg",quality=96)

raw_dec=dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rr=Image.new("RGB",(512,2*1048),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((512,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1048+24))
    ImageDraw.Draw(rr).text((4,i*1048+4),label,fill="black")
rr.save(out/"A57_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"A","run":run,"index":163,"asset":asset,
 "readiness_tier":"PENDING_ARTWORK_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "selection_note":"index95 37759842 remains manual/template-only C186 REWORK and rejected inpaint families were not repeated; index143 is preserve-original song artwork despite stale queue status; index163 is the next safely producible odd localize_text row",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"policy":"artwork_plan reviewed 24-stage order mapped to atlas idx0..23; mandatory controller source-contact verification pending","translations":{str(i):{"source":en,"korean":ko} for i,(en,ko) in enumerate(translations)}},
 "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
                    "exact_source_residue":residue,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"A57_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SEMANTIC_STYLE_QA"}
(out/"A57_59A79158_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":163,"asset":"59A79158","source_sha256":sha(sb),"candidate_sha256":sha(payload),
 "localized_physical_elements":24,"bbox_size_positive_margin":"24/24 PASS","clean_plate_validator":cleanrep["status"],
 "final_mask_validator":finalrep["status"],"source_residue":residue,"outside":outside,"alpha_outside":alphaout,
 "protected_changed":prot,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_A/{run}/A57_59A79158_REPORT.json"}
(wr/"A57_59A79158.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
