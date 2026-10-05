#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C150-9FC88069"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION77"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="e97d852a905aa8a219b786b843089e0998037f52"
ATLAS_BLOB_SHA1="77904226ad9347044c4c091575efbe0aba72717a"
SOURCE_SHA256="2729b78176ec648039f5b45baf52b1a78e8586e6233baf9a6be4f351f5b1add4"
INPUT_CANDIDATE_SHA256="667b64ac0336c7ae3f7b1f4b79f36c7237225104a4c948ac7158da9805d7e1a7"

base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_C150"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_9FC88069_1024x512_atlas.json",atlas)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    m=d.split()[0]
    for z in d.split()[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(48,48,48,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=dds.read_bytes(); ab=atlas.read_bytes(); ib=candidate.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("pinned source drift",gitblob(sb),gitblob(ab)))
if sha(sb)!=SOURCE_SHA256 or sha(ib)!=INPUT_CANDIDATE_SHA256:
    raise RuntimeError(("sha mismatch",sha(sb),sha(ib)))
if sb[:128]!=ib[:128] or len(sb)!=len(ib):
    raise RuntimeError("candidate structure mismatch")

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
masks=(pf[4],pf[5],pf[6])
mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
if not mode or (W,H)!=(4096,2048) or mips!=1 or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,masks,len(sb)))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
raw_in=Image.frombytes("RGBA",(W,H),ib[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
inp=raw_in.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={int(r["idx"]):r for r in json.loads(ab.decode("utf-8"))["regions"]}

# C semantic-policy correction:
# these parenthetical strings are part of displayed music-title/variant artwork and must remain original English.
restore={
    2:"(GUITAR MIX) song-title/variant qualifier",
    10:"(INSTRUMENTAL) song-title/variant qualifier",
    39:"(PROTOTYPE) song-title/variant qualifier",
}
targets={
    0:("RANDOM","무작위"),
    1:("= RANDOM PLAY =","- 무작위 재생 -"),
    40:("INTERMEDIATE B","중급 B"),
    41:("INTERMEDIATE A","중급 A"),
}

# Load B77 evidence only as construction masks; C independently rechecks corrected decoded pixels.
b77_report=json.loads((bdir/"B77_9FC_REPORT.json").read_text())
b77_clean=Image.open(bdir/"9FC_CLEAN_PLATE.png").convert("RGBA")
b77_source_mask=Image.open(bdir/"9FC_SOURCE_TEXT_MASK.png").convert("L")
b77_target=Image.open(bdir/"9FC_TARGET_TEXT_MASK.png").convert("L")
b77_allowed=Image.open(bdir/"9FC_ALLOWED_BBOX_MASK.png").convert("L")

# Produce the small corrective rework by restoring the three protected title-qualifier cells exactly.
final=inp.copy()
clean=b77_clean.copy()
source_mask=b77_source_mask.copy()
target_mask=b77_target.copy()
allowed=b77_allowed.copy()
for idx in restore:
    x,y,w,h=regions[idx]["rect"]
    crop=src.crop((x,y,x+w,y+h))
    final.paste(crop,(x,y))
    clean.paste(crop,(x,y))
    ImageDraw.Draw(source_mask).rectangle((x,y,x+w-1,y+h-1),fill=0)
    ImageDraw.Draw(target_mask).rectangle((x,y,x+w-1,y+h-1),fill=0)
    ImageDraw.Draw(allowed).rectangle((x,y,x+w-1,y+h-1),fill=0)

# Encode exact DDS header/raw orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128] or len(payload)!=len(sb):
    raise RuntimeError("output DDS structure")
candidate.write_bytes(payload)
OUTPUT_SHA256=sha(payload)

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox():
    raise RuntimeError("roundtrip mismatch")

# Corrective scope: C may only revert those three regions relative to B77.
c_change=dmask(inp,dec)
restore_union=Image.new("L",(W,H),0)
for idx in restore:
    x,y,w,h=regions[idx]["rect"]
    ImageDraw.Draw(restore_union).rectangle((x,y,x+w-1,y+h-1),fill=255)
changes_outside_restore=count(ImageChops.multiply(c_change,ImageOps.invert(restore_union)))
if changes_outside_restore:
    raise RuntimeError(("C correction escaped restore regions",changes_outside_restore))
corrective_pixels=count(c_change)
if corrective_pixels<=0:
    raise RuntimeError("expected semantic corrective pixel changes")

# Every restored qualifier must now be byte/pixel exact to source.
restored_changed={}
for idx in restore:
    x,y,w,h=regions[idx]["rect"]
    restored_changed[str(idx)]=count(dmask(src.crop((x,y,x+w,y+h)),dec.crop((x,y,x+w,y+h))))
if any(restored_changed.values()):
    raise RuntimeError(("protected qualifier not exact",restored_changed))

# Re-derive target/source bboxes for the four functional labels from masks.
row_results=[]
target_parts=[]
source_parts=[]
for idx,(en,ko) in targets.items():
    x,y,w,h=regions[idx]["rect"]
    sm=source_mask.crop((x,y,x+w,y+h))
    tm=target_mask.crop((x,y,x+w,y+h))
    sbb=sm.getbbox(); tbb=tm.getbbox()
    if not sbb or not tbb:
        raise RuntimeError(("missing masks",idx,sbb,tbb))
    ob=[x+sbb[0],y+sbb[1],x+sbb[2],y+sbb[3]]
    lb=[x+tbb[0],y+tbb[1],x+tbb[2],y+tbb[3]]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0:
        raise RuntimeError(("bbox size margin",idx,ob,lb,d))
    fulls=Image.new("L",(W,H),0); fulls.paste(sm,(x,y)); source_parts.append((idx,fulls))
    fullt=Image.new("L",(W,H),0); fullt.paste(tm,(x,y)); target_parts.append((idx,fullt))
    row_results.append({
        "region_idx":idx,"source":en,"korean":ko,"cell":[x,y,w,h],
        "original_bbox":ob,"localized_bbox":lb,
        "source_size":[sw,sh],"localized_size":[lw,lh],
        "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

# Whole-candidate exact static gates.
diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
protected_changed=count(ImageChops.multiply(diff,protected))
render_diff=dmask(clean,dec)
render_outside_target=count(ImageChops.multiply(render_diff,ImageOps.invert(target_mask)))
clean_change=dmask(src,clean)
equal_source=ImageOps.invert(diff)
source_residue=count(ImageChops.multiply(ImageChops.multiply(clean_change,ImageOps.invert(target_mask)),equal_source))

overlap=0; touch=[]
for i in range(len(target_parts)):
    for j in range(i+1,len(target_parts)):
        a=target_parts[i][1]; b=target_parts[j][1]
        ov=count(ImageChops.multiply(a,b))
        near=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        overlap+=ov
        if ov or near: touch.append([target_parts[i][0],target_parts[j][0],ov,near])

# Exact preservation of every non-target/non-corrective atlas cell.
preserved_changed={}
for idx,r in regions.items():
    if idx in targets: continue
    x,y,w,h=r["rect"]
    preserved_changed[str(idx)]=count(dmask(src.crop((x,y,x+w,y+h)),dec.crop((x,y,x+w,y+h))))
if any(preserved_changed.values()):
    raise RuntimeError(("preserved region changed", {k:v for k,v in preserved_changed.items() if v}))

# Card non-text art outside RANDOM source bbox must remain exact.
r0=row_results[0]["original_bbox"]
card=regions[0]["rect"]; cx,cy,cw,ch=card
cardmask=Image.new("L",(W,H),0)
ImageDraw.Draw(cardmask).rectangle((cx,cy,cx+cw-1,cy+ch-1),fill=255)
ImageDraw.Draw(cardmask).rectangle((r0[0],r0[1],r0[2]-1,r0[3]-1),fill=0)
card_art_changed=count(ImageChops.multiply(diff,cardmask))

if any([outside,alphaout,protected_changed,render_outside_target,source_residue,overlap,card_art_changed]) or touch:
    raise RuntimeError(("gates",outside,alphaout,protected_changed,render_outside_target,source_residue,overlap,card_art_changed,touch))

# Evidence.
source_mask.save(out/"C150_SOURCE_TEXT_MASK.png")
target_mask.save(out/"C150_TARGET_TEXT_MASK.png")
allowed.save(out/"C150_ALLOWED_BBOX_MASK.png")
protected.save(out/"C150_PROTECTED_VISIBLE_MASK.png")
clean.save(out/"C150_EXACT_CLEAN_PLATE.png")
dec.save(out/"C150_FINAL_DECODED_READABLE.png")

full=Image.new("RGB",(1024,4*540),"white")
for i,(label,im) in enumerate([("SOURCE",src),("B77_INPUT",inp),("C150_CLEAN",clean),("C150_FINAL",dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    full.paste(z,(0,i*540+24)); ImageDraw.Draw(full).text((5,i*540+4),label,fill="black")
full.save(out/"C150_9FC_SOURCE_B77_CLEAN_FINAL.jpg",quality=96)

cards=[]
display=list(targets.keys())+list(restore.keys())
for idx in display:
    x,y,w,h=regions[idx]["rect"]
    p=8; cr=(max(0,x-p),max(0,y-p),min(W,x+w+p),min(H,y+h+p))
    ims=[comp(z).crop(cr) for z in (src,inp,dec)]
    # cap very wide cells for readable contact
    outims=[]
    for z in ims:
        if z.width>560:
            sc=560/z.width
            z=z.resize((560,max(1,int(z.height*sc))),Image.Resampling.NEAREST)
        outims.append(z)
    c=Image.new("RGB",(sum(z.width for z in outims)+12,max(z.height for z in outims)+30),"white")
    xx=0
    for z in outims:
        c.paste(z,(xx,30)); xx+=z.width+6
    label=(targets[idx][0]+" -> "+targets[idx][1]) if idx in targets else (restore[idx]+" -> RESTORED ORIGINAL")
    ImageDraw.Draw(c).text((5,5),f"{idx} {label}",fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"C150_9FC_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,3*540),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("B77_RAW_MIRROR_Y",raw_in),("C150_FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    rr.paste(z,(0,i*540+24)); ImageDraw.Draw(rr).text((5,i*540+4),label,fill="black")
rr.save(out/"C150_9FC_RAW_COMPARE.jpg",quality=96)

report={
    "schema_version":1,"role":"C","run":run,"queue_index":198,"asset":asset,
    "producer_run":"20261005-B-PRODUCTION77",
    "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
    "input_candidate_sha256":INPUT_CANDIDATE_SHA256,"candidate_sha256":OUTPUT_SHA256,"candidate_changed_by_C":True,
    "semantic_policy_correction":{
        "reason":"Song titles/music-title artwork must remain original English. B77 localized three parenthetical title/variant qualifiers.",
        "restored_original_regions":{str(k):v for k,v in restore.items()},
        "retained_localized_functional_regions":{str(k):{"source":v[0],"korean":v[1]} for k,v in targets.items()},
        "corrective_pixels":corrective_pixels,"changes_outside_restore_regions":changes_outside_restore
    },
    "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
    "rows":row_results,
    "machine_checks":{
        "bbox_size_positive_margin":"4/4 PASS","final_outside":outside,"alpha_outside":alphaout,
        "protected_changed":protected_changed,"render_outside_target":render_outside_target,
        "source_residue":source_residue,"overlap":overlap,"touch_pairs":touch,
        "card_art_changed_outside_random_text_bbox":card_art_changed,
        "restored_qualifier_changed_pixels":restored_changed,
        "all_preserved_regions_changed_pixels":preserved_changed
    },
    "machine_status":"PASS","controller_visual_qa":"PENDING",
    "decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C150_9FC_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"9FC88069","index":198,
    "source_sha256":SOURCE_SHA256,"input_candidate_sha256":INPUT_CANDIDATE_SHA256,
    "candidate_sha256":OUTPUT_SHA256,"candidate_changed_by_C":True,
    "restored_song_title_qualifier_regions":[2,10,39],"localized_functional_regions":[0,1,40,41],
    "corrective_pixels":corrective_pixels,"machine_status":"PASS","bbox_size_positive_margin":"4/4",
    "outside":outside,"alpha_outside":alphaout,"protected_changed":protected_changed,
    "render_outside_target":render_outside_target,"source_residue":source_residue,
    "overlap":overlap,"touch_pairs":len(touch),"preserved_regions_changed":sum(preserved_changed.values()),
    "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C150_9FC_MACHINE_QA.json"
}
(wr/"C150_9FC88069.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
