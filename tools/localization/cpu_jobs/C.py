#!/usr/bin/env python3
import csv,hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")
repo=Path.cwd(); q=repo/"localization/graphics/asset_queue.csv"
out=repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW"; out.mkdir(parents=True,exist_ok=True)
for p in out.iterdir():
    if p.is_file(): p.unlink()
rows=list(csv.DictReader(q.open(encoding="utf-8-sig",newline="")))
def cpass(r):
    if r["action"]!="localize_text": return False
    s=r["artwork_status"].lower()
    return (s.startswith("c") and "pass" in s and "pending_c" not in s) or ("alias_of_c" in s and "pass" in s)
rows=sorted([r for r in rows if cpass(r)],key=lambda r:int(r["index"]))
try:
    f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",26)
    fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",19)
except: f=fs=ImageFont.load_default()
def flat(im):
    im=im.convert("RGBA"); bg=Image.new("RGB",im.size,(96,96,96)); bg.paste(im.convert("RGB"),mask=im.getchannel("A")); return bg
def fit(im,n=2048):
    s=min(1,n/max(im.size))
    return im.resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS) if s<1 else im
manifest=[]
for no,r in enumerate(rows,1):
    idx=int(r["index"]); rel=r["path"]; key=Path(rel).name.split("_",1)[0]
    cand=repo/"localization/graphics/hd_candidates"/rel
    name=f"{no:03d}_q{idx:03d}_{key}.jpg"; dst=out/name
    e={"number":no,"queue_index":idx,"asset_key":key,"asset_path":rel,"artwork_status":r["artwork_status"],"jpg":name}
    if cand.exists():
        e["candidate_sha256"]=hashlib.sha256(cand.read_bytes()).hexdigest(); e["source_kind"]="localized_candidate"
        with Image.open(cand) as im: raw=im.convert("RGBA")
        a=fit(flat(raw)); b=fit(flat(ImageOps.flip(raw))); w=max(a.width,b.width); head=105
        c=Image.new("RGB",(w,head+a.height+16+b.height+30),(28,28,28)); d=ImageDraw.Draw(c)
        d.text((16,10),f"{no:03d} q{idx:03d} {key}",font=f,fill="white")
        d.text((16,48),r["artwork_status"],font=fs,fill=(220,220,220))
        d.text((16,75),"TOP RAW DDS / BOTTOM FLIP-Y REVIEW",font=fs,fill=(205,205,205))
        y=head; c.paste(a,((w-a.width)//2,y)); y+=a.height+16; c.paste(b,((w-b.width)//2,y))
        c.save(dst,"JPEG",quality=94,subsampling=0,optimize=True)
    else:
        e["candidate_sha256"]=""; e["source_kind"]="policy_pass_no_candidate"
        c=Image.new("RGB",(1600,700),(44,44,44)); d=ImageDraw.Draw(c)
        d.text((60,60),f"{no:03d} q{idx:03d} {key}",font=f,fill="white")
        d.text((60,125),"C PASS - PRESERVE ORIGINAL / NO LOCALIZED CANDIDATE",font=f,fill=(235,235,235))
        d.text((60,200),rel,font=fs,fill=(215,215,215)); d.text((60,245),r["artwork_status"],font=fs,fill=(215,215,215))
        c.save(dst,"JPEG",quality=94,subsampling=0,optimize=True)
    manifest.append(e)

fields=["number","queue_index","asset_key","asset_path","artwork_status","source_kind","candidate_sha256","jpg"]
with (out/"manifest.csv").open("w",encoding="utf-8",newline="") as fp:
    w=csv.DictWriter(fp,fieldnames=fields)
    w.writeheader()
    for e in manifest:
        w.writerow({k:e.get(k,"") for k in fields})
(out/"manifest.json").write_text(json.dumps({"schema_version":1,"count":len(manifest),"items":manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

cand_count=sum(x["source_kind"]=="localized_candidate" for x in manifest)
policy_count=sum(x["source_kind"]=="policy_pass_no_candidate" for x in manifest)
(out/"README.md").write_text(
    "# C QA PASS - pre-in-game human JPG review\n\n"
    +f"Total numbered C-pass rows: {len(manifest)}\n\n"
    +f"Localized candidate JPGs: {cand_count}\n\n"
    +f"Preserve-original/no-candidate policy cards: {policy_count}\n\n"
    +"Ordering: queue index ascending. Each candidate JPG shows RAW DDS above and FLIP-Y below. "
    +"User visual rejection reopens that asset for A/B rework before in-game testing. "
    +"Report corrections using the leading JPG number.\n",
    encoding="utf-8")

thumbw,thumbh,cols=320,210,4
sheet=Image.new("RGB",(thumbw*cols,thumbh*((len(manifest)+cols-1)//cols)),(36,36,36))
sd=ImageDraw.Draw(sheet)
for i,e in enumerate(manifest):
    with Image.open(out/e["jpg"]) as im:
        im=im.convert("RGB")
        im.thumbnail((thumbw-10,thumbh-45),Image.Resampling.LANCZOS)
    x=(i%cols)*thumbw
    y=(i//cols)*thumbh
    sheet.paste(im,(x+(thumbw-im.width)//2,y+38))
    sd.text((x+6,y+6),f"{e['number']:03d} q{e['queue_index']:03d} {e['asset_key']}",font=fs,fill="white")
sheet.save(out/"000_INDEX.jpg","JPEG",quality=92,subsampling=0,optimize=True)
print(json.dumps({"output":str(out.relative_to(repo)),"count":len(manifest),"candidates":cand_count,"policy_cards":policy_count},ensure_ascii=False))
