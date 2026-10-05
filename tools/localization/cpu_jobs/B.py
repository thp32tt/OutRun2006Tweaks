#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION85"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
tmp=Path("/tmp/b84"); tmp.mkdir(exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_BA0147DA_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("unsupported source",W,H,pitch,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
at=json.loads(ab.decode())
if at.get("regions_count")!=60: raise RuntimeError(("atlas drift",at.get("regions_count")))
regions={r["idx"]:r for r in at["regions"]}

specs=[
 (14,"HEART ATTACK","하트 어택","red_big","left"),
 (15,"SHOWROOM","쇼룸","red_big","left"),
 (16,"COAST 2 COAST","코스트 2 코스트","red_big","left"),
 (17,"OUTRUN","아웃런","red_big","left"),
 (25,"SELECT STAR SIGN","별자리 선택","dark_menu","left"),
 (26,"SELECT PHOTO","사진 선택","dark_menu","left"),
 (27,"SELECT NATIONALITY","국적 선택","dark_menu","left"),
 (28,"ENTER NAME","이름 입력","dark_menu","left"),
 (30,"DONE","완료","dark_done_large","left"),
 (43,"PROFESSIONAL","프로","orange_prof","right"),
 (44,"OUTRUN","아웃런","red_small","right"),
 (53,"DONE","완료","dark_done_small","left"),
]
protected_semantics={"character_names":["CLARISSA","JENNIFER","WOLF","ALBERTO","HOLLY","SAM"],"car_color":["VERDE MUGELLO"],"zodiac_icons":"preserve","logos_icons":"preserve"}

source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0)
rows=[]; group_samples={}
for idx,en,ko,group,align in specs:
    x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch))
    lm=bmask(cell.getchannel("A")); bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty target",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    vals=[]; px=cell.load()
    for yy in range(ch):
      for xx in range(cw):
        r,g,b,a=px[xx,yy]
        if a>=192: vals.append((r,g,b,a))
    group_samples.setdefault(group,[]).extend(vals)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"group":group,"alignment":align,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(lm)})

clean=src.copy(); ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
sp=out/"BA_SOURCE_READABLE.png"; cp=out/"BA_CLEAN_PLATE.png"; sm=out/"BA_SOURCE_TEXT_MASK.png"; am=out/"BA_ALLOWED_BBOX_MASK.png"; pm=out/"BA_PROTECTED_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(sm); allowed.save(am); protected.save(pm)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(sm),"--protected-mask",str(pm),"--report",str(out/"B85_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B85_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if "NotoSansCJK" not in Path(FONT).name: raise RuntimeError(("font unavailable",font_line))

styles={}
for g,vals in group_samples.items():
    if len(vals)<30: raise RuntimeError(("style sample small",g,len(vals)))
    fill=tuple(int(round(statistics.median(v[k] for v in vals))) for k in range(3))+(255,)
    styles[g]={"fill_rgba":fill,"sample_count":len(vals)}

def render_low(text,fs,fill):
    f=ImageFont.truetype(FONT,fs,index=FI)
    t=Image.new("L",(8,8),0); bb=ImageDraw.Draw(t).textbbox((0,0),text,font=f)
    pad=2
    a=Image.new("L",(max(8,bb[2]-bb[0]+2*pad),max(8,bb[3]-bb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("empty render",text))
    a=a.crop(ab); rgba=Image.new("RGBA",a.size,fill); rgba.putalpha(a)
    return rgba.resize((rgba.width*4,rgba.height*4),Image.Resampling.NEAREST)

MARGIN=4
for g in styles:
    rs=[r for r in rows if r["group"]==g]; best=None
    for fs in range(40,4,-1):
        ok=True
        for r in rs:
            ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
            lay=render_low(r["korean"],fs,styles[g]["fill_rgba"])
            if lay.width>aw-2*MARGIN or lay.height>ah-2*MARGIN: ok=False; break
        if ok: best=fs; break
    if best is None: raise RuntimeError(("group fit failed",g))
    styles[g]["lowres_font_size"]=best; styles[g]["pixel_scale"]=4

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]; st=styles[r["group"]]
    lay=render_low(r["korean"],st["lowres_font_size"],st["fill_rgba"])
    px=ob[2]-MARGIN-lay.width if r["alignment"]=="right" else (ob[0]+(aw-lay.width)//2 if r["alignment"]=="center" else ob[0]+MARGIN)
    py=ob[1]+(ah-lay.height)//2; py=max(ob[1]+MARGIN,min(py,ob[3]-MARGIN-lay.height))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(lm.getbbox())
    if not (lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("positive margin",r["region_idx"],ob,lb))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah: raise RuntimeError(("size ceiling",r["region_idx"],ob,lb))
    targets.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"lowres_font_size":st["lowres_font_size"],"pixel_scale":4,"fill_rgba":st["fill_rgba"],"rework_status":"B85_NEW_EXACT_HD_CANDIDATE"})

overlap=0; touch=[]
for i in range(len(targets)):
    for j in range(i+1,len(targets)):
        x=count(ImageChops.multiply(targets[i][1],targets[j][1])); n=count(ImageChops.multiply(targets[i][1].filter(ImageFilter.MaxFilter(3)),targets[j][1]))
        overlap+=x
        if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128] or len(payload)!=len(sb): raise RuntimeError("dds structure drift")
candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")
fp=out/"BA_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(am),"--protected-mask",str(pm),"--report",str(out/"B85_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B85_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),bmask(dec.getchannel("A"))))
render_out=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
if finalrep["status"]!="PASS" or any([outside,alphaout,prot,residue,render_out,overlap]) or touch: raise RuntimeError(("final gates",finalrep["status"],outside,alphaout,prot,residue,render_out,overlap,touch))
target.save(out/"BA_TARGET_TEXT_MASK.png")

stack=Image.new("RGB",(1024,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"B85_BA_SOURCE_CLEAN_FINAL.jpg",quality=96)

cards=[]
for r in outrows:
    ob=r["original_bbox"]; p=14; cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]; maxw=max(z.width for z in ims); sc=min(2.0,650/max(1,maxw))
    ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((2200,16000),Image.Resampling.LANCZOS); sheet.save(out/"B85_BA_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"B85_BA_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"index":212,"asset":asset,"readiness_tier":"PREFLIGHT_TO_RENDER_COMPLETED_SAME_INVOCATION","source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},"semantic_binding":{"method":"B83 controller-reviewed numbered canonical atlas","physical_elements":len(specs),"rows":[{"region_idx":i,"source":en,"korean":ko,"group":g,"alignment":al} for i,en,ko,g,al in specs],"protected":protected_semantics},"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},"source_styles":styles,"rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"render_outside_target":render_out,"overlap":overlap,"touch_pairs":touch},"candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B85_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B85_BA_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":212,"asset":"BA0147DA","source_sha256":sha(sb),"candidate_sha256":csha,"localized_physical_elements":len(specs),"bbox_size_positive_margin":f"{len(specs)}/{len(specs)}","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_out,"overlap":overlap,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B85_BA_REPORT.json"}
(wr/"B85_BA0147DA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
