#!/usr/bin/env python3
import base64,hashlib,json,os,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION106-590A4724"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
TARGET_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
TPL_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
TPL_CAND_SHA="d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; mips=struct.unpack_from("<I",b,28)[0]
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+w*h*4: raise RuntimeError(("format",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return w,h,mips,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def dm(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=96):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

tmp=Path("/tmp/a106"); tmp.mkdir(exist_ok=True)
tp=tmp/"590A.dds"; sp=tmp/"C075.dds"
urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds",tp)
urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds",sp)
tb=tp.read_bytes(); sb=sp.read_bytes()
if sha(tb)!=TARGET_SHA or sha(sb)!=TPL_SHA: raise RuntimeError(("source drift",sha(tb),sha(sb)))
W,H,mips,mode,raw_src,src=decode(tb); _,_,_,_,_,tpl_src=decode(sb)
tpl_cand_b=(repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds").read_bytes()
if sha(tpl_cand_b)!=TPL_CAND_SHA: raise RuntimeError(("template candidate drift",sha(tpl_cand_b)))
_,_,_,_,_,tpl_final=decode(tpl_cand_b)
tpl_clean=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_CLEAN_PLATE.png").convert("RGBA")

# Target is the missing unselected Normal Balance state. C111 cell51 is the approved unselected pale plate.
target_cell=(1400,1960,1824,2048)
pale_cell=(1288,1712,1712,1800)   # C075 cell51 More BGM unselected
selected_cell=(864,1624,1288,1712) # C075 cell50 Normal Balance selected
tc=src.crop(target_cell); pale_clean=tpl_clean.crop(pale_cell); pale_src=tpl_src.crop(pale_cell)
source_mask_local=dm(tc,pale_clean)
source_bbox=source_mask_local.getbbox(); source_pixels=count(source_mask_local)
# If the plate were not pixel-identical, diff would reach the bevel/border. Expected Normal Balance text bbox is 390x72.
if source_bbox!=(11,8,401,80): raise RuntimeError(("unselected clean-plate mismatch",source_bbox,source_pixels))
# C111 pale cell's own source diff must stay inside its known More BGM text bbox.
pale_src_mask=dm(pale_src,pale_clean)
if pale_src_mask.getbbox()!=(12,8,367,80): raise RuntimeError(("pale template mask drift",pale_src_mask.getbbox()))

# Exact target clean plate from the pixel-identical C111-approved pale background.
clean=src.copy(); clean.paste(pale_clean,(target_cell[0],target_cell[1]))

# Reuse the C111-approved geometry of 일반 밸런스 from selected cell50, but recolor to C111-approved pale-state text tone.
sel_clean=np.asarray(tpl_clean.crop(selected_cell),dtype=np.float32)
sel_final=np.asarray(tpl_final.crop(selected_cell),dtype=np.float32)
sel_diff=np.max(np.abs(sel_final[:,:,:3]-sel_clean[:,:,:3]),axis=2)
render_mask=sel_diff>1
ys,xs=np.where(render_mask)
rb=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
if rb!=(104,26,302,66): raise RuntimeError(("localized geometry drift",rb))
# Coverage estimate from selected black render against opaque orange background.
# Foreground core is the darkest 10% of changed pixels.
lum=0.2126*sel_final[:,:,0]+0.7152*sel_final[:,:,1]+0.0722*sel_final[:,:,2]
vals=lum[render_mask]; thr=float(np.quantile(vals,0.10))
core=render_mask & (lum<=thr)
sel_fg=np.median(sel_final[core,:3],axis=0)
den=sel_clean[:,:,:3]-sel_fg.reshape(1,1,3)
num=sel_clean[:,:,:3]-sel_final[:,:,:3]
valid=np.abs(den)>15
rat=np.zeros_like(num)
rat[valid]=num[valid]/den[valid]
cov=np.median(np.where(valid,rat,np.nan),axis=2)
cov=np.nan_to_num(cov,nan=0.0,posinf=0.0,neginf=0.0)
cov=np.clip(cov,0,1); cov[~render_mask]=0

# Pale-state localized tone from C111-approved cell51 Korean render.
pale_final=np.asarray(tpl_final.crop(pale_cell),dtype=np.float32)
pale_clean_arr=np.asarray(pale_clean,dtype=np.float32)
pale_changed=np.max(np.abs(pale_final[:,:,:3]-pale_clean_arr[:,:,:3]),axis=2)>1
plum=0.2126*pale_final[:,:,0]+0.7152*pale_final[:,:,1]+0.0722*pale_final[:,:,2]
pvals=plum[pale_changed]; pthr=float(np.quantile(pvals,0.10))
pcore=pale_changed & (plum<=pthr)
pale_fg=np.median(pale_final[pcore,:3],axis=0)

# Composite accepted 일반 밸런스 coverage onto exact pale clean plate.
outcell=pale_clean_arr.copy()
a=cov[:,:,None]
outcell[:,:,:3]=np.round(pale_clean_arr[:,:,:3]*(1-a)+pale_fg.reshape(1,1,3)*a)
outcell[:,:,3]=pale_clean_arr[:,:,3]
outcell=np.clip(outcell,0,255).astype(np.uint8)
final=clean.copy(); final.paste(Image.fromarray(outcell,"RGBA"),(target_cell[0],target_cell[1]))

# Hard source/localized bboxes in target coordinates.
orig=[1411,1968,1801,2040]
loc=[1504,1986,1702,2026]
local_mask=Image.new("L",(W,H),0)
lm=(cov>0.01).astype(np.uint8)*255
local_mask.paste(Image.fromarray(lm,"L"),(target_cell[0],target_cell[1]))
got=local_mask.getbbox()
if got!=tuple(loc): raise RuntimeError(("localized bbox mismatch",got,loc))
margins=[loc[0]-orig[0],orig[2]-loc[2],loc[1]-orig[1],orig[3]-loc[3]]
if min(margins)<=0: raise RuntimeError(("margin",margins))

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((orig[0],orig[1],orig[2]-1,orig[3]-1),fill=255)
protected=ImageOps.invert(allowed)
clean_diff=dm(src,clean); final_diff=dm(src,final)
clean_out=count(ImageChops.multiply(clean_diff,protected)); final_out=count(ImageChops.multiply(final_diff,protected))
alpha_out=count(ImageChops.multiply(dm(src.getchannel("A"),final.getchannel("A")),protected))
if clean_out or final_out or alpha_out: raise RuntimeError(("outside",clean_out,final_out,alpha_out))
if count(ImageChops.multiply(local_mask,protected)): raise RuntimeError("localized outside source bbox")

# Exact DDS roundtrip.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=tb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")

srcp=out/"A106_SOURCE_READABLE.png"; clnp=out/"A106_CLEAN_PLATE.png"; finp=out/"A106_FINAL_READABLE.png"
src.save(srcp); clean.save(clnp); dec.save(finp)
sm=Image.new("L",(W,H),0); sm.paste(source_mask_local,(target_cell[0],target_cell[1])); sm.save(out/"A106_SOURCE_TEXT_MASK.png")
local_mask.save(out/"A106_RENDER_MASK.png")
allowedp=out/"A106_ALLOWED_BBOX_MASK.png"; protectedp=out/"A106_PROTECTED_MASK.png"; allowed.save(allowedp); protected.save(protectedp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(srcp),str(clnp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A106_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(srcp),str(finp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A106_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"A106_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A106_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Evidence.
box=(1380,1935,1844,2048)
ims=[comp(z.crop(box)).resize((928,226),Image.Resampling.NEAREST) for z in (src,clean,dec)]
sheet=Image.new("RGB",(2800,260),"white"); d=ImageDraw.Draw(sheet); d.text((5,5),"SOURCE | CLEAN | FINAL",fill="black")
x=0
for z in ims: sheet.paste(z,(x,34)); x+=936
save_b64(sheet,out/"A106_590A_CONTACTS.jpg",out/"A106_590A_CONTACTS_B64.txt",97)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1000,1040),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
 z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
save_b64(rr,out/"A106_590A_RAW_COMPARE.jpg",out/"A106_590A_RAW_COMPARE_B64.txt",92)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":103,"asset":asset,
 "source_sha256":TARGET_SHA,"candidate_sha256":csha,
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"header_128_exact":payload[:128]==tb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","source":"Normal Balance","korean":"일반 밸런스","occurrences":1},
 "template_provenance":{"approval":"C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","template_asset":"C075FB49","clean_plate_cell":"cell51 pale/unselected","glyph_geometry":"cell50 approved 일반 밸런스","pale_text_style":"cell51 approved Korean render","target_source_diff_vs_pale_clean_bbox":[11,8,401,80],"selected_korean_relative_bbox":[104,26,302,66],"selected_fg_rgb":[float(x) for x in sel_fg],"pale_fg_rgb":[float(x) for x in pale_fg]},
 "row":{"original_bbox":orig,"localized_bbox":loc,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":390,"source_height":72,"localized_width":198,"localized_height":40,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},
 "zero_pixel_gates":{"clean_outside":clean_out,"final_outside":final_out,"alpha_outside":alpha_out,"localized_overlap":0},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "candidate_path":str(candidate.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"A106_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
}
(out/"A106_590A4724_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A106_590A4724.json").write_text(json.dumps({"run":run,"index":103,"asset":"590A4724","candidate_sha256":csha,"bbox_size_positive_margin":"1/1 PASS","outside":final_out,"alpha_outside":alpha_out,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A106_590A4724_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"candidate_sha256":csha,"source_bbox":source_bbox,"source_pixels":source_pixels,"localized_bbox":loc,"margins":margins,"pale_fg":pale_fg.tolist(),"outside":final_out},ensure_ascii=False),flush=True)
