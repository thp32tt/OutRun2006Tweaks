#!/usr/bin/env python3
import hashlib,json,os,struct,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C134-EBFC709F-DIAG"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(srczip) as z: sb=z.read(asset)
sha=hashlib.sha256(sb).hexdigest()
if sha!="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0":
    raise RuntimeError(("source_sha",sha))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
if (W,H)!=(2048,1024) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
img=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
a=np.asarray(img,dtype=np.uint8)
alpha=a[:,:,3]>0

def groups(vals,gap=2):
    vals=[int(v) for v in vals]
    if not vals:return []
    out=[];g=[vals[0]]
    for v in vals[1:]:
        if v-g[-1]>gap: out.append(g);g=[v]
        else:g.append(v)
    out.append(g);return out

def line_scan(y0,y1,minpix=20):
    sub=alpha[y0:y1]
    ys=np.flatnonzero(np.count_nonzero(sub,axis=1)>=minpix)
    lines=[]
    for yg in groups(ys,3):
        ay0=y0+yg[0]; ay1=y0+yg[-1]+1
        row=alpha[ay0:ay1]
        xs=np.flatnonzero(np.any(row,axis=0))
        xgroups=[]
        for xg in groups(xs,8):
            x0,x1=xg[0],xg[-1]+1
            m=alpha[ay0:ay1,x0:x1]
            n=int(np.count_nonzero(m))
            if n<20: continue
            px=a[ay0:ay1,x0:x1][m]
            med=[int(v) for v in np.median(px,axis=0)] if len(px) else [0,0,0,0]
            xgroups.append({"bbox":[x0,ay0,x1,ay1],"pixels":n,"median_rgba":med})
        lines.append({"y":[ay0,ay1],"height":ay1-ay0,"xgroups":xgroups})
    return lines

# Target headings live in these two broad zones; scan exact source, not historical diff.
zones={
 "small_zone":[240,460],
 "large_zone":[620,1024]
}
report={
 "schema_version":1,"role":"C","run":run,"asset":"EBFC709F","queue_index":232,
 "source_sha256":sha,"structure":{"width":W,"height":H,"mipmaps":mips,"format":"RGBA32","raw_orientation":"mirror_y"},
 "zones":{k:line_scan(v[0],v[1]) for k,v in zones.items()},
 "runtime_validation":"UNTESTED"
}
(out/"C134_EBFC_SOURCE_LINE_DIAGNOSTIC.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

vis=img.copy()
d=ImageDraw.Draw(vis)
for zk,lines in report["zones"].items():
    for li,line in enumerate(lines,1):
        for gi,g in enumerate(line["xgroups"],1):
            x0,y0,x1,y1=g["bbox"]
            d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,0,255),width=2)
            d.text((x0,max(0,y0-14)),f"{zk}:{li}.{gi}",fill=(255,255,0,255))
vis.convert("RGB").save(out/"C134_EBFC_SOURCE_LINES.jpg",quality=96)
summary={"run":run,"asset":"EBFC709F","index":232,"status":"SOURCE_LINES_MEASURED","report":f"localization/graphics/role_C/{run}/C134_EBFC_SOURCE_LINE_DIAGNOSTIC.json","runtime_validation":"UNTESTED"}
(wr/"C134_EBFC709F_DIAG.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
