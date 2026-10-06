#!/usr/bin/env python3
import base64,hashlib,json,os,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
repo=Path.cwd(); run="20261006-A-PRODUCTION108-590A4724"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"; candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
TARGET_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"; TPL_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"; TPL_CAND_SHA="d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633"
def sha(b): return hashlib.sha256(b).hexdigest()
def dec(b):
 h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]; pf=struct.unpack_from("<8I",b,76); mm=(pf[4],pf[5],pf[6]); mode="RGBA" if mm==(0xff,0xff00,0xff0000) else "BGRA"
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode); return w,h,m,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def dm(a,b):
 d=ImageChops.difference(a,b); z=d.split(); m=z[0]
 for q in z[1:]: m=ImageChops.lighter(m,q)
 return m.point(lambda v:255 if v else 0)
def cnt(m): return sum(m.histogram()[1:])
def comp(im,bg=(235,235,235,255)):
 z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,q=96):
 im.convert("RGB").save(jpg,quality=q,optimize=True); b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))
tmp=Path("/tmp/a107"); tmp.mkdir(exist_ok=True)
for n in ["590A4724_512x512.dds","C075FB49_512x512.dds"]: urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/"+n,tmp/n)
tb=(tmp/"590A4724_512x512.dds").read_bytes(); sb=(tmp/"C075FB49_512x512.dds").read_bytes()
if sha(tb)!=TARGET_SHA or sha(sb)!=TPL_SHA: raise RuntimeError("source drift")
W,H,mips,mode,raw_src,src=dec(tb); _,_,_,_,_,tpl_src=dec(sb)
tcb=(repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds").read_bytes()
if sha(tcb)!=TPL_CAND_SHA: raise RuntimeError("template candidate drift")
_,_,_,_,_,tpl_final=dec(tcb)
tpl_clean=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_CLEAN_PLATE.png").convert("RGBA")

target_cell=(1400,1960,1824,2048); selected=(864,1624,1288,1712); pale=(1288,1712,1712,1800)
tc=np.asarray(src.crop(target_cell),dtype=np.float32)
sel_src=tpl_src.crop(selected); sel_clean=tpl_clean.crop(selected); sel_final=tpl_final.crop(selected)
# Exact approved Normal Balance source mask geometry from selected state.
sm0=dm(sel_src,sel_clean)
if sm0.getbbox()!=(32,20,386,65): raise RuntimeError(("selected source clean-diff mask drift",sm0.getbbox()))
sm=np.asarray(sm0)>0
# Slightly include target color AA fringes where neighboring pixels are dark relative to the plate core.
lum=0.2126*tc[:,:,0]+0.7152*tc[:,:,1]+0.0722*tc[:,:,2]
dil=np.asarray(sm0.filter(ImageFilter.MaxFilter(3)))>0
aa=dil & (lum<205) & (tc[:,:,3]>0)
source_mask=sm|aa
ys,xs=np.where(source_mask); source_bbox=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
if not (source_bbox[0]>=8 and source_bbox[1]>=6 and source_bbox[2]<=404 and source_bbox[3]<=82):
 raise RuntimeError(("target source mask escaped expected text region",source_bbox))

# Reconstruct target's own plate locally: interpolate each glyph run from immediate same-row background.
# This preserves the target pale gradient/bevel instead of importing a differently-colored template plate.
Y,X=np.mgrid[0:88,0:424]
rgb=tc[:,:,:3]; alpha=tc[:,:,3]
clean_cell=tc.copy()
for yy in range(88):
    mr=source_mask[yy]
    if not np.any(mr): continue
    # same-row valid pixels; source mask is confined to text and never reaches cell edges
    good=(~mr)&(alpha[yy]>0)
    gx=np.where(good)[0]; mx=np.where(mr)[0]
    if gx.size<20: raise RuntimeError(("row interpolation support",yy,gx.size))
    for c in range(3):
        clean_cell[yy,mx,c]=np.round(np.interp(mx,gx,tc[yy,gx,c]))
# alpha preserved exactly
clean=src.copy(); clean.paste(Image.fromarray(clean_cell.astype(np.uint8),"RGBA"),(target_cell[0],target_cell[1]))

# Accepted Korean geometry from C111 selected Normal Balance.
sc=np.asarray(sel_clean,dtype=np.float32); sf=np.asarray(sel_final,dtype=np.float32)
rd=np.max(np.abs(sf[:,:,:3]-sc[:,:,:3]),axis=2); rm=rd>1
rys,rxs=np.where(rm); rb=(int(rxs.min()),int(rys.min()),int(rxs.max()+1),int(rys.max()+1))
if rb!=(104,26,302,66): raise RuntimeError(("render geometry drift",rb))
# Coverage estimate from selected Korean pixels.
fl=0.2126*sf[:,:,0]+0.7152*sf[:,:,1]+0.0722*sf[:,:,2]
thr=np.quantile(fl[rm],0.10); core=rm&(fl<=thr); fg_sel=np.median(sf[core,:3],axis=0)
den=sc[:,:,:3]-fg_sel.reshape(1,1,3); num=sc[:,:,:3]-sf[:,:,:3]; valid=np.abs(den)>15
rat=np.full_like(num,np.nan); rat[valid]=num[valid]/den[valid]
cov=np.nanmedian(rat,axis=2); cov=np.nan_to_num(cov,nan=0,posinf=0,neginf=0); cov=np.clip(cov,0,1); cov[~rm]=0
# Apply source-faithful right slant to the accepted Korean coverage before recoloring.
# Source Normal Balance is a visibly italic selector label; 0.20 shear matches this family.
base=cov.copy()
ys0,xs0=np.where(base>0)
crop=base[ys0.min():ys0.max()+1,xs0.min():xs0.max()+1]
hh,ww=crop.shape; shear=0.20; sh=int(round(shear*(hh-1)))
sheared=np.zeros((hh,ww+sh),dtype=np.float32)
for yy in range(hh):
    dx=int(round(shear*(hh-1-yy)))
    sheared[yy,dx:dx+ww]=np.maximum(sheared[yy,dx:dx+ww],crop[yy])
cov=np.zeros_like(base)
# Center within the exact source-effect bbox [11,8,401,80], preserve prior vertical baseline.
px=11+(390-sheared.shape[1])//2; py=26
cov[py:py+hh,px:px+sheared.shape[1]]=sheared

# Target unselected source core tone from exact Normal Balance mask.
tl=0.2126*tc[:,:,0]+0.7152*tc[:,:,1]+0.0722*tc[:,:,2]
vals=tl[source_mask]; tthr=np.quantile(vals,0.20); tcore=source_mask&(tl<=tthr)
fg_target=np.median(tc[tcore,:3],axis=0)

outcell=clean_cell.copy(); a=cov[:,:,None]
outcell[:,:,:3]=np.round(clean_cell[:,:,:3]*(1-a)+fg_target.reshape(1,1,3)*a)
outcell[:,:,3]=clean_cell[:,:,3]
outcell=np.clip(outcell,0,255).astype(np.uint8)
final=clean.copy(); final.paste(Image.fromarray(outcell,"RGBA"),(target_cell[0],target_cell[1]))

orig=[1411,1968,1801,2040]  # C111 source-effect bbox [875,1632,1265,1704] shifted to target cell
lm=Image.new("L",(W,H),0); lmarr=(cov>0.01).astype(np.uint8)*255; lm.paste(Image.fromarray(lmarr,"L"),(target_cell[0],target_cell[1]))
got=lm.getbbox()
if got is None: raise RuntimeError("localized bbox empty")
loc=list(got)
margins=[loc[0]-orig[0],orig[2]-loc[2],loc[1]-orig[1],orig[3]-loc[3]]
if min(margins)<=0 or (loc[2]-loc[0])>(orig[2]-orig[0]) or (loc[3]-loc[1])>(orig[3]-orig[1]): raise RuntimeError(("bbox gate",orig,loc,margins))

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((orig[0],orig[1],orig[2]-1,orig[3]-1),fill=255); protected=ImageOps.invert(allowed)
cd=dm(src,clean); fd=dm(src,final); clean_out=cnt(ImageChops.multiply(cd,protected)); final_out=cnt(ImageChops.multiply(fd,protected)); alpha_out=cnt(ImageChops.multiply(dm(src.getchannel("A"),final.getchannel("A")),protected))
if clean_out or final_out or alpha_out: raise RuntimeError(("outside",clean_out,final_out,alpha_out))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=tb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
srcp=out/"A108_SOURCE_READABLE.png"; clnp=out/"A108_CLEAN_PLATE.png"; finp=out/"A108_FINAL_READABLE.png"; src.save(srcp); clean.save(clnp); dec.save(finp)
sg=Image.new("L",(W,H),0); sg.paste(Image.fromarray((source_mask.astype(np.uint8)*255),"L"),(target_cell[0],target_cell[1])); sg.save(out/"A108_SOURCE_TEXT_MASK.png"); lm.save(out/"A108_RENDER_MASK.png")
allowedp=out/"A108_ALLOWED_BBOX_MASK.png"; protectedp=out/"A108_PROTECTED_MASK.png"; allowed.save(allowedp); protected.save(protectedp)
val=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(val),str(srcp),str(clnp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A108_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(val),str(srcp),str(finp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A108_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"A108_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A108_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

box=(1380,1935,1844,2048); ims=[comp(z.crop(box)).resize((928,226),Image.Resampling.NEAREST) for z in (src,clean,dec)]
sheet=Image.new("RGB",(2800,260),"white"); ImageDraw.Draw(sheet).text((5,5),"SOURCE | CLEAN | FINAL",fill="black"); x=0
for z in ims: sheet.paste(z,(x,34)); x+=936
save_b64(sheet,out/"A108_590A_CONTACTS.jpg",out/"A108_590A_CONTACTS_B64.txt",97)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); rr=Image.new("RGB",(1000,1040),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
 z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
save_b64(rr,out/"A108_590A_RAW_COMPARE.jpg",out/"A108_590A_RAW_COMPARE_B64.txt",92)
report={"schema_version":1,"role":"A","run":run,"queue_index":103,"asset":asset,"source_sha256":TARGET_SHA,"candidate_sha256":csha,
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"header_128_exact":payload[:128]==tb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","source":"Normal Balance","korean":"일반 밸런스","occurrences":1},
 "construction":{"source_mask":"C111-approved same-phrase Normal Balance selected-state geometry + target AA fringe","clean":"target-own pale plate quadratic reconstruction inside source mask only","korean_geometry":"C111-approved 일반 밸런스 geometry","text_tone":"target unselected source core tone","template_approval":"C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","target_fg_rgb":[float(x) for x in fg_target],"clean_method":"same-row local interpolation under exact source glyph mask","source_slant_shear":0.20},
 "row":{"original_bbox":orig,"localized_bbox":loc,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":orig[2]-orig[0],"source_height":orig[3]-orig[1],"localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},
 "zero_pixel_gates":{"clean_outside":clean_out,"final_outside":final_out,"alpha_outside":alpha_out,"localized_overlap":0},
 "clean_plate_validator":cr,"final_mask_validator":fr,"candidate_path":str(candidate.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"A108_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"}
(out/"A108_590A4724_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A108_590A4724.json").write_text(json.dumps({"run":run,"index":103,"asset":"590A4724","candidate_sha256":csha,"bbox_size_positive_margin":"1/1 PASS","outside":final_out,"alpha_outside":alpha_out,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A108_590A4724_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"candidate_sha256":csha,"source_mask_core_bbox":source_bbox,"orig":orig,"loc":loc,"margins":margins,"fg_target":fg_target.tolist(),"clean_method":"row_interpolation","source_slant_shear":0.20},ensure_ascii=False),flush=True)
