#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-INGAME88-IGR001-C2C"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

assets={
 "BA":{
   "queue_index":212,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",
   "old_sha":"f5838261bd2015ade657d51f45175f1ef1c0351252c6505dc5eaf985be54d5a1",
   "source_sha":"f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png",
   "protected":"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png",
   "targets":[
      {"key":"coast2coast_title","source":"COAST 2 COAST","korean":"코스트 2 코스트",
       "bb":[0,964,1760,1124],"font_style":"Black","font_start":160,
       "fill":[186,0,0,255],"stroke":0,"slant":0.0,"align":"left","margin":4}
   ]
 },
 "8C":{
   "queue_index":188,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "old_sha":"8da8dbf1d5f577605e2268841667fdd64636f4358f27e17103587ee032c2575c",
   "source_sha":"dfc72a0d66c30257066d56c2b325dca00832ceeda0d07d46443c27b396e0cb38",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/8C259C68_512x512.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_CLEAN_PLATE.png",
   "protected":"localization/graphics/role_B/20261005-B-PRODUCTION81/8C_PROTECTED_VISIBLE_MASK.png",
   "targets":[
      {"key":"coast2coast_help","source":"Complete Race and Heart Attack missions to win OR Miles!",
       "korean":"레이스와 하트 어택 미션을 완료해 OR 마일을 획득하세요!",
       "bb":[6,1259,1727,1325],"font_style":"Bold","font_start":64,
       "fill":[63,71,74,255],"stroke":0,"slant":0.0,"align":"left","margin":3}
   ]
 },
 "D657":{
   "queue_index":220,
   "rel":"textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds",
   "old_sha":"6f5c0c5d2ec4998c29f49b5c9de24c08e0e0bfe016f6eae1c4304464048185a5",
   "source_sha":"439a09cdcaaf000802ce104ebb9e00b22df28e1f4657ff94021b4f92707c6ccc",
   "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds",
   "clean":"localization/graphics/role_B/20261005-B-PRODUCTION65/D657_CLEAN_PLATE.png",
   "protected":None,
   "targets":[
      {"key":"coast2coast_selector","source":"COAST 2 COAST","korean":"코스트 2 코스트",
       "bb":[20,266,626,330],"font_style":"Bold","font_start":64,
       "fill":[78,96,100,255],"stroke":2,"slant":0.0,"align":"left","margin":2}
   ]
 }
}
header_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
header_sha="884f333b7217fd975aec1c1fc81c98bfd4287e52dc60255eb6b06803430b2250"

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
    clean_path=repo/cfg["clean"]
    if not candidate.exists() or sha(candidate)!=cfg["old_sha"]:
        raise RuntimeError(("candidate drift",tag,sha(candidate) if candidate.exists() else None))
    source=Path(f"/tmp/a88_{tag}_source.dds"); urllib.request.urlretrieve(cfg["source_url"],source)
    if sha(source)!=cfg["source_sha"]: raise RuntimeError(("source drift",tag,sha(source)))

    header,src,meta=load_dds(source)
    oh,old,ometa=load_dds(candidate)
    if header!=oh or meta!=ometa: raise RuntimeError(("structure drift",tag))
    clean=Image.open(clean_path).convert("RGBA")
    if clean.size!=src.size: raise RuntimeError(("clean size",tag,clean.size,src.size))
    if cfg["protected"]:
        protected=np.asarray(Image.open(repo/cfg["protected"]).convert("L"))>0
        if protected.shape!=(src.height,src.width): raise RuntimeError(("protected size",tag))
    else:
        protected=np.zeros((src.height,src.width),bool)

    final=old.copy()
    allowed=np.zeros((src.height,src.width),bool)
    render_union=np.zeros_like(allowed)
    rows=[]
    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; bw=x1-x0; bh=y1-y0; margin=t["margin"]
        allowed[y0:y1,x0:x1]=1
        final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
        chosen=None
        for fs in range(t["font_start"],15,-1):
            f=ImageFont.truetype(FONT[t["font_style"]],fs)
            probe=Image.new("RGBA",(max(2400,bw+400),max(320,bh+120)),(0,0,0,0))
            d=ImageDraw.Draw(probe)
            tb=d.textbbox((0,0),t["korean"],font=f,stroke_width=t["stroke"])
            pos=(16-tb[0],16-tb[1])
            d.text(pos,t["korean"],font=f,fill=tuple(t["fill"]),
                   stroke_width=t["stroke"],stroke_fill=tuple(t["fill"]))
            g=shear(probe,t["slant"])
            gb=g.getchannel("A").getbbox()
            if not gb: continue
            g=g.crop(gb)
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
        if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1):
            raise RuntimeError(("margin",tag,t["key"],lb,t["bb"]))
        rows.append({
          "key":t["key"],"source":t["source"],"korean":t["korean"],
          "original_bbox":t["bb"],"localized_bbox":lb,
          "source_size":[bw,bh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
          "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
          "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
          "font":f"Noto Sans CJK KR {t['font_style']}","font_size":fs,
          "fill_rgba":t["fill"],"stroke":t["stroke"],"slant":t["slant"],"alignment":t["align"],
          "native_resolution_render":True,"upscaled_old_korean_reused":False
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

    Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/f"A88_{tag}_EDIT_MASK.png")
    Image.fromarray((protected*255).astype(np.uint8),"L").save(out/f"A88_{tag}_PROTECTED_MASK.png")
    tmp=Path(f"/tmp/a88_{tag}"); tmp.mkdir(exist_ok=True)
    old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
    subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                    str(old_png),str(final_png),str(out/f"A88_{tag}_EDIT_MASK.png"),
                    "--protected-mask",str(out/f"A88_{tag}_PROTECTED_MASK.png"),
                    "--report",str(out/f"A88_{tag}_FINAL_MASK_VALIDATION.json")],check=True)

    for t in cfg["targets"]:
        x0,y0,x1,y1=t["bb"]; pad=28
        crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        cards=[card(t["key"]+"_SOURCE",src,crop,2),card(t["key"]+"_OLD",old,crop,2),
               card(t["key"]+"_CLEAN",clean,crop,2),card(t["key"]+"_A88",decoded,crop,2)]
        W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
        sh=Image.new("RGB",(W,H),"white"); yy=0
        for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
        sh.save(out/f"A88_{tag}_{t['key']}_SOURCE_OLD_CLEAN_FINAL_2X.jpg",quality=97)

    ca=card("OLD",old,(0,0,src.width,src.height)); cb=card("A88_FINAL",decoded,(0,0,src.width,src.height))
    sh=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    sh.paste(ca,(0,0)); sh.paste(cb,(ca.width+8,0)); sh.thumbnail((2200,1200),Image.Resampling.LANCZOS)
    sh.save(out/f"A88_{tag}_FULL_OLD_FINAL.jpg",quality=94)

    reports[tag]={
      "queue_index":cfg["queue_index"],"asset":cfg["rel"],"source_sha256":cfg["source_sha"],
      "superseded_candidate_sha256":cfg["old_sha"],"candidate_sha256":new_sha,
      "candidate_path":str(candidate.relative_to(repo)),"structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "rows":rows,
      "scope_qa":{"changed_pixels":int(changed.sum()),"changed_outside_target_bboxes":outside,
                  "alpha_changed_outside_target_bboxes":alpha_out,"protected_changed_pixels":protected_changed,
                  "render_protected_overlap_pixels":render_protected,"status":"PASS"}
    }

header=repo/"localization/graphics/hd_candidates"/header_rel
if not header.exists() or sha(header)!=header_sha:
    raise RuntimeError(("754F header candidate drift",sha(header) if header.exists() else None))

report={
 "schema_version":1,"role":"A","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "user_ingame_regression":["IGR-001","스크린샷(143).png"],"owner_lane":"A",
 "mapping":{
   "status":"EXACT_GRAPHICS_MULTI_ASSET_NO_RUNTIME_TEXT","domain":"GRAPHICS",
   "visible_bindings":[
      {"screen":"large red 코스트 2 코스트 title","asset":"BA0147DA","queue_index":212,"source":"COAST 2 COAST","action":"REWORKED_NATIVE"},
      {"screen":"레이스와 하트 어택... help line","asset":"8C259C68","queue_index":188,"source":"Complete Race and Heart Attack missions to win OR Miles!","action":"REWORKED_NATIVE"},
      {"screen":"bottom 코스트 2 코스트 selector","asset":"D657C2EB","queue_index":220,"source":"COAST 2 COAST","action":"REWORKED_NATIVE"},
      {"screen":"top 싱글 플레이 mode header","asset":"754F0599","queue_index":175,"source":"single player","action":"PRESERVED_C171_NATIVE_SOURCE_STYLE"}
   ],
   "runtime_text_required":False,
   "note":"IGR-001 exact mapping resolved entirely to baked graphics. The three backlog-named title/subtitle/bottom-selector defects were materially re-rendered; the shared top SINGLE PLAYER header is independently mapped to 754F0599 and preserved because C171 already established native-HD source-style geometry."
 },
 "assets":reports,
 "preserved_header":{"queue_index":175,"asset":header_rel,"candidate_sha256":header_sha,
   "reason":"C171 pixel/visual PASS already uses native-HD metallic source-family geometry for single player; do not repeat completed bytes without a row-specific new failure."},
 "method":"Newer user in-game evidence overrides prior static PASS for the IGR-001-specific C2C rows. Re-render only those exact source bboxes directly at canonical HD resolution; preserve B166 Heart Attack corrections and all unrelated rows byte-for-pixel.",
 "visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A88_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"A88_IGR001_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A88_IGR001.json").write_text(json.dumps({
 "run":run,"regression":"IGR-001","mapping":"EXACT_GRAPHICS_MULTI_ASSET_NO_RUNTIME_TEXT",
 "assets":{k:{"queue_index":v["queue_index"],"candidate_sha256":v["candidate_sha256"],
 "bbox_size_positive_margin":f"{len(v['rows'])}/{len(v['rows'])} PASS",**v["scope_qa"]} for k,v in reports.items()},
 "preserved_754F_sha256":header_sha,"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "worker_status":report["status"],"report":str((out/"A88_IGR001_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n")
print("A88_DONE",json.dumps({k:v["candidate_sha256"] for k,v in reports.items()}))
