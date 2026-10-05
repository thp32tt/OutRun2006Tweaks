#!/usr/bin/env python3
import base64, hashlib, json, os, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261006-B-PREFLIGHT158-A8CE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
asset_rel="spr_sprani_fight_Exst/A8CE339F_512x256.dds"
source_url=BASE+"/Release/"+asset_rel
tmp=Path("/tmp/outrun_B158")
tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"A8CE339F_HD.dds"
urllib.request.urlretrieve(source_url,dds)

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

raw=Image.open(dds).convert("RGBA")
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
W,H=raw.size

def comp(im,bg=(80,80,80,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

def save_jpg_b64(im,name,quality=94):
    p=out/name
    im.convert("RGB").save(p,quality=quality,optimize=True)
    (out/(name+".b64.txt")).write_text(base64.b64encode(p.read_bytes()).decode("ascii"))

# Four-orientation sheet for fail-closed orientation review.
variants=[
 ("RAW_IDENTITY",raw),
 ("MIRROR_Y",readable),
 ("MIRROR_X",raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)),
 ("ROTATE_180",raw.transpose(Image.Transpose.ROTATE_180)),
]
cards=[]
for label,im in variants:
    z=comp(im)
    z.thumbnail((1600,900),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(z.width,z.height+46),"white")
    card.paste(z,(0,46))
    ImageDraw.Draw(card).text((8,12),label,fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+24*(len(cards)-1)),"white")
y=0
for c in cards:
    sheet.paste(c,(0,y)); y+=c.height+24
save_jpg_b64(sheet,"B158_A8CE_ORIENTATION_SHEET.jpg",92)

# Try canonical atlas metadata. Missing atlas is a HOLD, not guessed.
atlas=None; atlas_url=None; atlas_error=None
atlas_candidates=[
 BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_fight_Exst/4x_A8CE339F_512x256_atlas.json",
 BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_fight_Exst/A8CE339F_512x256_atlas.json",
]
for u in atlas_candidates:
    try:
        with urllib.request.urlopen(u,timeout=30) as r:
            atlas=json.loads(r.read().decode("utf-8"))
        atlas_url=u
        break
    except Exception as e:
        atlas_error=str(e)

regions=[]
if atlas and isinstance(atlas.get("regions"),list):
    for rr in atlas["regions"]:
        try:
            idx=int(rr.get("idx"))
            x,y,w,h=map(int,rr.get("rect"))
            if w<=0 or h<=0 or x<0 or y<0 or x+w>W or y+h>H: continue
            regions.append({"idx":idx,"rect":[x,y,w,h]})
        except Exception:
            pass

if regions:
    # Native-detail readable contact sheet by atlas cell.
    cellcards=[]
    for rr in regions:
        x,y,w,h=rr["rect"]
        crop=comp(readable.crop((x,y,x+w,y+h)))
        # Preserve detail: only enlarge small cells, never shrink below readable width unless huge.
        scale=min(4.0,max(1.0,720/max(1,w)))
        nw=max(1,int(w*scale)); nh=max(1,int(h*scale))
        crop=crop.resize((nw,nh),Image.Resampling.NEAREST if scale>1 else Image.Resampling.LANCZOS)
        card=Image.new("RGB",(nw,nh+42),"white")
        card.paste(crop,(0,42))
        ImageDraw.Draw(card).text((6,10),f"idx{rr['idx']} rect={rr['rect']}",fill="black")
        cellcards.append(card)
    width=max(c.width for c in cellcards)
    height=sum(c.height for c in cellcards)+18*(len(cellcards)-1)
    contact=Image.new("RGB",(width,height),"white")
    yy=0
    for c in cellcards:
        contact.paste(c,(0,yy)); yy+=c.height+18
    save_jpg_b64(contact,"B158_A8CE_ATLAS_CONTACT.jpg",95)

report={
 "schema_version":1,
 "role":"B",
 "run":run,
 "queue_index":52,
 "queue_asset":"textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds",
 "readiness_tier":"PREFLIGHT_ONLY_CONTROLLER_VISUAL_CLASSIFICATION_REQUIRED",
 "source_provenance":{
   "repository":"Sonic-TV/OR2006Sprites",
   "commit":COMMIT,
   "release_url":source_url,
   "source_sha256":sha256(dds)
 },
 "decoded":{"dimensions":[W,H],"mode":"RGBA","pil_format":"DDS"},
 "orientation_evidence":"B158_A8CE_ORIENTATION_SHEET.jpg",
 "atlas":{"url":atlas_url,"error_if_missing":atlas_error if atlas is None else None,"regions":regions},
 "atlas_contact":"B158_A8CE_ATLAS_CONTACT.jpg" if regions else None,
 "candidate_written":False,
 "status":"B158_PREFLIGHT_PREVIEW_READY_CONTROLLER_CLASSIFICATION_REQUIRED",
 "runtime_validation":"UNTESTED"
}
(out/"B158_A8CE_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B158_A8CE339F.json").write_text(json.dumps({
 "run":"B158","index":52,"asset":"A8CE339F",
 "source_sha256":report["source_provenance"]["source_sha256"],
 "dimensions":[W,H],
 "atlas_regions":len(regions),
 "worker_status":report["status"],
 "report":f"localization/graphics/role_B/{run}/B158_A8CE_PREFLIGHT.json"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B158","asset":"A8CE339F","sha256":report["source_provenance"]["source_sha256"],"dimensions":[W,H],"atlas_regions":len(regions)},ensure_ascii=False),flush=True)
