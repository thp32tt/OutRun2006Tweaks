#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C155-30CF0D"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
adir=repo/"localization/graphics/role_A/20261005-A-PRODUCTION22"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="a17e3caff8610356d70ddc52e89a7533aa99b98c"
SOURCE_SHA256="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
CANDIDATE_SHA256="6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b"

tmp=Path("/tmp/outrun_C155"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds",sp)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=1; return m
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("provenance/hash drift",gitblob(sb),sha(sb),sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS structure/header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or mode!="BGRA": raise RuntimeError(("structure",W,H,pitch,mips,masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); raw_fin=Image.frombytes("RGBA",(W,H),cb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
prod_clean=np.asarray(Image.open(adir/"30CF0D_HD_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)

rows=[
 ("manual_large",2,"MANUAL","수동",[0,220,888,96]),
 ("automatic_large",3,"AUTOMATIC","자동",[888,220,888,96]),
 ("manual_small",4,"MANUAL","수동",[0,136,808,84]),
 ("automatic_small",5,"AUTOMATIC","자동",[808,136,808,84]),
 ("select_transmission",6,"SELECT TRANSMISSION","변속 방식 선택",[0,56,1276,80]),
 ("transmission_small",7,"TRANSMISSION","변속 방식",[1276,88,508,48]),
]

source_masks=[]; allowed_masks=[]; result_rows=[]
for key,idx,en,ko,cell in rows:
    x,y,cw,ch=cell
    local=sa[y:y+ch,x:x+cw,3]>0
    bb=bbox(local)
    if not bb: raise RuntimeError(("empty source alpha",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    sm=np.zeros((H,W),bool); sm[y:y+ch,x:x+cw]=local
    source_masks.append(sm); allowed_masks.append(rect((H,W),ob))
    result_rows.append({"key":key,"region_idx":idx,"source":en,"korean":ko,"cell":cell,"original_bbox":ob,"source_visible_pixels":count(local)})

source_mask=np.logical_or.reduce(source_masks); allowed=np.logical_or.reduce(allowed_masks)

clean_alpha_residue=count(source_mask & (prod_clean[:,:,3]>0))
clean_changed=np.any(prod_clean!=sa,axis=2)
clean_outside=count(clean_changed & ~allowed)
clean_alpha_outside=count((prod_clean[:,:,3]!=sa[:,:,3]) & ~allowed)
if any([clean_alpha_residue,clean_outside,clean_alpha_outside]):
    raise RuntimeError(("clean gates",clean_alpha_residue,clean_outside,clean_alpha_outside))

expected_clean=sa.copy(); expected_clean[source_mask,3]=0
clean_img=Image.fromarray(expected_clean,"RGBA")

target_masks=[]; final_rows=[]
for i,r in enumerate(result_rows):
    am=allowed_masks[i]
    tm=(fa[:,:,3]>0)&am
    lb=bbox(tm)
    if not lb: raise RuntimeError(("missing target",r["region_idx"]))
    ob=r["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0: raise RuntimeError(("bbox/size/margin",r["region_idx"],ob,lb,d))
    target_masks.append(tm)
    final_rows.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

target=np.logical_or.reduce(target_masks)
final_diff=np.any(fa!=sa,axis=2); alpha_diff=fa[:,:,3]!=sa[:,:,3]
outside=count(final_diff&~allowed); alpha_out=count(alpha_diff&~allowed)
equal_source=np.all(fa==sa,axis=2); source_residue=count(source_mask&~target&equal_source)
render_diff=np.any(fa!=prod_clean,axis=2)
render_out=count(render_diff&~target)

overlap=0; touch=[]
for i in range(len(target_masks)):
    ag=np.asarray(Image.fromarray((target_masks[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(target_masks)):
        ov=count(target_masks[i]&target_masks[j]); near=count(ag&target_masks[j]); overlap+=ov
        if ov or near: touch.append([final_rows[i]["region_idx"],final_rows[j]["region_idx"],ov,near])

if any([outside,alpha_out,source_residue,render_out,overlap]) or touch:
    raise RuntimeError(("final gates",outside,alpha_out,source_residue,render_out,overlap,touch))

for name,m in [("C155_SOURCE_TEXT_MASK.png",source_mask),("C155_ALLOWED_BBOX_MASK.png",allowed),("C155_TARGET_TEXT_MASK.png",target)]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img.save(out/"C155_VISIBLE_CLEAN_PLATE.png")

cards=[]
for label,im in [("SOURCE",src),("VISIBLE_CLEAN",clean_img),("FINAL",fin)]:
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST); c=Image.new("RGB",(1024,538),"white"); c.paste(z,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,1614),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*538))
sheet.save(out/"C155_30CF_COMPARE.jpg",quality=96)

contacts=[]
for r in final_rows:
    x0,y0,x1,y1=r["original_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean_img,fin)]; outims=[]
    for z in ims:
        if z.width>600:
            sc=600/z.width; z=z.resize((600,max(1,int(z.height*sc))),Image.Resampling.NEAREST)
        outims.append(z)
    c=Image.new("RGB",(sum(z.width for z in outims)+12,max(z.height for z in outims)+28),"white"); xx=0
    for z in outims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rw=max(c.width for c in contacts); rh=sum(c.height for c in contacts)+4*(len(contacts)-1); rs=Image.new("RGB",(rw,rh),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"C155_30CF_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,1076),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST); rr.paste(z,(0,i*538+26)); ImageDraw.Draw(rr).text((5,i*538+5),label,fill="black")
rr.save(out/"C155_30CF_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":137,"asset":asset,"producer_run":"20261005-A-PRODUCTION22",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"canonical source visible-alpha masks per producer cell; visible source bbox is stricter than producer all-channel/effect bbox when transparent RGB exists; clean plate checked for zero visible alpha residue and zero changes outside exact visible bboxes; final candidate checked against visible bboxes",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":final_rows,"machine_checks":{"clean_alpha_residue":clean_alpha_residue,"clean_changed_outside_visible_bboxes":clean_outside,
   "clean_alpha_changed_outside_visible_bboxes":clean_alpha_outside,"bbox_size_positive_margin":"6/6 PASS","final_outside":outside,
   "alpha_outside":alpha_out,"render_outside_target":render_out,"source_residue":source_residue,"overlap":overlap,"touch_pairs":touch},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C155_30CF_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"30CF0D","index":137,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,"machine_status":"PASS",
 "bbox_size_positive_margin":"6/6","clean_alpha_residue":clean_alpha_residue,"clean_outside":clean_outside,"clean_alpha_outside":clean_alpha_outside,
 "outside":outside,"alpha_outside":alpha_out,"render_outside_target":render_out,"source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C155_30CF_MACHINE_QA.json"}
(wr/"C155_30CF0D.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
