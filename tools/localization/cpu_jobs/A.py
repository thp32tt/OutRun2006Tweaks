#!/usr/bin/env python3
import base64, hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION102-E989E3B7"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_HOLL_RANK_Exst/E989E3B7_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="b4f0146b9caa0469a410601d633d3394703e5ec85d07f9bd4973ddc766105583"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_A102"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"E989E3B7.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_HOLL_RANK_Exst/E989E3B7_1024x1024.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_HOLL_RANK_Exst/4x_E989E3B7_1024x1024_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(235,235,235,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=95):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,4096) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
expected_cells={6:[0,208,1720,1016],7:[1720,208,1640,1016]}
for idx,rect in expected_cells.items():
    got=list(map(int,regs[idx]["rect"]))
    if got!=rect: raise RuntimeError(("target atlas drift",idx,got,rect))

tpl=repo/"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN"
c215p=repo/"localization/graphics/role_C/20261006-C215-06AB5CEE/C215_06AB5CEE_CONTROLLER_FINAL_QA.json"
cq=json.loads(c215p.read_text())
if cq.get("decision")!="C215_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME":
    raise RuntimeError(("C215 approval drift",cq.get("decision")))
rep=json.loads((tpl/"B157_JENN_REPORT.json").read_text())
if rep.get("candidate_sha256")!="0b430a505c28b496fa2294326ac9dbc41821e5ddac5b830d348e11d1b67c39e5":
    raise RuntimeError("B157 candidate drift")
tsrc=Image.open(tpl/"B157_SOURCE_READABLE.png").convert("RGBA")
tclean=Image.open(tpl/"B157_CLEAN_PLATE.png").convert("RGBA")
tfinal=Image.open(tpl/"B157_FINAL_READABLE.png").convert("RGBA")
ts=np.asarray(tsrc,dtype=np.uint8); tc=np.asarray(tclean,dtype=np.uint8); tf=np.asarray(tfinal,dtype=np.uint8)

clean_arr=sa.copy()
final_arr=None
allowed=Image.new("L",(W,H),0)
source_mask=Image.new("L",(W,H),0)
render_mask_global=Image.new("L",(W,H),0)
rows=[]
mapping=[(2,6,"pink speech bubble","C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME"),
         (3,7,"green speech bubble","C206_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME")]
for template_region,target_region,kind,approval in mapping:
    row=next(r for r in rep["rows"] if int(r["region_idx"])==template_region)
    src_cell=list(map(int,row["cell"])); dst_cell=expected_cells[target_region]
    dx=dst_cell[0]-src_cell[0]; dy=dst_cell[1]-src_cell[1]
    if (dx,dy)!=(0,-1280): raise RuntimeError(("unexpected shift",template_region,target_region,dx,dy))
    ob=list(map(int,row["original_bbox"])); cb=list(map(int,row["source_core_bbox"])); lb0=list(map(int,row["localized_bbox"]))
    dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
    dcb=[cb[0]+dx,cb[1]+dy,cb[2]+dx,cb[3]+dy]
    dlb=[lb0[0]+dx,lb0[1]+dy,lb0[2]+dx,lb0[3]+dy]
    t_sp=ts[ob[1]:ob[3],ob[0]:ob[2]]
    t_cp=tc[ob[1]:ob[3],ob[0]:ob[2]]
    t_fp=tf[ob[1]:ob[3],ob[0]:ob[2]]
    dst_sp=sa[dob[1]:dob[3],dob[0]:dob[2]]
    if dst_sp.shape!=t_sp.shape: raise RuntimeError(("patch shape",template_region,dst_sp.shape,t_sp.shape))
    exact_diff=int(np.count_nonzero(np.any(dst_sp!=t_sp,axis=2)))
    if exact_diff!=0: raise RuntimeError(("target is not exact approved duplicate",template_region,exact_diff))
    removal=np.any(t_sp!=t_cp,axis=2)
    render=np.any(t_cp!=t_fp,axis=2)
    edit=removal|render
    # Exact C215-approved transfer: only the proven source-removal and Korean-render pixels.
    sub=clean_arr[dob[1]:dob[3],dob[0]:dob[2]]
    sub[removal]=t_cp[removal]
    clean_arr[dob[1]:dob[3],dob[0]:dob[2]]=sub
    ImageDraw.Draw(allowed).rectangle((dob[0],dob[1],dob[2]-1,dob[3]-1),fill=255)
    rm=Image.fromarray((removal.astype(np.uint8)*255),"L"); source_mask.paste(rm,(dob[0],dob[1]))
    em=Image.fromarray((render.astype(np.uint8)*255),"L"); render_mask_global.paste(em,(dob[0],dob[1]))
    rows.append({
      "template_region_idx":template_region,"target_region_idx":target_region,"kind":kind,"approval":approval,
      "shift":[dx,dy],"target_cell":dst_cell,"original_bbox":dob,"source_core_bbox":dcb,"localized_bbox":dlb,
      "source_width":dcb[2]-dcb[0],"source_height":dcb[3]-dcb[1],
      "localized_width":dlb[2]-dlb[0],"localized_height":dlb[3]-dlb[1],
      "margins":[dlb[0]-dcb[0],dcb[2]-dlb[2],dlb[1]-dcb[1],dcb[3]-dlb[3]],
      "source_removal_pixels":int(np.count_nonzero(removal)),"render_pixels":int(np.count_nonzero(render)),
      "target_vs_template_source_diff_pixels":exact_diff
    })

clean=Image.fromarray(clean_arr,"RGBA")
final_arr=clean_arr.copy()
for template_region,target_region,kind,approval in mapping:
    row=next(r for r in rep["rows"] if int(r["region_idx"])==template_region)
    src_cell=list(map(int,row["cell"])); dst_cell=expected_cells[target_region]
    dx=dst_cell[0]-src_cell[0]; dy=dst_cell[1]-src_cell[1]
    ob=list(map(int,row["original_bbox"])); dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
    t_cp=tc[ob[1]:ob[3],ob[0]:ob[2]]; t_fp=tf[ob[1]:ob[3],ob[0]:ob[2]]
    render=np.any(t_cp!=t_fp,axis=2)
    sub=final_arr[dob[1]:dob[3],dob[0]:dob[2]]
    sub[render]=t_fp[render]
    final_arr[dob[1]:dob[3],dob[0]:dob[2]]=sub
    # The complete approved patch must now be byte-identical.
    got=final_arr[dob[1]:dob[3],dob[0]:dob[2]]
    patch_diff=int(np.count_nonzero(np.any(got!=t_fp,axis=2)))
    if patch_diff!=0: raise RuntimeError(("final patch differs from C215-approved template",template_region,patch_diff))
final=Image.fromarray(final_arr,"RGBA")
protected=ImageOps.invert(allowed)

# Exact zero-pixel gates.
clean_diff=np.asarray(diffmask(src,clean))>0
source_global=np.asarray(source_mask)>0
clean_out=int(np.count_nonzero(clean_diff & (~source_global)))
if clean_out: raise RuntimeError(("clean outside source mask",clean_out))
fd=diffmask(src,final); outside=count(ImageChops.multiply(fd,protected))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
if outside or alpha_out: raise RuntimeError(("outside gate",outside,alpha_out))
for r in rows:
    l,t,rr,b=r["source_core_bbox"]; ll,tt,lr,bb=r["localized_bbox"]
    if not (ll>l and tt>t and lr<rr and bb<b): raise RuntimeError(("positive margin",r))
    if (lr-ll)>(rr-l) or (bb-tt)>(b-t): raise RuntimeError(("size ceiling",r))
# Rows are widely disjoint; still enforce 1px no-touch.
a,b=rows[0]["localized_bbox"],rows[1]["localized_bbox"]
touch=not (a[2]+1 < b[0] or b[2]+1 < a[0] or a[3]+1 < b[1] or b[3]+1 < a[1])
if touch: raise RuntimeError(("localized touch",a,b))

# Exact DDS roundtrip.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

# Repository validators.
srcp=out/"A102_SOURCE_READABLE.png"; clnp=out/"A102_CLEAN_PLATE.png"; finp=out/"A102_FINAL_READABLE.png"
src.save(srcp); clean.save(clnp); dec.save(finp)
source_mask.save(out/"A102_SOURCE_TEXT_MASK.png"); render_mask_global.save(out/"A102_RENDER_MASK.png")
allowed.save(out/"A102_ALLOWED_EFFECT_BBOX_MASK.png"); protected.save(out/"A102_PROTECTED_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
import subprocess
subprocess.run(["python3",str(validator),str(srcp),str(clnp),str(allowed),"--protected-mask",str(protected),"--report",str(out/"A102_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(srcp),str(finp),str(allowed),"--protected-mask",str(protected),"--report",str(out/"A102_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"A102_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"A102_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Controller review evidence: source / clean / final for both target rows.
panels=[]
for i,r in enumerate(rows,1):
    x0,y0,x1,y1=r["original_bbox"]; pad=120
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[comp(z.crop(box)) for z in (src,clean,dec)]
    scale=min(2.2,1050/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
    sh=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
    d=ImageDraw.Draw(sh); d.text((5,7),f"ROW {i} {r['kind']}: SOURCE | CLEAN | FINAL",fill="black")
    for z in ims:
        sh.paste(z,(xx,44)); xx+=z.width+8
    panels.append(sh)
Wsheet=max(z.width for z in panels); Hsheet=sum(z.height for z in panels)+8*(len(panels)-1)
sheet=Image.new("RGB",(Wsheet,Hsheet),"white"); yy=0
for z in panels: sheet.paste(z,(0,yy)); yy+=z.height+8
save_b64(sheet,out/"A102_E989_CONTACTS.jpg",out/"A102_E989_CONTACTS_B64.txt",96)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1200,1250),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1200,580),Image.Resampling.LANCZOS); rr.paste(z,(0,i*620+28)); ImageDraw.Draw(rr).text((5,i*620+5),lab,fill="black")
save_b64(rr,out/"A102_E989_RAW_COMPARE.jpg",out/"A102_E989_RAW_COMPARE_B64.txt",93)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":35,"asset":asset,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"source_sha256":SOURCE_SHA},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","localizable":"Total Rank x2","translation":"종합 랭킹","protected":["Holly character artwork","speech-bubble borders/glow","all non-title UI artwork"]},
 "approved_template_reuse":{"producer":"B157","final_qa":"C215_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","method":"exact duplicate sprite transfer; only C215-approved source-removal and Korean-render pixels copied","rows":rows},
 "bbox_gate":{"containment":"2/2 PASS","size_ceiling":"2/2 PASS","positive_margin":"2/2 PASS"},
 "zero_pixel_gates":{"clean_changed_outside_source_mask":clean_out,"decoded_changed_outside_union_source_bboxes":outside,"alpha_changed_outside_union_source_bboxes":alpha_out,"localized_overlap":0,"localized_1px_touch":0,"source_script_residue":"0 by exact C215 final-patch identity"},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"A102_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
}
(out/"A102_E989E3B7_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A102_E989E3B7.json").write_text(json.dumps({"run":run,"index":35,"asset":"E989E3B7","candidate_sha256":csha,"bbox_size_positive_margin":"2/2","outside":outside,"alpha_outside":alpha_out,"worker_status":report["status"],"report":f"localization/graphics/role_A/{run}/A102_E989E3B7_REPORT.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"A102","candidate_sha256":csha,"rows":rows,"outside":outside,"alpha_outside":alpha_out},ensure_ascii=False),flush=True)
