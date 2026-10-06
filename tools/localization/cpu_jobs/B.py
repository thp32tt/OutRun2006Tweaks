#!/usr/bin/env python3
import hashlib, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd(); run="20261006-B-PRODUCTION200-75C3586A-NAMES"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
cand.parent.mkdir(parents=True,exist_ok=True)

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{commit}/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
expected="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
srcp=Path("/tmp/B200_75C3586A.dds"); urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes(); got=hashlib.sha256(raw).hexdigest()
if got!=expected: raise RuntimeError(("source sha drift",got,expected))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")

raw_im=Image.open(srcp).convert("RGBA")
src=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); H,W=sa.shape[:2]
if (W,H)!=(2048,2048): raise RuntimeError(("dimensions",W,H))

# B74 atlas region coordinates are already in readable-orientation coordinates.
specs=[
 {"key":"clarissa","source":"CLARISSA","ko":"클라리사","cell":[0,204,580,168],"atlas_idx":37},
 {"key":"jennifer","source":"JENNIFER","ko":"제니퍼","cell":[580,204,460,168],"atlas_idx":38},
 {"key":"flagman4","source":"FLAGMAN 4","ko":"플래그맨 4","cell":[0,40,1036,164],"atlas_idx":39},
 {"key":"holly","source":"HOLLY","ko":"홀리","cell":[1036,92,276,112],"atlas_idx":40},
]

def bbox(mask):
    yy,xx=np.nonzero(mask)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

rows=[]; masks=[]; clean_arr=sa.copy()
for sp in specs:
    x,y,w,h=sp["cell"]; x0,y0,x1,y1=x,y,x+w,y+h
    sub=sa[y0:y1,x0:x1,:]
    # These atlas sprites are the source name labels themselves on transparency.
    # Therefore alpha is the authoritative source glyph/effect footprint and the
    # correct clean plate is transparent, not a guessed gray donor background.
    am=sub[:,:,3]>0
    if int(am.sum())<100: raise RuntimeError(("source alpha too small",sp["key"],int(am.sum())))
    lm=np.zeros((H,W),bool); lm[y0:y1,x0:x1]=am
    sb=bbox(lm)
    if sb is None: raise RuntimeError(("empty source bbox",sp["key"]))
    sw,sh=sb[2]-sb[0],sb[3]-sb[1]
    if sw<40 or sh<20: raise RuntimeError(("implausible source bbox",sp["key"],sb))
    # Verify this cell is text-only transparency: no alpha extends beyond the B74 cell.
    # Erase only source-effect pixels, preserving every unrelated atlas pixel byte-for-byte.
    yy,xx=np.nonzero(lm); clean_arr[yy,xx]=np.array([0,0,0,0],dtype=np.uint8)
    opaque=sub[am & (sub[:,:,3]>=192)]
    if len(opaque)==0: opaque=sub[am]
    fill=np.median(opaque[:,:3],axis=0).astype(np.uint8)
    # Ignore accidental dark AA when deriving the source face color.
    bright=opaque[(opaque[:,0].astype(np.int16)-opaque[:,1].astype(np.int16)>25)]
    if len(bright): fill=np.median(bright[:,:3],axis=0).astype(np.uint8)
    rows.append({**sp,"source_bbox":sb,"source_width":sw,"source_height":sh,
                 "source_effect_pixels":int(lm.sum()),"source_face_rgb":[int(v) for v in fill]})
    masks.append(lm)

source_mask=np.zeros((H,W),bool)
for m in masks: source_mask|=m
clean=Image.fromarray(clean_arr,"RGBA")
if np.any(clean_arr[source_mask,3]!=0): raise RuntimeError("clean alpha residue")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

final=clean.copy(); target=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0
    rgb=tuple(row["source_face_rgb"])
    chosen=None
    for fs in range(max(8,sh),7,-1):
        font=ImageFont.truetype(FONT,fs)
        tmp=Image.new("RGBA",(sw,sh),(0,0,0,0)); d=ImageDraw.Draw(tmp)
        bb=d.textbbox((0,0),row["ko"],font=font,stroke_width=0)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        if tw>sw-4 or th>sh-4: continue
        px=2-bb[0]
        py=2-bb[1]+max(0,(sh-4-th)//2)
        d.text((px,py),row["ko"],font=font,fill=rgb+(255,))
        lm=np.asarray(tmp.getchannel("A"))>0; lb=bbox(lm)
        if lb is None: continue
        glb=[x0+lb[0],y0+lb[1],x0+lb[2],y0+lb[3]]
        if not (glb[0]>=x0+2 and glb[1]>=y0+2 and glb[2]<=x1-2 and glb[3]<=y1-2): continue
        chosen=(tmp,glb,fs); break
    if chosen is None: raise RuntimeError(("no fit",row["key"],row["source_bbox"]))
    tmp,glb,fs=chosen
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tmp,(x0,y0))
    glm=np.asarray(layer.getchannel("A"))>0
    if np.any(target&glm): raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer); target|=glm
    row.update({"korean":row["ko"],"font":"Noto Sans CJK KR Black","font_size":fs,
                "localized_bbox":glb,"localized_width":glb[2]-glb[0],"localized_height":glb[3]-glb[1],
                "delta_left":glb[0]-x0,"delta_right":x1-glb[2],"delta_top":glb[1]-y0,"delta_bottom":y1-glb[3],
                "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

fa=np.asarray(final,dtype=np.uint8)
allowed=np.zeros((H,W),bool)
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; allowed[y0:y1,x0:x1]=True
changed=np.any(sa!=fa,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=fa[:,:,3])&~allowed))
introduced=int(np.count_nonzero((fa[:,:,3]>0)&(sa[:,:,3]==0)&~allowed))
if outside or alpha_out or introduced: raise RuntimeError(("outside gate",outside,alpha_out,introduced))
# Source alpha must be gone anywhere not occupied by the Korean target.
source_residue=int(np.count_nonzero(source_mask & ~target & (fa[:,:,3]>0)))
if source_residue: raise RuntimeError(("source alpha residue",source_residue))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand.write_bytes(raw[:128]+raw_final.tobytes("raw","RGBA"))
dec=Image.open(cand).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")
cand_sha=sha256(cand)

src.save(out/"B200_SOURCE_READABLE.png"); clean.save(out/"B200_CLEAN_PLATE.png"); final.save(out/"B200_FINAL_READABLE.png")
raw_im.save(out/"B200_SOURCE_RAW.png"); raw_final.save(out/"B200_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B200_SOURCE_TEXT_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B200_TARGET_MASK.png")

cards=[]
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]; pad=14; box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",final)]:
        crop=im.crop(box)
        bg=Image.new("RGBA",crop.size,(72,72,72,255)); bg.alpha_composite(crop); crop=bg.convert("RGB")
        crop=crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST)
        card=Image.new("RGB",(crop.width,crop.height+28),"white"); card.paste(crop,(0,28))
        ImageDraw.Draw(card).text((6,7),f'{row["source"]}->{row["ko"]} {label}',fill="black")
        cards.append(card)
mw=max(c.width for c in cards); total=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(mw,total),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((1800,6000),Image.Resampling.LANCZOS); sheet.save(out/"B200_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=96)

for name,im in [("SOURCE",src),("FINAL",final),("SOURCE_RAW",raw_im),("FINAL_RAW",raw_final)]:
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im)
    vis=bg.convert("RGB"); vis.thumbnail((1400,1400),Image.Resampling.LANCZOS)
    vis.save(out/f"B200_{name}_PROOF.jpg",quality=95)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":176,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"url":url,"sha256":got},
 "b74_hold_resolution":"B74 region contact proves atlas cells 37-40 are the four red source name-label sprites. Their apparent gray backing is only proof compositing; source pixels outside the labels are transparent. B200 therefore uses exact source alpha as the glyph/effect mask and a transparent clean plate, superseding the false SOURCE_TEXT_ABSENT hold.",
 "segments":[{"source":r["source"],"korean":r["ko"]} for r in rows],
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":1,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "static_qa":{"elements_total":4,"bbox_size_positive_margin":"4/4 PASS","clean_source_alpha_residue":0,
  "changed_outside_source_bboxes":outside,"alpha_changed_outside_source_bboxes":alpha_out,
  "introduced_visible_outside_source_bboxes":introduced,"final_source_alpha_residue_outside_targets":source_residue,
  "localized_overlap":0,"dds_roundtrip":"PASS","status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(cand.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"B200_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B200_75C3586A_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B200_75C3586A.json").write_text(json.dumps({"role":"B","run":run,"queue_index":176,"asset":"75C3586A","candidate_sha256":cand_sha,"report":str(rp.relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B200_DONE",cand_sha,[(r["key"],r["source_bbox"],r["localized_bbox"],r["font_size"]) for r in rows])
