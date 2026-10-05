#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C184-63C91067"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_B/20261005-B-PRODUCTION135"
pr=json.loads((pd/"B135_63C_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]
sp=pr["source_provenance"]; expected_source_sha=sp["source_sha256"]; expected_candidate_sha=pr["candidate_sha256"]
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
tmp=Path("/tmp/c181"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
urllib.request.urlretrieve(f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}/Release/{folder}/{name}",srcdds)

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
def saveb64(im,path,q=96):
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True); path.write_text(base64.b64encode(b.getvalue()).decode())

sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=expected_source_sha: raise RuntimeError(("source sha drift",sha(sb),expected_source_sha))
if sha(cb)!=expected_candidate_sha: raise RuntimeError(("candidate sha drift",sha(cb),expected_candidate_sha))
src,raw_src,dims,mips,mode=decode(sb); final,raw_final,dims2,mips2,mode2=decode(cb)
if dims!=[2048,2048] or dims2!=dims or mips2!=mips or cb[:128]!=sb[:128]: raise RuntimeError("structure/header drift")
W,H=dims
prodsrc=Image.open(pd/"63C_SOURCE_READABLE.png").convert("RGBA")
if ImageChops.difference(src,prodsrc).getbbox(): raise RuntimeError("producer source PNG != canonical source decode")
clean=Image.open(pd/"63C_CLEAN_PLATE.png").convert("RGBA")
sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
rows=pr["rows"]; allowed=np.zeros((H,W),bool); rowchecks=[]
for r in rows:
    ob=[int(v) for v in r["original_bbox"]]; lb=[int(v) for v in r["localized_bbox"]]
    x0,y0,x1,y1=ob; a,b,c,d=lb; allowed[y0:y1,x0:x1]=True
    dl,dr,dt,db=a-x0,x1-c,b-y0,y1-d
    rowchecks.append({"region_idx":r["region_idx"],"source":r["source"],"korean":r["korean"],
      "original_bbox":ob,"localized_bbox":lb,"delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if a>=x0 and b>=y0 and c<=x1 and d<=y1 else "FAIL",
      "size_ceiling":"PASS" if c-a<=x1-x0 and d-b<=y1-y0 else "FAIL",
      "positive_margin":"PASS" if min(dl,dr,dt,db)>0 else "FAIL"})
if len(rowchecks)!=2: raise RuntimeError(("rows",len(rowchecks)))
cdiff=np.any(ca!=sa,axis=2); fdiff=np.any(fa!=sa,axis=2); render=np.any(fa!=ca,axis=2)
machine={
 "clean_changed_outside_union_source_bboxes":count(cdiff&~allowed),
 "final_changed_outside_union_source_bboxes":count(fdiff&~allowed),
 "clean_alpha_outside_union_source_bboxes":count((ca[:,:,3]!=sa[:,:,3])&~allowed),
 "final_alpha_outside_union_source_bboxes":count((fa[:,:,3]!=sa[:,:,3])&~allowed),
 "render_outside_union_source_bboxes":count(render&~allowed)
}
protected=np.asarray(Image.open(pd/"63C_PROTECTED_MASK.png").convert("L"))>0
machine["protected_clean_changed"]=count(cdiff&protected)
machine["protected_final_changed"]=count(fdiff&protected)
# Independent residue test from every pixel actually removed in CLEAN, guarded only by current Korean render.
removed=cdiff&allowed
guard=np.asarray(Image.fromarray((render.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
machine["removed_source_pixels_unchanged_in_final_outside_korean_guard"]=count(removed & np.all(fa==sa,axis=2) & ~guard)
# Per-row residue and separation.
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; rm=np.zeros((H,W),bool); rm[y0:y1,x0:x1]=True
    rc["clean_changed_pixels"]=count(cdiff&rm)
    rc["source_equal_final_outside_korean_guard"]=count(rm & np.all(fa==sa,axis=2) & cdiff & ~guard)
masks=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=render[y0:y1,x0:x1]; masks.append(m)
machine["localized_pair_overlap_pixels"]=count(masks[0]&masks[1])
d0=np.asarray(Image.fromarray((masks[0].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
machine["localized_pair_1px_touch_pixels"]=count(d0&masks[1])

# Boundary continuity proxy: clean immediately inside each bbox edge vs source immediately outside edge.
# This catches abrupt rectangular seams without judging patterned interior semantics.
edge_stats=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; vals=[]
    # compare RGB mean absolute difference between clean inner edge and nearest source outer edge.
    for label,inner,outer in [
      ("left",ca[y0:y1,x0,:3],sa[y0:y1,max(0,x0-1),:3]),
      ("right",ca[y0:y1,x1-1,:3],sa[y0:y1,min(W-1,x1),:3]),
      ("top",ca[y0,x0:x1,:3],sa[max(0,y0-1),x0:x1,:3]),
      ("bottom",ca[y1-1,x0:x1,:3],sa[min(H-1,y1),x0:x1,:3])]:
        ii=np.asarray(inner,dtype=np.float32); oo=np.asarray(outer,dtype=np.float32)
        vals.append({"edge":label,"mean_abs_rgb_jump":float(np.mean(np.abs(ii-oo))),"max_abs_rgb_jump":int(np.max(np.abs(ii-oo)))})
    edge_stats.append({"region_idx":rc["region_idx"],"edges":vals})

hard_zero=["clean_changed_outside_union_source_bboxes","final_changed_outside_union_source_bboxes","clean_alpha_outside_union_source_bboxes","final_alpha_outside_union_source_bboxes","render_outside_union_source_bboxes","protected_clean_changed","protected_final_changed","removed_source_pixels_unchanged_in_final_outside_korean_guard","localized_pair_overlap_pixels","localized_pair_1px_touch_pixels"]
rowpass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" and x["source_equal_final_outside_korean_guard"]==0 for x in rowchecks)
status="PASS" if rowpass and all(machine[k]==0 for k in hard_zero) else "FAIL"

font=ImageFont.load_default(); evidence=[]
# high-detail per-row SOURCE/CLEAN/FINAL with generous surrounding patterned plate context.
for i,rc in enumerate(rowchecks):
    x0,y0,x1,y1=rc["original_bbox"]; padx=180; pady=100
    crop=(max(0,x0-padx),max(0,y0-pady),min(W,x1+padx),min(H,y1+pady))
    ims=[comp(z).crop(crop) for z in (src,clean,final)]
    cw,ch=ims[0].size
    sheet=Image.new("RGB",(cw*3,ch+30),"white"); d=ImageDraw.Draw(sheet)
    for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),ims)):
        sheet.paste(z,(k*cw,30)); d.text((k*cw+5,6),lab,fill="black",font=font)
    fn=out/f"C184_ROW{i}_DETAIL_B64.txt"; saveb64(sheet,fn,97); evidence.append(str(fn.relative_to(repo)))
# overview source/clean/final downscaled.
overview=Image.new("RGB",(1536,530),"white"); od=ImageDraw.Draw(overview)
for k,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),(src,clean,final))):
    zz=comp(z).resize((512,512),Image.Resampling.LANCZOS); overview.paste(zz,(k*512,18)); od.text((k*512+5,2),lab,fill="black",font=font)
fn=out/"C184_OVERVIEW_B64.txt"; saveb64(overview,fn,94); evidence.append(str(fn.relative_to(repo)))
rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(zz,(0,i*1035+22)); ImageDraw.Draw(rawcard).text((5,i*1035+4),lab,fill="black")
fn=out/"C184_RAW_B64.txt"; saveb64(rawcard,fn,92); evidence.append(str(fn.relative_to(repo)))

report={"schema_version":1,"role":"C","run":run,"qa_id":"C184","queue_index":pr["queue_index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":expected_source_sha,"candidate_sha256":expected_candidate_sha,
 "independent_source_decode_matches_producer_png":True,
 "structure":{"dimensions":dims,"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "row_checks":rowchecks,"all_2_bbox_size_positive_margin_pass":rowpass,"machine_checks":machine,"edge_continuity_proxy":edge_stats,
 "machine_status":status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C184_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED","preview_b64_files":evidence}
(out/"C184_63C91067_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C184_63C91067.json").write_text(json.dumps({"run":run,"qa_id":"C184","index":pr["queue_index"],"asset":"63C91067","candidate_sha256":expected_candidate_sha,"machine_status":status,"machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C184_63C91067_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C184","machine_status":status,"machine_checks":machine,"edge_continuity_proxy":edge_stats},ensure_ascii=False))
