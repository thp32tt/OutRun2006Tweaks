#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION71-ACF-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a71_acf")
work.mkdir(exist_ok=True)
dds=work/"src.dds"
atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_ACF61D7C_1024x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b):
    return hashlib.sha256(b).hexdigest()
if blob(sb)!="c9417c1b47b1af93d025cdfcdb08bef64de44341":
    raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="d41e6e15758c64086e0f6d3e93e6b4add7105951":
    raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,fourcc,bpp,rm,gm,bm,am,mode,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw.save(out/"A71_ACF_SOURCE_RAW.png")
readable.save(out/"A71_ACF_SOURCE_READABLE.png")
data=json.loads(ab.decode())
regions=sorted(data["regions"],key=lambda x:x["idx"])
font=ImageFont.load_default()

# Full numbered source preview.
full=readable.convert("RGB").copy()
d=ImageDraw.Draw(full)
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    d.rectangle((x,y,x+w-1,y+h-1),outline=(255,0,255),width=max(1,min(W,H)//1024))
    d.rectangle((x,y,x+max(28,8*len(str(idx))),y+18),fill=(255,255,255))
    d.text((x+2,y+2),str(idx),fill=(0,0,0),font=font)
preview=full.copy()
preview.thumbnail((2200,2200),Image.Resampling.LANCZOS)
preview.save(out/"A71_ACF_ATLAS_NUMBERED.jpg",quality=97)

# Contact sheets, one card per atlas region, readable orientation.
cards=[]
meta=[]
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    crop=readable.crop((x,y,x+w,y+h))
    alpha=crop.getchannel("A")
    bb=alpha.getbbox()
    meta.append({"idx":idx,"rect":[x,y,w,h],"alpha_bbox":list(bb) if bb else None,"alpha_pixels":sum(1 for v in alpha.getdata() if v)})
    scale=max(1,min(4,720//max(1,w),260//max(1,h)))
    disp=crop.convert("RGBA")
    bg=Image.new("RGBA",disp.size,(72,72,72,255)); bg.alpha_composite(disp); disp=bg.convert("RGB")
    if scale>1:
        disp=disp.resize((disp.width*scale,disp.height*scale),Image.Resampling.NEAREST)
    card=Image.new("RGB",(disp.width,max(48,disp.height+28)),"white")
    card.paste(disp,(0,28))
    ImageDraw.Draw(card).text((4,5),f"idx {idx} rect={x},{y},{w},{h} alpha_bbox={bb}",fill="black",font=font)
    cards.append(card)

# Pack ~16 cards per sheet to keep detail readable.
sheet_paths=[]
for start in range(0,len(cards),16):
    batch=cards[start:start+16]
    cols=2
    colw=max(c.width for c in batch)
    rows_n=math.ceil(len(batch)/cols)
    rowh=[0]*rows_n
    for i,c in enumerate(batch): rowh[i//cols]=max(rowh[i//cols],c.height)
    sh=sum(rowh)+8*(rows_n-1)
    sw=colw*cols+8*(cols-1)
    sheet=Image.new("RGB",(sw,sh),"white")
    yoffs=[0]
    for h0 in rowh[:-1]: yoffs.append(yoffs[-1]+h0+8)
    for i,c in enumerate(batch):
        rr=i//cols; cc=i%cols
        sheet.paste(c,(cc*(colw+8),yoffs[rr]))
    name=f"A71_ACF_CONTACTS_{start:02d}_{start+len(batch)-1:02d}.jpg"
    sheet.save(out/name,quality=97)
    sheet_paths.append(f"localization/graphics/role_A/{run}/{name}")

report={
    "schema_version":1,
    "role":"A",
    "run":run,
    "index":205,
    "asset":asset,
    "readiness_tier":"PREFLIGHT_ONLY_SEMANTIC_BINDING_REQUIRED",
    "source_provenance":{
        "repository":"Sonic-TV/OR2006Sprites","commit":commit,
        "git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),
        "source_sha256":sha(sb),"atlas_sha256":sha(ab)
    },
    "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
    "atlas_region_count":len(regions),
    "atlas_regions":meta,
    "transcription_expected_segments":20,
    "policy_notes":[
        "Song titles/music credits and OutRun2SP/product/logo artwork must remain protected original pixels.",
        "No candidate emitted in this discovery worker; controller must bind physical atlas regions before render.",
        "If semantic binding is resolved from these contacts, continue through candidate render in the same controller invocation."
    ],
    "evidence":[
        f"localization/graphics/role_A/{run}/A71_ACF_SOURCE_READABLE.png",
        f"localization/graphics/role_A/{run}/A71_ACF_SOURCE_RAW.png",
        f"localization/graphics/role_A/{run}/A71_ACF_ATLAS_NUMBERED.jpg",
        *sheet_paths
    ],
    "candidate_written":False,
    "runtime_validation":"UNTESTED",
    "status":"A71_PREFLIGHT_ONLY_PENDING_CONTROLLER_PHYSICAL_BINDING"
}
(out/"A71_ACF_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A71_ACF_PREFLIGHT.json").write_text(json.dumps({
    "run":run,"index":205,"asset":"ACF61D7C","source_sha256":sha(sb),"atlas_region_count":len(regions),
    "candidate_written":False,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A71_ACF_PREFLIGHT.json"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"index":205,"asset":"ACF61D7C","dimensions":[W,H],"regions":len(regions),"status":report["status"]},ensure_ascii=False))
