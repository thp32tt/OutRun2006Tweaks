#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-INGAME89-IGR003-SHOWROOM"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

assets={
 "97E":{
   "queue_index":193,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
   "old_sha":"b17c26ad47611de67365449d2fed5cd4d17114cb3d4eb3fcd8cd373afacf8d1d",
   "source_sha":"d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
   "clean":"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_CLEAN_PLATE.png",
   "protected":"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_PROTECTED_VISIBLE_MASK.png",
   "targets":[
      {"key":"welcome","source":"WELCOME TO THE","korean":"환영합니다",
       "bb":[3,148,476,195],"font_style":"Black","font_start":56,
       "fill":[46,53,57,255],"stroke":0,"align":"left","margin":2},
      {"key":"showroom_body","source":"SHOWROOM (OUTRUN line preserved)","korean":"쇼룸",
       "bb":[1205,957,1594,1011],"font_style":"Black","font_start":62,
       "fill":[46,53,57,255],"stroke":0,"align":"left","margin":2}
   ]
 },
 "A9":{
   "queue_index":201,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds",
   "old_sha":"59b21fa3aadf86e892dbd6adee4b178b2dad09048fd314fd731135f363d6a6fe",
   "source_sha":"6ac5ffd02c9162499f09f0b476176b56f0b144789f546ef34147d94e0a8451e5",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds",
   "clean":"localization/graphics/role_A/20261005-A-PRODUCTION69/A69_CLEAN_PLATE.png",
   "protected":"localization/graphics/role_A/20261005-A-PRODUCTION69/A69_PROTECTED_VISIBLE_MASK.png",
   "targets":[
      {"key":"stages","source":"STAGES","korean":"스테이지",
       "bb":[1173,1986,1379,2037],"font_style":"Black","font_start":58,
       "fill":[46,54,57,255],"stroke":0,"align":"left","margin":2},
      {"key":"goals","source":"GOALS","korean":"골",
       "bb":[1079,1734,1255,1785],"font_style":"Black","font_start":58,
       "fill":[46,54,57,255],"stroke":0,"align":"left","margin":2}
   ]
 }
}
preserved={
 "754F0599":{"queue_index":175,"sha":"884f333b7217fd975aec1c1fc81c98bfd4287e52dc60255eb6b06803430b2250",
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds","role":"metallic top SHOWROOM header"},
 "E95DA5":{"queue_index":230,"sha":"d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b",
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds","role":"native Ferrari Cars / BGM / Car Colors showroom menu rows"}
}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",p))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",p,w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{
       "width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,
       "masks":[hex(x) for x in masks],"raw_mode":mode
    }

def write_dds(header,readable,p,mode):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def font_path(style):
    q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",style,q))
    return q
FONT={"Black":font_path("Black")}

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

def card(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((5,5),label,fill="black")
    return c

reports={}
for tag,cfg in assets.items():
    candidate=repo/"localization/graphics/hd_candidates"/cfg["rel"]
    if not candidate.exists() or sha(candidate)!=cfg["old_sha"]:
        raise RuntimeError(("candidate drift",tag,sha(candidate) if candidate.exists() else None))
    source=Path(f"/tmp/a89_{tag}_source.dds"); urllib.request.urlretrieve(cfg["source_url"],source)
    if sha(source)!=cfg["source_sha"]: raise RuntimeError(("source drift",tag,sha(source)))

    header,src,meta=load_dds(source); oh,old,ometa=load_dds(candidate)
    if header!=oh or meta!=ometa: raise RuntimeError(("structure drift",tag))
    clean=Image.open(repo/cfg["clean"]).convert("RGBA")
    protected=np.asarray(Image.open(repo/cfg["protected"]).convert("L"))>0
    if clean.size!=src.size or protected.shape!=(src.height,src.width): raise RuntimeError(("evidence size",tag))

    final=old.copy(); allowed=np.zeros((src.height,src.width),bool); render_union=np.zeros_like(allowed); rows=[]
    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; bw=x1-x0; bh=y1-y0; margin=t["margin"]
        allowed[y0:y1,x0:x1]=1
        final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
        chosen=None
        for fs in range(t["font_start"],15,-1):
            f=ImageFont.truetype(FONT[t["font_style"]],fs)
            probe=Image.new("RGBA",(max(1200,bw+300),max(180,bh+80)),(0,0,0,0))
            d=ImageDraw.Draw(probe)
            tb=d.textbbox((0,0),t["korean"],font=f,stroke_width=t["stroke"])
            d.text((12-tb[0],12-tb[1]),t["korean"],font=f,fill=tuple(t["fill"]),
                   stroke_width=t["stroke"],stroke_fill=tuple(t["fill"]))
            gb=probe.getchannel("A").getbbox()
            if not gb: continue
            g=probe.crop(gb)
            if g.width>bw-margin*2 or g.height>bh-margin*2: continue
            px=x0+margin if t["align"]=="left" else x0+(bw-g.width)//2
            py=y0+(bh-g.height)//2
            gm=np.asarray(g.getchannel("A"))>0
            if px+g.width>x1-margin or py<y0+margin or py+g.height>y1-margin: continue
            if np.any(gm & protected[py:py+g.height,px:px+g.width]): continue
            chosen=(g,px,py,fs); break
        if chosen is None: raise RuntimeError(("fit",tag,t["key"]))
        g,px,py,fs=chosen
        layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py))
        final.alpha_composite(layer)
        gm=np.asarray(layer.getchannel("A"))>0; render_union|=gm
        lb=bbox_mask(gm)
        if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("margin",tag,t["key"],lb))
        rows.append({
          "key":t["key"],"source":t["source"],"korean":t["korean"],
          "original_bbox":t["bb"],"localized_bbox":lb,
          "source_size":[bw,bh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
          "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
          "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
          "font":"Noto Sans CJK KR Black","font_size":fs,"fill_rgba":t["fill"],
          "alignment":"left","native_resolution_render":True,"upscaled_old_korean_reused":False
        })

    oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
    changed=np.any(oa!=fa,axis=2)
    outside=int(np.logical_and(changed,~allowed).sum())
    alpha_out=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
    protected_changed=int(np.logical_and(changed,protected).sum())
    render_protected=int(np.logical_and(render_union,protected).sum())
    if outside or alpha_out or protected_changed or render_protected:
        raise RuntimeError(("scope",tag,outside,alpha_out,protected_changed,render_protected))

    new_sha=write_dds(header,final,candidate,meta["raw_mode"])
    dh,decoded,dmeta=load_dds(candidate)
    if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox(): raise RuntimeError(("roundtrip",tag))

    Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/f"A89_{tag}_EDIT_MASK.png")
    Image.fromarray((protected*255).astype(np.uint8),"L").save(out/f"A89_{tag}_PROTECTED_MASK.png")
    tmp=Path(f"/tmp/a89_{tag}"); tmp.mkdir(exist_ok=True)
    old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
    subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                    str(old_png),str(final_png),str(out/f"A89_{tag}_EDIT_MASK.png"),
                    "--protected-mask",str(out/f"A89_{tag}_PROTECTED_MASK.png"),
                    "--report",str(out/f"A89_{tag}_FINAL_MASK_VALIDATION.json")],check=True)

    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; pad=20
        crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        cards=[card(t["key"]+"_SOURCE",src,crop,3),card(t["key"]+"_OLD",old,crop,3),
               card(t["key"]+"_CLEAN",clean,crop,3),card(t["key"]+"_A89",decoded,crop,3)]
        W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
        sh=Image.new("RGB",(W,H),"white"); yy=0
        for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
        sh.save(out/f"A89_{tag}_{t['key']}_SOURCE_OLD_CLEAN_FINAL_3X.jpg",quality=97)

    ca=card("OLD",old,(0,0,src.width,src.height)); cb=card("A89_FINAL",decoded,(0,0,src.width,src.height))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0)); sh.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    sh.save(out/f"A89_{tag}_FULL_OLD_FINAL.jpg",quality=94)
    raw_old=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM); raw_final=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ca=card("OLD_RAW",raw_old,(0,0,src.width,src.height)); cb=card("A89_RAW",raw_final,(0,0,src.width,src.height))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0)); sh.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    sh.save(out/f"A89_{tag}_RAW_OLD_FINAL.jpg",quality=94)

    reports[tag]={
      "queue_index":cfg["queue_index"],"asset":cfg["rel"],"source_sha256":cfg["source_sha"],
      "superseded_candidate_sha256":cfg["old_sha"],"candidate_sha256":new_sha,
      "candidate_path":str(candidate.relative_to(repo)),"structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "rows":rows,
      "scope_qa":{"changed_pixels":int(changed.sum()),"changed_outside_target_bboxes":outside,
                  "alpha_changed_outside_target_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
                  "render_protected_overlap_pixels":render_protected,"status":"PASS"}
    }

for key,p in preserved.items():
    f=repo/"localization/graphics/hd_candidates"/p["rel"]
    if not f.exists() or sha(f)!=p["sha"]: raise RuntimeError(("preserved drift",key,sha(f) if f.exists() else None))

report={
 "schema_version":1,"role":"A","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "user_ingame_regression":["IGR-003","스크린샷(145).png"],"owner_lane":"A",
 "mapping":{
   "status":"EXACT_GRAPHICS_MULTI_ASSET_NO_RUNTIME_TEXT","domain":"GRAPHICS",
   "visible_bindings":[
     {"asset":"754F0599","queue_index":175,"screen":"metallic top SHOWROOM header","action":"PRESERVED_C171_NATIVE"},
     {"asset":"97E863AD","queue_index":193,"screen":"WELCOME TO THE / OUTRUN SHOWROOM body","action":"REWORKED_NATIVE_VISIBLE_ROWS"},
     {"asset":"A9ABD877","queue_index":201,"screen":"STAGES / GOALS main-list rows","action":"REWORKED_NATIVE_VISIBLE_ROWS"},
     {"asset":"E95DA5","queue_index":230,"screen":"FERRARI CARS / BGM / CAR COLORS main-list rows","action":"PRESERVED_C149_NATIVE"}
   ],
   "runtime_text_required":False,
   "note":"Actual screenshot(145) shows one menu composed from four baked graphics families. User-visible mixed-resolution defect is isolated to legacy lowres*4 rows in 97E/A9; E95 and 754F visible rows are already native source-style and are preserved."
 },
 "assets":reports,"preserved_assets":preserved,
 "method":"Re-render only screenshot-visible legacy lowres*4 Korean rows directly at canonical HD resolution with Noto Sans CJK KR Black, exact source median fill and left alignment. Preserve already-native C149/C171 rows and all unrelated atlas content.",
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A89_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A89_IGR003_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A89_IGR003.json").write_text(json.dumps({
 "run":run,"regression":"IGR-003","mapping":"EXACT_GRAPHICS_MULTI_ASSET_NO_RUNTIME_TEXT",
 "assets":{k:{"queue_index":v["queue_index"],"candidate_sha256":v["candidate_sha256"],
 "bbox_size_positive_margin":f"{len(v['rows'])}/{len(v['rows'])} PASS",**v["scope_qa"]} for k,v in reports.items()},
 "preserved":{"754F0599":preserved["754F0599"]["sha"],"E95DA5":preserved["E95DA5"]["sha"]},
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "worker_status":report["status"],"report":str((out/"A89_IGR003_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n")
print("A89_DONE",json.dumps({k:v["candidate_sha256"] for k,v in reports.items()}))
