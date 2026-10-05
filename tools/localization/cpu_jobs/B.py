#!/usr/bin/env python3
import base64, hashlib, json, os, struct, urllib.request
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo = Path.cwd()
run = "20261005-B-PRODUCTION140-8215-PREFLIGHT"
out = repo / "localization/graphics/role_B" / run
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB = "64a92104d3158614283d0d63baee7ec29ca45316"
base = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT
tmp = Path("/tmp/outrun_B140")
tmp.mkdir(parents=True, exist_ok=True)
dds = tmp / "8215FD25_1024x512.dds"
atlas = tmp / "8215_atlas.json"
urllib.request.urlretrieve(base + "/Release/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds", dds)
urllib.request.urlretrieve(base + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_FLAG_RANK_Exst/4x_8215FD25_1024x512_atlas.json", atlas)

def gitblob(b):
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def sha256(b):
    return hashlib.sha256(b).hexdigest()

sb = dds.read_bytes()
ab = atlas.read_bytes()
if gitblob(sb) != SOURCE_BLOB:
    raise RuntimeError(("source drift", gitblob(sb)))

if sb[:4] != b"DDS ":
    raise RuntimeError("not DDS")
H = struct.unpack_from("<I", sb, 12)[0]
W = struct.unpack_from("<I", sb, 16)[0]
mips = struct.unpack_from("<I", sb, 28)[0]
pf = struct.unpack_from("<8I", sb, 76)
masks = (pf[4], pf[5], pf[6], pf[7])
need = 128 + W * H * 4
if (W,H) != (4096,2048) or len(sb) != need:
    raise RuntimeError(("unexpected raw RGBA DDS",W,H,len(sb),need,masks))
if masks[:3] == (0xff,0xff00,0xff0000):
    mode = "RGBA"
elif masks[:3] == (0xff0000,0xff00,0xff):
    mode = "BGRA"
else:
    raise RuntimeError(("unknown channel masks",masks))

raw = Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
readable = raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions = json.loads(ab.decode("utf-8"))["regions"]

def comp(im,bg=(62,62,62,255)):
    z = Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")

def save_b64_jpeg(im, jpg_path, b64_path, quality=82):
    im.save(jpg_path, quality=quality, optimize=True)
    b64_path.write_text(base64.b64encode(jpg_path.read_bytes()).decode("ascii"))

meta=[]
cards=[]
for r in regions:
    idx=int(r["idx"]); x,y,cw,ch=map(int,r["rect"])
    crop=readable.crop((x,y,x+cw,y+ch))
    a=crop.getchannel("A")
    bb=a.getbbox()
    global_bb=None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    hist=a.histogram()
    alpha_pixels=sum(hist[1:])
    opaque=sum(hist[250:])
    meta.append({"idx":idx,"name":r["name"],"cell":[x,y,cw,ch],"alpha_bbox":global_bb,
                 "alpha_pixels":alpha_pixels,"opaque_alpha_pixels":opaque})
    show=comp(crop)
    maxw=920
    scale=min(1.0,maxw/max(1,show.width))
    if scale < 1.0:
        show=show.resize((max(1,int(show.width*scale)),max(1,int(show.height*scale))),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(show.width,max(1,show.height+34)),"white")
    card.paste(show,(0,34))
    ImageDraw.Draw(card).text((5,6),f"idx={idx} {r['name']} cell={x},{y},{cw},{ch} alpha_bbox={global_bb}",fill="black")
    cards.append(card)

for part in range(2):
    subset=cards[part*4:(part+1)*4]
    width=max(c.width for c in subset)
    height=sum(c.height+6 for c in subset)
    sheet=Image.new("RGB",(width,height),"white")
    yy=0
    for c in subset:
        sheet.paste(c,(0,yy))
        yy += c.height+6
    sheet.thumbnail((1200,5000),Image.Resampling.LANCZOS)
    save_b64_jpeg(sheet,out/f"B140_8215_CONTACT_{part+1}.jpg",out/f"B140_8215_CONTACT_{part+1}_B64.txt",82)

ov=comp(readable)
ov.thumbnail((1200,700),Image.Resampling.LANCZOS)
save_b64_jpeg(ov,out/"B140_8215_OVERVIEW.jpg",out/"B140_8215_OVERVIEW_B64.txt",82)

rawv=comp(raw)
rawv.thumbnail((1200,700),Image.Resampling.LANCZOS)
save_b64_jpeg(rawv,out/"B140_8215_RAW.jpg",out/"B140_8215_RAW_B64.txt",82)

report={
  "schema_version":1,"role":"B","run":run,"queue_index":30,
  "asset":"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "queue_action":"zoom_review","prior_status":"blocked_review",
  "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
                       "git_blob_sha1":SOURCE_BLOB,"source_sha256":sha256(sb)},
  "structure":{"width":W,"height":H,"format":"RGBA32","raw_mode":mode,
               "mipmaps":mips,"raw_orientation":"mirror_y"},
  "regions":meta,
  "controller_visual_qa":"PENDING_CONTROLLER_CLASSIFICATION",
  "candidate_persisted":False,
  "decision":"PREFLIGHT_EVIDENCE_READY",
  "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B140_8215_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B140_8215FD25.json").write_text(json.dumps({
  "run":run,"index":30,"asset":"8215FD25","source_sha256":sha256(sb),
  "regions":len(regions),"decision":report["decision"],
  "candidate_persisted":False,"runtime_validation":"UNTESTED",
  "report":f"localization/graphics/role_B/{run}/B140_8215_PREFLIGHT.json"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"regions":len(regions),"source_sha256":sha256(sb),
                  "decision":report["decision"]},ensure_ascii=False),flush=True)
