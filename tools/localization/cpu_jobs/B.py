#!/usr/bin/env python3
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PROBE174-A8CE339F"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
tmp=Path("/tmp/B174_A8CE339F.dds")
urllib.request.urlretrieve(url,tmp)
b=tmp.read_bytes()
sha=hashlib.sha256(b).hexdigest()
im=Image.open(tmp).convert("RGBA")
raw=im.copy()
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw.save(out/"B174_SOURCE_RAW.png")
readable.save(out/"B174_SOURCE_READABLE.png")

def comp(x,bg=(88,88,88,255)):
    z=Image.new("RGBA",x.size,bg); z.alpha_composite(x); return z.convert("RGB")

a=comp(readable); r=comp(raw)
W=max(a.width,r.width)
sheet=Image.new("RGB",(W,a.height+r.height+64),"white")
sheet.paste(a,(0,32)); sheet.paste(r,(0,a.height+64))
d=ImageDraw.Draw(sheet); d.text((8,8),"READABLE (flip_y)",fill="black"); d.text((8,a.height+40),"RAW DDS",fill="black")
sheet.thumbnail((2200,1600),Image.Resampling.LANCZOS)
sheet.save(out/"B174_READABLE_RAW_CONTACT.jpg",quality=96)

rep={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":52,"asset":rel,"prior_action":"zoom_review",
 "source_url":url,"source_sha256":sha,
 "decoded":{"width":im.width,"height":im.height,"mode":"RGBA"},
 "orientation_probe":"READABLE_ASSUMED_FLIP_Y_PLUS_RAW_SAVED_FOR_CONTROLLER",
 "status":"B174_SOURCE_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION",
 "same_invocation_rule":"If controller identifies localizable text and safe canonical geometry, continue to render in this user invocation.",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B174_A8CE339F_PROBE.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/B174_A8CE339F_PROBE.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":52,"asset":"A8CE339F","source_sha256":sha,
 "report":str((out/"B174_A8CE339F_PROBE.json").relative_to(repo)),
 "status":"PROBE_READY_CONTROLLER_CLASSIFICATION"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B174_PROBE_DONE",sha,im.size,im.mode)
