#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C164-C165-A26-A27"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT

def sha(b): return hashlib.sha256(b).hexdigest()
def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(88,88,88,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_mask(m,p):
    Image.fromarray((m.astype(np.uint8)*255),"L").save(p)
def profile(arr,mask,bb,bins=5):
    x0,y0,x1,y1=bb; h=max(1,y1-y0); rows=[]
    lum=arr[:,:,:3].astype(np.float32).mean(axis=2)
    for i in range(bins):
        ya=y0+(h*i)//bins; yb=y0+(h*(i+1))//bins
        mm=mask.copy(); mm[:ya,:]=False; mm[yb:,:]=False
        vals=arr[mm,:3]
        if len(vals)==0: rows.append(None); continue
        lv=lum[mm]
        cut=np.percentile(lv,60)
        vals=vals[lv>=cut]
        rows.append([int(round(float(np.median(vals[:,k])))) for k in range(3)])
    return rows

results={}

# ---- C164: independent re-QA of A26 2EA557B4 after C163 source-style rework ----
asset2="textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"
cand2=repo/"localization/graphics/hd_candidates"/asset2
sp2=Path("/tmp/c164_2ea_source.dds")
urllib.request.urlretrieve(base+"/Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds",sp2)
sb=sp2.read_bytes(); cb=cand2.read_bytes()
SOURCE_BLOB="bbf53949c7d9f1dc4949e661caeeaf19fe667d79"
SOURCE_SHA="b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685"
CAND_SHA="b0cf1dbdd1c73801f3023e9c45af245b4f655f1d4c6f6b0a08e1c1bdae16d7fc"
if gitblob(sb)!=SOURCE_BLOB or sha(sb)!=SOURCE_SHA or sha(cb)!=CAND_SHA: raise RuntimeError("2EA provenance/hash drift")
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("2EA header/length drift")
H,W=struct.unpack_from("<II",sb,12); mips=struct.unpack_from("<I",sb,28)[0]; fourcc=sb[84:88]
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H)!=(2048,256) or fourcc!=b"DXT5" or mips not in (0,1) or len(sb)!=need: raise RuntimeError("2EA structure drift")
raws=Image.open(sp2).convert("RGBA"); rawf=Image.open(cand2).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
sm=sa[:,:,3]>0; ob=bbox(sm)
if not ob: raise RuntimeError("2EA source alpha empty")
allowed=np.zeros((H,W),bool); allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
diff=np.any(sa!=fa,axis=2); ad=sa[:,:,3]!=fa[:,:,3]
outside=count(diff&~allowed); alphaout=count(ad&~allowed)
intro=count((fa[:,:,3]>0)&(sa[:,:,3]<=0)&~allowed)
target=fa[:,:,3]>0; lb=bbox(target)
if not lb: raise RuntimeError("2EA localized alpha empty")
sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
deltas=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
if outside or alphaout or intro or lw>sw or lh>sh or min(deltas)<=0: raise RuntimeError("2EA containment fail")
bw=(W+3)//4; bh=(H+3)//4; allowed_raw=np.flipud(allowed)
changed_blocks=partial=bad_partial=bad_out=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16; sblk=sb[off:off+16]; cblk=cb[off:off+16]
        if sblk==cblk: continue
        changed_blocks+=1
        am=allowed_raw[by*4:min(H,by*4+4),bx*4:min(W,bx*4+4)]
        if not np.any(am): bad_out+=1; continue
        if not np.all(am):
            partial+=1
            if sblk[:2]!=cblk[:2] or sblk[8:16]!=cblk[8:16]: bad_partial+=1
if bad_out or bad_partial: raise RuntimeError(("2EA BC3 boundary",bad_out,bad_partial))
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(9)))>0
same=np.max(np.abs(sa[:,:,:3].astype(np.int16)-fa[:,:,:3].astype(np.int16)),axis=2)<=4
residue=count(sm&~guard&(fa[:,:,3]>8)&same)
if residue: raise RuntimeError(("2EA residue",residue))
save_mask(sm,out/"C164_2EA_SOURCE_MASK.png"); save_mask(target,out/"C164_2EA_TARGET_MASK.png")
detail=Image.new("RGB",(2048,420),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    cr=comp(im).crop((0,92,1120,256)).resize((1904,279),Image.Resampling.NEAREST)
    detail.paste(cr,(0,i*205+24)); ImageDraw.Draw(detail).text((5,i*205+4),label,fill="black")
detail.save(out/"C164_2EA_SOURCE_FINAL_DETAIL.jpg",quality=96)
rr=Image.new("RGB",(1024,340),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf)]):
    z=comp(im).resize((1024,128),Image.Resampling.NEAREST); rr.paste(z,(0,i*170+28)); ImageDraw.Draw(rr).text((5,i*170+5),label,fill="black")
rr.save(out/"C164_2EA_RAW_COMPARE.jpg",quality=96)
r2={"schema_version":1,"role":"C","run":run,"qa_id":"C164","queue_index":55,"asset":asset2,
 "producer_run":"20261005-A-PRODUCTION26","source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,"candidate_changed_by_C":False,
 "independent_method":"Pinned canonical source re-download; independent DXT5 decode; source alpha bbox derivation; decoded containment/alpha/introduced-visible checks; changed-BC3 boundary audit; source-residue screen; independent visual evidence.",
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"raw_orientation":"mirror_y"},
 "semantic_binding":{"source":"NEXT ROUND","korean":"다음 라운드"},"original_bbox":ob,"localized_bbox":lb,
 "source_size":[sw,sh],"localized_size":[lw,lh],"delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
 "machine_checks":{"decoded_changed_outside":outside,"alpha_outside":alphaout,"introduced_visible_outside":intro,"source_residue":residue,
 "changed_bc3_blocks":changed_blocks,"partial_boundary_changed_blocks":partial,"changed_bc3_blocks_wholly_outside_allowed":bad_out,"partial_endpoint_or_color_drift":bad_partial},
 "style_profiles":{"source_bright_vertical":profile(sa,sm,ob),"candidate_bright_vertical":profile(fa,target,lb)},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C164_2EA_MACHINE_QA.json").write_text(json.dumps(r2,ensure_ascii=False,indent=2)+"\n")
(wr/"C164_2EA557B4.json").write_text(json.dumps({"run":run,"qa_id":"C164","asset":"2EA557B4","index":55,"candidate_sha256":CAND_SHA,"machine_status":"PASS","bbox_size_positive_margin":"1/1","runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C164_2EA_MACHINE_QA.json"},ensure_ascii=False,indent=2)+"\n")
results["C164"]=r2

# ---- C165: independent QA of A27 E1639D2E ----
assetE="textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds"
candE=repo/"localization/graphics/hd_candidates"/assetE
spE=Path("/tmp/c165_e163_source.dds")
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",spE)
sb=spE.read_bytes(); cb=candE.read_bytes()
SOURCE_BLOB="1a119356bf20b0116d408ffe510e62ec90fc0c53"; SOURCE_SHA="e250a41e7c59ccd5b8a68a02aace066f6578fbe0d84a365d7a0a27044b353511"; CAND_SHA="fe9bb931d94a13a44a08bcf61b6325c01080b462afff84f92c97205cbe0eea65"
if gitblob(sb)!=SOURCE_BLOB or sha(sb)!=SOURCE_SHA or sha(cb)!=CAND_SHA: raise RuntimeError("E163 provenance/hash drift")
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("E163 header/length drift")
H,W=struct.unpack_from("<II",sb,12); mips=struct.unpack_from("<I",sb,28)[0]; fourcc=sb[84:88]
if (W,H)!=(1024,256) or fourcc!=b"\x00\x00\x00\x00" or len(sb)!=128+W*H*4: raise RuntimeError(("E163 structure",W,H,mips,fourcc,len(sb)))
raws=Image.open(spE).convert("RGBA"); rawf=Image.open(candE).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
sm=sa[:,:,3]>0; tm=fa[:,:,3]>0
bands=[(104,H),(0,104)]
obs=[]; lbs=[]; allowed=np.zeros((H,W),bool); targets=[]
for ya,yb in bands:
    sband=sm.copy(); sband[:ya,:]=False; sband[yb:,:]=False
    tband=tm.copy(); tband[:ya,:]=False; tband[yb:,:]=False
    ob=bbox(sband); lb=bbox(tband)
    obs.append(ob); lbs.append(lb)
    if ob is None or lb is None: raise RuntimeError(("E163 empty band",ya,yb,ob,lb))
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True; targets.append(tband)
if any(x is None for x in obs): raise RuntimeError(("E163 source alpha empty",obs))
# Candidate bboxes are independently derived above; do not trust producer bbox bookkeeping.\n# Exact containment/size/margin gates below are authoritative.
rows=[]; ok=True
for i,(ob,lb) in enumerate(zip(obs,lbs)):
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    ds=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(ds)<=0: ok=False
    rows.append({"region_idx":i,"original_bbox":ob,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
                 "delta_left":ds[0],"delta_right":ds[1],"delta_top":ds[2],"delta_bottom":ds[3],"containment":"PASS" if min(ds)>=0 else "FAIL",
                 "size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL","positive_margin":"PASS" if min(ds)>0 else "FAIL"})
if not ok: raise RuntimeError(("E163 bbox fail",rows))
diff=np.any(sa!=fa,axis=2); ad=sa[:,:,3]!=fa[:,:,3]
outside=count(diff&~allowed); alphaout=count(ad&~allowed); intro=count((fa[:,:,3]>0)&(sa[:,:,3]<=0)&~allowed)
if outside or alphaout or intro: raise RuntimeError(("E163 outside",outside,alphaout,intro))
overlap=count(targets[0]&targets[1])
near=count((np.asarray(Image.fromarray((targets[0].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0)&targets[1])
if overlap or near: raise RuntimeError(("E163 overlap/touch",overlap,near))
guard=np.zeros((H,W),bool)
for t in targets: guard|=np.asarray(Image.fromarray((t.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(9)))>0
same=np.max(np.abs(sa[:,:,:3].astype(np.int16)-fa[:,:,:3].astype(np.int16)),axis=2)<=4
residue=count(sm&~guard&(fa[:,:,3]>8)&same)
if residue: raise RuntimeError(("E163 residue",residue))
save_mask(sm,out/"C165_E163_SOURCE_MASK.png"); save_mask(tm,out/"C165_E163_TARGET_MASK.png")
stack=Image.new("RGB",(1024,620),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    z=comp(im).resize((1024,256),Image.Resampling.NEAREST); stack.paste(z,(0,i*300+28)); ImageDraw.Draw(stack).text((5,i*300+5),label,fill="black")
stack.save(out/"C165_E163_SOURCE_FINAL.jpg",quality=96)
cards=[]
for i,(ob,lb) in enumerate(zip(obs,lbs)):
    x0=min(ob[0],lb[0]); y0=min(ob[1],lb[1]); x1=max(ob[2],lb[2]); y1=max(ob[3],lb[3]); p=16
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    c=Image.new("RGB",((cr[2]-cr[0])*2,(cr[3]-cr[1])*4+52),"white")
    for j,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
        z=comp(im).crop(cr).resize(((cr[2]-cr[0])*2,(cr[3]-cr[1])*2),Image.Resampling.NEAREST)
        c.paste(z,(0,j*((cr[3]-cr[1])*2+26)+22)); ImageDraw.Draw(c).text((5,j*((cr[3]-cr[1])*2+26)+4),label,fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(x.width for x in cards),sum(x.height+6 for x in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
sheet.save(out/"C165_E163_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,620),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf)]):
    z=comp(im).resize((1024,256),Image.Resampling.NEAREST); rr.paste(z,(0,i*300+28)); ImageDraw.Draw(rr).text((5,i*300+5),label,fill="black")
rr.save(out/"C165_E163_RAW_COMPARE.jpg",quality=96)
rE={"schema_version":1,"role":"C","run":run,"qa_id":"C165","queue_index":241,"asset":assetE,
 "producer_run":"20261005-A-PRODUCTION27","source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,"candidate_changed_by_C":False,
 "independent_method":"Pinned canonical source re-download; independent RGBA decode; source/localized alpha bboxes independently split into the two physical text bands; exact source-bbox containment/size/margin, changed-pixel/alpha protection, overlap/touch and residue checks; independent readable/raw visual evidence.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y"},"semantic_binding":[{"source":"Loading","korean":"로딩"},{"source":"PLEASE WAIT","korean":"잠시만요"}],
 "rows":rows,"machine_checks":{"decoded_changed_outside":outside,"alpha_outside":alphaout,"introduced_visible_outside":intro,"localized_overlap":overlap,"localized_1px_near":near,"source_residue":residue},
 "style_profiles":{"source_loading_bright_vertical":profile(sa,targets[0]|(sm&allowed),obs[0]),"candidate_loading_bright_vertical":profile(fa,targets[0],lbs[0])},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C165_E163_MACHINE_QA.json").write_text(json.dumps(rE,ensure_ascii=False,indent=2)+"\n")
(wr/"C165_E1639D2E.json").write_text(json.dumps({"run":run,"qa_id":"C165","asset":"E1639D2E","index":241,"candidate_sha256":CAND_SHA,"machine_status":"PASS","bbox_size_positive_margin":"2/2","runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C165_E163_MACHINE_QA.json"},ensure_ascii=False,indent=2)+"\n")
results["C165"]=rE

print(json.dumps({k:{"asset":v["asset"],"candidate_sha256":v["candidate_sha256"],"machine_status":v["machine_status"]} for k,v in results.items()},ensure_ascii=False),flush=True)
