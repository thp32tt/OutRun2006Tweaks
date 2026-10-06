#!/usr/bin/env python3
import base64,hashlib,json,os,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION104-590A4724"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
TARGET_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
TPL_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
TPL_CAND_SHA="d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+w*h*4: raise RuntimeError(("rgba32 structure",w,h,m,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return w,h,m,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def bmask(im): return im.point(lambda v:255 if v else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def count(im): return sum(im.histogram()[1:])
def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=95):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

tmp=Path("/tmp/a104"); tmp.mkdir(exist_ok=True)
tp=tmp/"590A.dds"; cp=tmp/"C075.dds"
urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds",tp)
urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds",cp)
tb=tp.read_bytes(); cb=cp.read_bytes()
if sha(tb)!=TARGET_SHA: raise RuntimeError(("target source drift",sha(tb)))
if sha(cb)!=TPL_SHA: raise RuntimeError(("template source drift",sha(cb)))
W,H,mips,mode,raw_src,src=decode_rgba32(tb)
TW,TH,tmips,tmode,raw_tpl,tpl_src=decode_rgba32(cb)
if (W,H,mips,mode)!=(2048,2048,1,"RGBA") or (TW,TH,tmips,tmode)!=(2048,2048,1,"RGBA"):
    raise RuntimeError(("structure drift",(W,H,mips,mode),(TW,TH,tmips,tmode)))

tpl_cand_p=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
tpl_cand_b=tpl_cand_p.read_bytes()
if sha(tpl_cand_b)!=TPL_CAND_SHA: raise RuntimeError(("template candidate drift",sha(tpl_cand_b)))
_,_,_,_,raw_tpl_final,tpl_final=decode_rgba32(tpl_cand_b)
tpl_clean=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_CLEAN_PLATE.png").convert("RGBA")

src_cell=(864,1624,1288,1712); dst_cell=(1400,1960,1824,2048)
sp=np.asarray(tpl_src); sa=np.asarray(src)
sref=sp[src_cell[1]:src_cell[3],src_cell[0]:src_cell[2]]
tdst=sa[dst_cell[1]:dst_cell[3],dst_cell[0]:dst_cell[2]]
cell_diff=int(np.count_nonzero(np.any(sref!=tdst,axis=2)))
if cell_diff!=0: raise RuntimeError(("590A cell is not exact C111 normal-balance source duplicate",cell_diff))

# C111 normal_balance exact policy geometry shifted into target cell.
dx=dst_cell[0]-src_cell[0]; dy=dst_cell[1]-src_cell[1]
orig=[875+dx,1632+dy,1265+dx,1704+dy]
loc=[968+dx,1650+dy,1166+dx,1690+dy]
expected_orig=[1411,1968,1801,2040]; expected_loc=[1504,1986,1702,2026]
if orig!=expected_orig or loc!=expected_loc: raise RuntimeError(("geometry drift",orig,loc))

clean=src.copy(); final=src.copy()
clean.paste(tpl_clean.crop(src_cell),(dst_cell[0],dst_cell[1]))
final.paste(tpl_final.crop(src_cell),(dst_cell[0],dst_cell[1]))

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((orig[0],orig[1],orig[2]-1,orig[3]-1),fill=255)
protected=ImageOps.invert(allowed)
cd=diffmask(src,clean); fd=diffmask(src,final)
clean_out=count(ImageChops.multiply(cd,protected)); final_out=count(ImageChops.multiply(fd,protected))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
if clean_out or final_out or alpha_out: raise RuntimeError(("outside",clean_out,final_out,alpha_out))
margins=[loc[0]-orig[0],orig[2]-loc[2],loc[1]-orig[1],orig[3]-loc[3]]
if min(margins)<=0 or (loc[2]-loc[0])>(orig[2]-orig[0]) or (loc[3]-loc[1])>(orig[3]-orig[1]):
    raise RuntimeError(("bbox gate",orig,loc,margins))

# Exact source removal/render masks transferred only within the known source bbox.
tpl_source_crop=tpl_src.crop(src_cell); tpl_clean_crop=tpl_clean.crop(src_cell); tpl_final_crop=tpl_final.crop(src_cell)
source_mask_local=diffmask(tpl_source_crop,tpl_clean_crop); render_mask_local=diffmask(tpl_clean_crop,tpl_final_crop)
source_mask=Image.new("L",(W,H),0); source_mask.paste(source_mask_local,(dst_cell[0],dst_cell[1]))
render_mask=Image.new("L",(W,H),0); render_mask.paste(render_mask_local,(dst_cell[0],dst_cell[1]))
if count(ImageChops.multiply(source_mask,protected)) or count(ImageChops.multiply(render_mask,protected)):
    raise RuntimeError("template mask outside shifted source bbox")

# DDS exact roundtrip.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=tb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

srcp=out/"A104_SOURCE_READABLE.png"; clnp=out/"A104_CLEAN_PLATE.png"; finp=out/"A104_FINAL_READABLE.png"
src.save(srcp); clean.save(clnp); dec.save(finp); source_mask.save(out/"A104_SOURCE_TEXT_MASK.png"); render_mask.save(out/"A104_RENDER_MASK.png")
allowedp=out/"A104_ALLOWED_BBOX_MASK.png"; protectedp=out/"A104_PROTECTED_MASK.png"; allowed.save(allowedp); protected.save(protectedp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(srcp),str(clnp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A104_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(srcp),str(finp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A104_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"A104_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A104_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Visual evidence.
pad=35; box=(dst_cell[0]-pad,dst_cell[1]-pad,dst_cell[2]+pad,dst_cell[3])
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); x=0
d=ImageDraw.Draw(sheet); d.text((5,6),"SOURCE | CLEAN | FINAL  (Normal Balance -> 일반 밸런스)",fill="black")
for z in ims: sheet.paste(z,(x,44)); x+=z.width+8
save_b64(sheet,out/"A104_590A_CONTACTS.jpg",out/"A104_590A_CONTACTS_B64.txt",97)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1000,1040),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
save_b64(rr,out/"A104_590A_RAW_COMPARE.jpg",out/"A104_590A_RAW_COMPARE_B64.txt",92)

# Extra small index151 proof to make controller review transport-safe.
p151=repo/"localization/graphics/role_A/20261006-A-PROBE103-ZOOM103151153/A103_4668C688_READABLE.png"
im151=Image.open(p151).convert("RGBA"); pr=comp(im151); pr.thumbnail((900,900),Image.Resampling.LANCZOS)
pr.save(out/"A104_4668C688_SMALL_PROOF.jpg",quality=82,optimize=True)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":103,"asset":asset,
 "source_sha256":TARGET_SHA,"candidate_sha256":csha,
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"header_128_exact":payload[:128]==tb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","source":"Normal Balance","korean":"일반 밸런스","occurrences":1},
 "template_provenance":{"template_asset":"C075FB49","template_candidate_sha256":TPL_CAND_SHA,"approval":"C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","template_cell":[864,1624,424,88],"target_cell":[1400,1960,424,88],"source_cell_pixel_diff":cell_diff,"shift":[dx,dy],"method":"exact duplicate source cell: transfer C111-approved clean/final cell"},
 "row":{"original_bbox":orig,"localized_bbox":loc,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":orig[2]-orig[0],"source_height":orig[3]-orig[1],"localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},
 "zero_pixel_gates":{"clean_outside":clean_out,"final_outside":final_out,"alpha_outside":alpha_out,"source_residue":"0 by exact approved template transfer","localized_overlap":0},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "candidate_path":str(candidate.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"A104_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
}
(out/"A104_590A4724_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A104_590A4724.json").write_text(json.dumps({"run":run,"index":103,"asset":"590A4724","candidate_sha256":csha,"source_cell_pixel_diff":cell_diff,"bbox_size_positive_margin":"1/1 PASS","outside":final_out,"alpha_outside":alpha_out,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A104_590A4724_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"candidate_sha256":csha,"cell_diff":cell_diff,"orig":orig,"loc":loc,"margins":margins,"outside":final_out,"alpha_outside":alpha_out},ensure_ascii=False),flush=True)
