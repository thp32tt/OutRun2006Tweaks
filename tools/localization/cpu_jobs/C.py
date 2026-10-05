#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C189-63C91067"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_B/20261005-B-PRODUCTION137"
pr=json.loads((pd/"B137_63C_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]; sp=pr["source_provenance"]

tmp=Path("/tmp/c189"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
srcurl=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}/Release/{asset.split('/')[-2]}/{asset.split('/')[-1]}"
urllib.request.urlretrieve(srcurl,srcdds)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def decode(data):
    if data[:4]!=b"DDS ": raise RuntimeError("not dds")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(data)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw,[W,H],mips,mode
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def saveb64(im,path,q=97):
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True); path.write_text(base64.b64encode(b.getvalue()).decode())

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=sp["source_sha256"]: raise RuntimeError(("source sha drift",sha(sb),sp["source_sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate sha drift",sha(cb),pr["candidate_sha256"]))
src,raw_src,dims,mips,mode=decode(sb); final,raw_final,dims2,mips2,mode2=decode(cb)
if dims!=[2048,2048] or dims2!=dims or mips2!=mips or cb[:128]!=sb[:128]: raise RuntimeError("structure/header drift")
W,H=dims

prodsrc=Image.open(pd/"63C_SOURCE_READABLE.png").convert("RGBA")
if np.any(np.asarray(prodsrc)!=np.asarray(src)): raise RuntimeError("producer source PNG != canonical source decode")
clean=Image.open(pd/"63C_CLEAN_PLATE.png").convert("RGBA")
if clean.size!=src.size: raise RuntimeError("clean plate size drift")

sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
# C-owned exact bboxes established in earlier C160/C184 audits, not inferred from producer masks.
c_rows=[
 {"region_idx":0,"source":"Total Rank","korean":"종합 랭킹","original_bbox":[747,1174,1271,1275]},
 {"region_idx":1,"source":"Total Rank","korean":"종합 랭킹","original_bbox":[599,156,1124,246]}
]
allowed=np.zeros((H,W),bool)
for r in c_rows:
    x0,y0,x1,y1=r["original_bbox"]; allowed[y0:y1,x0:x1]=True

clean_changed=np.any(ca!=sa,axis=2)
final_changed=np.any(fa!=sa,axis=2)
render=np.any(fa!=ca,axis=2)
machine={
 "clean_changed_outside_c_exact_bboxes":count(clean_changed&~allowed),
 "final_changed_outside_c_exact_bboxes":count(final_changed&~allowed),
 "clean_alpha_changed_outside_c_exact_bboxes":count((ca[:,:,3]!=sa[:,:,3])&~allowed),
 "final_alpha_changed_outside_c_exact_bboxes":count((fa[:,:,3]!=sa[:,:,3])&~allowed),
 "render_outside_c_exact_bboxes":count(render&~allowed)
}

rowchecks=[]
render_masks=[]
for r in c_rows:
    x0,y0,x1,y1=r["original_bbox"]
    local_render=render[y0:y1,x0:x1]
    bb=bbox(local_render)
    if bb is None:
        actual=None
    else:
        actual=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
    # Independently derive a source-title mask from the unique navy outline plus adjacent white fill.
    rgb=sa[y0:y1,x0:x1,:3]
    alpha=sa[y0:y1,x0:x1,3]>0
    navy=(rgb[:,:,0]<45)&(rgb[:,:,1]<55)&(rgb[:,:,2]<110)&alpha
    white=(rgb.min(axis=2)>220)&((rgb.max(axis=2)-rgb.min(axis=2))<35)&alpha
    navy_img=Image.fromarray((navy.astype(np.uint8)*255),"L")
    near=np.asarray(navy_img.filter(ImageFilter.MaxFilter(17)))>0
    title=(navy | (white&near))
    # retain components tied to navy; title mask itself is already within exact C bbox.
    # guard current Korean pixels with 2px neighborhood so only old-source residue outside Korean is counted.
    rend=local_render
    guard=np.asarray(Image.fromarray((rend.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    unchanged_clean=title & np.all(ca[y0:y1,x0:x1]==sa[y0:y1,x0:x1],axis=2)
    unchanged_final=title & np.all(fa[y0:y1,x0:x1]==sa[y0:y1,x0:x1],axis=2) & ~guard
    if actual:
        a,b,c,d=actual
        dl=a-x0; dr=x1-c; dt=b-y0; db=y1-d
        contain=(a>=x0 and b>=y0 and c<=x1 and d<=y1)
        size=(c-a<=x1-x0 and d-b<=y1-y0)
        positive=min(dl,dr,dt,db)>0
    else:
        dl=dr=dt=db=-1; contain=size=positive=False
    rc={
      **r,
      "independent_localized_bbox":actual,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "independent_source_title_mask_pixels":count(title),
      "source_title_pixels_unchanged_in_clean":count(unchanged_clean),
      "source_title_pixels_unchanged_in_final_outside_korean_guard":count(unchanged_final),
      "clean_changed_pixels_in_bbox":count(clean_changed[y0:y1,x0:x1]),
      "render_pixels_in_bbox":count(local_render)
    }
    rowchecks.append(rc)
    m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=local_render; render_masks.append(m)

machine["localized_pair_overlap_pixels"]=count(render_masks[0]&render_masks[1])
d0=np.asarray(Image.fromarray((render_masks[0].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
machine["localized_pair_1px_touch_pixels"]=count(d0&render_masks[1])
machine["source_title_pixels_unchanged_in_clean_total"]=sum(x["source_title_pixels_unchanged_in_clean"] for x in rowchecks)
machine["source_title_pixels_unchanged_in_final_outside_korean_guard_total"]=sum(x["source_title_pixels_unchanged_in_final_outside_korean_guard"] for x in rowchecks)

# Edge continuity diagnostics: compare clean inside exact bbox edge against canonical source just outside.
edge=[]
for r in c_rows:
    x0,y0,x1,y1=r["original_bbox"]; vals=[]
    pairs=[
      ("left",ca[y0:y1,x0,:3],sa[y0:y1,max(0,x0-1),:3]),
      ("right",ca[y0:y1,x1-1,:3],sa[y0:y1,min(W-1,x1),:3]),
      ("top",ca[y0,x0:x1,:3],sa[max(0,y0-1),x0:x1,:3]),
      ("bottom",ca[y1-1,x0:x1,:3],sa[min(H-1,y1),x0:x1,:3])
    ]
    for name,ii,oo in pairs:
        ii=np.asarray(ii,dtype=np.float32); oo=np.asarray(oo,dtype=np.float32)
        vals.append({"edge":name,"mean_abs_rgb_jump":float(np.mean(np.abs(ii-oo))),"max_abs_rgb_jump":int(np.max(np.abs(ii-oo)))})
    edge.append({"region_idx":r["region_idx"],"edges":vals})

hard_zero=[
 "clean_changed_outside_c_exact_bboxes","final_changed_outside_c_exact_bboxes",
 "clean_alpha_changed_outside_c_exact_bboxes","final_alpha_changed_outside_c_exact_bboxes",
 "render_outside_c_exact_bboxes","localized_pair_overlap_pixels","localized_pair_1px_touch_pixels",
 "source_title_pixels_unchanged_in_clean_total","source_title_pixels_unchanged_in_final_outside_korean_guard_total"
]
rows_pass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in rowchecks)
status="PASS" if rows_pass and all(machine[k]==0 for k in hard_zero) else "FAIL"

font=ImageFont.load_default(); evidence=[]
# High-detail SOURCE/CLEAN/FINAL around each title, 2x enlargement to expose interpolation/seam artifacts.
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; padx=150; pady=95
    crop=(max(0,x0-padx),max(0,y0-pady),min(W,x1+padx),min(H,y1+pady))
    ims=[comp(z).crop(crop) for z in (src,clean,final)]
    ims=[im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST) for im in ims]
    cw=max(z.width for z in ims); ch=max(z.height for z in ims)
    sheet=Image.new("RGB",(cw*3,ch+34),"white"); d=ImageDraw.Draw(sheet)
    for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),ims)):
        sheet.paste(z,(k*cw,34)); d.text((k*cw+6,7),lab,fill="black",font=font)
    fn=out/f"C189_ROW{rc['region_idx']}_DETAIL_B64.txt"; saveb64(sheet,fn,98); evidence.append(str(fn.relative_to(repo)))

overview=Image.new("RGB",(1536,530),"white"); d=ImageDraw.Draw(overview)
for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),(src,clean,final))):
    zz=comp(z).resize((512,512),Image.Resampling.LANCZOS); overview.paste(zz,(k*512,18)); d.text((k*512+6,2),lab,fill="black",font=font)
fn=out/"C189_OVERVIEW_B64.txt"; saveb64(overview,fn,95); evidence.append(str(fn.relative_to(repo)))

rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(zz,(0,i*1035+22)); ImageDraw.Draw(rawcard).text((5,i*1035+4),lab,fill="black")
fn=out/"C189_RAW_B64.txt"; saveb64(rawcard,fn,94); evidence.append(str(fn.relative_to(repo)))

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C189","queue_index":pr["queue_index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
 "independent_source_decode_matches_producer_png":True,
 "structure":{"dimensions":dims,"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "c_exact_bboxes_source":"prior C160/C184 established geometry",
 "row_checks":rowchecks,"all_2_bbox_size_positive_margin_pass":rows_pass,
 "machine_checks":machine,"edge_continuity_proxy":edge,
 "machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C189_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED","preview_b64_files":evidence
}
(out/"C189_63C91067_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C189_63C91067.json").write_text(json.dumps({
 "run":run,"qa_id":"C189","index":pr["queue_index"],"asset":"63C91067","candidate_sha256":pr["candidate_sha256"],
 "machine_status":status,"machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C189_63C91067_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C189","machine_status":status,"machine_checks":machine,"row_checks":rowchecks},ensure_ascii=False))
