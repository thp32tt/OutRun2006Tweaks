#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C177-37759842"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

producer_dir=repo/"localization/graphics/role_A/20261005-A-PRODUCTION34"
producer_report=json.loads((producer_dir/"A34_37759842_REPORT.json").read_text())
asset=producer_report["asset"]
candidate=repo/producer_report["candidate_path"]
source_commit=producer_report["source_provenance"]["commit"]
source_rel=producer_report["source_provenance"]["path"]
expected_source_sha=producer_report["source_provenance"]["sha256"]
expected_candidate_sha=producer_report["candidate_sha256"]
source_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{source_commit}/{source_rel}"
tmp=Path("/tmp/c177"); tmp.mkdir(exist_ok=True)
source_dds=tmp/"source.dds"
urllib.request.urlretrieve(source_url,source_dds)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def decode_rgba32(data):
    if data[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(data)!=128+W*H*4:
        raise RuntimeError(("unsupported structure",W,H,mips,masks,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw,{"dimensions":[W,H],"mipmaps":mips,"mode":mode,"header":data[:128]}
def bm(im): return np.asarray(im.convert("L"))>0

sb=source_dds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=expected_source_sha: raise RuntimeError(("source sha drift",sha(sb),expected_source_sha))
if sha(cb)!=expected_candidate_sha: raise RuntimeError(("candidate sha drift",sha(cb),expected_candidate_sha))
src,raw_src,ss=decode_rgba32(sb); final,raw_final,cs=decode_rgba32(cb)
if ss["dimensions"]!=[4096,4096] or cs["dimensions"]!=ss["dimensions"] or cs["mipmaps"]!=ss["mipmaps"] or cb[:128]!=sb[:128]:
    raise RuntimeError(("structure mismatch",ss,cs,cb[:128]==sb[:128]))
W,H=ss["dimensions"]
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)

# Cross-check the producer's decoded source evidence against an independently downloaded canonical DDS.
prod_source=Image.open(producer_dir/"37759842_HD_SOURCE_READABLE.png").convert("RGBA")
if ImageChops.difference(src,prod_source).getbbox():
    raise RuntimeError("producer source PNG differs from independently decoded canonical DDS")
clean=Image.open(producer_dir/"37759842_HD_CLEAN_PLATE.png").convert("RGBA")
ca=np.asarray(clean,dtype=np.uint8)
if clean.size!=(W,H): raise RuntimeError("clean size drift")

source_core=bm(Image.open(producer_dir/"37759842_HD_SOURCE_CORE_MASK.png"))
protected=bm(Image.open(producer_dir/"37759842_HD_PROTECTED_VISIBLE_MASK.png"))

rows=producer_report["rows"]
allowed=np.zeros((H,W),bool)
row_checks=[]
for r in rows:
    ob=[int(v) for v in r["source_effect_bbox"]]
    lb=[int(v) for v in r["localized_bbox"]]
    x0,y0,x1,y1=ob; lx0,ly0,lx1,ly1=lb
    allowed[y0:y1,x0:x1]=True
    dl=lx0-x0; dr=x1-lx1; dt=ly0-y0; db=y1-ly1
    row_checks.append({
        "idx":r["idx"],"source_effect_bbox":ob,"localized_bbox":lb,
        "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
        "containment":"PASS" if lx0>=x0 and ly0>=y0 and lx1<=x1 and ly1<=y1 else "FAIL",
        "size_ceiling":"PASS" if (lx1-lx0)<= (x1-x0) and (ly1-ly0)<= (y1-y0) else "FAIL",
        "positive_margin":"PASS" if min(dl,dr,dt,db)>0 else "FAIL",
        "korean_lines":r.get("korean_lines"),"style":r.get("style")
    })
if len(row_checks)!=33 or any(x["containment"]!="PASS" or x["size_ceiling"]!="PASS" or x["positive_margin"]!="PASS" for x in row_checks):
    raise RuntimeError("row containment/size/margin failure")

clean_diff=np.any(ca!=sa,axis=2)
final_diff=np.any(fa!=sa,axis=2)
alpha_clean=ca[:,:,3]!=sa[:,:,3]
alpha_final=fa[:,:,3]!=sa[:,:,3]
clean_out=count(clean_diff & ~allowed)
final_out=count(final_diff & ~allowed)
clean_alpha_out=count(alpha_clean & ~allowed)
final_alpha_out=count(alpha_final & ~allowed)
protected_clean=count(clean_diff & protected)
protected_final=count(final_diff & protected)
clean_core_unchanged=count(source_core & np.all(ca==sa,axis=2))

# Derive actual Korean-render pixels from clean->final, not from producer's render mask.
render=np.any(fa!=ca,axis=2)
render_out=count(render & ~allowed)
# Any unchanged canonical source-core pixel that is not covered/touched by Korean rendering is residue.
render_guard=np.asarray(Image.fromarray((render.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
source_residue=count(source_core & np.all(fa==sa,axis=2) & ~render_guard)

# Exact pairwise label separation check from per-row render slices.
row_render=[]
for rc in row_checks:
    x0,y0,x1,y1=rc["source_effect_bbox"]
    m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=render[y0:y1,x0:x1]
    row_render.append(m)
overlap=0; touch=0
for i in range(len(row_render)):
    mi=row_render[i]
    di=np.asarray(Image.fromarray((mi.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(row_render)):
        mj=row_render[j]
        overlap += count(mi & mj)
        touch += count(di & mj)
protected_render=count(render & protected)
near_protected=np.asarray(Image.fromarray((protected.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
render_near_protected=count(render & near_protected)

machine={
 "clean_changed_outside_union_source_bboxes":clean_out,
 "final_changed_outside_union_source_bboxes":final_out,
 "clean_alpha_outside_union_source_bboxes":clean_alpha_out,
 "final_alpha_outside_union_source_bboxes":final_alpha_out,
 "protected_clean_changed":protected_clean,
 "protected_final_changed":protected_final,
 "clean_source_core_unchanged":clean_core_unchanged,
 "source_core_residue_pixels":source_residue,
 "render_outside_union_source_bboxes":render_out,
 "localized_pair_overlap_pixels":overlap,
 "localized_pair_1px_touch_pixels":touch,
 "localized_render_on_protected_pixels":protected_render,
 "localized_render_1px_near_protected_pixels":render_near_protected
}
if any(machine.values()):
    status="FAIL"
else:
    status="PASS"

# Generate controller-review contact sheets in three groups. Each row is SOURCE | CLEAN | FINAL.
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

font=ImageFont.load_default()
preview_files=[]
groups=[row_checks[0:11],row_checks[11:22],row_checks[22:33]]
for gi,grp in enumerate(groups,1):
    row_cards=[]
    for rc in grp:
        x0,y0,x1,y1=rc["source_effect_bbox"]
        pad=24
        crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
        ims=[comp(im).crop(crop) for im in (src,clean,final)]
        target_h=min(220,max(100,max(im.height for im in ims)))
        resized=[]
        for im in ims:
            if im.height>target_h:
                nw=max(1,round(im.width*target_h/im.height)); im=im.resize((nw,target_h),Image.Resampling.LANCZOS)
            resized.append(im)
        panel_w=max(360,max(im.width for im in resized))
        card=Image.new("RGB",(panel_w*3+24,target_h+34),"white")
        d=ImageDraw.Draw(card)
        labels=["SOURCE","CLEAN","FINAL"]
        for ci,im in enumerate(resized):
            ox=ci*panel_w+8
            card.paste(im,(ox,28))
            d.text((ox,6),labels[ci],fill="black",font=font)
        d.text((panel_w*2+130,6),f"idx {rc['idx']}  {' / '.join(rc.get('korean_lines') or [])}",fill="black",font=font)
        row_cards.append(card)
    sheet=Image.new("RGB",(max(c.width for c in row_cards),sum(c.height for c in row_cards)+8*(len(row_cards)-1)),"white")
    yy=0
    for c in row_cards:
        sheet.paste(c,(0,yy)); yy+=c.height+8
    # cap width for compact transfer while retaining row detail
    if sheet.width>1800:
        nh=round(sheet.height*1800/sheet.width); sheet=sheet.resize((1800,nh),Image.Resampling.LANCZOS)
    jpg=io.BytesIO(); sheet.save(jpg,format="JPEG",quality=92,optimize=True)
    b64=base64.b64encode(jpg.getvalue()).decode("ascii")
    txt=out/f"C177_CONTACTS_{gi}_B64.txt"; txt.write_text(b64)
    preview_files.append(str(txt.relative_to(repo)))

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C177","queue_index":producer_report["index"],"asset":asset,
 "producer_run":producer_report["run"],"producer_candidate_sha256":expected_candidate_sha,
 "source_provenance":producer_report["source_provenance"],
 "independent_source_decode_matches_producer_png":True,
 "structure":{"dimensions":ss["dimensions"],"format":"RGBA32","mipmaps":ss["mipmaps"],"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "row_checks":row_checks,"all_33_bbox_size_positive_margin_pass":all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in row_checks),
 "machine_checks":machine,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C177_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED","preview_b64_files":preview_files
}
(out/"C177_37759842_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C177_37759842.json").write_text(json.dumps({
 "run":run,"qa_id":"C177","index":producer_report["index"],"asset":"37759842",
 "candidate_sha256":expected_candidate_sha,"machine_status":status,
 "all_33_bbox_size_positive_margin_pass":report["all_33_bbox_size_positive_margin_pass"],
 "machine_checks":machine,
 "report":f"localization/graphics/role_C/{run}/C177_37759842_MACHINE_QA.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C177","machine_status":status,"machine_checks":machine,"previews":preview_files},ensure_ascii=False))
