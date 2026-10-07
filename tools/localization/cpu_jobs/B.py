#!/usr/bin/env python3
# B239: q52 A8CE339F duplicate Start-family consistency repair.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import base64, hashlib, io, json, struct, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

repo=Path.cwd()
RUN="20261007-B239-Q052-A8CE339F-START-FAMILY"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
cleanp=repo/"localization/graphics/role_B/20261006-B-PRODUCTION176-A8CE339F-DXT5-RESIDUE/B176_CLEAN_PLATE.png"
PRIOR_SHA="d9e590a8e36a735d1edb116ee606aa486e85de8b926bab3a95a741cbfca66fd8"
FINAL_SHA="c37ce8ccc4438c985dcc73691c6b3b4c8f699d6e9c841e5db2bb2cfb9e58c67e"
SOURCE_SHA="08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"
PATCH_PACKAGE=json.loads(r'''{"prior_sha256":"d9e590a8e36a735d1edb116ee606aa486e85de8b926bab3a95a741cbfca66fd8","candidate_sha256":"c37ce8ccc4438c985dcc73691c6b3b4c8f699d6e9c841e5db2bb2cfb9e58c67e","size":2097280,"ranges":[{"offset":1387888,"length":238,"sha256":"f56ceab49f21bffa7503873369b293805a474befb681342a66dd28da6d0d0f83","b64":"eNr7x+A5KURTgPEHAwPD379/z/5n8GQCMhlA/Pj//88j80PJ4H8D8tUYmBXA/Pp6519A+2I6JzCD+V+B9slA1HsrejCEhoZe/q8A4RtEg/n3CfLlIXwBCP/6HyagfQ7MGiDzr9fXezNAgSkjA8P/9wDmHkjY"},{"offset":1396080,"length":224,"sha256":"e78c75f97904167b75b2d8c131d2b553c1ea0fdd8d8787f9a752752568e2797f","b64":"eNr7zyAowAhEPxgYGP7+/Xv2/38GMPj/v3wtExOTE4y/73sGA4MDQyiC70EU/x8TA5MCEPUAxVatWpX1l8FQgBmIMO3TtWJkZHRE8IH2MTiEIfgeIH4oLj7YPgag/YwNTBoNTDog8+vr650B/LVE9A=="},{"offset":1404272,"length":224,"sha256":"4c5f1256e05cae544050efb5697ce3976b7f89b2afe789a3cd1b0c1880431135","b64":"eNr7zyAowMgowPCDgYHh79+/Z///ZwCDfd89gKRDKIz//38Gwyq8fA8QfyqMf/8/r1WWg4PHf4YDTBYNzBYg8+vr653/MhgKMAMRun3//+s5MTI6roTx533PYAhjcGCA8997MIQi8UHuQ+b//9/BEerg4PKPzYFZxYFJBWYfAGPlSZk="},{"offset":1412448,"length":240,"sha256":"640c68dfd53a39cf168dd73da6489811cfaf26d720091489d2ce33aca413b9ee","b64":"eNr7z+A5ScVzjsQPBgaG0NCroX8ZGAUYmBgYQPy/f/+f//+fAQxq33sASYdQGH/ee3UQ/yqM////1SmrGBhOwPj7vqOq//9fneHAgROh/xgamC0Y2MDm19cDzWcwFGA2V8CwD6Q+lJnZGcH3YAgFGoiLfx/IF0WRPyngAAT/ORyYVIAIYl+9MwCLP0/2"},{"offset":1420640,"length":240,"sha256":"39752e5b2879bad37fdcf8543d22e7255779826169d42d935d43e228ae721bdd","b64":"eNr7z8A5kefkBJ4fDAwMX79+Pfr/PwMY3P+ewRDKWckJ4+/77sEQyuDAgOCrM1xF4v///3OvA4PDKtzqsfAL6goQ+oH8UNajCH4HRyhQA37+gTMw/jyQe6devYqQPykQmuXg85/NgUkFiED+q6+vdwYA6qdUig=="},{"offset":1428832,"length":256,"sha256":"9878cfe0ef01c4e0f76952dab0a86b5d85d76f59bd3ca36cf43c2fd3adc71927","b64":"eNr7x8g5UcZzWsoPBgaGr1+vXv3/nwEMat97MISKfl0K4///38ER+oLBAcbf9z2DITQ8gQPGtzoGVB8a+gWhPoMj9Cq3AxKfIVSLAZUfHhaG4HswsLKyusL494H2MQQEByPs6+D4MHXqVIR6gWgHBwcXGD8W6F5RUYT7//8/KQCUd/h3nYEJbl9oaN5/Bj8m9YQmVZB/w+PjgwGhslqF"},{"offset":1437024,"length":256,"sha256":"7bdb3e54700ed69f374cf8a9081be12954137952da831949f1a8dd883e65615e","b64":"eNpbxeA5YYnnJJUfDAwMoUDwLwXIYBVg+DYng+FqaOjV//8ZwOD//wyGvaGhDTD+/f8dHAy8pg4I+R1bVRgYkPgeDA0VYXD+vO8eDHWhoSz/X4C5LJkMbgyrgABZPSsrqysyH2hcMMI+MH8qQl4g2sHBwQXGj33vwSAqehXJvZ0cDAwHXBB8dYaEjPrQvwwRTaoRTWog/8bHxwcDAOtVVkY="},{"offset":1445232,"length":240,"sha256":"8bcef75cf469e92f5d4587b5041100bc21db7c230a7e6649eac5ebb92b02ca4c","b64":"eNr7x8gawMAmwBiY7MFw9Wpo6P//DGAw77sHQwEDEv89iH/1Koz///8bQwaGhh5c6muB6lmA/H9xDQwcBxhSMhncGFYBAUJ/BgPr1aWhyPzg4Cg4/+qUDKBtU5HkPRgOPHgF58cCzRcVRXbPSQEHIPjHwsDww4FJ5QdYrN55FoPHJBXPSWB+KBAAADR8VSQ="},{"offset":1445551,"length":1,"sha256":"8d33f520a3c4cef80d2453aef81b612bfe1cb44c8b2025630ad38662763f13d3","b64":"eNpLAAAAYQBh"},{"offset":1453343,"length":1,"sha256":"74cd9ef9c7e15f57bdad73c511462ca65cb674c46c49639c60f1b44650fa1dcb","b64":"eNqLAwAAXwBf"},{"offset":1453424,"length":224,"sha256":"a561d3542b52ec2afe3b74176ccea08db3cfb8b222f53bbabd75ed0c9ab35f9f","b64":"eNq7z/BzgornJJUfDAwMsaGhX18wMMD58aGhof8YGAQYd054clLAg+FqaOjV/9pACaCSNZoZDFOA8j+BPJMEiPr/9fFfniPpvx8a+v8UQ8YsGD8cyAeal5AH5f8/H/r/LwPDhotI/B8MohMKYPyzof//AOVzkdUzMSgwKE5QyVaEuOcfL8Q9XJIeDGVA93xlcGhS9Yaor4+P+w8AJ2pUeg=="},{"offset":1453727,"length":1,"sha256":"3f79bb7b435b05321651daefd374cdc681dc06faa65e374e38337b88ca046dea","b64":"eNpLBQAAZgBm"}]}''')

def sha(b): return hashlib.sha256(b).hexdigest()

prior_bytes=cand.read_bytes()
if sha(prior_bytes)!=PRIOR_SHA:
    raise RuntimeError(("q52 candidate drift",sha(prior_bytes),PRIOR_SHA))
if len(prior_bytes)!=PATCH_PACKAGE["size"]:
    raise RuntimeError(("size drift",len(prior_bytes),PATCH_PACKAGE["size"]))

# Replay the exact previously controller-inspected B239 BC3 bytes.
outb=bytearray(prior_bytes)
for r in PATCH_PACKAGE["ranges"]:
    raw=zlib.decompress(base64.b64decode(r["b64"]))
    if len(raw)!=r["length"] or sha(raw)!=r["sha256"]:
        raise RuntimeError(("patch integrity",r["offset"]))
    a=r["offset"]; b=a+r["length"]
    outb[a:b]=raw
final_bytes=bytes(outb)
if sha(final_bytes)!=FINAL_SHA:
    raise RuntimeError(("final SHA mismatch",sha(final_bytes),FINAL_SHA))
if final_bytes[:128]!=prior_bytes[:128]:
    raise RuntimeError("DDS header changed")
cand.write_bytes(final_bytes)

# Authoritative persisted-DDS decode from exact prior/final bytes.
prior_raw=Image.open(io.BytesIO(prior_bytes)).convert("RGBA")
final_raw=Image.open(io.BytesIO(final_bytes)).convert("RGBA")
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
final=final_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(cleanp).convert("RGBA")
W,H=final.size
if (W,H)!=(2048,1024) or clean.size!=(W,H):
    raise RuntimeError(("dimensions",W,H,clean.size))

pa=np.asarray(prior); fa=np.asarray(final); ca=np.asarray(clean)
left_bb=(24,308,131,349)
right_bb=(801,309,908,350)
extra_bb=(16,213,485,284)
goal_left=(649,308,744,349)
goal_right=(1426,308,1521,349)

def introduced_bbox(arr,bb):
    x0,y0,x1,y1=bb
    m=(arr[y0:y1,x0:x1,3]>8)&(ca[y0:y1,x0:x1,3]<=1)
    ys,xs=np.nonzero(m)
    if not len(xs): raise RuntimeError(("empty localized bbox",bb))
    return [x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]

left_prior=introduced_bbox(pa,left_bb)
right_prior=introduced_bbox(pa,right_bb)
left_final=introduced_bbox(fa,left_bb)
right_final=introduced_bbox(fa,right_bb)
if left_prior!=[46,310,106,346] or right_prior!=[829,314,882,345]:
    raise RuntimeError(("B176 geometry drift",left_prior,right_prior))
if left_final!=left_prior or right_final!=[826,312,886,348]:
    raise RuntimeError(("B239 geometry drift",left_final,right_final))

ls=[left_final[2]-left_final[0],left_final[3]-left_final[1]]
rs=[right_final[2]-right_final[0],right_final[3]-right_final[1]]
if ls!=[60,36] or rs!=[60,36]:
    raise RuntimeError(("family mismatch",ls,rs))
margins=[right_final[0]-right_bb[0],right_bb[2]-right_final[2],right_final[1]-right_bb[1],right_bb[3]-right_final[3]]
if min(margins)<=0: raise RuntimeError(("margin",margins))

allowed=np.zeros((H,W),bool);allowed[right_bb[1]:right_bb[3],right_bb[0]:right_bb[2]]=True
diff=np.any(pa!=fa,axis=2)
ad=pa[:,:,3]!=fa[:,:,3]
outside=int(np.count_nonzero(diff&~allowed))
alpha_out=int(np.count_nonzero(ad&~allowed))
if outside or alpha_out:
    raise RuntimeError(("blast radius",outside,alpha_out))

# Every non-target B176 localized family must remain pixel-exact.
for name,bb in [("extra_time",extra_bb),("goal_left",goal_left),("goal_right",goal_right),("start_left",left_bb)]:
    x0,y0,x1,y1=bb
    if np.any(pa[y0:y1,x0:x1]!=fa[y0:y1,x0:x1]):
        raise RuntimeError(("non-target drift",name))

# Count changed DXT5 blocks and verify the patch remains narrowly scoped.
bw=W//4; bh=H//4
changed_blocks=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if prior_bytes[off:off+16]!=final_bytes[off:off+16]:
            changed_blocks+=1
if changed_blocks!=137:
    raise RuntimeError(("changed BC3 block drift",changed_blocks,137))

def comp(im,bg=(88,88,88,255)):
    z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")

# Focus evidence: left and right duplicate Start, prior vs current.
rows=[]
for name,bb in [("START LEFT",left_bb),("START RIGHT",right_bb)]:
    x0,y0,x1,y1=bb;pad=20
    cr=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    cards=[]
    for lab,im in [("B176",prior),("B239",final)]:
        z=comp(im).crop(cr).resize(((cr[2]-cr[0])*4,(cr[3]-cr[1])*4),Image.Resampling.NEAREST)
        c=Image.new("RGB",(z.width,z.height+30),(20,20,20));c.paste(z,(0,30))
        ImageDraw.Draw(c).text((6,6),f"{name} {lab}",fill="white");cards.append(c)
    rr=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(20,20,20))
    x=0
    for c in cards: rr.paste(c,(x,0));x+=c.width
    rows.append(rr)
sheet=Image.new("RGB",(max(r.width for r in rows),sum(r.height for r in rows)),(20,20,20))
y=0
for r in rows:sheet.paste(r,(0,y));y+=r.height
sheet.save(out/"B239_START_FAMILY_B176_FINAL.jpg",quality=96,subsampling=0)

def full_card(label,im,maxw=950):
    v=comp(im)
    if v.width>maxw:v=v.resize((maxw,round(v.height*maxw/v.width)),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+30),(20,20,20));c.paste(v,(0,30))
    ImageDraw.Draw(c).text((6,6),label,fill="white");return c
cards=[full_card("B176 READABLE",prior),full_card("B239 READABLE",final)]
fs=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(20,20,20))
x=0
for c in cards:fs.paste(c,(x,0));x+=c.width
fs.save(out/"B239_FULL_READABLE.jpg",quality=94,subsampling=0)
cards=[full_card("B176 RAW",prior_raw),full_card("B239 RAW",final_raw)]
rsheet=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(20,20,20))
x=0
for c in cards:rsheet.paste(c,(x,0));x+=c.width
rsheet.save(out/"B239_RAW.jpg",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"B","run":RUN,"queue_index":52,"asset":asset,
 "trigger":"CURRENT_POLICY_UI_FAMILY_STYLE_PROFILE_FALSE_NEGATIVE_DUPLICATE_START_SCALE_MISMATCH",
 "source_sha256":SOURCE_SHA,
 "prior_candidate_sha256":PRIOR_SHA,"candidate_sha256":FINAL_SHA,
 "prior_family":{"start_left":{"bbox":left_prior,"size":[60,36],"font_size":30},
                 "start_right":{"bbox":right_prior,"size":[53,31],"font_size":27}},
 "repair":{"scope":"right Start only","korean":"출발","final_left_bbox":left_final,"final_right_bbox":right_final,
           "final_duplicate_sizes":{"left":ls,"right":rs},"right_margins":margins,
           "style":{"font":"Noto Sans CJK KR Bold","ttc_index":1,"font_size":30,
                    "fill":[255,255,255,255],"outer":[0,10,65,255],"stroke":3,"slant":0.0}},
 "machine_qa":{"duplicate_start_size_delta":[rs[0]-ls[0],rs[1]-ls[1]],
               "changed_pixels_outside_right_start_bbox":outside,
               "alpha_changed_outside_right_start_bbox":alpha_out,
               "changed_bc3_blocks":changed_blocks,
               "header_128_exact":True,"raw_orientation":"mirror_y",
               "extra_time_goal_left_goal_right_left_start_pixel_exact":True,
               "persisted_decode":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_B176_VALIDATED_CLEAN_PLATE_LINEAGE",
   "2_source_matching_slant":"PASS_UPRIGHT",
   "3_no_undersized_lettering":"PASS_RIGHT_START_RESTORED_TO_LEFT_START_60x36_FAMILY",
   "4_source_faithful_weight_effect":"PASS_WHITE_NAVY_3PX_MATCH",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
   "6_protected_art_clearance":"PASS_ZERO_DRIFT_OUTSIDE_RIGHT_START_BBOX",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM"
 },
 "execution_backend":"EXACT_CONTROLLER_VALIDATED_B239_BC3_PATCH_REPLAY_ON_GITHUB_HOSTED_WORKER",
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "status":"B239_WORKER_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA_AND_FRESH_C",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"B239_Q052_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
(wr/"B239_Q052_A8CE339F.json").write_text(json.dumps({
 "role":"B","run":RUN,"queue_index":52,"candidate_sha256":FINAL_SHA,
 "report":str((out/"B239_Q052_MACHINE_QA.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"run":RUN,"prior":PRIOR_SHA,"candidate":FINAL_SHA,
 "left_prior":left_prior,"right_prior":right_prior,"left_final":left_final,"right_final":right_final,
 "duplicate_sizes":{"left":ls,"right":rs},"margins":margins,"outside":outside,"alpha_out":alpha_out,
 "changed_blocks":changed_blocks,"runtime_validation":"UNTESTED"},ensure_ascii=False))
