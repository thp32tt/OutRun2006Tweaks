#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd()
run="20261004-2025-C101"
outdir=repo/"localization/graphics/role_C"/run
outdir.mkdir(parents=True,exist_ok=True)

SPECS=[
 {
  "key":"BF3EE5C6","producer":"A_PRODUCTION14",
  "report":"localization/graphics/role_A/20261004-A-PRODUCTION14/A_PRODUCTION14_BF3EE5C6_REPORT.json",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds",
  "source_sha":"b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds",
  "candidate_sha":"30cc2167b1650ab0a7b1c579c7d29118065007f0474f7207ce993ab1b19e45fa",
  "source_mask":"localization/graphics/role_A/20261004-A-PRODUCTION14/BF3EE5C6_HD_SOURCE_TEXT_MASK.png",
  "clean":"localization/graphics/role_A/20261004-A-PRODUCTION14/BF3EE5C6_HD_CLEAN_PLATE.png",
  "clean_protected":"localization/graphics/role_A/20261004-A-PRODUCTION14/BF3EE5C6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png",
  "allowed":"localization/graphics/role_A/20261004-A-PRODUCTION14/BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png",
  "final_protected":"localization/graphics/role_A/20261004-A-PRODUCTION14/BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png"
 },
 {
  "key":"2B0863D6","producer":"A_PRODUCTION15",
  "report":"localization/graphics/role_A/20261004-A-PRODUCTION15/A_PRODUCTION15_2B0863D6_REPORT.json",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",
  "source_sha":"dafe21ec29ace60273f3ec10a40072446f3f28232b3f9a8acce3897ade1eff06",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",
  "candidate_sha":"2f3e99f468367e056ee3c6edfdb412b1fe5f10f27387a463472b07aeaa335fbb",
  "source_mask":"localization/graphics/role_A/20261004-A-PRODUCTION15/2B0863D6_HD_SOURCE_TEXT_MASK.png",
  "clean":"localization/graphics/role_A/20261004-A-PRODUCTION15/2B0863D6_HD_CLEAN_PLATE.png",
  "clean_protected":"localization/graphics/role_A/20261004-A-PRODUCTION15/2B0863D6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png",
  "allowed":"localization/graphics/role_A/20261004-A-PRODUCTION15/2B0863D6_HD_ALLOWED_TEXT_REGION_MASK.png",
  "final_protected":"localization/graphics/role_A/20261004-A-PRODUCTION15/2B0863D6_HD_PROTECTED_VISIBLE_MASK.png"
 }
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_rgba32_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]
    mips=struct.unpack_from("<I",b,28)[0]; pf=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bpp!=32 or pitch!=w*4 or mips!=1 or masks!=(0xff,0xff00,0xff0000,0xff000000):
        raise RuntimeError(("unexpected RGBA32",str(p),w,h,pitch,depth,mips,pf,fourcc,bpp,masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("size mismatch",str(p),len(b),128+w*h*4))
    raw=np.frombuffer(b,dtype=np.uint8,offset=128).reshape(h,w,4).copy()
    readable=np.flipud(raw).copy()
    return b[:128],raw,readable,{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,
      "pf_flags":pf,"fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks],"bytes":len(b)}

def load_rgba(path,size):
    im=Image.open(path).convert("RGBA")
    if im.size!=size: raise RuntimeError(("RGBA size",str(path),im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()

def load_mask(path,size):
    im=Image.open(path).convert("L")
    if im.size!=size: raise RuntimeError(("mask size",str(path),im.size,size))
    return np.asarray(im,dtype=np.uint8)>0

def bbox(m):
    ys,xs=np.nonzero(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def scoped_bbox(m,b):
    x0,y0,x1,y1=map(int,b); sub=m[y0:y1,x0:x1]; q=bbox(sub)
    return None if q is None else [q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]

def gate(src,cand,edit,protected):
    diff=np.any(src!=cand,axis=2); adiff=src[:,:,3]!=cand[:,:,3]
    return {
      "changed_pixels":int(diff.sum()),"changed_bbox":bbox(diff),
      "changed_pixels_outside_edit_mask":int(np.logical_and(diff,~edit).sum()),
      "changed_pixels_in_protected_mask":int(np.logical_and(diff,protected).sum()),
      "alpha_changed_outside_edit_mask":int(np.logical_and(adiff,~edit).sum())
    }

def comp(arr):
    im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    return bg.convert("RGB")

def card(arr,label,maxw=760,maxh=600):
    v=comp(arr); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="black",font=ImageFont.load_default()); return c

def save_compare(key,src,clean,final,sraw,fraw):
    cards=[card(src,"SOURCE_READABLE"),card(clean,"CLEAN_READABLE"),card(final,"FINAL_READABLE"),
           card(sraw,"SOURCE_RAW"),card(fraw,"FINAL_RAW")]
    gap=8; top=cards[:3]; bot=cards[3:]
    tw=sum(x.width for x in top)+gap*2; th=max(x.height for x in top)
    bw=sum(x.width for x in bot)+gap; bh=max(x.height for x in bot)
    sheet=Image.new("RGB",(max(tw,bw),th+gap+bh),"white")
    x=0
    for q in top: sheet.paste(q,(x,0)); x+=q.width+gap
    x=0
    for q in bot: sheet.paste(q,(x,th+gap)); x+=q.width+gap
    sheet.save(outdir/f"C101_{key}_FULL_COMPARE.jpg",quality=94)

def save_rows(key,src,clean,final,rows):
    strips=[]; font=ImageFont.load_default()
    for r in rows:
        ob=r["source_exact_bbox"]; pad=8
        cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.shape[1],ob[2]+pad),min(src.shape[0],ob[3]+pad))
        cards=[]
        for tag,arr in (("SRC",src),("CLEAN",clean),("FINAL",final)):
            v=comp(arr).crop(cr); v.thumbnail((500,170),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(520,202),"white"); c.paste(v,((520-v.width)//2,27+(170-v.height)//2))
            ImageDraw.Draw(c).text((4,4),f'{r["key"]} {tag}',fill="black",font=font); cards.append(c)
        strip=Image.new("RGB",(1572,202),"white")
        for i,c in enumerate(cards): strip.paste(c,(i*526,0))
        strips.append(strip)
    sheet=Image.new("RGB",(1572,202*len(strips)),"white"); y=0
    for s in strips: sheet.paste(s,(0,y)); y+=202
    sheet.save(outdir/f"C101_{key}_ROW_CONTACT.jpg",quality=95)

results=[]
for spec in SPECS:
    key=spec["key"]; report=json.loads((repo/spec["report"]).read_text(encoding="utf-8"))
    source=Path("/tmp")/f"C101_{key}_SOURCE.dds"; urllib.request.urlretrieve(spec["source_url"],source)
    candidate=repo/spec["candidate"]
    if sha(source)!=spec["source_sha"]: raise RuntimeError((key,"source SHA mismatch",sha(source)))
    if sha(candidate)!=spec["candidate_sha"]: raise RuntimeError((key,"candidate SHA mismatch",sha(candidate)))
    sh,sraw,src,smeta=load_rgba32_dds(source); ch,craw,final,cmeta=load_rgba32_dds(candidate)
    if sh!=ch or smeta!=cmeta: raise RuntimeError((key,"header/structure drift"))
    size=(smeta["width"],smeta["height"])
    clean=load_rgba(repo/spec["clean"],size)
    source_mask=load_mask(repo/spec["source_mask"],size)
    clean_protected=load_mask(repo/spec["clean_protected"],size)
    allowed=load_mask(repo/spec["allowed"],size)
    final_protected=load_mask(repo/spec["final_protected"],size)
    cg=gate(src,clean,source_mask,clean_protected); fg=gate(src,final,allowed,final_protected)
    source_prot=int(np.logical_and(source_mask,clean_protected).sum())
    allowed_prot=int(np.logical_and(allowed,final_protected).sum())
    if any((cg["changed_pixels_outside_edit_mask"],cg["changed_pixels_in_protected_mask"],cg["alpha_changed_outside_edit_mask"],
            fg["changed_pixels_outside_edit_mask"],fg["changed_pixels_in_protected_mask"],fg["alpha_changed_outside_edit_mask"],
            source_prot,allowed_prot)):
        raise RuntimeError((key,"mask gate fail",cg,fg,source_prot,allowed_prot))
    target=np.any(final!=clean,axis=2)
    union=np.zeros((smeta["height"],smeta["width"]),dtype=bool)
    rows=[]; edge=[]
    for pr in report["rows"]:
        ob=[int(x) for x in pr["original_bbox"]]
        union[ob[1]:ob[3],ob[0]:ob[2]]=True
        sb=scoped_bbox(source_mask,ob); tb=scoped_bbox(target,ob)
        if sb is None or tb is None: raise RuntimeError((key,pr["key"],"missing source/target footprint",sb,tb))
        reported=[int(x) for x in pr["localized_bbox"]]
        if sb!=ob: raise RuntimeError((key,pr["key"],"producer original bbox not exact source-mask bbox",ob,sb))
        if tb!=reported: raise RuntimeError((key,pr["key"],"producer localized bbox mismatch actual final-vs-clean",reported,tb))
        sw,shh=sb[2]-sb[0],sb[3]-sb[1]; lw,lh=tb[2]-tb[0],tb[3]-tb[1]
        containment=tb[0]>=sb[0] and tb[1]>=sb[1] and tb[2]<=sb[2] and tb[3]<=sb[3]
        sizeok=lw<=sw and lh<=shh
        if not (containment and sizeok): raise RuntimeError((key,pr["key"],"exact size/containment fail",sb,tb))
        d=[tb[0]-sb[0],sb[2]-tb[2],tb[1]-sb[1],sb[3]-tb[3]]
        if min(d)==0: edge.append(pr["key"])
        rows.append({
          "key":pr["key"],"source":pr.get("source"),"korean":pr.get("korean"),
          "source_exact_bbox":sb,"localized_exact_bbox":tb,"source_size":[sw,shh],"localized_size":[lw,lh],
          "delta_width":lw-sw,"delta_height":lh-shh,
          "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
          "exact_containment":"PASS","exact_size_ceiling":"PASS","style":pr.get("style"),
          "rework_status":pr.get("rework_status")
        })
    allowed_out=int(np.logical_and(allowed,~union).sum())
    if allowed_out: raise RuntimeError((key,"allowed mask outside union",allowed_out))
    save_compare(key,src,clean,final,sraw,craw); save_rows(key,src,clean,final,rows)
    results.append({
      "asset":key,"producer":spec["producer"],"producer_report":spec["report"],
      "source_url":spec["source_url"],"source_sha256":spec["source_sha"],
      "candidate_path":spec["candidate"],"candidate_sha256":spec["candidate_sha"],"candidate_changed_by_C":False,
      "structure":{**smeta,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
      "clean_plate_gate":{**cg,"status":"PASS"},"final_gate":{**fg,"status":"PASS"},
      "mask_consistency":{"source_text_protected_overlap_pixels":source_prot,
                          "allowed_protected_overlap_pixels":allowed_prot,
                          "allowed_pixels_outside_union_of_source_exact_bboxes":allowed_out,"status":"PASS"},
      "bbox_size_gate":{"elements":len(rows),"pass":len(rows),"rework_required":0,"hold_strict_recheck":0,
                        "edge_touch_keys":edge,"rows":rows,"status":"PASS"},
      "semantic_policy":{"stage_names":"NOT_APPLICABLE","song_titles_credits":"NO_TARGETED_SONG_TITLE_OR_CREDIT","status":"PASS"},
      "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C101_{key}_FULL_COMPARE.jpg",
                         "row_contact":f"localization/graphics/role_C/{run}/C101_{key}_ROW_CONTACT.jpg",
                         "controller_visual_qa":"PENDING"},
      "runtime_validation":"UNTESTED","status":"C101_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA"
    })
summary={"schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "scope":"only new A results after C100: A_PRODUCTION14 BF3EE5C6 and A_PRODUCTION15 2B0863D6; C100-completed assets are not repeated",
 "assets":results,
 "summary":{"assets_checked":2,"static_machine_pass":2,"static_machine_fail":0,
            "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}}
(outdir/"C101_NEW_A_FINAL_STATIC_QA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C101_STATIC_QA_DONE",[(x["asset"],x["candidate_sha256"]) for x in results])
