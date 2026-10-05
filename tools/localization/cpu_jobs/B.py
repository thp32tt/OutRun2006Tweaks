#!/usr/bin/env python3
import base64, hashlib, json, os, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION149-DCC7-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="7f8f0d10f2ac8a19bda1933d6a324a37123b48c0"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B149"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"DCC7B488.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_FLAG_RANK_Exst/4x_DCC7B488_512x256_atlas.json",atlas)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64):
    im.save(jpg,quality=94,optimize=True); b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB: raise RuntimeError(("source drift",gitblob(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regs=json.loads(ab.decode())["regions"]
if len(regs)!=1: raise RuntimeError(("region count",len(regs)))
r=regs[0]; x,y,cw,ch=map(int,r["rect"]); crop=readable.crop((x,y,x+cw,y+ch))
alpha_bbox=crop.getchannel("A").getbbox()
global_bbox=None if alpha_bbox is None else [x+alpha_bbox[0],y+alpha_bbox[1],x+alpha_bbox[2],y+alpha_bbox[3]]

ov=comp(readable); ov.thumbnail((1600,900),Image.Resampling.LANCZOS)
save_b64(ov,out/"B149_DCC7_OVERVIEW.jpg",out/"B149_DCC7_OVERVIEW_B64.txt")
cr=comp(crop); cr.thumbnail((1800,1000),Image.Resampling.LANCZOS)
card=Image.new("RGB",(cr.width,cr.height+42),"white"); card.paste(cr,(0,42))
ImageDraw.Draw(card).text((5,8),f"idx=0 cell={x},{y},{cw},{ch} alpha_bbox={global_bbox}",fill="black")
save_b64(card,out/"B149_DCC7_REGION.jpg",out/"B149_DCC7_REGION_B64.txt")
rr=comp(raw); rr.thumbnail((1600,900),Image.Resampling.LANCZOS)
save_b64(rr,out/"B149_DCC7_RAW_MIRROR_Y.jpg",out/"B149_DCC7_RAW_MIRROR_Y_B64.txt")

report={
 "schema_version":1,"role":"B","run":run,"queue_index":32,
 "asset":"textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",
 "prior_queue_action":"zoom_review","prior_status":"blocked_review",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB,"source_sha256":sha(sb)},
 "structure":{"width":W,"height":H,"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y"},
 "regions":[{"idx":0,"cell":[x,y,cw,ch],"alpha_bbox":global_bbox}],
 "controller_visual_qa":"PENDING_CONTROLLER_CLASSIFICATION",
 "candidate_persisted":False,"decision":"PREFLIGHT_EVIDENCE_READY","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B149_DCC7_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B149_DCC7B488.json").write_text(json.dumps({
 "run":run,"index":32,"asset":"DCC7B488","source_sha256":sha(sb),"regions":1,
 "decision":"PREFLIGHT_EVIDENCE_READY","candidate_persisted":False,
 "report":f"localization/graphics/role_B/{run}/B149_DCC7_PREFLIGHT.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"index":32,"source_sha256":sha(sb),"alpha_bbox":global_bbox},ensure_ascii=False))
