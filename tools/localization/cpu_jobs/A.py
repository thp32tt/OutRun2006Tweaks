#!/usr/bin/env python3
import hashlib, json, os, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PREFLIGHT135-NAME-ENTRY-66743AA8"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_name_entry_xst"
dds_url=base+"/66743AA8_1024x1024.dds"
png_url=base+"/66743AA8_1024x1024.png"
atlas_url=base+"/66743AA8_1024x1024_atlas.json"

dds=Path("/tmp/A135_66743AA8.dds")
png=Path("/tmp/A135_66743AA8.png")
atlasp=Path("/tmp/A135_66743AA8_atlas.json")
urllib.request.urlretrieve(dds_url,dds)
urllib.request.urlretrieve(png_url,png)
urllib.request.urlretrieve(atlas_url,atlasp)

raw=dds.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
src=Image.open(dds).convert("RGBA")
published=Image.open(png).convert("RGBA")
atlas=json.loads(atlasp.read_text(encoding="utf-8"))
if src.size!=(1024,1024) or published.size!=(1024,1024):
    raise RuntimeError(("unexpected source size",src.size,published.size))
# Published PNG and PIL DDS decode should identify the correct raw orientation.
same=ImageOps.invert(Image.new("L",(1,1),0)).getbbox() is not None
same_rgba=list(src.getdata())==list(published.getdata())
flip=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
same_flip=list(flip.getdata())==list(published.getdata())
if not (same_rgba or same_flip):
    # Do not guess orientation: still emit evidence and hold.
    orientation="UNRESOLVED"
    readable=published
elif same_rgba:
    orientation="DDS_DECODE_MATCHES_PUBLISHED_PNG"
    readable=src
else:
    orientation="DDS_DECODE_REQUIRES_MIRROR_Y"
    readable=flip

regions=atlas.get("regions",[])
if len(regions)!=49:
    raise RuntimeError(("region count",len(regions)))

# Atlas records are sprite_44..sprite_92 in a 7x7 logical set.
records=[]
cards=[]
for reg in regions:
    idx=int(reg["idx"])
    name=reg["name"]
    x,y,w,h=[int(v) for v in reg["rect"]]
    crop=published.crop((x,y,x+w,y+h))
    alpha=crop.getchannel("A")
    ab=alpha.getbbox()
    nonzero=sum(1 for v in alpha.getdata() if v)
    if ab:
        glyph_bbox=[x+ab[0],y+ab[1],x+ab[2],y+ab[3]]
    else:
        glyph_bbox=None
    records.append({
        "atlas_idx":idx,
        "sprite_name":name,
        "rect":[x,y,w,h],
        "alpha_bbox_global":glyph_bbox,
        "nonzero_alpha_pixels":nonzero
    })
    # Normalize each cell to 160x160 without changing the source pixels; nearest scaling for inspection.
    tile=Image.new("RGBA",(192,192),(238,238,238,255))
    sc=max(1,min(4,160//max(1,max(w,h))))
    shown=crop.resize((w*sc,h*sc),Image.Resampling.NEAREST)
    px=(192-shown.width)//2; py=(192-shown.height)//2
    tile.alpha_composite(shown,(px,py))
    card=Image.new("RGB",(192,220),"white")
    card.paste(tile.convert("RGB"),(0,28))
    ImageDraw.Draw(card).text((5,6),f"{idx:02d} {name}",fill="black")
    cards.append(card)

cols=7; rowsn=7
sheet=Image.new("RGB",(cols*192,rowsn*220),"white")
for i,c in enumerate(cards):
    sheet.paste(c,((i%cols)*192,(i//cols)*220))
sheet.save(out/"A135_NAME_ENTRY_49_CELL_CONTACT.jpg",quality=97)

# Full atlas + mirror-Y proof.
def on_white(im):
    z=Image.new("RGBA",im.size,(238,238,238,255))
    z.alpha_composite(im)
    return z.convert("RGB")
full=on_white(published)
full.thumbnail((1200,1200),Image.Resampling.LANCZOS)
full.save(out/"A135_NAME_ENTRY_PUBLISHED_READABLE.jpg",quality=97)
rawproof=on_white(src)
rawproof.thumbnail((1200,1200),Image.Resampling.LANCZOS)
rawproof.save(out/"A135_NAME_ENTRY_DDS_DECODE.jpg",quality=97)
flipproof=on_white(flip)
flipproof.thumbnail((1200,1200),Image.Resampling.LANCZOS)
flipproof.save(out/"A135_NAME_ENTRY_DDS_MIRROR_Y.jpg",quality=97)

# Cell geometry sanity.
widths=sorted(set(r["rect"][2] for r in records))
heights=sorted(set(r["rect"][3] for r in records))
nonempty=sum(1 for r in records if r["alpha_bbox_global"] is not None)

report={
  "schema_version":1,
  "role":"A",
  "run":run,
  "queue_index":24,
  "asset":"textures/load/spr_name_entry_xst/66743AA8_1024x1024.dds",
  "work_stolen_from_lane":"B",
  "source":{
    "repo":"Sonic-TV/OR2006Sprites",
    "commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
    "dds_url":dds_url,
    "png_url":png_url,
    "atlas_url":atlas_url,
    "dds_sha256":sha,
    "dds_bytes":len(raw),
    "canvas":[1024,1024]
  },
  "atlas":{
    "regions_count":len(records),
    "sprite_range":["sprite_44","sprite_92"],
    "logical_grid":"49 regions / 7x7 inspection contact",
    "region_widths":widths,
    "region_heights":heights,
    "nonempty_alpha_regions":nonempty,
    "records":records
  },
  "orientation":{
    "dds_decode_equals_published_png":same_rgba,
    "dds_mirror_y_equals_published_png":same_flip,
    "decision":orientation
  },
  "evidence":[
    "A135_NAME_ENTRY_49_CELL_CONTACT.jpg",
    "A135_NAME_ENTRY_PUBLISHED_READABLE.jpg",
    "A135_NAME_ENTRY_DDS_DECODE.jpg",
    "A135_NAME_ENTRY_DDS_MIRROR_Y.jpg"
  ],
  "decision":"PREFLIGHT_READY_FOR_CONTROLLER_SEMANTIC_REVIEW",
  "candidate_written":False,
  "blocker":"Do not repurpose the 49 name-entry sprite slots until controller visual review identifies the stock symbol set and runtime input/storage mapping; atlas capacity alone does not prove Hangul-safe input.",
  "runtime_validation":"UNTESTED",
  "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A135_NAME_ENTRY_PREFLIGHT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A135_NAME_ENTRY_66743AA8.json").write_text(json.dumps({
  "role":"A","run":run,"queue_index":24,"asset":"66743AA8",
  "source_sha256":sha,"regions":len(records),"orientation":orientation,
  "report":str(rp.relative_to(repo)),
  "status":"PREFLIGHT_READY_FOR_CONTROLLER_SEMANTIC_REVIEW",
  "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"source_sha256":sha,"regions":len(records),"nonempty":nonempty,"orientation":orientation,"status":"PREFLIGHT_READY_FOR_CONTROLLER_SEMANTIC_REVIEW"},ensure_ascii=False),flush=True)
