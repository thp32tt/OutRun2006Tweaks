#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION23-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; wr=repo/"localization/graphics/worker_results"
out.mkdir(parents=True,exist_ok=True); wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
srcp=Path("/tmp/7CE1CFC5_HD.dds"); atp=Path("/tmp/7CE1CFC5_atlas.json")
urllib.request.urlretrieve(base+"/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds",srcp)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_game_cvt_Exst/4x_7CE1CFC5_512x128_atlas.json",atp)
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
sb=srcp.read_bytes(); ab=atp.read_bytes()
if blob(sb)!="8e79a14a4453c7e015144c1c2e25a4aacc633645": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="1a13020899080238d4177800382137f0a3e291a5": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
native=Image.open(srcp); native_mode=native.mode
raw=native.convert("RGBA"); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if src.size!=(2048,512): raise RuntimeError(("unexpected dimensions",src.size,pf,len(sb),native_mode))
regs={r["idx"]:r for r in json.loads(ab.decode("utf-8"))["regions"]}
specs=[(0,"NEXT MISSION","다음 미션"),(1,"Race The Rivals!","라이벌과 레이스!"),(2,"Drift To Score!","드리프트 점수 도전!"),(8,"Slipstream To Score!","슬립스트림 점수 도전!")]
rows=[]
for idx,en,ko in specs:
    x,y,cw,ch=regs[idx]["rect"]; alpha=src.crop((x,y,x+cw,y+ch)).getchannel("A"); bb=alpha.getbbox()
    if not bb: raise RuntimeError(("empty target",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"alpha_pixels":sum(alpha.histogram()[1:])})
src.save(out/"7CE_HD_SOURCE_READABLE.png"); raw.save(out/"7CE_HD_SOURCE_RAW_MIRROR_Y.png")
cards=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=20; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    im=src.crop(cr); bg=Image.new("RGBA",im.size,(80,80,80,255)); bg.alpha_composite(im); z=bg.convert("RGB")
    sc=max(1,min(3,1200//max(1,z.width))); z=z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST)
    c=Image.new("RGB",(z.width,z.height+32),"white"); c.paste(z,(0,32)); ImageDraw.Draw(c).text((4,6),f'{row["region_idx"]} {row["source"]} -> {row["korean"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A23_7CE_REGION_CONTACT.jpg",quality=97)
ann=src.copy(); d=ImageDraw.Draw(ann)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,0,255),width=2); d.text((x0,max(0,y0-16)),str(row["region_idx"]),fill=(255,255,0,255))
bg=Image.new("RGBA",ann.size,(80,80,80,255)); bg.alpha_composite(ann); bg.convert("RGB").save(out/"A23_7CE_ANNOTATED_SOURCE.jpg",quality=96)
report={"schema_version":1,"role":"A","run":run,"queue_index":59,"asset":"textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds","readiness_tier":"ONE_STAGE_TO_RENDER_PREFLIGHT","source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"source_git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},"structure":{"dimensions":[W,H],"dds_pixel_format_words":list(pf),"native_pillow_mode":native_mode,"mipmaps":mips,"payload_bytes":len(sb)-128,"raw_orientation":"mirror_y"},"rows":rows,"next":"controller confirms semantic/style binding then render same invocation","RUNTIME_VALIDATION":"UNTESTED","status":"A23_PREFLIGHT_READY_TO_RENDER"}
(out/"A23_7CE_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A23_7CE_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":59,"asset":"7CE1CFC5","source_sha256":sha(sb),"rows":rows,"structure":report["structure"],"status":report["status"],"report":str((out/"A23_7CE_PREFLIGHT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
