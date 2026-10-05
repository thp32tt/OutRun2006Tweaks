#!/usr/bin/env python3
import os,json,hashlib,urllib.request,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def dds_decode(data):
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
    mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(data)!=128+W*H*4: raise RuntimeError(("dds structure",W,H,fourcc,bpp,rm,gm,bm,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return W,H,mips,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def x_groups(mask, expected_words):
    bb=bbox(mask)
    if bb is None: raise RuntimeError("empty word mask")
    cols=[x for x in range(bb[0],bb[2]) if mask[:,x].any()]
    runs=[]
    if cols:
        s=p=cols[0]
        for x in cols[1:]:
            if x==p+1: p=x
            else: runs.append((s,p+1)); s=p=x
        runs.append((s,p+1))
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:expected_words-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        g=runs[start:cut+1]; groups.append((g[0][0],g[-1][1])); start=cut+1
    if len(groups)!=expected_words: raise RuntimeError(("word grouping",expected_words,groups))
    return groups
def touch_stats(targets,H,W):
    ov=0; touch=0
    for i,(ii,mi) in enumerate(targets):
        yy,xx=np.nonzero(mi); dil=np.zeros_like(mi)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ys=np.clip(yy+dy,0,H-1); xs=np.clip(xx+dx,0,W-1); dil[ys,xs]=True
        for jj,mj in targets[i+1:]:
            ov += count(mi & mj); touch += count(dil & mj)
    return ov,touch
def make_contacts(src,clean,fin,rows,outpath,maxw=1800):
    cards=[]
    for r in rows:
        ob=r["independent_source_bbox"]; x0,y0,x1,y1=ob; pad=12
        cr=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        ims=[comp(z).crop(cr) for z in (src,clean,fin)]
        cw=max(z.width for z in ims); ch=max(z.height for z in ims)
        card=Image.new("RGB",(cw*3+12,ch+26),"white")
        for i,z in enumerate(ims): card.paste(z,(i*(cw+6),26))
        d=ImageDraw.Draw(card); d.text((3,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
        cards.append(card)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white")
    yy=0
    for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
    if sheet.width>maxw: sheet=sheet.resize((maxw,round(sheet.height*maxw/sheet.width)),Image.Resampling.LANCZOS)
    sheet.save(outpath,quality=96)
def make_raw(raws,rawf,outpath):
    sh=Image.new("RGB",(1024,1072),"white")
    for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf))):
        z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS)
        sh.paste(z,(0,i*536+24)); ImageDraw.Draw(sh).text((4,i*536+4),lab,fill="black")
    sh.save(outpath,quality=94)

def process_a70():
    run="20261005-C212-97E863AD"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
    pr=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_97E863AD_REPORT.json").read_text())
    asset=pr["asset"]; sp=pr["source_provenance"]; cand=repo/pr["candidate_path"]
    folder=asset.split("/")[-2]; name=asset.split("/")[-1]
    tmp=Path("/tmp/c210"); tmp.mkdir(exist_ok=True); sfile=tmp/"source.dds"; afile=tmp/"atlas.json"
    base=f'https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp["commit"]}'
    urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",sfile)
    urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",afile)
    sb=sfile.read_bytes(); cb=cand.read_bytes()
    if sha(sb)!=sp["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or sb[:128]!=cb[:128]:
        raise RuntimeError(("C212 identity/header",sha(sb),sha(cb),sb[:128]==cb[:128]))
    W,H,mips,mode,raws,src=dds_decode(sb); W2,H2,m2,mode2,rawf,fin=dds_decode(cb)
    if (W,H,mips,mode)!=(2048,1024,1,"RGBA") or (W2,H2,m2,mode2)!=(W,H,mips,mode): raise RuntimeError(("C212 structure",W,H,mips,mode,W2,H2,m2,mode2))
    sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
    regs={int(r["idx"]):r for r in json.loads(afile.read_text())["regions"]}
    prows={int(r["region_idx"]):r for r in pr["rows"]}
    ids=set(pr["semantic_binding"]["localized_indices"])
    source_mask=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool); protected=[]
    source_bboxes={}
    for idx,r in regs.items():
        x,y,w,h=map(int,r["rect"]); a=sa[y:y+h,x:x+w,3]>0
        if idx not in ids:
            # Entire protected atlas region must remain byte/pixel exact.
            pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=True; protected.append((f"region_{idx}",pm))
            continue
        lm=a.copy()
        if idx in (1,2):
            groups=x_groups(a,5 if idx==1 else 4); tx0,tx1=groups[1]
            tok=np.zeros_like(a); tok[:,tx0:tx1]=a[:,tx0:tx1]; lm &= ~tok
            pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=tok; protected.append((f"inline_token_{idx}",pm))
        elif idx==4:
            ys=[yy for yy in range(h) if a[yy,:].any()]; yr=[]
            if ys:
                s=p=ys[0]
                for yy in ys[1:]:
                    if yy==p+1: p=yy
                    else: yr.append((s,p+1)); s=p=yy
                yr.append((s,p+1))
            if len(yr)<2: raise RuntimeError(("C212 idx4 split",yr))
            bottom=yr[-1]; keep=np.zeros_like(a); keep[bottom[0]:bottom[1],:]=a[bottom[0]:bottom[1],:]
            top=a & ~keep; lm=keep
            pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=top; protected.append(("idx4_OUTRUN_top",pm))
        sm=np.zeros((H,W),bool); sm[y:y+h,x:x+w]=lm; source_mask|=sm
        bb=bbox(sm); source_bboxes[idx]=bb
        x0,y0,x1,y1=bb; allowed[y0:y1,x0:x1]=True
    clean_arr=sa.copy(); clean_arr[source_mask,3]=0; clean=Image.fromarray(clean_arr,"RGBA")
    final_alpha=fa[:,:,3]>0
    targets=[]; rows=[]; source_exact=True; target_exact=True
    for idx in sorted(ids):
        p=prows[idx]; ob=source_bboxes[idx]; pob=list(map(int,p["original_bbox"])); se=(ob==pob); source_exact &= se
        x0,y0,x1,y1=ob; tm=np.zeros((H,W),bool); tm[y0:y1,x0:x1]=final_alpha[y0:y1,x0:x1] & (clean_arr[y0:y1,x0:x1,3]==0)
        lbb=bbox(tm); plb=list(map(int,p["localized_bbox"])); te=(lbb==plb); target_exact &= te
        if lbb is None: raise RuntimeError(("C212 empty target",idx))
        a,b,c,d=lbb; margins=[a-x0,x1-c,b-y0,y1-d]
        contain=a>=x0 and b>=y0 and c<=x1 and d<=y1; sizeok=(c-a)<=x1-x0 and (d-b)<=y1-y0; pos=min(margins)>0
        targets.append((idx,tm))
        rows.append({"region_idx":idx,"source":p["source"],"korean":p["korean"],"independent_source_bbox":ob,"producer_source_bbox":pob,
                     "source_bbox_exact_match_producer":se,"independent_localized_bbox":lbb,"producer_localized_bbox":plb,"localized_bbox_exact_match_producer":te,
                     "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
                     "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL","positive_margin":"PASS" if pos else "FAIL",
                     "localized_to_source_width_ratio":round((c-a)/(x1-x0),4),"localized_to_source_height_ratio":round((d-b)/(y1-y0),4)})
    chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
    protected_changes={k:count(chg&m) for k,m in protected}
    localized_union=np.zeros((H,W),bool)
    for _,m in targets:
        bb=bbox(m); x0,y0,x1,y1=bb; localized_union[y0:y1,x0:x1]=True
    exact=np.all(fa==sa,axis=2)
    residue=count(source_mask & exact & (sa[:,:,3]>0) & ~localized_union)
    ov,touch=touch_stats(targets,H,W)
    machine={"decoded_changed_outside_union_source_bboxes":count(chg & ~allowed),"alpha_changed_outside_union_source_bboxes":count(ach & ~allowed),
             "introduced_visible_outside_union_source_bboxes":count(intro & ~allowed),"source_script_exact_residue_pixels":residue,
             "localized_overlap_pixels":ov,"localized_1px_touch_pixels":touch,"protected_changed_pixels":sum(protected_changes.values())}
    rowpass=sum(1 for r in rows if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
    status="PASS" if source_exact and target_exact and rowpass==len(rows) and all(v==0 for v in machine.values()) else "FAIL"
    make_contacts(src,clean,fin,rows,out/"C212_SOURCE_CLEAN_FINAL_CONTACTS.jpg")
    make_raw(raws,rawf,out/"C212_RAW_COMPARE.jpg")
    rep={"schema_version":1,"role":"C","run":run,"qa_id":"C212","queue_index":193,"asset":asset,"producer_run":pr["run"],
         "source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_exact":True,"raw_orientation":"mirror_y"},
         "source_bbox_exact_match_all":source_exact,"candidate_bbox_exact_match_all":target_exact,"row_checks":rows,"row_gate":f"{rowpass}/{len(rows)} PASS",
         "machine_checks":machine,"protected_pixel_changes":protected_changes,"machine_status":status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
         "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C212_REWORK_REQUIRED_MACHINE_GATE","runtime_validation":"UNTESTED",
         "preview_files":[f"localization/graphics/role_C/{run}/C212_SOURCE_CLEAN_FINAL_CONTACTS.jpg",f"localization/graphics/role_C/{run}/C212_RAW_COMPARE.jpg"]}
    (out/"C212_97E863AD_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
    (wr/"C212_97E863AD.json").write_text(json.dumps({"run":run,"qa_id":"C212","index":193,"asset":"97E863AD","candidate_sha256":pr["candidate_sha256"],"machine_status":status,"row_gate":rep["row_gate"],"machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C212_97E863AD_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
    return {"machine_status":status,"row_gate":rep["row_gate"],"machine_checks":machine}

def process_a69():
    run="20261005-C211-A9ABD877"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
    pr=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION69/A69_A9ABD877_REPORT.json").read_text())
    asset=pr["asset"]; sp=pr["source_provenance"]; cand=repo/pr["candidate_path"]
    folder=asset.split("/")[-2]; name=asset.split("/")[-1]
    tmp=Path("/tmp/c211"); tmp.mkdir(exist_ok=True); sfile=tmp/"source.dds"; afile=tmp/"atlas.json"
    base=f'https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp["commit"]}'
    urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",sfile)
    urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",afile)
    sb=sfile.read_bytes(); cb=cand.read_bytes()
    if sha(sb)!=sp["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or sb[:128]!=cb[:128]:
        raise RuntimeError(("C211 identity/header",sha(sb),sha(cb),sb[:128]==cb[:128]))
    W,H,mips,mode,raws,src=dds_decode(sb); W2,H2,m2,mode2,rawf,fin=dds_decode(cb)
    if (W,H,mips,mode)!=(2048,2048,1,"BGRA") or (W2,H2,m2,mode2)!=(W,H,mips,mode): raise RuntimeError(("C211 structure",W,H,mips,mode,W2,H2,m2,mode2))
    sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
    regs={int(r["idx"]):r for r in json.loads(afile.read_text())["regions"]}
    prows={int(r["region_idx"]):r for r in pr["rows"]}
    ids=set(prows)
    source_mask=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool); source_bboxes={}; protected=[]
    for idx,r in regs.items():
        x,y,w,h=map(int,r["rect"])
        if idx not in ids:
            pm=np.zeros((H,W),bool); pm[y:y+h,x:x+w]=True; protected.append((f"protected_region_{idx}",pm)); continue
        a=sa[y:y+h,x:x+w,3]>0; sm=np.zeros((H,W),bool); sm[y:y+h,x:x+w]=a; source_mask|=sm
        bb=bbox(sm); source_bboxes[idx]=bb; x0,y0,x1,y1=bb; allowed[y0:y1,x0:x1]=True
    clean_arr=sa.copy(); clean_arr[source_mask,3]=0; clean=Image.fromarray(clean_arr,"RGBA")
    final_alpha=fa[:,:,3]>0
    rows=[]; targets=[]; source_exact=True; target_exact=True
    expected_stage={"CONIFEROUS FOREST":"코니퍼러스 포레스트","ICE SCAPE":"아이스스케이프","GIANT STATUES":"자이언트 스태추스","GHOST FOREST":"고스트 포레스트",
                    "FLORAL VILLAGE":"플로럴 빌리지","DESERT":"데저트","DEEP LAKE":"딥 레이크","CLOUDY HIGHLAND":"클라우디 하이랜드","CASTLE WALL":"캐슬 월",
                    "CASINO TOWN":"카지노 타운","CAPE WAY":"케이프 웨이","CANYON":"캐니언","BIG FOREST":"빅 포레스트","BAY AREA":"베이 에어리어"}
    semantic_ok=True
    for idx in sorted(ids):
        p=prows[idx]; ob=source_bboxes[idx]; pob=list(map(int,p["original_bbox"])); se=(ob==pob); source_exact &= se
        if p["kind"]=="stage": semantic_ok &= expected_stage.get(p["source"])==p["korean"]
        elif p["source"]=="Special": semantic_ok &= p["korean"]=="스페셜"
        elif p["source"]=="STAGES": semantic_ok &= p["korean"]=="스테이지"
        elif p["source"]=="GOALS": semantic_ok &= p["korean"]=="골"
        else: semantic_ok=False
        x0,y0,x1,y1=ob; tm=np.zeros((H,W),bool); tm[y0:y1,x0:x1]=final_alpha[y0:y1,x0:x1] & (clean_arr[y0:y1,x0:x1,3]==0)
        lbb=bbox(tm); plb=list(map(int,p["localized_bbox"])); te=(lbb==plb); target_exact &= te
        if lbb is None: raise RuntimeError(("C211 empty target",idx))
        a,b,c,d=lbb; margins=[a-x0,x1-c,b-y0,y1-d]; contain=a>=x0 and b>=y0 and c<=x1 and d<=y1; sizeok=(c-a)<=x1-x0 and (d-b)<=y1-y0; pos=min(margins)>0
        targets.append((idx,tm))
        rows.append({"region_idx":idx,"source":p["source"],"korean":p["korean"],"kind":p["kind"],"independent_source_bbox":ob,"producer_source_bbox":pob,
                     "source_bbox_exact_match_producer":se,"independent_localized_bbox":lbb,"producer_localized_bbox":plb,"localized_bbox_exact_match_producer":te,
                     "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
                     "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL","positive_margin":"PASS" if pos else "FAIL",
                     "localized_to_source_width_ratio":round((c-a)/(x1-x0),4),"localized_to_source_height_ratio":round((d-b)/(y1-y0),4)})
    chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
    protected_changes={k:count(chg&m) for k,m in protected}
    localized_union=np.zeros((H,W),bool)
    for _,m in targets:
        bb=bbox(m); x0,y0,x1,y1=bb; localized_union[y0:y1,x0:x1]=True
    exact=np.all(fa==sa,axis=2); residue=count(source_mask & exact & (sa[:,:,3]>0) & ~localized_union)
    ov,touch=touch_stats(targets,H,W)
    machine={"decoded_changed_outside_union_source_bboxes":count(chg & ~allowed),"alpha_changed_outside_union_source_bboxes":count(ach & ~allowed),
             "introduced_visible_outside_union_source_bboxes":count(intro & ~allowed),"source_script_exact_residue_pixels":residue,
             "localized_overlap_pixels":ov,"localized_1px_touch_pixels":touch,"protected_changed_pixels":sum(protected_changes.values())}
    rowpass=sum(1 for r in rows if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
    status="PASS" if source_exact and target_exact and semantic_ok and rowpass==len(rows) and all(v==0 for v in machine.values()) else "FAIL"
    make_contacts(src,clean,fin,rows,out/"C211_SOURCE_CLEAN_FINAL_CONTACTS.jpg")
    make_raw(raws,rawf,out/"C211_RAW_COMPARE.jpg")
    rep={"schema_version":1,"role":"C","run":run,"qa_id":"C211","queue_index":201,"asset":asset,"producer_run":pr["run"],"source_sha256":sp["source_sha256"],
         "candidate_sha256":pr["candidate_sha256"],"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_exact":True,"raw_orientation":"mirror_y"},
         "source_bbox_exact_match_all":source_exact,"candidate_bbox_exact_match_all":target_exact,"semantic_binding_policy_pass":bool(semantic_ok),
         "song_title_protection":"idx17 Night Bird + idx18 Radiation full atlas regions exact" if sum(protected_changes.values())==0 else "FAIL",
         "row_checks":rows,"row_gate":f"{rowpass}/{len(rows)} PASS","machine_checks":machine,"protected_pixel_changes":protected_changes,"machine_status":status,
         "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C211_REWORK_REQUIRED_MACHINE_GATE",
         "runtime_validation":"UNTESTED","preview_files":[f"localization/graphics/role_C/{run}/C211_SOURCE_CLEAN_FINAL_CONTACTS.jpg",f"localization/graphics/role_C/{run}/C211_RAW_COMPARE.jpg"]}
    (out/"C211_A9ABD877_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
    (wr/"C211_A9ABD877.json").write_text(json.dumps({"run":run,"qa_id":"C211","index":201,"asset":"A9ABD877","candidate_sha256":pr["candidate_sha256"],"machine_status":status,"row_gate":rep["row_gate"],"semantic_binding_policy_pass":semantic_ok,"machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C211_A9ABD877_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
    return {"machine_status":status,"row_gate":rep["row_gate"],"semantic_binding_policy_pass":semantic_ok,"machine_checks":machine}

print(json.dumps({"C212":process_a70()},ensure_ascii=False),flush=True)
