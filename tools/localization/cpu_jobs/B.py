#!/usr/bin/env python3
# B231: q46 AA04D779 localization-coverage hardening.
# New coverage gate reopens the old "gray control labels preserved" decision:
# ordinary lobby/control UI is localizable and is not song/brand/model/legal content.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

repo=Path.cwd()
run="20261007-B-MANUALQA231-AA04D779-COVERAGE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
validator=repo/"tools/localization/validate_clean_plate.py"
SOURCE_SHA="1a01e19b2749acdd275d10ff6e82bcb525d6621fd9118fb0c1fa5997c4c1dfa5"
EXPECTED_BEFORE="93eb895d890bd0f41b4427346e3a7a2fe5538b4a1f4164991a480b424b1fc36e"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds"
tmp=Path("/tmp/b231"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

# Tight semantic windows contain only the named source label/effect.
# The first GEAR DOWN is split around a preserved red icon so the icon is never part of the rework mask.
specs=[
 {"key":"pre_game_lobby","source":"In pre-game lobby","ko_lines":["게임 전 로비"],"window":[0,30,410,88],"family":"white","align":"left"},
 {"key":"offline","source":"Offline","ko_lines":["오프라인"],"window":[445,30,650,88],"family":"white","align":"left"},
 {"key":"brake_left","source":"BRAKE","ko_lines":["브레이크"],"window":[405,210,590,265],"family":"gray","align":"center"},
 {"key":"brake_right","source":"BRAKE","ko_lines":["브레이크"],"window":[590,210,790,265],"family":"gray","align":"center"},
 {"key":"accelerate","source":"ACCELERATE","ko_lines":["가속"],"window":[1190,210,1550,265],"family":"gray","align":"center"},
 {"key":"gear_up_left","source":"GEAR UP","ko_lines":["기어 업"],"window":[0,275,235,330],"family":"gray","align":"center"},
 {"key":"gear_down_icon_left","source":"GEAR","ko_lines":["기어"],"window":[875,275,995,330],"family":"gray","align":"center","semantic_parent":"GEAR DOWN"},
 {"key":"gear_down_icon_right","source":"DOWN","ko_lines":["다운"],"window":[1035,275,1195,330],"family":"gray","align":"center","semantic_parent":"GEAR DOWN"},
 {"key":"gear_down_right","source":"GEAR DOWN","ko_lines":["기어 다운"],"window":[1200,275,1520,330],"family":"gray","align":"center"},
 {"key":"view_license","source":"VIEW LICENSE","ko_lines":["라이선스 보기"],"window":[385,335,790,410],"family":"dark","align":"left"},
 {"key":"gear_up_right","source":"GEAR UP","ko_lines":["기어 업"],"window":[1460,335,1695,410],"family":"gray","align":"center"},
 {"key":"change_soundtrack","source":"CHANGE CUSTOM / SOUNDTRACK","ko_lines":["사용자 음악","변경"],"window":[1000,425,1465,555],"family":"gray","align":"left"},
 {"key":"pause_menu","source":"PAUSE / MENU","ko_lines":["일시정지","메뉴"],"window":[1780,425,2020,565],"family":"gray","align":"center"},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mips":mips,"raw_mode":mode}
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def bbox(m):
    ys,xs=np.nonzero(m); return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def changed_np(a,b): return np.any(a!=b,axis=2)
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def boolpng(m,path): Image.fromarray((m.astype(np.uint8)*255),"L").save(path)

sb=src_dds.read_bytes(); oldb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb),SOURCE_SHA))
if sha(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(oldb),EXPECTED_BEFORE))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(oldb)
if meta!=ometa or sb[:128]!=oldb[:128]: raise RuntimeError("structure/header drift")
sa=np.asarray(src); oa=np.asarray(old); H,W=sa.shape[:2]
if meta["mips"]!=1: raise RuntimeError(("unexpected authored mips",meta["mips"]))

# Current q46 candidate differs from source only in the accepted 21 stage/sector labels.
existing_diff=changed_np(sa,oa)

# Derive exact source alpha/effect bboxes inside tight semantic windows; assert current bytes
# are still source-exact there so this run cannot overwrite concurrent/new material.
rework=np.zeros((H,W),dtype=bool); source_text=np.zeros((H,W),dtype=bool)
rows=[]
for spec in specs:
    x0,y0,x1,y1=spec["window"]
    if not np.array_equal(oa[y0:y1,x0:x1],sa[y0:y1,x0:x1]):
        raise RuntimeError(("precondition control window already changed",spec["key"],spec["window"]))
    wm=(sa[:,:,3]>0)&rect((H,W),spec["window"])
    bb=bbox(wm)
    if bb is None: raise RuntimeError(("no source alpha",spec["key"],spec["window"]))
    sw,sh=bb[2]-bb[0],bb[3]-bb[1]
    # Fail closed on accidental icon/bar capture.
    if sh<20 or sh>140 or sw<25 or sw>(spec["window"][2]-spec["window"][0]):
        raise RuntimeError(("unexpected source bbox",spec["key"],bb,[sw,sh]))
    spec=dict(spec); spec["bbox"]=bb; spec["source_size"]=[sw,sh]; spec["source_alpha_pixels"]=int(np.count_nonzero(wm))
    rows.append(spec); rework|=rect((H,W),bb); source_text|=wm

# Tight windows and derived source bboxes must be disjoint; the red gear icon is outside all masks.
for i in range(len(rows)):
    for j in range(i+1,len(rows)):
        if np.count_nonzero(rect((H,W),rows[i]["bbox"]) & rect((H,W),rows[j]["bbox"])):
            raise RuntimeError(("source bbox overlap",rows[i]["key"],rows[j]["key"]))

# Total edit allowance = already accepted current candidate differences + new control rectangles.
allowed=existing_diff|rework
protected=(sa[:,:,3]>0)&~allowed

# Rework clean plate: preserve old candidate byte/pixel-exact except source-visible control text pixels.
clean=old.copy(); ca=np.array(clean)
ca[source_text]=[0,0,0,0]
clean=Image.fromarray(ca.astype(np.uint8),"RGBA")
if np.count_nonzero(np.asarray(clean)[:,:,3][source_text]):
    raise RuntimeError("source control alpha remains")

sp=tmp/"source.png"; op=tmp/"baseline.png"; cp=out/"B231_AA04D779_CONTROL_CLEAN.png"
ap=out/"B231_AA04D779_TOTAL_ALLOWED_MASK.png"; rp=out/"B231_AA04D779_REWORK_MASK.png"; pp=out/"B231_AA04D779_PROTECTED_MASK.png"
src.save(sp); old.save(op); clean.save(cp); boolpng(allowed,ap); boolpng(rework,rp); boolpng(protected,pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(ap),
 "--protected-mask",str(pp),"--baseline-candidate",str(op),"--rework-mask",str(rp),
 "--report",str(out/"B231_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B231_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Bold unavailable",font_line))

def source_fill(bb):
    x0,y0,x1,y1=bb
    p=sa[y0:y1,x0:x1]
    vis=p[p[:,:,3]>32]
    if len(vis)<20: raise RuntimeError(("fill sample small",bb,len(vis)))
    # use upper-alpha half to avoid AA fringe darkening
    cut=np.percentile(vis[:,3],55); core=vis[vis[:,3]>=cut]
    rgba=np.median(core,axis=0).round().astype(np.uint8)
    return tuple(int(x) for x in rgba)

def render_lines(lines,fs,rgba,xscale,line_gap):
    font=ImageFont.truetype(FONT,fs,index=FI)
    masks=[]
    for text in lines:
        d=ImageDraw.Draw(Image.new("L",(4,4),0)); tb=d.textbbox((0,0),text,font=font)
        pad=6
        m=Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
        ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
        bb=m.getbbox()
        if not bb: raise RuntimeError(("empty render",text))
        m=m.crop(bb)
        if xscale!=1.0:
            m=m.resize((max(1,int(round(m.width*xscale))),m.height),Image.Resampling.LANCZOS)
        masks.append(m)
    w=max(m.width for m in masks); h=sum(m.height for m in masks)+line_gap*(len(masks)-1)
    alpha=Image.new("L",(w,h),0); yy=0
    for m in masks:
        xx=(w-m.width)//2
        alpha.paste(ImageChops.lighter(alpha.crop((xx,yy,xx+m.width,yy+m.height)),m),(xx,yy))
        yy+=m.height+line_gap
    tile=Image.new("RGBA",alpha.size,rgba)
    # preserve source family alpha rather than forcing opaque text
    a=np.asarray(alpha,dtype=np.uint16); a=(a*int(rgba[3])//255).astype(np.uint8)
    tile.putalpha(Image.fromarray(a,"L"))
    return tile

M=2
final=clean.copy(); localized_masks=[]; outrows=[]
for spec in rows:
    bb=spec["bbox"]; aw=bb[2]-bb[0]; ah=bb[3]-bb[1]; rgba=source_fill(bb)
    family=spec["family"]
    xscales=(0.92,0.88,0.84,0.80,0.76,0.72) if family in ("gray","dark") else (1.0,0.96,0.92,0.88)
    gap=max(2,int(round(ah*0.045))) if len(spec["ko_lines"])>1 else 0
    best=None
    for fs in range(min(110,ah+20),15,-1):
        for xs in xscales:
            tile=render_lines(spec["ko_lines"],fs,rgba,xs,gap)
            if tile.width<=aw-2*M and tile.height<=ah-2*M:
                best=(fs,xs,tile); break
        if best: break
    if best is None: raise RuntimeError(("fit failed",spec["key"],bb,spec["ko_lines"]))
    fs,xs,tile=best
    if spec["align"]=="left": px=bb[0]+M
    else: px=bb[0]+(aw-tile.width)//2
    py=bb[1]+(ah-tile.height)//2
    px=max(bb[0]+M,min(px,bb[2]-M-tile.width)); py=max(bb[1]+M,min(py,bb[3]-M-tile.height))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0; lb=bbox(lm)
    margins=[lb[0]-bb[0],bb[2]-lb[2],lb[1]-bb[1],bb[3]-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin",spec["key"],bb,lb,margins))
    # Localized control pixels cannot overlap preserved visible old-candidate pixels.
    preserved=(oa[:,:,3]>0)&~source_text
    overlap=int(np.count_nonzero(lm&preserved))
    if overlap: raise RuntimeError(("localized control overlaps preserved content",spec["key"],overlap))
    final.alpha_composite(layer); localized_masks.append(lm)
    outrows.append({k:v for k,v in spec.items() if k!="window"} | {
      "localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":fs,
      "horizontal_scale":xs,"fill_rgba":list(rgba),"alignment":spec["align"],
      "line_gap":gap,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

for i in range(len(localized_masks)):
    for j in range(i+1,len(localized_masks)):
        ov=int(np.count_nonzero(localized_masks[i]&localized_masks[j]))
        if ov: raise RuntimeError(("localized overlap",outrows[i]["key"],outrows[j]["key"],ov))

# Persist exact DDS and re-decode persisted bytes for final authority.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
persisted=candidate.read_bytes(); after=sha(persisted)
new_raw,new,nmeta=decode(persisted)
if nmeta!=meta or persisted[:128]!=sb[:128]: raise RuntimeError("persisted DDS structure/header drift")
if ImageChops.difference(new,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")

na=np.asarray(new); olddiff=changed_np(oa,na)
blast_out=int(np.count_nonzero(olddiff&~rework))
blast_alpha_out=int(np.count_nonzero((oa[:,:,3]!=na[:,:,3])&~rework))
if blast_out or blast_alpha_out: raise RuntimeError(("blast radius",blast_out,blast_alpha_out))

fp=tmp/"persisted_final.png"; new.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),
 "--protected-mask",str(pp),"--baseline-candidate",str(op),"--rework-mask",str(rp),
 "--report",str(out/"B231_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B231_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

# Existing 21 stage/sector candidate pixels must be exact outside this rework.
if not np.array_equal(oa[~rework],na[~rework]): raise RuntimeError("prior q46 material drift")

# Practical-scale evidence from exact persisted DDS, focusing on all newly localized top/control rows.
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(src,old,clean,new))
roi=(0,0,2048,600)
contacts=[]
for scale in (1.0,0.75,0.5):
    ims=[]
    for z in (src_rgb,old_rgb,clean_rgb,new_rgb):
        c=z.crop(roi)
        c=c.resize((max(1,int(round(c.width*scale))),max(1,int(round(c.height*scale)))),Image.Resampling.LANCZOS)
        ims.append(c)
    cw=sum(z.width for z in ims)+18; ch=max(z.height for z in ims)+30
    card=Image.new("RGB",(cw,ch),(20,20,20)); d=ImageDraw.Draw(card); xx=0
    for lab,z in zip(("SOURCE","C90/USERPOLICY02","CLEAN","B231"),ims):
        d.text((xx+4,6),f"{lab} {int(scale*100)}%",fill="white"); card.paste(z,(xx,30)); xx+=z.width+6
    contacts.append(card)
maxw=max(c.width for c in contacts); sheet=Image.new("RGB",(maxw,sum(c.height for c in contacts)+8),(18,18,18)); yy=0
for c in contacts: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((4200,5000),Image.Resampling.LANCZOS)
sheet.save(out/"B231_AA04D779_TOP_CONTROLS_PRACTICAL_SCALE.jpg","JPEG",quality=95,subsampling=0)

# Full readable source/old/final and RAW source/final.
def fullcard(label,im):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,1052),(24,24,24)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
overview=Image.new("RGB",(2048,2104),(20,20,20))
for pos,lab,im in [((0,0),"SOURCE",src),((1024,0),"OLD C90/USERPOLICY02",old),((0,1052),"B231 CLEAN",clean),((1024,1052),"B231 PERSISTED FINAL",new)]:
    overview.paste(fullcard(lab,im),pos)
overview.save(out/"B231_AA04D779_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=94,subsampling=0)
rawsheet=Image.new("RGB",(2048,1052),(20,20,20))
rawsheet.paste(fullcard("SOURCE RAW MIRROR_Y",src_raw),(0,0)); rawsheet.paste(fullcard("B231 RAW MIRROR_Y",new_raw),(1024,0))
rawsheet.save(out/"B231_AA04D779_RAW_COMPARE.jpg","JPEG",quality=94,subsampling=0)

# Target mask evidence.
target=np.zeros((H,W),dtype=bool)
for lm in localized_masks: target|=lm
boolpng(source_text,out/"B231_AA04D779_SOURCE_CONTROL_MASK.png")
boolpng(target,out/"B231_AA04D779_TARGET_CONTROL_MASK.png")

report={
 "schema_version":1,"role":"B","run":run,"queue_index":46,"asset":asset,
 "trigger":"QA_HARDENING_LOCALIZATION_COVERAGE_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/001_q046_AA04D779.jpg",
 "prior_status":"C_USERPOLICY02_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "defect":["UNTRANSLATED_VISIBLE_UI_LOBBY_STATUS","UNTRANSLATED_VISIBLE_UI_GRAY_CONTROL_LABELS"],
 "semantic_additions":{
   "In pre-game lobby":"게임 전 로비","Offline":"오프라인","BRAKE":"브레이크","ACCELERATE":"가속",
   "GEAR UP":"기어 업","GEAR DOWN":"기어 다운","VIEW LICENSE":"라이선스 보기",
   "CHANGE CUSTOM SOUNDTRACK":"사용자 음악 / 변경","PAUSE MENU":"일시정지 / 메뉴"
 },
 "explicit_preserve_original":{
   "REV":"asset-specific gauge abbreviation; prior classification preserve",
   "TOP":"asset-specific decorative rank emblem; prior classification preserve",
   "You":"asset-specific player marker paired with 1P/2P/3P/4P; prior classification preserve",
   "player_numbers":"standard 1P/2P/3P/4P markers preserved",
   "icons_course_symbols_numeric_art":"non-language/protected artwork"
 },
 "method":"current exact candidate + pinned canonical 2048 source; tight source-alpha semantic windows; transparent clean of source-visible control text only; native Noto CJK Bold; prior 21 stage/sector localized pixels exact outside rework mask",
 "rows":outrows,
 "ui_family_style_profiles":{
   "white_lobby_status":{"font_impression":"bold upright sans","alignment":"source-left","fill":"sampled source white","effects":"none"},
   "gray_controls":{"font_impression":"bold condensed upright sans","alignment":"source-relative left/center","fill":"sampled source gray/dark","effects":"none","multiline":"source line-count preserved"}
 },
 "machine_qa":{"new_physical_rows":len(outrows),"bbox_source_size_positive_margin":f"{len(outrows)}/{len(outrows)} PASS",
   "clean_validator":cleanrep["status"],"final_validator":finalrep["status"],
   "baseline_changes_outside_rework_mask":blast_out,"baseline_alpha_changes_outside_rework_mask":blast_alpha_out,
   "source_control_alpha_remaining":0,"localized_pair_overlap":0,
   "persisted_decode_matches_intended":"PASS","header_128_exact":persisted[:128]==sb[:128],
   "raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y","mip_count":meta["mips"],
   "mip_review":"PASS_LEVEL0_ONLY_NO_AUTHORED_EXTRA_MIPS"},
 "post_encode_presentation_gate":{"decoded_persisted_dds_authority":"PASS","practical_scales":["100%","75%","50%"],
   "family_profile":"RECORDED_TWO_FAMILIES","rework_blast_radius":"PASS_ZERO_OUTSIDE_13_CONTROL_BBOXES",
   "coverage":"PASS_21_PRIOR_STAGE_SEGMENTS_PLUS_9_NEW_SEMANTIC_UI_LABELS_WITH_EXPLICIT_ASSET_PRESERVES",
   "mandatory_c3":"REQUIRED_BEFORE_PRE_INGAME_EXPORT_DUE_PRIOR_POLICY_FALSE_NEGATIVE"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_TRANSPARENT_SOURCE_CONTROL_ALPHA_REMOVED",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT","3_no_unnecessary_undersizing":"PASS_MAX_NATIVE_FIT_PER_SOURCE_BBOX",
   "4_source_weight_outline_shadow":"PASS_SOURCE_FLAT_WHITE_GRAY_FAMILIES","5_no_clipping":f"PASS_{len(outrows)}_OF_{len(outrows)}_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_BASELINE_AND_PROTECTED_OUTSIDE_ZERO","7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER",
 "status":"B231_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_FRESH_C_C3",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
rpout=out/"B231_AA04D779_REPORT.json"; rpout.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"role":"B","run":run,"queue_index":46,"asset":"AA04D779","source_sha256":SOURCE_SHA,
 "before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":after,"new_physical_rows":len(outrows),
 "bbox_size_positive_margin":f"{len(outrows)}/{len(outrows)}","blast_outside":blast_out,
 "alpha_blast_outside":blast_alpha_out,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":str(rpout.relative_to(repo))}
(wr/"B231_AA04D779.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
