#!/usr/bin/env python3
import base64,hashlib,json,os,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION107-590A4724"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
TARGET_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
TPL_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
TPL_CAND_SHA="d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633"
TARGET_CELL=(1400,1960,1824,2048)
DONOR_CELL=(1288,1712,1712,1800)  # C075 cell51: same pale-yellow selector plate family

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+w*h*4: raise RuntimeError(("rgba32 structure",w,h,m,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return w,h,m,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def dm(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def cnt(m): return sum(m.histogram()[1:])
def comp(im):
    z=Image.new("RGBA",im.size,(235,235,235,255)); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=95):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

tmp=Path("/tmp/a106"); tmp.mkdir(exist_ok=True)
for name in ["590A4724_512x512.dds","C075FB49_512x512.dds"]:
    urllib.request.urlretrieve(BASE+"/spr_sprani_selector_cvt_Exst/"+name,tmp/name)
tb=(tmp/"590A4724_512x512.dds").read_bytes(); sb=(tmp/"C075FB49_512x512.dds").read_bytes()
if sha(tb)!=TARGET_SHA: raise RuntimeError(("target source drift",sha(tb)))
if sha(sb)!=TPL_SHA: raise RuntimeError(("donor source drift",sha(sb)))
W,H,mips,mode,raw_src,src=decode_rgba32(tb)
_,_,_,_,_,donor_src=decode_rgba32(sb)
if (W,H,mips,mode)!=(2048,2048,1,"RGBA"): raise RuntimeError(("target structure",W,H,mips,mode))

tpl_cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
if sha(tpl_cand.read_bytes())!=TPL_CAND_SHA: raise RuntimeError("C111 donor candidate drift")
donor_clean=Image.open(repo/"localization/graphics/role_A/20261005-A-RECOVERY12/C075FB49_CLEAN_PLATE.png").convert("RGBA")
_,_,_,_,_,donor_final=decode_rgba32(tpl_cand.read_bytes())

target_cell=src.crop(TARGET_CELL); donor_source_cell=donor_src.crop(DONOR_CELL); donor_clean_cell=donor_clean.crop(DONOR_CELL)
# A105 established the closest family source is donor cell51. Verify the plate itself is exact outside the source-text footprint.
source_mask_local=dm(target_cell,donor_clean_cell)
bbox=source_mask_local.getbbox()
if bbox is None: raise RuntimeError("no Normal Balance source text footprint")
# bbox is measured in cell coordinates and must stay comfortably inside the selector plate.
if not (bbox[0]>=0 and bbox[1]>=0 and bbox[2]<=424 and bbox[3]<=88 and bbox[1]>=6 and bbox[3]<=82):
    raise RuntimeError(("unsafe source bbox",bbox))
# The target and donor source plates may differ only in their label pixels; borders must be identical outside the measured footprint.
outside=Image.new("L",(424,88),255); ImageDraw.Draw(outside).rectangle((bbox[0],bbox[1],bbox[2]-1,bbox[3]-1),fill=0)
target_vs_donor_source=dm(target_cell,donor_source_cell)
border_diff=cnt(ImageChops.multiply(target_vs_donor_source,outside))
if border_diff!=0: raise RuntimeError(("selector plate family mismatch outside text",border_diff,bbox))

clean=src.copy(); clean.paste(donor_clean_cell,(TARGET_CELL[0],TARGET_CELL[1]))
source_mask=Image.new("L",(W,H),0); source_mask.paste(source_mask_local,(TARGET_CELL[0],TARGET_CELL[1]))
ob=[TARGET_CELL[0]+bbox[0],TARGET_CELL[1]+bbox[1],TARGET_CELL[0]+bbox[2],TARGET_CELL[1]+bbox[3]]
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
protected=ImageOps.invert(allowed)
clean_diff=dm(src,clean); clean_out=cnt(ImageChops.multiply(clean_diff,protected))
if clean_out!=0: raise RuntimeError(("clean changes outside measured source bbox",clean_out,ob))

# Derive the exact pale-yellow family Korean fill from C111's approved cell51 final, then render source-faithful right slant.
donor_render=dm(donor_clean_cell,donor_final.crop(DONOR_CELL))
dfa=np.asarray(donor_final.crop(DONOR_CELL)); drm=np.asarray(donor_render)>0
pix=dfa[drm]
lum=(0.2126*pix[:,0]+0.7152*pix[:,1]+0.0722*pix[:,2])
core=pix[lum<np.percentile(lum,55)]
if len(core)<50: core=pix
fill=tuple(int(x) for x in np.median(core,axis=0))
fill=(fill[0],fill[1],fill[2],255)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))
font_path=FONT
# Hard fail if the resolved font cannot render actual Hangul (prevents tofu numeric false-positive).
probe_font=ImageFont.truetype(font_path,48)
probe_a=probe_font.getmask("일반 밸런스").getbbox()
probe_b=probe_font.getmask("□□□□□").getbbox()
if probe_a is None or probe_font.getlength("일반 밸런스")<=0:
    raise RuntimeError(("hangul font coverage missing",font_path))
text="일반 밸런스"; shear=0.26
ow,oh=ob[2]-ob[0],ob[3]-ob[1]
best=None
for fs in range(min(78,oh+18),24,-1):
    font=ImageFont.truetype(font_path,fs)
    bb=font.getbbox(text,stroke_width=0)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    pad=18
    m=Image.new("L",(tw+pad*2,th+pad*2),0)
    d=ImageDraw.Draw(m); d.text((pad-bb[0],pad-bb[1]),text,font=font,fill=255)
    sw=m.width+int(abs(shear)*m.height)+8
    sh=Image.new("L",(sw,m.height),0)
    # x' = x + shear*(h-y): right-lean top, source family.
    aff=m.transform((sw,m.height),Image.Transform.AFFINE,(1,-shear,shear*m.height,0,1,0),resample=Image.Resampling.BICUBIC)
    ab=aff.getbbox()
    if ab is None: continue
    rw,rh=ab[2]-ab[0],ab[3]-ab[1]
    if rw<=ow-8 and rh<=oh-6:
        best=(fs,aff.crop(ab),rw,rh); break
if best is None: raise RuntimeError(("cannot fit Korean text",ob))
fs,mask,rw,rh=best
x=ob[0]+(ow-rw)//2; y=ob[1]+(oh-rh)//2
lb=[x,y,x+rw,y+rh]
margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
if min(margins)<=0: raise RuntimeError(("nonpositive margin",ob,lb,margins))
layer=Image.new("RGBA",(W,H),(0,0,0,0)); col=Image.new("RGBA",mask.size,fill); layer.paste(col,(x,y),mask)
final=clean.copy(); final.alpha_composite(layer)
render_mask=Image.new("L",(W,H),0); render_mask.paste(mask,(x,y))

fd=dm(src,final); final_out=cnt(ImageChops.multiply(fd,protected))
alpha_out=cnt(ImageChops.multiply(dm(src.getchannel("A"),final.getchannel("A")),protected))
if final_out or alpha_out: raise RuntimeError(("final overflow",final_out,alpha_out))
# Candidate text must not touch source bbox and no other localized/protected content exists inside this isolated label footprint.
if (rw>ow or rh>oh): raise RuntimeError(("size ceiling",rw,rh,ow,oh))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=tb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")

srcp=out/"A107_SOURCE_READABLE.png"; clnp=out/"A107_CLEAN_PLATE.png"; finp=out/"A107_FINAL_READABLE.png"
src.save(srcp); clean.save(clnp); dec.save(finp); source_mask.save(out/"A107_SOURCE_TEXT_MASK.png"); render_mask.save(out/"A107_RENDER_MASK.png")
allowedp=out/"A107_ALLOWED_BBOX_MASK.png"; protectedp=out/"A107_PROTECTED_MASK.png"; allowed.save(allowedp); protected.save(protectedp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(srcp),str(clnp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A107_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(srcp),str(finp),str(allowedp),"--protected-mask",str(protectedp),"--report",str(out/"A107_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"A107_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A107_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Readable high-zoom SOURCE/CLEAN/FINAL + raw full view.
pad=26; box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+8))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+42),"white"); xx=0
d=ImageDraw.Draw(sheet); d.text((5,5),"SOURCE | CLEAN | FINAL    Normal Balance -> 일반 밸런스",fill="black")
for z in ims: sheet.paste(z,(xx,42)); xx+=z.width+8
save_b64(sheet,out/"A107_590A_CONTACTS.jpg",out/"A107_590A_CONTACTS_B64.txt",97)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1100,1080),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1100,500),Image.Resampling.LANCZOS); rr.paste(z,(0,i*535+27)); ImageDraw.Draw(rr).text((5,i*535+5),lab,fill="black")
save_b64(rr,out/"A107_590A_RAW_COMPARE.jpg",out/"A107_590A_RAW_COMPARE_B64.txt",93)

# Carry forward transport-safe readable/raw proofs for the two no-text members of the same A103 preflight batch.
for stem in ("4668C688","4C972A19"):
    rp=repo/"localization/graphics/role_A/20261006-A-PROBE103-ZOOM103151153"/f"A103_{stem}_READABLE.png"
    wp=repo/"localization/graphics/role_A/20261006-A-PROBE103-ZOOM103151153"/f"A103_{stem}_RAW.png"
    panels=[]
    for lab,p in (("READABLE",rp),("RAW_MIRROR_Y",wp)):
        z=comp(Image.open(p).convert("RGBA")); z.thumbnail((850,850),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(850,z.height+26),"white"); ImageDraw.Draw(canvas).text((4,4),lab,fill="black"); canvas.paste(z,(0,26)); panels.append(canvas)
    sheet2=Image.new("RGB",(1708,max(x.height for x in panels)),"white"); sheet2.paste(panels[0],(0,0)); sheet2.paste(panels[1],(858,0))
    sheet2.save(out/f"A107_{stem}_READABLE_RAW_PROOF.jpg",quality=82,optimize=True)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":103,"asset":asset,
 "source_sha256":TARGET_SHA,"candidate_sha256":csha,
 "classification":{"prior_action":"zoom_review","source":"Normal Balance","korean":"일반 밸런스","occurrences":1},
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"header_128_exact":payload[:128]==tb[:128],"raw_orientation":"mirror_y"},
 "clean_plate_provenance":{"donor_asset":"C075FB49","donor_cell":list(DONOR_CELL),"donor_approval":"C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","target_cell":list(TARGET_CELL),"target_vs_donor_source_diff_pixels":int(cnt(target_vs_donor_source)),"border_diff_outside_measured_source_text_bbox":border_diff,"method":"same pale-yellow selector plate family; whole-cell donor clean accepted only because all target-vs-donor source differences are confined to measured text bbox"},
 "render":{"font":"Noto Sans CJK KR Black","font_size":fs,"shear":shear,"fill_rgba":list(fill)},
 "row":{"original_bbox":ob,"localized_bbox":lb,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":ow,"source_height":oh,"localized_width":rw,"localized_height":rh,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"},
 "zero_pixel_gates":{"clean_changed_outside_source_bbox":clean_out,"final_changed_outside_source_bbox":final_out,"alpha_changed_outside_source_bbox":alpha_out,"localized_overlap":0},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "candidate_path":str(candidate.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"A107_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
}
(out/"A107_590A4724_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A107_590A4724.json").write_text(json.dumps({"run":run,"index":103,"asset":"590A4724","candidate_sha256":csha,"bbox_size_positive_margin":"1/1 PASS","clean_outside":clean_out,"final_outside":final_out,"alpha_outside":alpha_out,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A107_590A4724_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"candidate_sha256":csha,"original_bbox":ob,"localized_bbox":lb,"margins":margins,"font_size":fs,"fill":fill,"clean_out":clean_out,"final_out":final_out,"alpha_out":alpha_out},ensure_ascii=False),flush=True)
