#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-INGAME169-IGR019-MULTIPLAYER-INTRO"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)

assets={
 "97E":{
   "queue_index":193,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
   "current_sha":"cb9cfaab87891c9c7edc047d43fc2e55c512e1bc5c9ccb8fbb5ba9bbb0215418",
   "source_sha":"d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
   "clean":"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_CLEAN_PLATE.png",
   "clean_sha":"a8b16f437f565a70aa5447c51023dc6baf75df36f8da780bc14fd43ac4f07c68",
   "protected":"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_PROTECTED_VISIBLE_MASK.png",
   "protected_sha":"12228745cf607194a590bdf9e2a729b29803702e4c011e499f0ef80ff58aa829",
   "source_text":"localization/graphics/role_A/20261005-A-PRODUCTION70-REWORK/A70_SOURCE_TEXT_MASK.png",
   "source_text_sha":"ee9b7212dd5c3d430bf6fb6eb0060eaa3a92221554999f6ad2ca18974927ad88",
   "target":{"key":"multiplayer_intro_title","source":"MULTIPLAYER","korean":"멀티플레이",
             "bb":[8,297,540,359],"font_style":"Black","font_start":60,
             "fill":[78,96,100,255],"stroke":0,"align":"left","margin":2}
 },
 "8C":{
   "queue_index":188,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "current_sha":"00e16af1e3d468667fe13ed5291ec55bbfd06f18e6895a6be7e79f413ade94bd",
   "source_sha":"dfc72a0d66c30257066d56c2b325dca00832ceeda0d07d46443c27b396e0cb38",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_CLEAN_PLATE.png",
   "clean_sha":"859259fa90a6d70e86f788914c36604b05dfee939f740d215486981fa5ff9b49",
   "protected":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_PROTECTED_VISIBLE_MASK.png",
   "protected_sha":"e7e746011b4aa5eb384e36b062d5d0689172afe30d3a2e0a40cd35696ea12d0b",
   "source_text":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_SOURCE_TEXT_MASK.png",
   "source_text_sha":"6ea5b0c415a8e70c70437040f56b9be41e4f2a549bae11a9bb8081c1b88feadd",
   "target":{"key":"multiplayer_help","source":"Online and LAN OutRun for up to 6 players",
             "korean":"온라인/LAN 아웃런 최대 6인 플레이",
             "bb":[10,1099,1243,1165],"font_style":"Bold","font_start":62,
             "fill":[63,71,74,255],"stroke":0,"align":"left","margin":3}
 }
}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    pf_flags=struct.unpack_from("<I",b,80)[0]; fourcc=b[84:88]
    bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",str(p),w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{
      "width":w,"height":h,"pitch":pitch,"mips":mips,"pf_flags":pf_flags,
      "bpp":bpp,"masks":[hex(x) for x in masks],"raw_mode":mode
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

FONT={"Black":font_path("Black"),"Bold":font_path("Bold")}

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def comp(im,bg=(96,96,96,255)):
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
    if not candidate.exists() or sha(candidate)!=cfg["current_sha"]:
        raise RuntimeError(("candidate drift",tag,sha(candidate) if candidate.exists() else None,cfg["current_sha"]))
    for k in ["clean","protected","source_text"]:
        p=repo/cfg[k]
        expected=cfg[k+"_sha"]
        if not p.exists() or sha(p)!=expected: raise RuntimeError(("evidence drift",tag,k,sha(p) if p.exists() else None,expected))

    source=Path(f"/tmp/b169_{tag}_source.dds")
    urllib.request.urlretrieve(cfg["source_url"],source)
    if sha(source)!=cfg["source_sha"]: raise RuntimeError(("source drift",tag,sha(source),cfg["source_sha"]))

    header,src,meta=load_dds(source)
    oh,old,ometa=load_dds(candidate)
    if header!=oh or meta!=ometa: raise RuntimeError(("structure drift",tag))

    master_clean=Image.open(repo/cfg["clean"]).convert("RGBA")
    protected=np.asarray(Image.open(repo/cfg["protected"]).convert("L"))>0
    source_text=np.asarray(Image.open(repo/cfg["source_text"]).convert("L"))>0
    if master_clean.size!=src.size or protected.shape!=(src.height,src.width) or source_text.shape!=protected.shape:
        raise RuntimeError(("evidence size",tag))

    t=cfg["target"]; x0,y0,x1,y1=t["bb"]; bw=x1-x0; bh=y1-y0
    allowed=np.zeros((src.height,src.width),bool); allowed[y0:y1,x0:x1]=1
    if np.any(protected & allowed): raise RuntimeError(("target intersects protected",tag,int(np.logical_and(protected,allowed).sum())))

    # Reproducible target-only clean plate: exact source everywhere except this exact source bbox.
    clean_target=src.copy()
    clean_target.paste(master_clean.crop((x0,y0,x1,y1)),(x0,y0))
    clean_target.save(out/f"B169_{tag}_TARGET_CLEAN.png")
    Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/f"B169_{tag}_EDIT_MASK.png")
    Image.fromarray((protected*255).astype(np.uint8),"L").save(out/f"B169_{tag}_PROTECTED_MASK.png")
    src_png=Path(f"/tmp/b169_{tag}_source.png"); src.save(src_png)
    subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                    str(src_png),str(out/f"B169_{tag}_TARGET_CLEAN.png"),str(out/f"B169_{tag}_EDIT_MASK.png"),
                    "--protected-mask",str(out/f"B169_{tag}_PROTECTED_MASK.png"),
                    "--report",str(out/f"B169_{tag}_CLEAN_VALIDATION.json")],check=True)

    final=old.copy()
    final.paste(master_clean.crop((x0,y0,x1,y1)),(x0,y0))
    chosen=None
    for fs in range(t["font_start"],15,-1):
        f=ImageFont.truetype(FONT[t["font_style"]],fs)
        probe=Image.new("RGBA",(max(1800,bw+400),max(240,bh+100)),(0,0,0,0))
        d=ImageDraw.Draw(probe)
        tb=d.textbbox((0,0),t["korean"],font=f,stroke_width=t["stroke"])
        d.text((12-tb[0],12-tb[1]),t["korean"],font=f,fill=tuple(t["fill"]),
               stroke_width=t["stroke"],stroke_fill=tuple(t["fill"]))
        gb=probe.getchannel("A").getbbox()
        if not gb: continue
        g=probe.crop(gb)
        m=t["margin"]
        if g.width>bw-2*m or g.height>bh-2*m: continue
        px=x0+m if t["align"]=="left" else x0+(bw-g.width)//2
        py=y0+(bh-g.height)//2
        gm=np.asarray(g.getchannel("A"))>0
        if px<x0+m or py<y0+m or px+g.width>x1-m or py+g.height>y1-m: continue
        if np.any(gm & protected[py:py+g.height,px:px+g.width]): continue
        chosen=(g,px,py,fs); break
    if chosen is None: raise RuntimeError(("fit",tag,t["key"]))

    g,px,py,fs=chosen
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(g,(px,py))
    render=np.asarray(layer.getchannel("A"))>0
    final.alpha_composite(layer)
    lb=bbox_mask(render)
    if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("margin",tag,lb,t["bb"]))
    if lb[2]-lb[0]>bw or lb[3]-lb[1]>bh: raise RuntimeError(("size ceiling",tag,lb,t["bb"]))

    oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8); sa=np.asarray(src,dtype=np.uint8)
    changed=np.any(oa!=fa,axis=2)
    outside=int(np.logical_and(changed,~allowed).sum())
    alpha_out=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
    protected_changed=int(np.logical_and(changed,protected).sum())
    render_protected=int(np.logical_and(render,protected).sum())
    exact_source=np.all(fa==sa,axis=2)
    residue=int(np.logical_and(np.logical_and(source_text,allowed),np.logical_and(exact_source,~render)).sum())
    if outside or alpha_out or protected_changed or render_protected or residue:
        raise RuntimeError(("scope/residue",tag,outside,alpha_out,protected_changed,render_protected,residue))

    new_sha=write_dds(header,final,candidate,meta["raw_mode"])
    dh,decoded,dmeta=load_dds(candidate)
    if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
        raise RuntimeError(("roundtrip",tag))

    tmp=Path(f"/tmp/b169_{tag}"); tmp.mkdir(exist_ok=True)
    old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
    subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                    str(old_png),str(final_png),str(out/f"B169_{tag}_EDIT_MASK.png"),
                    "--protected-mask",str(out/f"B169_{tag}_PROTECTED_MASK.png"),
                    "--report",str(out/f"B169_{tag}_FINAL_SCOPE_VALIDATION.json")],check=True)

    pad=24; crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    cards=[card(t["key"]+"_SOURCE",src,crop,3),card(t["key"]+"_OLD",old,crop,3),
           card(t["key"]+"_CLEAN",clean_target,crop,3),card(t["key"]+"_B169",decoded,crop,3)]
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
    sh=Image.new("RGB",(W,H),"white"); yy=0
    for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
    sh.save(out/f"B169_{tag}_{t['key']}_SOURCE_OLD_CLEAN_FINAL_3X.jpg",quality=97)

    ca=card("OLD",old,(0,0,src.width,src.height)); cb=card("B169_FINAL",decoded,(0,0,src.width,src.height))
    full=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    full.paste(ca,(0,0)); full.paste(cb,(ca.width+8,0)); full.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    full.save(out/f"B169_{tag}_FULL_OLD_FINAL.jpg",quality=94)
    ro=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ca=card("OLD_RAW",ro,(0,0,src.width,src.height)); cb=card("B169_RAW",rf,(0,0,src.width,src.height))
    raw=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    raw.paste(ca,(0,0)); raw.paste(cb,(ca.width+8,0)); raw.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    raw.save(out/f"B169_{tag}_RAW_OLD_FINAL.jpg",quality=94)

    reports[tag]={
      "queue_index":cfg["queue_index"],"asset":cfg["rel"],"source_sha256":cfg["source_sha"],
      "superseded_candidate_sha256":cfg["current_sha"],"candidate_sha256":new_sha,
      "candidate_path":str(candidate.relative_to(repo)),
      "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "row":{"key":t["key"],"source":t["source"],"korean":t["korean"],
             "original_bbox":t["bb"],"localized_bbox":lb,
             "source_size":[bw,bh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
             "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
             "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
             "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
             "font":f"Noto Sans CJK KR {t['font_style']}","font_size":fs,
             "fill_rgba":t["fill"],"alignment":t["align"],
             "native_resolution_render":True,"upscaled_old_korean_reused":False},
      "zero_pixel_qa":{"changed_pixels":int(changed.sum()),"changed_outside_target_bbox":outside,
                       "alpha_changed_outside_target_bbox":alpha_out,
                       "protected_changed_pixels":protected_changed,
                       "render_protected_overlap_pixels":render_protected,
                       "exact_source_residue_pixels":residue,"status":"PASS"}
    }

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "user_ingame_regression":["IGR-019","스크린샷(142).png"],"owner_lane":"B",
 "mapping":{"status":"EXACT_GRAPHICS_MULTI_ASSET_NO_RUNTIME_TEXT","domain":"GRAPHICS",
   "visible_bindings":[
      {"screen":"WELCOME TO THE / MULTIPLAYER intro body","asset":"97E863AD","queue_index":193,
       "source":"MULTIPLAYER","action":"REWORKED_NATIVE","preserved":"A89R WELCOME TO THE native row"},
      {"screen":"multiplayer intro help copy","asset":"8C259C68","queue_index":188,
       "source":"Online and LAN OutRun for up to 6 players","action":"REWORKED_NATIVE",
       "preserved":"A88 C2C help + B166 Heart Attack help + all unrelated rows"}
   ],
   "runtime_text_required":False,
   "excluded_completed_asset":{"asset":"4D38BBB0","queue_index":154,
      "reason":"B60/C141 already renders both MULTIPLAYER physical rows natively at 4096x1024 with source-family red/gray styles; screenshot-confirmed low-resolution defect is explained by still-upscaled 97E/8C rows and completed 4D38 is not repeated."},
   "note":"IGR-019 belongs to the same front-end intro/help family as IGR-001/002. Current metadata proves the screenshot-visible 97E MULTIPLAYER row remained A70 12px->4x and the 8C Online/LAN help row remained B82 12px->4x, while A89R only fixed 97E WELCOME/SHOWROOM and A88/B166 fixed different 8C rows."
 },
 "assets":reports,
 "method":"User in-game LOW_RES_FONT override: replace only the two proven legacy 4x-upscaled Korean rows with direct canonical-HD Noto CJK rendering from validated clean plates; preserve all newer native intro-family fixes and protected artwork byte-for-pixel outside the exact source bboxes.",
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"B169_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B169_IGR019_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(out/"B169_STATIC_VALIDATION_SUMMARY.json").write_text(json.dumps({
 "assets":{k:{"queue_index":v["queue_index"],"candidate_sha256":v["candidate_sha256"],
              "bbox_size_positive_margin":"1/1 PASS",**v["zero_pixel_qa"]} for k,v in reports.items()},
 "status":"PASS"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B169_DONE",json.dumps({k:v["candidate_sha256"] for k,v in reports.items()}))
