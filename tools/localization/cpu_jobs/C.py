#!/usr/bin/env python3
import os,json,hashlib,urllib.request,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}"

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def decode_dds(data):
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
    if fourcc!=0 or bpp!=32: raise RuntimeError(("not RGBA32",fourcc,bpp))
    if (rm,gm,bm)==(0xff,0xff00,0xff0000): mode="RGBA"
    elif (rm,gm,bm)==(0xff0000,0xff00,0xff): mode="BGRA"
    else: raise RuntimeError(("unknown masks",rm,gm,bm))
    if len(data)!=128+W*H*4: raise RuntimeError(("size",len(data),W,H))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return W,H,mips,mode,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def runs(vals):
    vals=sorted(set(int(v) for v in vals))
    out=[]
    if not vals:return out
    s=p=vals[0]
    for v in vals[1:]:
        if v==p+1:p=v
        else:out.append((s,p+1));s=p=v
    out.append((s,p+1))
    return out

def word_groups(mask,nwords):
    bb=bbox(mask)
    if bb is None: raise RuntimeError("empty word mask")
    cols=np.where(mask.any(axis=0))[0]
    cr=runs(cols)
    gaps=[(cr[i+1][0]-cr[i][1],i) for i in range(len(cr)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:nwords-1])
    groups=[]; start=0
    for cut in cuts+[len(cr)-1]:
        g=cr[start:cut+1]
        groups.append((g[0][0],g[-1][1]))
        start=cut+1
    if len(groups)!=nwords: raise RuntimeError(("word groups",nwords,groups))
    return groups

def save_three(src,clean,final,boxes,path,labels=None):
    cards=[]
    for bi,b in enumerate(boxes):
        x0,y0,x1,y1=b; pad=20
        cr=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        ims=[comp(x).crop(cr) for x in (src,clean,final)]
        cw=max(i.width for i in ims); ch=max(i.height for i in ims)
        card=Image.new("RGB",(cw*3+12,ch+26),"white")
        for j,im in enumerate(ims): card.paste(im,(j*(cw+6),26))
        d=ImageDraw.Draw(card); d.text((3,4),(labels[bi] if labels else f"box{bi}")+" | SOURCE / CLEAN / FINAL",fill="black")
        cards.append(card)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
    y=0
    for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
    if sheet.width>2000: sheet=sheet.resize((2000,round(sheet.height*2000/sheet.width)),Image.Resampling.LANCZOS)
    sheet.save(path,quality=95)

def process_acf():
    run="20261006-C217-ACF61D7C"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
    pr=json.loads((repo/"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF61D7C_REPORT.json").read_text())
    candidate=repo/pr["candidate_path"]
    tmp=Path("/tmp/c214"); tmp.mkdir(exist_ok=True)
    sfile=tmp/"source.dds"; afile=tmp/"atlas.json"
    urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds",sfile)
    urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_ACF61D7C_1024x512_atlas.json",afile)
    sb=sfile.read_bytes(); cb=candidate.read_bytes()
    if sha(sb)!=pr["source_provenance"]["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or sb[:128]!=cb[:128]:
        raise RuntimeError(("ACF identity/header",sha(sb),sha(cb),sb[:128]==cb[:128]))
    W,H,mips,mode,raws,src=decode_dds(sb); W2,H2,m2,mode2,rawf,final=decode_dds(cb)
    if (W,H,mips,mode)!=(4096,2048,1,"RGBA") or (W2,H2,m2,mode2)!=(W,H,mips,mode):
        raise RuntimeError(("ACF structure",W,H,mips,mode,W2,H2,m2,mode2))
    sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
    clean=Image.open(repo/"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_CLEAN_PLATE.png").convert("RGBA")
    ca=np.asarray(clean,dtype=np.uint8)
    regs={int(r["idx"]):r for r in json.loads(afile.read_text())["regions"]}

    rows=pr["rows"]
    allowed=np.zeros((H,W),bool)
    row_checks=[]
    for r in rows:
        ob=list(map(int,r["original_bbox"])); x0,y0,x1,y1=ob
        allowed[y0:y1,x0:x1]=True
        # Independent source bbox from canonical source alpha inside the producer row window.
        sm=sa[y0:y1,x0:x1,3]>0
        ib=bbox(sm)
        if ib is not None: ib=[ib[0]+x0,ib[1]+y0,ib[2]+x0,ib[3]+y0]
        # Independent localized bbox from CLEAN -> FINAL delta.
        lm=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
        lb=bbox(lm)
        if lb is not None: lb=[lb[0]+x0,lb[1]+y0,lb[2]+x0,lb[3]+y0]
        plb=list(map(int,r["localized_bbox"]))
        row_checks.append({
          "key":r["key"],"region_idx":int(r["region_idx"]),"source":r["source"],"korean":r["korean"],
          "producer_original_bbox":ob,"independent_source_alpha_bbox_within_row":ib,
          "producer_localized_bbox":plb,"independent_clean_to_final_bbox":lb,
          "localized_bbox_exact_match":lb==plb,
          "source_width":int(r["source_width"]),"source_height":int(r["source_height"]),
          "localized_width":int(r["localized_width"]),"localized_height":int(r["localized_height"]),
          "width_ratio":round(int(r["localized_width"])/int(r["source_width"]),4),
          "height_ratio":round(int(r["localized_height"])/int(r["source_height"]),4),
          "containment":r["containment"],"size_ceiling":r["size_ceiling"],"positive_margin":r["positive_margin"]
        })

    chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
    outside=count(chg & ~allowed); alpha_out=count(ach & ~allowed); intro_out=count(intro & ~allowed)

    # Full-atlas protected policy regions must be pixel-exact.
    protected_ids=sorted(int(k) for k in pr["semantic_binding"]["protected_policy_regions"].keys())
    protected_changes={}
    for idx in protected_ids:
        x,y,w,h=map(int,regs[idx]["rect"])
        protected_changes[str(idx)]=count(chg[y:y+h,x:x+w])

    # Independently recover inline product-token word masks from canonical source text.
    token_checks=[]
    def token_from_row(row_key,nwords,which,relation=None,override_bbox=None):
        r=next(x for x in rows if x["key"]==row_key)
        ob=override_bbox or list(map(int,r["original_bbox"]))
        x0,y0,x1,y1=ob
        m=sa[y0:y1,x0:x1,3]>0
        groups=word_groups(m,nwords)
        gx0,gx1=groups[which]
        tok=np.zeros((H,W),bool)
        tok[y0:y1,x0+gx0:x0+gx1]=m[:,gx0:gx1]
        tbb=bbox(tok)
        changed=count(chg & tok)
        loc=list(map(int,r["localized_bbox"]))
        relpass=True
        if relation=="after": relpass=loc[0]>=tbb[2]
        if relation=="before": relpass=loc[2]<=tbb[0]
        token_checks.append({"row_key":row_key,"source":r["source"],"token_bbox":tbb,"changed_source_token_pixels":changed,
                             "localized_bbox":loc,"required_relation":relation,"relation_pass":bool(relpass),"word_groups_relative":groups})
        return tbb,changed,relpass

    token_from_row("out_run_1p",4,0,"after")
    token_from_row("exchange_line1",3,1,None)

    # Region 10 contains more than the intended sentence. Recover the sentence as the
    # broad left-side alpha line and prove A72 did not use unrelated right-side pixels
    # as its source bbox/token anchor.
    r10=next(x for x in rows if x["key"]=="enjoy_original")
    rx,ry,rw,rh=map(int,regs[10]["rect"])
    rm=sa[ry:ry+rh,rx:rx+rw,3]>0
    yruns=runs(np.where(rm.any(axis=1))[0])
    run_boxes=[]
    for ya,yb in yruns:
        sub=rm[ya:yb,:]; bb=bbox(sub)
        if bb is None: continue
        ab=[rx+bb[0],ry+ya+bb[1],rx+bb[2],ry+ya+bb[3]]
        run_boxes.append({"y_run":[int(ya),int(yb)],"bbox":ab,"width":ab[2]-ab[0],"pixels":count(sub)})
    # Phrase is the widest run whose left edge begins near the region's left side.
    phrase_candidates=[x for x in run_boxes if x["bbox"][0] < rx+900 and x["width"]>500]
    if not phrase_candidates: raise RuntimeError(("ACF idx10 phrase run not found",run_boxes))
    phrase=max(phrase_candidates,key=lambda x:x["width"])
    pbox=phrase["bbox"]
    px0,py0,px1,py1=pbox
    pm=sa[py0:py1,px0:px1,3]>0
    groups=word_groups(pm,4)
    gx0,gx1=groups[3]
    tok=np.zeros((H,W),bool); tok[py0:py1,px0+gx0:px0+gx1]=pm[:,gx0:gx1]
    tbb=bbox(tok); tchg=count(chg & tok)
    loc10=list(map(int,r10["localized_bbox"]))
    loc_in_phrase=(loc10[0]>=px0 and loc10[1]>=py0 and loc10[2]<=px1 and loc10[3]<=py1)
    rel_before=(loc10[2]<=tbb[0])
    token_checks.append({"row_key":"enjoy_original","source":r10["source"],"independent_phrase_bbox":pbox,
                         "region10_y_runs":run_boxes,"token_bbox":tbb,"changed_source_token_pixels":tchg,
                         "localized_bbox":loc10,"localized_inside_independent_phrase_bbox":bool(loc_in_phrase),
                         "required_relation":"before","relation_pass":bool(rel_before),"word_groups_relative":groups})

    # Exact-source residue outside localized CLEAN->FINAL bboxes, excluding protected token pixels.
    token_union=np.zeros((H,W),bool)
    # Rebuild masks from token_checks bboxes conservatively using source alpha.
    for tc in token_checks:
        tb=tc["token_bbox"]; x0,y0,x1,y1=tb
        token_union[y0:y1,x0:x1] |= (sa[y0:y1,x0:x1,3]>0)
    local_source=np.zeros((H,W),bool)
    loc_union=np.zeros((H,W),bool)
    for r,rc in zip(rows,row_checks):
        ob=list(map(int,r["original_bbox"])); x0,y0,x1,y1=ob
        local_source[y0:y1,x0:x1] |= (sa[y0:y1,x0:x1,3]>0)
        if rc["independent_clean_to_final_bbox"]:
            a,b,c,d=rc["independent_clean_to_final_bbox"]; loc_union[b:d,a:c]=True
    exact=np.all(fa==sa,axis=2)
    residue=count(local_source & ~token_union & exact & ~loc_union)

    under70=[{"key":r["key"],"source":r["source"],"korean":r["korean"],"height_ratio":r["height_ratio"],"width_ratio":r["width_ratio"]}
             for r in row_checks if r["height_ratio"]<0.70]
    token_fail=sum(tc["changed_source_token_pixels"] for tc in token_checks)
    token_relation_fail=sum(0 if tc.get("relation_pass",True) else 1 for tc in token_checks)
    bbox_mismatch=sum(0 if r["localized_bbox_exact_match"] else 1 for r in row_checks)
    protected_total=sum(protected_changes.values())
    machine_status="PASS" if outside==0 and alpha_out==0 and intro_out==0 and protected_total==0 and token_fail==0 and token_relation_fail==0 and bbox_mismatch==0 and loc_in_phrase else "FAIL"

    # Controller-targeted evidence: rows with strongest scale/alignment risk + idx10.
    focus_keys=["congrats_title","out_run_1p","view_rankings","enjoy_original","adjust_settings","yes","no","your_position"]
    boxes=[list(map(int,next(r for r in rows if r["key"]==k)["original_bbox"])) for k in focus_keys]
    save_three(src,clean,final,boxes,out/"C217_ACF_RISK_CONTACTS.jpg",focus_keys)
    # Region10 broad view.
    save_three(src,clean,final,[[rx,ry,rx+rw,ry+rh]],out/"C217_ACF_REGION10.jpg",["atlas region10"])
    rawsheet=Image.new("RGB",(1200,2*630),"white")
    for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf))):
        z=comp(im); z.thumbnail((1200,600),Image.Resampling.LANCZOS); rawsheet.paste(z,(0,i*630+25)); ImageDraw.Draw(rawsheet).text((5,i*630+5),lab,fill="black")
    rawsheet.save(out/"C217_ACF_RAW_COMPARE.jpg",quality=92)

    rep={
      "schema_version":1,"role":"C","run":run,"qa_id":"C217","queue_index":205,"asset":pr["asset"],"producer_run":pr["run"],
      "source_sha256":pr["source_provenance"]["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
      "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_exact":True,"raw_orientation":"mirror_y"},
      "row_checks":row_checks,"machine_checks":{"decoded_changed_outside_union_producer_rows":outside,"alpha_changed_outside_union_producer_rows":alpha_out,
        "introduced_visible_outside_union_producer_rows":intro_out,"protected_full_region_changed_pixels":protected_total,
        "protected_inline_token_changed_pixels":token_fail,"token_relation_failures":token_relation_fail,
        "localized_bbox_clean_to_final_mismatches":bbox_mismatch,"source_exact_residue_outside_localized_bboxes":residue},
      "protected_region_changes":protected_changes,"inline_product_token_checks":token_checks,
      "region10_independent_geometry":{"atlas_rect":[rx,ry,rw,rh],"y_runs":run_boxes,"selected_phrase_bbox":pbox,
        "producer_original_bbox":list(map(int,r10["original_bbox"])),"producer_localized_bbox":loc10,
        "localized_inside_phrase_bbox":bool(loc_in_phrase)},
      "style_diagnostics":{"rows_height_ratio_below_0_70":under70},
      "machine_status":machine_status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
      "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C217_REWORK_REQUIRED_MACHINE_OR_SEMANTIC_GEOMETRY_GATE",
      "runtime_validation":"UNTESTED",
      "preview_files":[f"localization/graphics/role_C/{run}/C217_ACF_RISK_CONTACTS.jpg",f"localization/graphics/role_C/{run}/C217_ACF_REGION10.jpg",f"localization/graphics/role_C/{run}/C217_ACF_RAW_COMPARE.jpg"]
    }
    (out/"C217_ACF61D7C_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
    (wr/"C217_ACF61D7C.json").write_text(json.dumps({"run":run,"qa_id":"C217","index":205,"asset":"ACF61D7C","candidate_sha256":pr["candidate_sha256"],
       "machine_status":machine_status,"machine_checks":rep["machine_checks"],"report":f"localization/graphics/role_C/{run}/C217_ACF61D7C_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
    return {"machine_status":machine_status,"machine_checks":rep["machine_checks"],"region10":rep["region10_independent_geometry"],"token_checks":token_checks,"under70":under70}

def process_jenn():
    run="20261006-C215-06AB5CEE"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
    pr=json.loads((repo/"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_JENN_REPORT.json").read_text())
    candidate=repo/pr["candidate_path"]
    tmp=Path("/tmp/c215"); tmp.mkdir(exist_ok=True); sfile=tmp/"source.dds"
    urllib.request.urlretrieve(BASE+"/Release/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds",sfile)
    sb=sfile.read_bytes(); cb=candidate.read_bytes()
    if sha(sb)!=pr["source_provenance"]["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or sb[:128]!=cb[:128]:
        raise RuntimeError(("JENN identity/header",sha(sb),sha(cb),sb[:128]==cb[:128]))
    W,H,mips,mode,raws,src=decode_dds(sb); W2,H2,m2,mode2,rawf,final=decode_dds(cb)
    if (W,H,mips,mode)!=(4096,4096,1,"RGBA") or (W2,H2,m2,mode2)!=(W,H,mips,mode):
        raise RuntimeError(("JENN structure",W,H,mips,mode,W2,H2,m2,mode2))
    sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)

    b148=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
    b152=repo/"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7"
    c202=json.loads((repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json").read_text())
    c206=json.loads((repo/"localization/graphics/role_C/20261005-C206-DCC7B488/C206_DCC7B488_CONTROLLER_FINAL_QA.json").read_text())
    if c202.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME" or c206.get("decision")!="C206_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME":
        raise RuntimeError(("template approval drift",c202.get("decision"),c206.get("decision")))
    r148=json.loads((b148/"B148_8215_REPORT.json").read_text()); r152=json.loads((b152/"B152_DCC7_REPORT.json").read_text())
    templates={
      1:(Image.open(b148/"B148_SOURCE_READABLE.png").convert("RGBA"),Image.open(b148/"B148_CLEAN_PLATE.png").convert("RGBA"),Image.open(b148/"B148_FINAL_READABLE.png").convert("RGBA"),next(r for r in r148["rows"] if int(r["region_idx"])==1),[1088,3080,2048,1016],"C202"),
      2:(Image.open(b148/"B148_SOURCE_READABLE.png").convert("RGBA"),Image.open(b148/"B148_CLEAN_PLATE.png").convert("RGBA"),Image.open(b148/"B148_FINAL_READABLE.png").convert("RGBA"),next(r for r in r148["rows"] if int(r["region_idx"])==2),[0,1488,1720,1016],"C202"),
      3:(Image.open(b152/"B152_SOURCE_READABLE.png").convert("RGBA"),Image.open(b152/"B152_CLEAN_PLATE.png").convert("RGBA"),Image.open(b152/"B152_FINAL_READABLE.png").convert("RGBA"),r152["rows"][0],[1720,1488,1640,1016],"C206")
    }
    expected=sa.copy(); allowed=np.zeros((H,W),bool); rows=[]; unsafe_variants=0
    for idx in (1,2,3):
        ts,tc,tf,row,dc,approval=templates[idx]
        tc0=list(map(int,row["cell"])); dx=dc[0]-tc0[0]; dy=dc[1]-tc0[1]
        ob=list(map(int,row["original_bbox"])); core=list(map(int,row["source_core_bbox"])); lb=list(map(int,row["localized_bbox"]))
        dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
        dcore=[core[0]+dx,core[1]+dy,core[2]+dx,core[3]+dy]
        dlb=[lb[0]+dx,lb[1]+dy,lb[2]+dx,lb[3]+dy]
        tsa=np.asarray(ts,dtype=np.uint8); tca=np.asarray(tc,dtype=np.uint8); tfa=np.asarray(tf,dtype=np.uint8)
        sp=tsa[ob[1]:ob[3],ob[0]:ob[2]]; cp=tca[ob[1]:ob[3],ob[0]:ob[2]]; fp=tfa[ob[1]:ob[3],ob[0]:ob[2]]
        tp=sa[dob[1]:dob[3],dob[0]:dob[2]]
        removal=np.any(sp!=cp,axis=2); render=np.any(cp!=fp,axis=2); variant=np.any(sp!=tp,axis=2); outside=variant & ~removal
        yy,xx=np.nonzero(outside)
        bad=0
        for y,x in zip(yy,xx):
            a=tp[y,x]; b=sp[y,x]
            if not ((a[3]<=16 or b[3]<=16) and (max(a[:3])>=210 or max(b[:3])>=210)): bad+=1
        unsafe_variants+=bad
        clean_mask=removal|outside
        dest=expected[dob[1]:dob[3],dob[0]:dob[2]]
        dest[clean_mask]=cp[clean_mask]; dest[render]=fp[render]
        allowed[dob[1]:dob[3],dob[0]:dob[2]]=True
        independent_lb=bbox(render)
        if independent_lb is not None: independent_lb=[independent_lb[0]+dob[0],independent_lb[1]+dob[1],independent_lb[2]+dob[0],independent_lb[3]+dob[1]]
        prod=next(r for r in pr["rows"] if int(r["region_idx"])==idx)
        rows.append({"region_idx":idx,"approval":approval,"independent_original_bbox":dob,"producer_original_bbox":list(map(int,prod["original_bbox"])),
          "independent_source_core_bbox":dcore,"producer_source_core_bbox":list(map(int,prod["source_core_bbox"])),
          "independent_localized_bbox":independent_lb,"producer_localized_bbox":list(map(int,prod["localized_bbox"])),
          "localized_bbox_exact_match":independent_lb==list(map(int,prod["localized_bbox"])),
          "containment":prod["containment"],"size_ceiling":prod["size_ceiling"],"positive_margin":prod["positive_margin"],
          "target_variant_outside_removal_pixels":int(np.count_nonzero(outside)),"unsafe_variant_pixels":bad})

    expected_diff=count(np.any(expected!=fa,axis=2))
    chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
    outside=count(chg & ~allowed); alpha_out=count(ach & ~allowed); intro_out=count(intro & ~allowed)
    bbox_mismatch=sum(0 if r["localized_bbox_exact_match"] else 1 for r in rows)
    machine_status="PASS" if expected_diff==0 and outside==0 and alpha_out==0 and intro_out==0 and unsafe_variants==0 and bbox_mismatch==0 else "FAIL"

    clean=Image.open(repo/"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_CLEAN_PLATE.png").convert("RGBA")
    save_three(src,clean,final,[r["independent_original_bbox"] for r in rows],out/"C215_JENN_CONTACTS.jpg",[f"idx{r['region_idx']}" for r in rows])
    rawsheet=Image.new("RGB",(1200,2*1230),"white")
    for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf))):
        z=comp(im); z.thumbnail((1200,1200),Image.Resampling.LANCZOS); rawsheet.paste(z,(0,i*1230+25)); ImageDraw.Draw(rawsheet).text((5,i*1230+5),lab,fill="black")
    rawsheet.save(out/"C215_JENN_RAW_COMPARE.jpg",quality=92)

    rep={"schema_version":1,"role":"C","run":run,"qa_id":"C215","queue_index":36,"asset":pr["asset"],"producer_run":pr["run"],
      "source_sha256":pr["source_provenance"]["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
      "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_exact":True,"raw_orientation":"mirror_y"},
      "template_approvals":{"C202":c202["decision"],"C206":c206["decision"]},"row_checks":rows,
      "machine_checks":{"candidate_vs_independently_rebuilt_approved_template_composite_diff_pixels":expected_diff,
        "decoded_changed_outside_union_source_bboxes":outside,"alpha_changed_outside_union_source_bboxes":alpha_out,
        "introduced_visible_outside_union_source_bboxes":intro_out,"unsafe_target_template_variant_pixels":unsafe_variants,
        "localized_bbox_mismatches":bbox_mismatch},
      "machine_status":machine_status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
      "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C215_REWORK_REQUIRED_MACHINE_GATE",
      "runtime_validation":"UNTESTED",
      "preview_files":[f"localization/graphics/role_C/{run}/C215_JENN_CONTACTS.jpg",f"localization/graphics/role_C/{run}/C215_JENN_RAW_COMPARE.jpg"]}
    (out/"C215_06AB5CEE_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
    (wr/"C215_06AB5CEE.json").write_text(json.dumps({"run":run,"qa_id":"C215","index":36,"asset":"06AB5CEE","candidate_sha256":pr["candidate_sha256"],
      "machine_status":machine_status,"machine_checks":rep["machine_checks"],"report":f"localization/graphics/role_C/{run}/C215_06AB5CEE_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
    return {"machine_status":machine_status,"machine_checks":rep["machine_checks"],"rows":rows}

print(json.dumps({"C217":process_acf()},ensure_ascii=False),flush=True)
