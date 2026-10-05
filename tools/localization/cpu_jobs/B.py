#!/usr/bin/env python3
import base64, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION154-HOLL"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="3d5539326e4c75877457f946622c561aa20557520007dfd5851f7fe9f2056023"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B154_masked"); tmp.mkdir(parents=True,exist_ok=True)
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
def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy in range(im.height):
        o.alpha_composite(im.crop((0,yy,im.width,yy+1)),(int(round(s*(im.height-1-yy))),yy))
    return o

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
dst_cell=list(map(int,regs[1]["rect"]))
if dst_cell!=[1280,1032,2048,1016]: raise RuntimeError(("atlas drift",dst_cell))

tpl=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
c202p=repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json"
cq=json.loads(c202p.read_text())
if cq.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME": raise RuntimeError(("C202 drift",cq))
rep=json.loads((tpl/"B148_8215_REPORT.json").read_text())
row=next(r for r in rep["rows"] if int(r["region_idx"])==1)
tsrc=Image.open(tpl/"B148_SOURCE_READABLE.png").convert("RGBA")
tclean=Image.open(tpl/"B148_CLEAN_PLATE.png").convert("RGBA")
src_cell=list(map(int,row["cell"])); dx=dst_cell[0]-src_cell[0]; dy=0
if (dx,dy)!=(192,0): raise RuntimeError(("shift",dx,dy))
ob=list(map(int,row["original_bbox"])); cb=list(map(int,row["source_core_bbox"]))
dob=[ob[0]+dx,ob[1],ob[2]+dx,ob[3]]
dcb=[cb[0]+dx,cb[1],cb[2]+dx,cb[3]]
ts=np.asarray(tsrc,dtype=np.uint8); tc=np.asarray(tclean,dtype=np.uint8)
tpl_src_patch=ts[ob[1]:ob[3],ob[0]:ob[2]]
tpl_clean_patch=tc[ob[1]:ob[3],ob[0]:ob[2]]
holl_patch=sa[dob[1]:dob[3],dob[0]:dob[2]]
if tpl_src_patch.shape!=holl_patch.shape: raise RuntimeError("patch shape")

# C202-approved clean plate tells us exactly which template source-effect pixels were removed.
removal=np.any(tpl_src_patch!=tpl_clean_patch,axis=2)
variant=np.any(tpl_src_patch!=holl_patch,axis=2)
extra=variant & (~removal)
# HOLL differs from the approved source by only title AA/effect variants.
if int(np.count_nonzero(variant))!=240 or int(np.count_nonzero(extra))>4:
    raise RuntimeError(("unexpected HOLL template delta",int(np.count_nonzero(variant)),int(np.count_nonzero(extra))))
# The extra variant pixels must be title-family colors, not unrelated art.
extra_rgba=holl_patch[extra]
def title_family(px):
    r,g,b,a=map(int,px)
    white=(a>0 and r>135 and g>135 and b>135 and max(r,g,b)-min(r,g,b)<85)
    navy=(a>0 and r<90 and g<95 and b<145)
    return white or navy
if any(not title_family(px) for px in extra_rgba):
    raise RuntimeError(("extra delta not title-family",extra_rgba.tolist()))
holl_remove=removal|extra

# Preserve every HOLL pixel except the proven source-title/effect footprint.
clean_arr=sa.copy()
sub=clean_arr[dob[1]:dob[3],dob[0]:dob[2]]
sub[holl_remove]=tpl_clean_patch[holl_remove]
clean_arr[dob[1]:dob[3],dob[0]:dob[2]]=sub
clean=Image.fromarray(clean_arr,"RGBA")

allowed=Image.new("L",(W,H),0)
ImageDraw.Draw(allowed).rectangle((dob[0],dob[1],dob[2]-1,dob[3]-1),fill=255)
protected=ImageOps.invert(allowed)
source_mask=Image.new("L",(W,H),0)
rm=Image.fromarray((holl_remove.astype(np.uint8)*255),"L")
source_mask.paste(rm,(dob[0],dob[1]))

# Clean changes must equal the proven removal mask and nothing else.
clean_diff=np.asarray(diffmask(src,clean))>0
mask_global=np.asarray(source_mask)>0
clean_outside=int(np.count_nonzero(clean_diff & (~mask_global)))
if clean_outside: raise RuntimeError(("clean outside removal",clean_outside))
residual_changed_expected=int(np.count_nonzero(mask_global & (~clean_diff)))
# Some source-effect pixels can already equal reconstructed background; this is allowed only for zero-alpha pixels.
if residual_changed_expected:
    unchanged_rgba=sa[mask_global & (~clean_diff)]
    if np.any(unchanged_rgba[:,3]>0): raise RuntimeError(("opaque removal pixels unchanged",residual_changed_expected))

# Render the same C202-approved source family onto the HOLL-specific clean background.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)
style=rep["source_style"]; fs=int(style["shared_font_size"]); sw=int(style["stroke_width"]); slant=float(style["slant"])
fill=tuple(style["fill_rgba"]); outline=tuple(style["outline_rgba"])
font=ImageFont.truetype(fp,fs,index=fi)
fb=font.getbbox("종합 랭킹",stroke_width=sw)
tile=Image.new("RGBA",(fb[2]-fb[0]+32,fb[3]-fb[1]+32),(0,0,0,0))
ImageDraw.Draw(tile).text((16-fb[0],16-fb[1]),"종합 랭킹",font=font,fill=fill,stroke_width=sw,stroke_fill=outline)
tile=shear_rgba(tile,slant); ab=tile.getchannel("A").getbbox(); tile=tile.crop(ab)
px=dcb[0]+(dcb[2]-dcb[0]-tile.width)//2; py=dcb[1]+(dcb[3]-dcb[1]-tile.height)//2
final=clean.copy(); final.alpha_composite(tile,(px,py))
tm=Image.new("L",(W,H),0); tm.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(tm.getbbox())
if not(lb[0]>dcb[0] and lb[1]>dcb[1] and lb[2]<dcb[2] and lb[3]<dcb[3]):
    raise RuntimeError(("localized bbox",dcb,lb))
source_w=dcb[2]-dcb[0]; source_h=dcb[3]-dcb[1]; lw=lb[2]-lb[0]; lh=lb[3]-lb[1]
if lw>source_w or lh>source_h: raise RuntimeError(("size",source_w,source_h,lw,lh))

# Static gates.
fd=diffmask(src,final)
outside=count(ImageChops.multiply(fd,protected))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
if outside or alpha_out: raise RuntimeError(("outside gate",outside,alpha_out))
# No localized glyph may touch the exact source core bbox edge.
if min(lb[0]-dcb[0],dcb[2]-lb[2],lb[1]-dcb[1],dcb[3]-lb[3])<=0:
    raise RuntimeError(("no positive margin",dcb,lb))

# Exact DDS roundtrip.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

# Repository validators.
srcp=out/"B154_SOURCE_READABLE.png"; clnp=out/"B154_CLEAN_PLATE.png"; finp=out/"B154_FINAL_READABLE.png"
src.save(srcp); clean.save(clnp); dec.save(finp); source_mask.save(out/"B154_SOURCE_TEXT_MASK.png"); allowed.save(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"); protected.save(out/"B154_PROTECTED_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(srcp),str(clnp),str(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B154_PROTECTED_MASK.png"),"--report",str(out/"B154_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(srcp),str(finp),str(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B154_PROTECTED_MASK.png"),"--report",str(out/"B154_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"B154_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"B154_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Controller evidence.
pad=110; box=(max(0,dob[0]-pad),max(0,dob[1]-pad),min(W,dob[2]+pad),min(H,dob[3]+pad))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.5,1450/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    sheet.paste(z,(xx,44)); ImageDraw.Draw(sheet).text((xx+5,8),lab,fill="black"); xx+=z.width+8
save_b64(sheet,out/"B154_HOLL_FOCUS.jpg",out/"B154_HOLL_FOCUS_B64.txt",95)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1024,1100),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),lab,fill="black")
save_b64(rr,out/"B154_HOLL_RAW_COMPARE.jpg",out/"B154_HOLL_RAW_COMPARE_B64.txt",91)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":34,"asset":asset,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"source_sha256":SOURCE_SHA},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","localizable":"Total Rank","translation":"종합 랭킹","protected":["Holly character artwork","lens flare","rank letters A/B/C/D/E","heart/cross UI"]},
 "template_provenance":{"producer":"B148","final_qa":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","template_asset":"8215FD25","shift":[dx,dy],
   "template_vs_holl_patch_diff_pixels":int(np.count_nonzero(variant)),"holl_variant_outside_template_removal_pixels":int(np.count_nonzero(extra)),
   "variant_extra_rgba":extra_rgba.tolist(),"clean_method":"apply only C202-approved source-to-clean removal pixels plus verified HOLL title-AA variants; preserve all other HOLL pixels"},
 "row":{"region_idx":1,"source":"Total Rank","korean":"종합 랭킹","cell":dst_cell,"source_core_bbox":dcb,"original_bbox":dob,"localized_bbox":lb,
        "source_width":source_w,"source_height":source_h,"localized_width":lw,"localized_height":lh,
        "delta_left":lb[0]-dcb[0],"delta_right":dcb[2]-lb[2],"delta_top":lb[1]-dcb[1],"delta_bottom":dcb[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":fp,"font_style":fstyle,"font_size":fs,"stroke_width":sw,"slant":slant},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alpha_out,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"B154_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
}
(out/"B154_HOLL_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B154_HOLL.json").write_text(json.dumps({"run":run,"index":34,"asset":"B7E25BAD","candidate_sha256":csha,"bbox_size_positive_margin":"1/1","outside":outside,"alpha_outside":alpha_out,"worker_status":report["status"],"report":f"localization/graphics/role_B/{run}/B154_HOLL_REPORT.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B154","candidate_sha256":csha,"bbox":lb,"outside":outside,"alpha_outside":alpha_out,"variant_pixels":int(np.count_nonzero(variant)),"extra_title_aa":int(np.count_nonzero(extra))},ensure_ascii=False),flush=True)
