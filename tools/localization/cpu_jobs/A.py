#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-DXT5-STRICT-PREFLIGHT117"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

assets=[
  {
    "index":99,
    "id":"4F68708E",
    "path":"textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",
    "url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",
    "sha256":"d97206d8ab5e0898c81d9cc0d6562db1a381894b0fa3e2d9fa75303867a638e2",
    "bboxes":[[537,41,1350,126],[517,126,1610,213]],
    "source":"Drive against the Ghost Car and challenge for the course record!!",
    "korean":"고스트 카와 달리며 코스 기록에 도전하세요!"
  },
  {
    "index":119,
    "id":"F6811E94",
    "path":"textures/load/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds",
    "url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds",
    "sha256":"2336da3c2d08d1bfb99e3a8612a3fe7d39f9c852d7da433204c8d4a19b49c552",
    "bboxes":[[390,54,1632,200]],
    "source":"Time Attack Mode",
    "korean":"타임 어택 모드"
  }
]

def alpha_palette(a0,a1):
    if a0>a1:
        return [a0,a1,
            (6*a0+1*a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,
            (3*a0+4*a1)//7,(2*a0+5*a1)//7,(1*a0+6*a1)//7]
    return [a0,a1,
        (4*a0+1*a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,
        (1*a0+4*a1)//5,0,255]

def rgb565(v):
    r=((v>>11)&31)*255//31
    g=((v>>5)&63)*255//63
    b=(v&31)*255//31
    return [r,g,b]

def color_palette(c0,c1):
    p0=rgb565(c0); p1=rgb565(c1)
    return [p0,p1,
        [(2*p0[i]+p1[i])//3 for i in range(3)],
        [(p0[i]+2*p1[i])//3 for i in range(3)]]

def block_info(raw,w,h,bx,by):
    blocks_x=(w+3)//4
    off=128+(by*blocks_x+bx)*16
    b=raw[off:off+16]
    a0,a1=b[0],b[1]
    ap=alpha_palette(a0,a1)
    c0,c1=struct.unpack_from("<HH",b,8)
    cp=color_palette(c0,c1)
    return {"offset":off,"a0":a0,"a1":a1,"alpha_palette":ap,
            "color0_565":c0,"color1_565":c1,"color_palette":cp}

reports=[]
for spec in assets:
    tmp=Path("/tmp")/(spec["id"]+".dds")
    urllib.request.urlretrieve(spec["url"],tmp)
    raw=tmp.read_bytes()
    got=hashlib.sha256(raw).hexdigest()
    if got!=spec["sha256"]: raise RuntimeError((spec["id"],"source drift",got))
    if raw[:4]!=b"DDS ": raise RuntimeError("not dds")
    H=struct.unpack_from("<I",raw,12)[0]; W=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]; fourcc=raw[84:88]
    if fourcc!=b"DXT5": raise RuntimeError((spec["id"],"not DXT5",fourcc))
    raw_im=Image.open(tmp).convert("RGBA")
    readable=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    arr=np.asarray(readable,dtype=np.uint8)
    alpha=arr[:,:,3]
    raw_im.save(out/f'{spec["id"]}_SOURCE_RAW.png')
    readable.save(out/f'{spec["id"]}_SOURCE_READABLE.png')

    rows=[]
    boundary_blocks={}
    union=np.zeros((H,W),bool)
    for ri,bb in enumerate(spec["bboxes"]):
        x0,y0,x1,y1=bb
        union[y0:y1,x0:x1]=True
        sub=arr[y0:y1,x0:x1,:]
        nz=sub[:,:,3]>0
        ys,xs=np.nonzero(nz)
        actual=None if len(xs)==0 else [x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()+1),y0+int(ys.max()+1)]
        pix=sub[nz]
        if len(pix):
            uniq_a,cnt_a=np.unique(pix[:,3],return_counts=True)
            alpha_top=sorted([(int(c),int(a)) for a,c in zip(uniq_a,cnt_a)],reverse=True)[:12]
            rgb=pix[:,:3]
            # coarse 16-level RGB histogram for source-style overview
            q=(rgb//16)*16
            vals,counts=np.unique(q,axis=0,return_counts=True)
            order=np.argsort(counts)[::-1][:12]
            colors=[{"rgb":vals[i].astype(int).tolist(),"count":int(counts[i])} for i in order]
        else:
            alpha_top=[]; colors=[]
        bx0=x0//4; bx1=(x1-1)//4; by0=y0//4; by1=(y1-1)//4
        full=partial=0
        part_zero_alpha=0
        part_src_transparent_outside=0
        samples=[]
        for by in range(by0,by1+1):
            for bx in range(bx0,bx1+1):
                px0,py0=bx*4,by*4; px1,py1=px0+4,py0+4
                ix0,iy0=max(px0,x0),max(py0,y0); ix1,iy1=min(px1,x1),min(py1,y1)
                inside=(ix1-ix0)*(iy1-iy0)
                if inside==16:
                    full+=1; continue
                partial+=1
                # DDS block coordinates are raw orientation. readable y maps to raw y = H-1-y.
                # The readable boundary block may map to one/two raw rows; use its raw block row.
                raw_py0=H-py1
                raw_by=raw_py0//4
                info=block_info(raw,W,H,bx,raw_by)
                if 0 in info["alpha_palette"]: part_zero_alpha+=1
                outside_vals=[]
                for yy in range(py0,py1):
                    for xx in range(px0,px1):
                        if not (x0<=xx<x1 and y0<=yy<y1) and 0<=xx<W and 0<=yy<H:
                            outside_vals.append(int(arr[yy,xx,3]))
                if outside_vals and max(outside_vals)==0: part_src_transparent_outside+=1
                key=f"{bx},{by}"
                if key not in boundary_blocks:
                    boundary_blocks[key]={**info,"readable_block":[px0,py0,px1,py1],
                        "outside_alpha_values":sorted(set(outside_vals))}
                if len(samples)<10:
                    samples.append({"readable_block":[px0,py0,px1,py1],
                        "inside_pixels":inside,"alpha_palette":info["alpha_palette"],
                        "color_palette":info["color_palette"],
                        "outside_alpha_values":sorted(set(outside_vals))})
        rows.append({
            "bbox":bb,"actual_nonzero_bbox_within_bbox":actual,
            "nonzero_pixels":int(nz.sum()),"alpha_hist_top":alpha_top,
            "coarse_rgb_top":colors,
            "block_counts":{"full":full,"partial":partial,
                "partial_with_zero_alpha_palette":part_zero_alpha,
                "partial_with_all_outside_alpha_zero":part_src_transparent_outside},
            "partial_block_samples":samples
        })
    outside_nz=int(np.count_nonzero((alpha>0)&~union))
    # visual crop contact
    cards=[]
    for i,bb in enumerate(spec["bboxes"]):
        x0,y0,x1,y1=bb; pad=20
        box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
        c=readable.crop(box)
        bg=Image.new("RGBA",c.size,(255,255,255,255)); bg.alpha_composite(c)
        rgb=bg.convert("RGB").resize((c.width*2,c.height*2),Image.Resampling.NEAREST)
        d=ImageDraw.Draw(rgb); d.rectangle((0,0,rgb.width-1,rgb.height-1),outline="black",width=2)
        cards.append(rgb)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+10 for c in cards)),"white")
    yy=0
    for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+10
    sheet.save(out/f'{spec["id"]}_SOURCE_BBOX_CONTACT.jpg',quality=96)

    rep={
      "schema_version":1,"role":"A","run":run,"queue_index":spec["index"],
      "asset":spec["path"],"source_sha256":got,
      "structure":{"width":W,"height":H,"mipmaps":mips,"fourcc":"DXT5","raw_orientation":"mirror_y"},
      "translation":{"source":spec["source"],"korean":spec["korean"]},
      "prior_strict_bboxes":spec["bboxes"],"rows":rows,
      "nonzero_alpha_outside_prior_bboxes":outside_nz,
      "unique_partial_blocks":len(boundary_blocks),
      "partial_block_zero_alpha_palette_count":sum(1 for v in boundary_blocks.values() if 0 in v["alpha_palette"]),
      "feasibility_rule":"partial DXT5 blocks can preserve every outside decoded pixel exactly by keeping original endpoints and outside indices; inside indices may be reassigned only to the original block palettes. Full-inside blocks may be normally reconstructed. This preflight measures whether source boundary blocks provide transparent/background palette support before candidate construction.",
      "status":"A117_DXT5_CONSTRAINED_PREFLIGHT_COMPLETE_PENDING_CONTROLLER_REVIEW",
      "runtime_validation":"UNTESTED"
    }
    (out/f'A117_{spec["id"]}_DXT5_PREFLIGHT.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    reports.append(rep)

summary={
  "run":run,"role":"A","assets":[{"index":r["queue_index"],"id":assets[i]["id"],
    "partial_blocks":r["unique_partial_blocks"],
    "partial_zero_alpha_palette":r["partial_block_zero_alpha_palette_count"],
    "report":f'localization/graphics/role_A/{run}/A117_{assets[i]["id"]}_DXT5_PREFLIGHT.json'}
    for i,r in enumerate(reports)],
  "candidate_written":False,
  "status":"A117_STRICT_DXT5_PREFLIGHT_COMPLETE",
  "runtime_validation":"UNTESTED"
}
(wr/"A117_DXT5_STRICT_PREFLIGHT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
