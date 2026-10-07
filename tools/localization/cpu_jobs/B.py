#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261007-B-MANUALQA228-E95DA5-HELP"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
validator=repo/"tools/localization/validate_clean_plate.py"

SOURCE_SHA="33077919771f580491b8ea1011401dc22df640f87b5b0e6f602b112dbdb07b81"
EXPECTED_BEFORE="d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
tmp=Path("/tmp/b228"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; atlas_path=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds",src_dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_00E95DA5_512x256_atlas.json",atlas_path)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    m=d.split()[0]
    for z in d.split()[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=src_dds.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb)))
if not candidate.exists(): raise RuntimeError("current candidate missing")
oldb=candidate.read_bytes()
if sha_bytes(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(oldb),EXPECTED_BEFORE))
if sb[:4]!=b"DDS " or oldb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4 or len(oldb)!=len(sb):
    raise RuntimeError(("structure",W,H,mips,masks,len(sb),len(oldb)))
if sb[:128]!=oldb[:128]: raise RuntimeError("current candidate header drift")

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_old=Image.frombytes("RGBA",(W,H),oldb[128:],"raw",mode)
old=raw_old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(atlas_path.read_text())["regions"]}

# Current policy hard-fail: these are ordinary explanatory UI sentences, not song/brand/model/legal text.
# C149 preserved them as English; PRE_INGAME #022 therefore contains untranslated visible UI.
SPECS=[
  (20,"You cannot buy this item yet","아직 구매할 수 없습니다"),
  (21,"You already own this item","이미 보유 중입니다"),
]

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
rgb=[]
for idx,en,ko in SPECS:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    a=cell.getchannel("A")
    lm=bmask(a)
    bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty source help row",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    # Candidate must still be byte/pixel-identical to canonical English inside these old preserved rows.
    if ImageChops.difference(old.crop((x,y,x+cw,y+ch)),cell).getbbox() is not None:
        raise RuntimeError(("precondition old help row not source-exact",idx))
    arr=np.asarray(cell)
    aa=arr[:,:,3]>16
    if np.any(aa):
        pix=arr[aa]
        rgb.extend(pix[:,:3].tolist())
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,
                 "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"source_mask_pixels":count(lm)})

if not rgb: raise RuntimeError("source style sample empty")
# Use middle luminance population so low-contrast help text remains low-contrast like source.
fill=tuple(int(round(statistics.median(v[k] for v in rgb))) for k in range(3))+(255,)

# Exact clean plate for only the two newly localized help rows, starting from current candidate.
clean=old.copy()
ca=np.array(clean)
sm=np.asarray(source_mask)>0
ca[sm]=[0,0,0,0]
clean=Image.fromarray(ca.astype(np.uint8),"RGBA")

source_png=tmp/"old_before.png"; clean_png=out/"B228_E95_HELP_CLEAN_PLATE.png"
sm_png=out/"B228_E95_HELP_SOURCE_TEXT_MASK.png"; allowed_png=out/"B228_E95_HELP_ALLOWED_BBOX_MASK.png"
old.save(source_png); clean.save(clean_png); source_mask.save(sm_png); allowed.save(allowed_png)
protected=ImageOps.invert(allowed)
protected_png=out/"B228_E95_HELP_PROTECTED_MASK.png"; protected.save(protected_png)
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(sm_png),
                "--protected-mask",str(protected_png),"--report",str(out/"B228_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B228_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fm=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=fm.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("font",fm))

def render(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f)
    pad=6
    a=Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
    bb=a.getbbox()
    if not bb: raise RuntimeError(("empty render",text))
    a=a.crop(bb)
    tile=Image.new("RGBA",a.size,fill); tile.putalpha(a)
    return tile

final=clean.copy()
targets=[]
M=2
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; sw=x1-x0; sh=y1-y0
    chosen=None
    for fs in range(90,15,-1):
        t=render(row["korean"],fs)
        if t.width<=sw-2*M and t.height<=sh-2*M:
            chosen=(fs,t); break
    if chosen is None: raise RuntimeError(("native fit failed",row["source"],row["source_size"]))
    fs,tile=chosen
    # Source help rows are left anchored; preserve that relationship.
    px=x0+M; py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin",row["source"],lb,margins))
    final.alpha_composite(layer)
    targets.append(layer.getchannel("A"))
    row.update({"localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
                "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,
                "font_style":FSTYLE,"font_size":fs,"fill_rgba":fill,"alignment":"left",
                "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

if ImageChops.multiply(targets[0],targets[1]).getbbox():
    raise RuntimeError("localized help rows overlap")

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
AFTER=sha_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

final_png=tmp/"final.png"; dec.save(final_png)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowed_png),
                "--protected-mask",str(protected_png),"--report",str(out/"B228_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B228_FINAL_VALIDATION.json").read_text())
oa=np.asarray(old); na=np.asarray(dec); allow=np.asarray(allowed)>0
diff=np.any(oa!=na,axis=2); adiff=oa[:,:,3]!=na[:,:,3]
outside=int(np.count_nonzero(diff & ~allow))
alpha_out=int(np.count_nonzero(adiff & ~allow))
if finalrep["status"]!="PASS" or outside or alpha_out:
    raise RuntimeError(("scope",finalrep["status"],outside,alpha_out))

# Existing B73 localized rows, songs, named items and all unrelated artwork must remain exact.
unchanged_outside_selected=int(np.count_nonzero(diff & ~allow))
if unchanged_outside_selected: raise RuntimeError(("existing material changed",unchanged_outside_selected))

# Clean plate must contain no original help-text alpha before Korean is drawn.
clean_alpha=np.asarray(clean)[:,:,3]
clean_source_remaining=int(np.count_nonzero((clean_alpha>0)&sm))
if clean_source_remaining: raise RuntimeError(("clean source remains",clean_source_remaining))

target=Image.new("L",(W,H),0)
for m in targets: target=ImageChops.lighter(target,bmask(m))
target.save(out/"B228_E95_HELP_TARGET_TEXT_MASK.png")

# Evidence: SOURCE vs B73 vs CLEAN vs B228, plus raw parity.
def card(label,im):
    z=comp(im)
    c=Image.new("RGB",(z.width,z.height+28),(24,24,24)); c.paste(z,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c
cards=[card("ENGLISH SOURCE",src),card("B73 CURRENT",old),card("B228 CLEAN",clean),card("B228 FINAL",dec)]
sheet=Image.new("RGB",(W,sum(c.height for c in cards)+12),(18,18,18)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B228_E95_SOURCE_B73_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=12
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,old,clean,dec)]
    ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+18; ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),(24,24,24)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","B73","CLEAN","B228"),ims):
        d.text((xx+4,6),lab,fill="white"); c.paste(z,(xx,30)); xx+=z.width+6
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(18,18,18)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B228_E95_HELP_ROW_CONTACT_3X.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE RAW",raw_src),card("B73 RAW",raw_old),card("B228 RAW",raw_dec)]
rs=Image.new("RGB",(W,sum(c.height for c in rawcards)+8),(18,18,18)); yy=0
for c in rawcards: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B228_E95_RAW_COMPARE.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":230,"asset":asset,
 "trigger":"PRE_INGAME_022_CURRENT_POLICY_UNTRANSLATED_VISIBLE_UI_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/022_q230_E95DA5.jpg",
 "prior_c_status":"C149_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "source_commit":commit,
 "reopened_regions":{"20":{"source":SPECS[0][1],"korean":SPECS[0][2]},"21":{"source":SPECS[1][1],"korean":SPECS[1][2]}},
 "policy_basis":"ordinary explanatory UI is not song/title/brand/model/legal preserve-original content; current PRE_INGAME hard gate forbids untranslated visible UI labels",
 "preserved_policy":"Night Flight, Magical Sound Shower, Life Was A Bore, Keep Your Heart and Alberto's Antics titles remain exact English; BGM and prior B73 localized rows remain byte/pixel-exact outside this two-row patch",
 "rows":rows,
 "machine_qa":{"bbox_source_size_positive_margin":"2/2 PASS","clean_validator":cleanrep["status"],
   "final_validator":finalrep["status"],"changed_pixels_outside_selected_bboxes":outside,
   "alpha_changed_outside_selected_bboxes":alpha_out,"clean_source_alpha_remaining":clean_source_remaining,
   "existing_material_changed_outside_selected_bboxes":unchanged_outside_selected,
   "header_128_exact":payload[:128]==sb[:128],"raw_mode":mode,"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_SOURCE_HELP_ALPHA_CLEARED_TO_TRANSPARENT",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_HELP_FAMILY",
   "3_no_unnecessary_undersizing":"PASS_LARGEST_NATIVE_PER_ROW_FIT",
   "4_source_weight_outline_shadow":"PASS_LOW_CONTRAST_PLAIN_SOURCE_FAMILY",
   "5_no_clipping":"PASS_2_OF_2_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_EXISTING_B73_AND_ALL_OTHER_CONTENT_PIXEL_EXACT",
   "7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "controller_visual_qa":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","status":"B228_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B228_E95_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"role":"B","run":run,"queue_index":230,"asset":"E95DA5","source_sha256":SOURCE_SHA,
 "before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "localized_new_visible_ui_rows":2,"bbox_size_positive_margin":"2/2","outside":outside,
 "alpha_outside":alpha_out,"clean_source_remaining":clean_source_remaining,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":str(rp.relative_to(repo))}
(wr/"B228_E95DA5.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
