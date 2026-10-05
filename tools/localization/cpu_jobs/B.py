#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-INGAME166-IGR002-INTRO"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)

assets={
 "BA":{
   "queue_index":212,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",
   "old_sha":"869cf1bea8b27dcc89f5b2ab68f9dd163e4bf41fa6de4b53c7b3f19b3b1c74ad",
   "source_sha":"f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png",
   "clean_sha":"c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67",
   "protected":"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png",
   "protected_sha":"1f72955d86631ae0b380d0145966fb5bdd824b804ae4247f9f615f535f3bf532",
   "targets":[
      {"key":"heart_attack_title","source":"HEART ATTACK","korean":"하트 어택",
       "bb":[21,1316,1780,1474],"font_style":"Black","font_start":158,
       "fill":[186,0,0,255],"stroke":0,"slant":0.0,"align":"left"}
   ]
 },
 "8C":{
   "queue_index":188,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "old_sha":"03f52892acd091496c53c19a0a48c2f9c2d1acf9b05d9f96801ff4032e756b03",
   "source_sha":"dfc72a0d66c30257066d56c2b325dca00832ceeda0d07d46443c27b396e0cb38",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_CLEAN_PLATE.png",
   "clean_sha":"859259fa90a6d70e86f788914c36604b05dfee939f740d215486981fa5ff9b49",
   "protected":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_PROTECTED_VISIBLE_MASK.png",
   "protected_sha":"e7e746011b4aa5eb384e36b062d5d0689172afe30d3a2e0a40cd35696ea12d0b",
   "targets":[
      {"key":"heart_attack_help","source":"Try to win Hearts by meeting your girlfriend's demands!",
       "korean":"여자친구의 요구를 들어주고 하트를 획득하세요!",
       "bb":[0,1417,1623,1488],"font_style":"Bold","font_start":68,
       "fill":[63,71,74,255],"stroke":0,"slant":0.0,"align":"left"}
   ]
 }
}

d657_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds"
d657_sha="6f5c0c5d2ec4998c29f49b5c9de24c08e0e0bfe016f6eae1c4304464048185a5"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",p))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    pf_flags=struct.unpack_from("<I",b,80)[0]; fourcc=b[84:88]
    bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",p,w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000):
        mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000):
        mode="BGRA"
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
    pat=f"Noto Sans CJK KR:style={style}"
    q=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",style,q))
    return q

FONT={"Black":font_path("Black"),"Bold":font_path("Bold")}

def shear(im,s):
    if not s: return im
    add=int(np.ceil(abs(s)*(im.height-1)))+2
    z=im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                   (1,-s,s*(im.height-1),0,1,0),resample=Image.Resampling.BICUBIC)
    bb=z.getchannel("A").getbbox()
    return z.crop(bb) if bb else z

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
    clean_path=repo/cfg["clean"]; protected_path=repo/cfg["protected"]
    if not candidate.exists() or sha(candidate)!=cfg["old_sha"]: raise RuntimeError(("candidate drift",tag,sha(candidate) if candidate.exists() else None))
    if sha(clean_path)!=cfg["clean_sha"] or sha(protected_path)!=cfg["protected_sha"]: raise RuntimeError(("evidence drift",tag))
    source=Path(f"/tmp/{tag}_source.dds"); urllib.request.urlretrieve(cfg["source_url"],source)
    if sha(source)!=cfg["source_sha"]: raise RuntimeError(("source drift",tag,sha(source)))

    header,src,meta=load_dds(source)
    oh,old,ometa=load_dds(candidate)
    if header!=oh or meta!=ometa: raise RuntimeError(("structure drift",tag))
    clean=Image.open(clean_path).convert("RGBA")
    protected=np.asarray(Image.open(protected_path).convert("L"))>0
    if clean.size!=src.size or protected.shape!=(src.height,src.width): raise RuntimeError(("evidence size",tag))

    final=old.copy()
    allowed=np.zeros((src.height,src.width),bool)
    render_union=np.zeros_like(allowed)
    rows=[]
    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; bw=x1-x0; bh=y1-y0
        allowed[y0:y1,x0:x1]=1
        final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
        chosen=None
        for fs in range(t["font_start"],15,-1):
            f=ImageFont.truetype(FONT[t["font_style"]],fs)
            probe=Image.new("RGBA",(max(2200,bw+300),max(300,bh+100)),(0,0,0,0))
            d=ImageDraw.Draw(probe)
            tb=d.textbbox((0,0),t["korean"],font=f,stroke_width=t["stroke"])
            pos=(12-tb[0],12-tb[1])
            d.text(pos,t["korean"],font=f,fill=tuple(t["fill"]),
                   stroke_width=t["stroke"],stroke_fill=tuple(t["fill"]))
            g=shear(probe,t["slant"])
            gb=g.getchannel("A").getbbox()
            if not gb: continue
            g=g.crop(gb)
            if g.width>bw-8 or g.height>bh-8: continue
            px=x0+4 if t["align"]=="left" else x0+(bw-g.width)//2
            py=y0+(bh-g.height)//2
            gm=np.asarray(g.getchannel("A"))>0
            if px+g.width>x1-4 or py<y0+4 or py+g.height>y1-4: continue
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
          "font":f"Noto Sans CJK KR {t['font_style']}","font_size":fs,
          "fill_rgba":t["fill"],"slant":t["slant"],"alignment":t["align"]
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
    if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
        raise RuntimeError(("roundtrip",tag))

    # Evidence masks and generic validator.
    Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/f"B166_{tag}_EDIT_MASK.png")
    Image.fromarray((protected*255).astype(np.uint8),"L").save(out/f"B166_{tag}_PROTECTED_MASK.png")
    tmp=Path(f"/tmp/b166_{tag}"); tmp.mkdir(exist_ok=True)
    old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
    subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                    str(old_png),str(final_png),str(out/f"B166_{tag}_EDIT_MASK.png"),
                    "--protected-mask",str(out/f"B166_{tag}_PROTECTED_MASK.png"),
                    "--report",str(out/f"B166_{tag}_FINAL_MASK_VALIDATION.json")],check=True)

    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; pad=24
        crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        cards=[card(t["key"]+"_SOURCE",src,crop,2),card(t["key"]+"_OLD",old,crop,2),
               card(t["key"]+"_CLEAN",clean,crop,2),card(t["key"]+"_B166",decoded,crop,2)]
        W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
        sh=Image.new("RGB",(W,H),"white"); yy=0
        for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
        sh.save(out/f"B166_{tag}_{t['key']}_SOURCE_OLD_CLEAN_FINAL_2X.jpg",quality=97)

    ca=card("OLD",old,(0,0,src.width,src.height)); cb=card("B166_FINAL",decoded,(0,0,src.width,src.height))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0)); sh.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    sh.save(out/f"B166_{tag}_FULL_OLD_FINAL.jpg",quality=94)
    raw_old=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM); raw_final=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ca=card("OLD_RAW",raw_old,(0,0,src.width,src.height)); cb=card("B166_RAW",raw_final,(0,0,src.width,src.height))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0)); sh.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    sh.save(out/f"B166_{tag}_RAW_OLD_FINAL.jpg",quality=94)

    reports[tag]={
      "queue_index":cfg["queue_index"],"asset":cfg["rel"],"source_sha256":cfg["source_sha"],
      "superseded_candidate_sha256":cfg["old_sha"],"candidate_sha256":new_sha,
      "candidate_path":str(candidate.relative_to(repo)),"structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "rows":rows,
      "scope_qa":{"changed_pixels":int(changed.sum()),"changed_outside_target_bboxes":outside,
                  "alpha_changed_outside_target_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
                  "render_protected_overlap_pixels":render_protected,"status":"PASS"}
    }

# D657 is part of exact screen mapping but intentionally unchanged because its gray selector hierarchy already
# consumes nearly the full source height and matches the source-selected/unselected family.
d657=repo/"localization/graphics/hd_candidates"/d657_rel
if not d657.exists() or sha(d657)!=d657_sha: raise RuntimeError(("D657 drift",sha(d657) if d657.exists() else None))

report={
 "schema_version":1,"role":"B","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "user_ingame_regression":["IGR-002","스크린샷(144).png"],"owner_lane":"B",
 "mapping":{"status":"EXACT_HIGH_CONFIDENCE_MULTI_ASSET","domain":"GRAPHICS",
   "visible_bindings":[
      {"screen":"large red 하트 어택 title","asset":"BA0147DA","queue_index":212,"source":"HEART ATTACK","action":"REWORKED"},
      {"screen":"gray 하트 어택 / 타임 어택 tabs","asset":"D657C2EB","queue_index":220,"source":"HEART ATTACK / TIME ATTACK","action":"PRESERVED_SOURCE_HIERARCHY"},
      {"screen":"쇼룸 tab/state","asset":"BA0147DA","queue_index":212,"source":"SHOWROOM","action":"PRESERVED_EXISTING"},
      {"screen":"여자친구의 요구... help line","asset":"8C259C68","queue_index":188,"source":"Try to win Hearts by meeting your girlfriend's demands!","action":"REWORKED"}
   ],
   "runtime_text_search":"No localization runtime source is required for these screenshot-visible labels; all mapped elements are baked graphics assets.",
   "note":"IGR-002 is the Heart Attack intro member of the same front-end family as IGR-001/019, but this B run modifies only screenshot(144)-visible B-owned mapped rows."
 },
 "assets":reports,
 "preserved_asset":{"queue_index":220,"asset":d657_rel,"candidate_sha256":d657_sha,
   "reason":"gray selector rows already fill source-height hierarchy with exact static PASS; user defect is addressed in title/help copy without flattening intentional selected/unselected tab hierarchy"},
 "method":"User screenshot override of earlier static PASS: exact multi-asset mapping, native-resolution rerender only of the large Heart Attack title and Heart Attack help copy from already-validated clean plates. Increase title/help source-relative height/weight while preserving exact source bboxes, fills, alignment, protected artwork, and raw orientation.",
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"B166_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B166_IGR002_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(out/"B166_STATIC_VALIDATION_SUMMARY.json").write_text(json.dumps({
 "mapping":"IGR-002_EXACT_GRAPHICS_MULTI_ASSET","assets":{k:{
   "queue_index":v["queue_index"],"candidate_sha256":v["candidate_sha256"],
   "bbox_size_positive_margin":f"{len(v['rows'])}/{len(v['rows'])} PASS",
   **v["scope_qa"]} for k,v in reports.items()},
 "preserved_D657_sha256":d657_sha,"status":"PASS"
},ensure_ascii=False,indent=2)+"\n")
print("B166_DONE",json.dumps({k:v["candidate_sha256"] for k,v in reports.items()}))
