#!/usr/bin/env python3
# C250 C1 fresh independent QA: q57/q61/q65
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT=Path("localization/graphics/role_C/20261007-C250-C1-BATCH-Q057-Q061-Q065"); OUT.mkdir(parents=True,exist_ok=True)

A=[
{"index":57,"key":"39229D64","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds","candidate_sha":"3dae27fdeb7d2cde6d440b45f1e94ddafe35a97fe749447fdf0f3974d5e90c16","prior_sha":"7b8afadca8d1a5adf3490b157c3f328255c7e308f25d29a3d4ead28d5629f116","source_dds":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds","source_sha":"2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481","defect":"PJR-018 WRONG_SLANT_DIRECTION|PLATE_RECONSTRUCTION_DIRTY|SOURCE_FOOTPRINT_HAZE|TEXT_BOX_INTRUSION|TARGET_VEHICLE_GRAPHIC_INTRUSION|ALBERTO_POSITION_INTRUSION|TOTAL_RANK_PLATE_DIRTY","rows":[
["hearts",[1715,5,2048,102],[1803,10,1959,97]],["technical_bonus",[2393,77,3610,259],[2435,83,3567,252]],["mission_cleared",[128,256,1587,787],[134,352,1580,690]],["total_rank_green",[512,896,1101,1075],[518,911,1095,1060]],["storing",[1652,858,2975,998],[1758,864,2868,987]],["special_request",[1644,1114,2624,1267],[1790,1119,2477,1261]],["target",[2625,555,2825,640],[2660,563,2789,632]],["start",[2487,1016,2662,1085],[2519,1021,2629,1079]],["goal",[2975,1016,3131,1085],[3024,1021,3081,1080]],["hit_ghost",[3163,1017,3633,1106],[3168,1032,3628,1090]],["exit",[3083,1143,3494,1281],[3169,1149,3408,1275]],["collect_stars",[3469,1172,3998,1267],[3474,1177,3993,1262]],["mission_failed",[1984,1280,3187,1792],[1990,1397,3180,1675]],["total_rank_brown",[717,1915,1318,2099],[723,1931,1311,2083]],["total_rank_pink",[2598,1900,3238,2099],[2603,1918,3233,2080]],["special_request_alt",[2280,361,3269,514],[2431,366,3118,508]]],
"critical":["mission_cleared","total_rank_green","special_request","target","mission_failed","total_rank_brown","total_rank_pink"]},
{"index":61,"key":"C4A2937B","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds","candidate_sha":"fe1e7e7d264694c39f2bdbf50bb0a94ba15b88aea5b52873df4ceae749a8f95e","prior_sha":"bd9861961f8ff6183d1d0a52e1791df895cb8c8eff847d42a204c7c0321a9eab","source_dds":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds","source_sha":"821dddc662ca2349aa313f49278d5558c07e29b7a8f5d755e6987a349f0e7dd0","defect":"PJR-020 PLATE_RECONSTRUCTION_DIRTY|SOURCE_TEXT_RESIDUE|WRONG_SLANT_DIRECTION","rows":[
["go_gate",[2066,998,2548,1106],[2072,1025,2541,1078]],["cut_line",[2595,998,3029,1106],[2603,1022,3021,1081]],["keep_passing",[3067,1022,3568,1106],[3072,1039,3562,1089]],["double_speed",[3607,1025,4032,1106],[3617,1030,4021,1101]],["hit_blue_cone",[1038,1486,1511,1568],[1045,1499,1503,1555]],["dont_crash",[1566,1487,1990,1567],[1572,1498,1984,1556]],["collect_coins",[2053,1486,2517,1568],[2059,1494,2510,1559]],["run_red",[1030,1603,1554,1696],[1036,1621,1547,1678]],["run_blue",[1554,1603,2053,1696],[1560,1622,2047,1677]],["pass_convoy",[2053,1603,2573,1695],[2058,1623,2568,1674]],["catch_heart",[2555,1606,3067,1688],[2563,1611,3058,1683]],["beat_car_1",[3054,1607,3526,1687],[3061,1615,3519,1679]],["red",[3110,1446,3443,1584],[3158,1452,3394,1578]],["blue",[3571,1446,3904,1582],[3620,1452,3855,1576]],["drift",[3707,1607,3881,1688],[3713,1627,3875,1668]],["stage_bonus",[3814,1798,4076,1894],[3821,1827,4069,1865]],["get",[3594,1894,3930,2034],[3600,1900,3924,2027]],["beat_car_2",[3518,2060,3990,2140],[3525,2068,3983,2132]],["next_stage",[2557,2179,3015,2272],[2563,2186,3008,2265]],["drift_and",[3052,2185,3400,2266],[3058,2195,3394,2255]],["position",[1394,2720,1726,2829],[1469,2725,1651,2824]]],
"critical":["go_gate","cut_line","keep_passing","double_speed","red","blue","get","next_stage","position"]},
{"index":65,"key":"EBEF6D20","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds","candidate_sha":"2b39cf005e79149890f0cfee605d29144d7d257e9cc9179b6c1f583ce393fce5","prior_sha":"074cf03b504cb715e6b1328ecb33cec46a7b12fe6df74f8261eccfc77242cacc","source_png":"localization/graphics/role_A/20261005-A-PRODUCTION21/EBEF6D20_HD_SOURCE_READABLE.png","source_sha":"8d832df296241c372cf182439d9f44721b07f7555b9ee3b17b0750908194877c","defect":"PJR-021 UNTRANSLATED_COURSE_LEFT_RIGHT_EASY_HARD","rows":[
["loading_left",[256,441,672,543],[384,447,544,537]],["loading_right",[1176,441,1592,543],[1304,447,1464,537]],["course",[458,1256,745,1340],[527,1264,676,1331]],["left",[270,1340,520,1470],[290,1348,500,1462]],["right",[685,1405,874,1470],[701,1410,858,1465]],["easy",[102,1470,430,1620],[145,1479,387,1611]],["hard",[720,1470,1058,1618],[725,1484,1052,1603]]],
"critical":["loading_left","loading_right","course","left","right","easy","hard"]}
]

def H(b): return hashlib.sha256(b).hexdigest()
def old(path,want):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:continue
        if H(b)==want:return b,c
    raise RuntimeError(f"prior SHA not found {want} {path}")
def dec(b):return Image.open(io.BytesIO(b)).convert("RGBA")
def meta(b):
    return {"height":struct.unpack_from("<I",b,12)[0],"width":struct.unpack_from("<I",b,16)[0],"mips":struct.unpack_from("<I",b,28)[0] or 1,"header_sha":H(b[:128])}
def union(shape,rows):
    m=np.zeros(shape[:2],bool)
    for _,bb,_ in rows:
        x0,y0,x1,y1=bb;m[y0:y1,x0:x1]=1
    return m
def bbox(m):
    y,x=np.where(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def resize(im,maxw,maxh):
    s=min(maxw/im.width,maxh/im.height,1)
    return im.convert("RGB") if s==1 else im.resize((int(im.width*s),int(im.height*s)),Image.Resampling.LANCZOS).convert("RGB")
def overview(src,oldi,cur,path,title):
    ims=[resize(x,900,900) for x in (src,oldi,cur)]; W=sum(x.width for x in ims)+24*2; H=max(x.height for x in ims)+44
    o=Image.new("RGB",(W,H),(30,30,30));d=ImageDraw.Draw(o);x=0
    for lab,im in zip(["SOURCE","PRIOR","CURRENT"],ims): d.text((x+4,4),lab,fill="white");o.paste(im,(x,30));x+=im.width+24
    d.text((4,H-3),title,fill="white",anchor="ls");o.save(path,quality=90,subsampling=0,optimize=True)
def contacts(src,oldi,cur,rows,critical,path):
    cards=[]
    for name,bb,_ in rows:
        if name not in critical:continue
        x0,y0,x1,y1=bb;p=32;box=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
        ims=[src.crop(box),oldi.crop(box),cur.crop(box)]
        ims=[resize(x,620,260) for x in ims]; W=sum(x.width for x in ims)+16*2; H=max(x.height for x in ims)+42
        card=Image.new("RGB",(W,H),(42,42,42));d=ImageDraw.Draw(card);xx=0
        for lab,im in zip(["SRC","PRIOR","CUR"],ims):d.text((xx+3,3),lab,fill="white");card.paste(im,(xx,24));xx+=im.width+16
        d.text((4,H-3),name,fill="white",anchor="ls");cards.append(card)
    W=max(x.width for x in cards);H=sum(x.height for x in cards)+8*(len(cards)-1);o=Image.new("RGB",(W,H),(18,18,18));y=0
    for c in cards:o.paste(c,(0,y));y+=c.height+8
    o.save(path,quality=94,subsampling=0,optimize=True)

summary={"schema_version":1,"role":"C","run":"C250","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","execution_backend":"github-actions fallback because ChatGPT local git/DDS materialization failed DNS; N100 not used","assets":[]}
for a in A:
    cb=Path(a["candidate"]).read_bytes(); actual=H(cb)
    if actual!=a["candidate_sha"]:raise RuntimeError(f'q{a["index"]} candidate drift {actual}')
    pb,pcommit=old(a["candidate"],a["prior_sha"])
    cm,pm=meta(cb),meta(pb);cur_raw,old_raw=dec(cb),dec(pb);cur=ImageOps.flip(cur_raw);oldr=ImageOps.flip(old_raw)
    if "source_dds" in a:
        sb=Path(a["source_dds"]).read_bytes()
        if H(sb)!=a["source_sha"]:raise RuntimeError(f'q{a["index"]} source drift {H(sb)}')
        sm=meta(sb)
        if cm["header_sha"]!=sm["header_sha"]:raise RuntimeError(f'q{a["index"]} header differs source')
        src=ImageOps.flip(dec(sb))
    else:
        src=Image.open(a["source_png"]).convert("RGBA")
        if cm["header_sha"]!=pm["header_sha"]:raise RuntimeError(f'q{a["index"]} header differs prior')
    if src.size!=cur.size:raise RuntimeError(f'q{a["index"]} size mismatch {src.size} {cur.size}')
    s=np.array(src);c=np.array(cur);p=np.array(oldr)
    diff=np.any(s!=c,2);ad=s[:,:,3]!=c[:,:,3];allowed=union(c.shape,a["rows"])
    outside=int((diff&~allowed).sum());aout=int((ad&~allowed).sum())
    blast=np.any(p!=c,2);blastout=int((blast&~allowed).sum())
    per=[]
    for name,sb,lb in a["rows"]:
        sx0,sy0,sx1,sy1=sb;lx0,ly0,lx1,ly1=lb
        d=[lx0-sx0,sx1-lx1,ly0-sy0,sy1-ly1]
        per.append({"key":name,"original_bbox":sb,"localized_bbox":lb,"source_size":[sx1-sx0,sy1-sy0],"localized_size":[lx1-lx0,ly1-ly0],"delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],"containment":"PASS" if min(d)>=0 else "FAIL","size_ceiling":"PASS" if lx1-lx0<=sx1-sx0 and ly1-ly0<=sy1-sy0 else "FAIL","positive_margin":"PASS" if min(d)>0 else "FAIL"})
    if outside or aout or blastout or any(x["containment"]!="PASS" or x["size_ceiling"]!="PASS" or x["positive_margin"]!="PASS" for x in per):
        raise RuntimeError(f'q{a["index"]} machine hard fail outside={outside} alpha={aout} blast={blastout}')
    overview(src,oldr,cur,OUT/f'C250_q{a["index"]:03d}_{a["key"]}_OVERVIEW.jpg',f'q{a["index"]} readable FLIP-Y / defect: {a["defect"]}')
    contacts(src,oldr,cur,a["rows"],a["critical"],OUT/f'C250_q{a["index"]:03d}_{a["key"]}_CRITICAL_CONTACTS.jpg')
    overview(ImageOps.flip(src),old_raw,cur_raw,OUT/f'C250_q{a["index"]:03d}_{a["key"]}_RAW.jpg',f'q{a["index"]} RAW DDS orientation')
    rep={"schema_version":1,"role":"C","run":"C250","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","queue_index":a["index"],"asset_key":a["key"],"candidate_sha256":actual,"canonical_source_sha256":a["source_sha"],"prior_candidate_sha256":a["prior_sha"],"prior_blob_commit":pcommit,"defect_revalidation":a["defect"],"machine_qa":{"dimensions":[cm["width"],cm["height"]],"mips":cm["mips"],"header_exact":True,"source_vs_current_changed_outside_exact_source_bboxes":outside,"source_vs_current_alpha_changed_outside_exact_source_bboxes":aout,"prior_vs_current_changed_outside_rework_union":blastout,"source_vs_current_changed_bbox":bbox(diff),"bbox_size_positive_margin":f'{len(per)}/{len(per)} PASS',"per_region":per},"visual_evidence":[f'C250_q{a["index"]:03d}_{a["key"]}_OVERVIEW.jpg',f'C250_q{a["index"]:03d}_{a["key"]}_CRITICAL_CONTACTS.jpg',f'C250_q{a["index"]:03d}_{a["key"]}_RAW.jpg'],"controller_visual_qa":"PENDING","c3_strict_audit":"PENDING","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    (OUT/f'C250_q{a["index"]:03d}_{a["key"]}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":actual,"machine_qa":"PASS","controller_visual_qa":"PENDING","c3":"PENDING"})
(OUT/"C250_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
