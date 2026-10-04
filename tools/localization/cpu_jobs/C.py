#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd()
run="20261004-1920-C98"
outdir=repo/"localization/graphics/role_C"/run
outdir.mkdir(parents=True,exist_ok=True)

SPECS=[
 {
  "key":"455717B2","producer":"A_PRODUCTION10",
  "report":"localization/graphics/role_A/20261004-A-PRODUCTION10/A_PRODUCTION10_455717B2_REPORT.json",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",
  "source_sha":"ce5d3610eac8945d76a559bb7f7201f9b1efb409c965bd20ed0a26164ed7f356",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",
  "candidate_sha":"50bb8b8d0541a090e032d47d1ebc62800b559a48f5ddb22e8982c8b625b1773f",
  "source_mask":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_SOURCE_TEXT_MASK.png",
  "clean":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_CLEAN_PLATE.png",
  "clean_protected":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_CLEAN_PROTECTED_VISIBLE_MASK.png",
  "allowed":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_ALLOWED_TEXT_REGION_MASK.png",
  "final_protected":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_PROTECTED_VISIBLE_MASK.png"
 },
 {
  "key":"43B07A77","producer":"A_PRODUCTION12",
  "report":"localization/graphics/role_A/20261004-A-PRODUCTION12/A_PRODUCTION12_43B07A77_REPORT.json",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  "source_sha":"906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  "candidate_sha":"d2311d4c20327363bacf8b336e925e527ef8c5c8f13a385b0a2fb2e25a946cbc",
  "source_mask":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_SOURCE_TEXT_MASK.png",
  "clean":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png",
  "clean_protected":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PROTECTED_VISIBLE_MASK.png",
  "allowed":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_ALLOWED_TEXT_REGION_MASK.png",
  "final_protected":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_PROTECTED_VISIBLE_MASK.png"
 },
 {
  "key":"CBF8ECBF","producer":"B_RECOVERY08",
  "report":"localization/graphics/role_B/20261004-B-RECOVERY08/B_RECOVERY08_CBF8ECBF_REPORT.json",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds",
  "source_sha":"3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe",
  "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds",
  "candidate_sha":"ecc4cbb6cdc064d2c7ccccfc378569f1dc7fc8339c46330ec68ec81c8f899df1",
  "source_mask":"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_SOURCE_TEXT_MASK.png",
  "clean":"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_CLEAN_PLATE.png",
  "clean_protected":"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_PROTECTED_MASK.png",
  "allowed":"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_ALLOWED_TEXT_REGION_MASK.png",
  "final_protected":"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_PROTECTED_MASK.png"
 }
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
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
    read=np.flipud(raw).copy()
    return b[:128],raw,read,{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"pf_flags":pf,
                              "fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks],"bytes":len(b)}
def png_rgba(p,size):
    im=Image.open(p).convert("RGBA")
    if im.size!=size: raise RuntimeError(("PNG size",str(p),im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()
def mask(p,size):
    im=Image.open(p).convert("L")
    if im.size!=size: raise RuntimeError(("mask size",str(p),im.size,size))
    return np.asarray(im,dtype=np.uint8)>0
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def gate(src,cand,edit,protected):
    d=np.any(src!=cand,axis=2); ad=src[:,:,3]!=cand[:,:,3]
    return {"changed_pixels":int(d.sum()),"changed_bbox":bbox(d),
            "changed_pixels_outside_edit_mask":int(np.logical_and(d,~edit).sum()),
            "changed_pixels_in_protected_mask":int(np.logical_and(d,protected).sum()),
            "alpha_changed_outside_edit_mask":int(np.logical_and(ad,~edit).sum())}
def panel(arr,label,maxw=720,maxh=640):
    im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    v=bg.convert("RGB"); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+24),"white"); c.paste(v,(0,24))
    ImageDraw.Draw(c).text((4,4),label,fill="black",font=ImageFont.load_default())
    return c
def save_compare(key,src,clean,final,sraw,fraw):
    cards=[panel(src,"SOURCE_READABLE"),panel(clean,"CLEAN_READABLE"),panel(final,"FINAL_READABLE"),
           panel(sraw,"SOURCE_RAW"),panel(fraw,"FINAL_RAW")]
    gap=8; top=cards[:3]; bot=cards[3:]
    tw=sum(c.width for c in top)+gap*2; th=max(c.height for c in top)
    bw=sum(c.width for c in bot)+gap; bh=max(c.height for c in bot)
    sheet=Image.new("RGB",(max(tw,bw),th+gap+bh),"white")
    x=0
    for c in top: sheet.paste(c,(x,0)); x+=c.width+gap
    x=0
    for c in bot: sheet.paste(c,(x,th+gap)); x+=c.width+gap
    sheet.save(outdir/f"C98_{key}_FULL_COMPARE.jpg",quality=94)
def save_rows(key,src,clean,final,rows):
    font=ImageFont.load_default(); strips=[]
    for r in rows:
        ob=r["original_bbox"]; pad=8
        cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.shape[1],ob[2]+pad),min(src.shape[0],ob[3]+pad))
        cs=[]
        for tag,arr in (("SRC",src),("CLEAN",clean),("FINAL",final)):
            im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
            v=bg.convert("RGB").crop(cr); v.thumbnail((480,170),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(500,202),"white"); c.paste(v,((500-v.width)//2,27+(170-v.height)//2))
            ImageDraw.Draw(c).text((4,4),f'{r["key"]} {tag}',fill="black",font=font); cs.append(c)
        strip=Image.new("RGB",(1512,202),"white")
        for i,c in enumerate(cs): strip.paste(c,(i*506,0))
        strips.append(strip)
    sheet=Image.new("RGB",(1512,202*len(strips)),"white")
    y=0
    for s in strips: sheet.paste(s,(0,y)); y+=202
    sheet.save(outdir/f"C98_{key}_ROW_CONTACT.jpg",quality=95)

results=[]
for spec in SPECS:
    key=spec["key"]
    report=json.loads((repo/spec["report"]).read_text(encoding="utf-8"))
    source=Path("/tmp")/f"C98_{key}_SOURCE.dds"
    urllib.request.urlretrieve(spec["source_url"],source)
    candidate=repo/spec["candidate"]
    if sha(source)!=spec["source_sha"]: raise RuntimeError((key,"source SHA mismatch",sha(source)))
    if sha(candidate)!=spec["candidate_sha"]: raise RuntimeError((key,"candidate SHA mismatch",sha(candidate)))
    sh,sraw,src,smeta=load_dds(source); ch,craw,final,cmeta=load_dds(candidate)
    if sh!=ch or smeta!=cmeta: raise RuntimeError((key,"header/structure drift"))
    size=(smeta["width"],smeta["height"])
    clean=png_rgba(repo/spec["clean"],size)
    sm=mask(repo/spec["source_mask"],size); cp=mask(repo/spec["clean_protected"],size)
    allowed=mask(repo/spec["allowed"],size); fp=mask(repo/spec["final_protected"],size)
    cg=gate(src,clean,sm,cp); fg=gate(src,final,allowed,fp)
    overlaps={"source_text_protected":int(np.logical_and(sm,cp).sum()),
              "allowed_protected":int(np.logical_and(allowed,fp).sum())}
    if any((cg["changed_pixels_outside_edit_mask"],cg["changed_pixels_in_protected_mask"],cg["alpha_changed_outside_edit_mask"],
            fg["changed_pixels_outside_edit_mask"],fg["changed_pixels_in_protected_mask"],fg["alpha_changed_outside_edit_mask"],
            overlaps["source_text_protected"],overlaps["allowed_protected"])):
        raise RuntimeError((key,"mask gate fail",cg,fg,overlaps))
    if key=="43B07A77":
        source_rows=[{"key":"game_over","source":report["translation"]["source"],"korean":report["translation"]["korean"],
                      "original_bbox":report["original_bbox"],"localized_bbox":report["localized_bbox"],
                      "rework_status":"A_PRODUCTION12_HD_REBUILD"}]
    else:
        source_rows=report["rows"]
    target=np.any(final!=clean,axis=2)
    union=np.zeros((smeta["height"],smeta["width"]),dtype=bool)
    rows=[]; edge=[]
    for r in source_rows:
        ob=[int(x) for x in r["original_bbox"]]; lb=[int(x) for x in r["localized_bbox"]]
        union[ob[1]:ob[3],ob[0]:ob[2]]=True
        if not (ob[0]<=lb[0] and ob[1]<=lb[1] and lb[2]<=ob[2] and lb[3]<=ob[3]):
            raise RuntimeError((key,r["key"],"reported containment fail",ob,lb))
        local=np.zeros_like(target); local[ob[1]:ob[3],ob[0]:ob[2]]=target[ob[1]:ob[3],ob[0]:ob[2]]
        db=bbox(local)
        if db is None: raise RuntimeError((key,r["key"],"empty final-vs-clean"))
        if not (ob[0]<=db[0] and ob[1]<=db[1] and db[2]<=ob[2] and db[3]<=ob[3]):
            raise RuntimeError((key,r["key"],"derived containment fail",ob,db))
        d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
        if min(d)==0: edge.append(r["key"])
        rows.append({"key":r["key"],"source":r.get("source"),"korean":r.get("korean"),
                     "original_bbox":ob,"localized_bbox":lb,"derived_final_vs_clean_bbox":db,
                     "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
                     "containment":"PASS","rework_status":r.get("rework_status")})
    allowed_out=int(np.logical_and(allowed,~union).sum())
    if allowed_out: raise RuntimeError((key,"allowed mask outside row union",allowed_out))
    save_compare(key,src,clean,final,sraw,craw); save_rows(key,src,clean,final,rows)
    results.append({
      "asset":key,"producer":spec["producer"],"producer_report":spec["report"],
      "source_url":spec["source_url"],"source_sha256":spec["source_sha"],"candidate_path":spec["candidate"],
      "candidate_sha256":spec["candidate_sha"],"candidate_changed_by_C":False,
      "structure":{**smeta,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
      "clean_plate_gate":{**cg,"status":"PASS"},"final_gate":{**fg,"status":"PASS"},
      "mask_consistency":{**overlaps,"allowed_pixels_outside_union_of_original_bboxes":allowed_out,"status":"PASS"},
      "bbox_gate":{"elements":len(rows),"pass":len(rows),"fail":0,"edge_touch_keys":edge,"rows":rows,"status":"PASS"},
      "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C98_{key}_FULL_COMPARE.jpg",
                         "row_contact":f"localization/graphics/role_C/{run}/C98_{key}_ROW_CONTACT.jpg","controller_visual_qa":"PENDING"},
      "runtime_validation":"UNTESTED","status":"C98_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA"
    })
summary={"schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
         "scope":"new pending C candidates only: A_PRODUCTION10 455717B2, A_PRODUCTION12 43B07A77, B_RECOVERY08 CBF8ECBF; C96-finalized FD90AA9/B1696633 are not recomputed",
         "assets":results,"summary":{"assets_checked":len(results),"static_machine_pass":len(results),"static_machine_fail":0,
                                      "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}}
(outdir/"C98_CROSS_LANE_STATIC_QA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C98_STATIC_QA_DONE",[(x["asset"],x["candidate_sha256"]) for x in results])
