#!/usr/bin/env python3
import base64, hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION154-HOLL"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="3d5539326e4c75877457f946622c561aa20557520007dfd5851f7fe9f2056023"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B154"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"B7E25BAD.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_HOLL_RANK_Exst/4x_B7E25BAD_1024x512_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=94):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
if list(map(int,regs[1]["rect"])) != [1280,1032,2048,1016]:
    raise RuntimeError(("idx1 atlas drift",regs[1]))

# Reuse only the already C202-approved B148 starburst title patch.
tpl_dir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
tpl_src=Image.open(tpl_dir/"B148_SOURCE_READABLE.png").convert("RGBA")
tpl_clean=Image.open(tpl_dir/"B148_CLEAN_PLATE.png").convert("RGBA")
tpl_final=Image.open(tpl_dir/"B148_FINAL_READABLE.png").convert("RGBA")
tpl_rep=json.loads((tpl_dir/"B148_8215_REPORT.json").read_text())
row=next(r for r in tpl_rep["rows"] if int(r["region_idx"])==1)
if row["cell"] != [1088,1032,2048,1016]:
    raise RuntimeError(("template cell drift",row["cell"]))
shift_x=1280-1088; shift_y=0
src_box=list(map(int,row["original_bbox"]))
dst_box=[src_box[0]+shift_x,src_box[1],src_box[2]+shift_x,src_box[3]]
core=[int(v) for v in row["source_core_bbox"]]
dst_core=[core[0]+shift_x,core[1],core[2]+shift_x,core[3]]
loc=[int(v) for v in row["localized_bbox"]]
dst_loc=[loc[0]+shift_x,loc[1],loc[2]+shift_x,loc[3]]

tsa=np.asarray(tpl_src,dtype=np.uint8)
tca=np.asarray(tpl_clean,dtype=np.uint8)
tfa=np.asarray(tpl_final,dtype=np.uint8)
# Fail closed unless the entire source effect bbox is pixel-identical after translation.
sp=tsa[src_box[1]:src_box[3],src_box[0]:src_box[2]]
cp=sa[dst_box[1]:dst_box[3],dst_box[0]:dst_box[2]]
if sp.shape!=cp.shape: raise RuntimeError(("patch shape",sp.shape,cp.shape))
pd=np.abs(sp.astype(np.int16)-cp.astype(np.int16))
patch_max=int(pd.max()); patch_changed=int(np.count_nonzero(np.any(pd!=0,axis=2)))
if patch_changed!=0: raise RuntimeError(("template source patch mismatch",patch_changed,patch_max))
# Also require an untouched ring around the patch to be pixel-identical.
p=24
sx0=max(0,src_box[0]-p); sy0=max(0,src_box[1]-p); sx1=min(W,src_box[2]+p); sy1=min(H,src_box[3]+p)
dx0=sx0+shift_x; dy0=sy0; dx1=sx1+shift_x; dy1=sy1
ring_a=tsa[sy0:sy1,sx0:sx1]
ring_b=sa[dy0:dy1,dx0:dx1]
rm=np.ones(ring_a.shape[:2],dtype=bool)
rm[src_box[1]-sy0:src_box[3]-sy0,src_box[0]-sx0:src_box[2]-sx0]=False
rd=np.abs(ring_a.astype(np.int16)-ring_b.astype(np.int16))
ring_changed=int(np.count_nonzero(np.any(rd!=0,axis=2)&rm))
ring_max=int(rd[rm].max()) if np.any(rm) else 0
if ring_changed!=0: raise RuntimeError(("template ring mismatch",ring_changed,ring_max))

clean_arr=sa.copy(); final_arr=sa.copy()
clean_arr[dst_box[1]:dst_box[3],dst_box[0]:dst_box[2]]=tca[src_box[1]:src_box[3],src_box[0]:src_box[2]]
final_arr[dst_box[1]:dst_box[3],dst_box[0]:dst_box[2]]=tfa[src_box[1]:src_box[3],src_box[0]:src_box[2]]
clean=Image.fromarray(clean_arr,"RGBA"); final=Image.fromarray(final_arr,"RGBA")

allowed=Image.new("L",(W,H),0)
ImageDraw.Draw(allowed).rectangle((dst_box[0],dst_box[1],dst_box[2]-1,dst_box[3]-1),fill=255)
protected=ImageOps.invert(allowed)
diff=diffmask(src,final)
outside=count(ImageChops.multiply(diff,protected))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
if outside or alphaout: raise RuntimeError(("outside",outside,alphaout))

# Exact DDS roundtrip preserving header/raw orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

# Source script residue is impossible if current source patch equals the approved template source
# and current final patch equals the approved C202 template final; record this equivalence explicitly.
template_final_diff=int(np.count_nonzero(np.any(
    np.asarray(dec)[dst_box[1]:dst_box[3],dst_box[0]:dst_box[2]] !=
    tfa[src_box[1]:src_box[3],src_box[0]:src_box[2]],axis=2)))
if template_final_diff: raise RuntimeError(("template final mismatch",template_final_diff))

# Evidence.
src_png=out/"B154_SOURCE_READABLE.png"; clean_png=out/"B154_CLEAN_PLATE.png"; final_png=out/"B154_FINAL_READABLE.png"
src.save(src_png); clean.save(clean_png); dec.save(final_png); allowed.save(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"); protected.save(out/"B154_PROTECTED_MASK.png")
x0,y0,x1,y1=dst_box; pad=120; box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.4,1450/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
focus=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    focus.paste(z,(xx,44)); ImageDraw.Draw(focus).text((xx+5,8),lab,fill="black"); xx+=z.width+8
save_b64(focus,out/"B154_B7_SOURCE_CLEAN_FINAL.jpg",out/"B154_B7_SOURCE_CLEAN_FINAL_B64.txt",95)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
raw_sheet=Image.new("RGB",(1024,1100),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS); raw_sheet.paste(z,(0,i*550+26)); ImageDraw.Draw(raw_sheet).text((5,i*550+5),lab,fill="black")
save_b64(raw_sheet,out/"B154_B7_RAW_COMPARE.jpg",out/"B154_B7_RAW_COMPARE_B64.txt",91)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":34,"asset":asset,
 "classification":{"prior_action":"zoom_review","localizable":"Total Rank","translation":"종합 랭킹","protected":["Holly character artwork","lens flare","rank letters A/B/C/D/E","heart/x icon"]},
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"source_sha256":SOURCE_SHA},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "approved_template":{"asset":"8215FD25","producer":"B148","final_qa":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","shift":[shift_x,shift_y],"source_patch_changed_pixels":patch_changed,"source_patch_max_channel_delta":patch_max,"ring_changed_pixels":ring_changed,"ring_max_channel_delta":ring_max,"final_patch_diff_pixels":template_final_diff},
 "row":{"region_idx":1,"source":"Total Rank","korean":"종합 랭킹","cell":[1280,1032,2048,1016],"source_core_bbox":dst_core,"original_bbox":dst_box,"localized_bbox":dst_loc,
        "source_width":dst_core[2]-dst_core[0],"source_height":dst_core[3]-dst_core[1],
        "localized_width":dst_loc[2]-dst_loc[0],"localized_height":dst_loc[3]-dst_loc[1],
        "delta_left":dst_loc[0]-dst_core[0],"delta_right":dst_core[2]-dst_loc[2],
        "delta_top":dst_loc[1]-dst_core[1],"delta_bottom":dst_core[3]-dst_loc[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","source_style":tpl_rep["source_style"]},
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alphaout,"localized_overlap":0,"source_script_residue":0},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"B154_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B154_B7_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B154_B7E25BAD.json").write_text(json.dumps({"run":"B154","index":34,"asset":"B7E25BAD","candidate_sha256":sha(payload),"status":report["status"],"report":f"localization/graphics/role_B/{run}/B154_B7_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":sha(payload),"source_patch_changed":patch_changed,"ring_changed":ring_changed,"bbox":dst_loc,"outside":outside,"alpha_outside":alphaout},ensure_ascii=False),flush=True)
