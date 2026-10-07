#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")
repo=Path.cwd(); run="20261007-A-MANUALQA154-59A79158"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a154"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
EXPECTED_BEFORE="1ea13a96c0f1e670b7455561b747e1bc85871e3e9419d52cd1ee493afd94b583"
GLOBAL_CONDENSE=0.92
MARGIN_X=2
MARGIN_Y=2
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_59A79158_256x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="693548c2c4ec53a4b75adbfe2868328896a115de": raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="bcd439152c3fe1b04b1374609db27244a4d0e9df": raise RuntimeError(("atlas blob drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(1024,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if not candidate.exists() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A154",hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.exists() else None,EXPECTED_BEFORE))
old_payload=candidate.read_bytes()
if old_payload[:128]!=sb[:128]: raise RuntimeError("prior candidate header drift")
old_raw=Image.frombytes("RGBA",(W,H),old_payload[128:],"raw",mode)
old_readable=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# A58 controller source-contact review: atlas rows are reverse of artwork-plan transcription order.
specs=[
(0,"Waterfalls","워터폴스"),(1,"Tulip Garden","튤립 가든"),(2,"Sunny Beach","서니 비치"),(3,"Snow Mountain","스노 마운틴"),
(4,"Skyscrapers","스카이스크레이퍼스"),(5,"Palm Beach","팜 비치"),(6,"National Park","내셔널 파크"),(7,"Milky Way","밀키 웨이"),
(8,"Metropolis","메트로폴리스"),(9,"Lost City","로스트 시티"),(10,"Legend","레전드"),(11,"Jungle","정글"),
(12,"Industrial Complex","인더스트리얼 컴플렉스"),(13,"Imperial Avenue","임페리얼 애비뉴"),(14,"Ice Scape","아이스스케이프"),
(15,"Giant Statues","자이언트 스태추스"),(16,"Ghost Forest","고스트 포레스트"),(17,"Floral Village","플로럴 빌리지"),
(18,"Desert","데저트"),(19,"Deep Lake","딥 레이크"),(20,"Coniferous Forest","코니퍼러스 포레스트"),
(21,"Cloudy Highland","클라우디 하이랜드"),(22,"Casino Town","카지노 타운"),(23,"Castle Wall","캐슬 월")]

source_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); rows=[]
for idx,en,ko in specs:
    x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); lm=bmask(cell.getchannel("A")); bb=lm.getbbox()
    if not bb: raise RuntimeError(("empty source",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_mask.paste(ImageChops.lighter(source_mask.crop((x,y,x+cw,y+ch)),lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    vals=[]; p=cell.load()
    for yy in range(ch):
      for xx in range(cw):
        r,g,b,a=p[xx,yy]
        if a>=96: vals.append((r,g,b,a))
    med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,
                 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"source_mask_pixels":count(lm),"source_median_rgba":med})

clean=src.copy(); ca=clean.getchannel("A"); ca.paste(0,(0,0,W,H),source_mask); clean.putalpha(ca)
sp=out/"A154_SOURCE_READABLE.png"; cp=out/"A154_CLEAN_PLATE.png"; smp=out/"A154_SOURCE_TEXT_MASK.png"; ap=out/"A154_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed)); pp=out/"A154_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"A154_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A154_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)

def render_native(text,fs,fill):
    f=ImageFont.truetype(FONT,fs,index=FI)
    stroke=1
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+6
    a=Image.new("L",(max(8,bb[2]-bb[0]+2*pad),max(8,bb[3]-bb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    ab=a.getbbox()
    if not ab: raise RuntimeError(("empty native render",text,fs))
    a=a.crop(ab)
    rgba=Image.new("RGBA",a.size,(fill[0],fill[1],fill[2],255)); rgba.putalpha(a)
    rgba=rgba.resize((max(1,int(round(rgba.width*GLOBAL_CONDENSE))),rgba.height),Image.Resampling.LANCZOS)
    rb=rgba.getchannel("A").getbbox()
    if rb: rgba=rgba.crop(rb)
    return rgba

shared_fs=None
for fs in range(72,20,-1):
    ok=True
    for r in rows:
        lay=render_native(r["korean"],fs,r["source_median_rgba"])
        if lay.height>r["source_height"]-2*MARGIN_Y:
            ok=False; break
    if ok:
        shared_fs=fs; break
if shared_fs is None: raise RuntimeError("native shared style height fit failed")

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw=r["source_width"]; ah=r["source_height"]; fill=r["source_median_rgba"]
    lay=render_native(r["korean"],shared_fs,fill)
    native_pre_fit=list(lay.size); scale_x=GLOBAL_CONDENSE
    maxw=aw-2*MARGIN_X
    if lay.width>maxw:
        fit=maxw/lay.width; scale_x*=fit
        lay=lay.resize((maxw,lay.height),Image.Resampling.LANCZOS)
        rb=lay.getchannel("A").getbbox()
        if rb: lay=lay.crop(rb)
    px=ob[0]+MARGIN_X; py=ob[1]+(ah-lay.height)//2
    if px+lay.width>=ob[2]: px=ob[2]-MARGIN_X-lay.width
    if py<=ob[1]: py=ob[1]+MARGIN_Y
    if py+lay.height>=ob[3]: py=ob[3]-MARGIN_Y-lay.height
    if not(px>ob[0] and py>ob[1] and px+lay.width<ob[2] and py+lay.height<ob[3]):
        raise RuntimeError(("placement",r["region_idx"],ob,[px,py,px+lay.width,py+lay.height]))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py)); lb=list(lm.getbbox())
    oldbb=old_readable.crop(tuple(ob)).getchannel("A").getbbox()
    oldloc=[ob[0]+oldbb[0],ob[1]+oldbb[1],ob[0]+oldbb[2],ob[1]+oldbb[3]] if oldbb else None
    if not oldloc: raise RuntimeError(("prior bbox missing",r["region_idx"]))
    oldw=oldloc[2]-oldloc[0]; oldh=oldloc[3]-oldloc[1]
    neww=lb[2]-lb[0]; newh=lb[3]-lb[1]
    if newh < oldh-3: raise RuntimeError(("native height regression",r["region_idx"],oldh,newh))
    targets.append((r["region_idx"],lm))
    outrows.append({**r,"localized_bbox":lb,"localized_width":neww,"localized_height":newh,
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","native_font_size":shared_fs,
      "native_direct_render":True,"nearest_neighbor_upscale":False,"native_pre_fit_size":native_pre_fit,
      "horizontal_scale":round(scale_x,4),"alignment":"left_source_bbox_plus_2px_vertical_centered",
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"stroke_width":1,
      "fill_rgba":[fill[0],fill[1],fill[2],255],"prior_localized_bbox":oldloc,
      "prior_localized_width":oldw,"prior_localized_height":oldh,"width_gain_px":neww-oldw,"height_gain_px":newh-oldh})

ov=0; touch=[]
for i in range(len(targets)):
  for j in range(i+1,len(targets)):
    a=targets[i][1]; b=targets[j][1]; x=count(ImageChops.multiply(a,b)); n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
    ov+=x
    if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("overlap/touch",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"A154_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"A154_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A154_FINAL_VALIDATION.json").read_text())
diff=dmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected)); target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),bmask(dec.getchannel("A"))))
render_outside=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or render_outside or ov or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,render_outside,ov,touch))
target.save(out/"A154_TARGET_TEXT_MASK.png")

cards=[]
for r in outrows:
    ob=r["original_bbox"]; cr=(max(0,ob[0]-8),max(0,ob[1]-8),min(W,ob[2]+8),min(H,ob[3]+8))
    ims=[comp(z).crop(cr) for z in (src,old_readable,clean,dec)]; sc=max(1,min(3,1100//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+18,max(z.height for z in ims)+30),"white"); xx=0
    for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]} old={r["prior_localized_width"]} new={r["localized_width"]} sx={r["horizontal_scale"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS); sheet.save(out/"A154_ROW_CONTACTS.jpg",quality=97)

raw_dec=dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rr=Image.new("RGB",(512,2*1048),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((512,1024),Image.Resampling.LANCZOS); rr.paste(z,(0,i*1048+24)); ImageDraw.Draw(rr).text((4,i*1048+4),label,fill="black")
rr.save(out/"A154_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"A","run":run,"index":163,"asset":asset,
 "readiness_tier":"EXISTING_C203_PASS_REOPENED_BY_CURRENT_NATIVE_HD_POLICY",
 "trigger":"PRE_INGAME_018_LOWRES_NEAREST_UPSCALE_AND_SOURCE_WEIGHT_FALSE_NEGATIVE",
 "selection_note":"No active A-owned P0/P1/C-returned REWORK/render-ready item remained after refresh. PRE_INGAME #018 q163 exposes A60 fs9*x4 nearest-neighbor Korean, which is a current-policy low-resolution hard failure.",
 "prior_c_status":"C203_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","prior_candidate_sha256":EXPECTED_BEFORE,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"source_contact":"A58_59A79158_SOURCE_ROWS.jpg","mapping":"atlas idx0..23 = Waterfalls..Castle Wall reverse artwork-plan order","translations":{str(i):{"source":en,"korean":ko} for i,en,ko in specs}},
 "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"family":"shared dark-gray bold condensed stage-list labels","shared_native_font_size":shared_fs,"alignment":"left","fill_median_rgba":[46,54,57,255],"global_horizontal_condense":GLOBAL_CONDENSE,"stroke_width":1,"native_direct_render":True,"nearest_neighbor_upscale":False,"rework":"A60 fs9*x4 nearest-neighbor historical renderer superseded by direct native-resolution antialiased Hangul"},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
   "exact_source_residue":residue,"render_outside_target":render_outside,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":sha(payload),"candidate_path":str(candidate.relative_to(repo)),
 "ordered_generation_gate":{"plate_restoration":"PASS_CANONICAL_SOURCE_ALPHA_CLEAR","slant_direction":"PASS_SOURCE_UPRIGHT_CONDENSED_FAMILY","no_unnecessary_undersizing":"PASS_NATIVE_HEIGHT_MAXIMIZED_WITH_POSITIVE_MARGIN","source_weight_outline_shadow":"REWORKED_NATIVE_BLACK_PLUS_1PX_WEIGHT_PENDING_CONTROLLER","clipping":"PASS_24_OF_24_POSITIVE_MARGIN","protected_clearance":"PASS_ZERO_PROTECTED_CHANGE","flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"A154_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA","no_vr_ffb_dx11_dxvk_work":True}
(out/"A154_59A79158_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A154_59A79158.json").write_text(json.dumps({"run":run,"index":163,"asset":"59A79158","source_sha256":sha(sb),"prior_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":sha(payload),
 "localized_physical_elements":24,"bbox_size_positive_margin":"24/24 PASS","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_outside,
 "overlap":ov,"touch_pairs":len(touch),"native_direct_render":True,"nearest_neighbor_upscale":False,"width_improved_rows":sum(1 for r in outrows if r["width_gain_px"]>0),"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_A/{run}/A154_59A79158_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"asset":"59A79158","candidate_sha256":sha(payload),"shared_native_font_size":shared_fs,"width_improved_rows":sum(1 for r in outrows if r["width_gain_px"]>0),
 "min_width_gain":min(r["width_gain_px"] for r in outrows),"max_horizontal_compression":min(r["horizontal_scale"] for r in outrows),"status":report["status"]},ensure_ascii=False))
