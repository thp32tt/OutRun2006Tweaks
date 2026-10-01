#!/usr/bin/env python3
import argparse, hashlib, json, struct, zipfile
from pathlib import Path

ARCHIVE_SIZE=306223257
ARCHIVE_SHA="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
MEMBER="textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds"
MEMBER_SHA="439a09cdcaaf000802ce104ebb9e00b22df28e1f4657ff94021b4f92707c6ccc"
PINNED_GIT_BLOB="0b3bdc37870e75da3290f2d5587cebd9cd73655c"
W,H=2048,512
EXPECTED=[
("REMOVE FRIEND",[3,51,394,88],8195),
("SEND GAME INVITE",[3,115,461,152],9088),
("TIME ATTACK gray",[17,180,508,241],15105),
("OUTRUN",[808,180,1096,241],10273),
("COAST 2 COAST",[20,266,625,329],17021),
("HEART ATTACK",[1022,268,1557,329],16968),
("TIME ATTACK red",[14,352,1360,499],100007),
]
def sha256_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def bbox(points):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    return [min(xs),min(ys),max(xs),max(ys)]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("archive",nargs="?",default="/mnt/data/OR2-HD-GUI-v0.25.10a.zip")
    args=ap.parse_args()
    p=Path(args.archive)
    out={"schema":"outrun-index220-source-geometry-verifier-v1","archive":str(p)}
    out["archive_size"]=p.stat().st_size
    out["archive_sha256"]=sha256_file(p)
    if out["archive_size"]!=ARCHIVE_SIZE or out["archive_sha256"]!=ARCHIVE_SHA:
        out["status"]="FAIL_PINNED_ARCHIVE_IDENTITY"; print(json.dumps(out,indent=2)); return 2
    with zipfile.ZipFile(p) as z: data=z.read(MEMBER)
    out["member_sha256"]=hashlib.sha256(data).hexdigest()
    git_obj=hashlib.sha1(("blob %d\0"%len(data)).encode()+data).hexdigest()
    out["git_blob_sha"]=git_obj
    if out["member_sha256"]!=MEMBER_SHA or git_obj!=PINNED_GIT_BLOB:
        out["status"]="FAIL_SOURCE_IDENTITY"; print(json.dumps(out,indent=2)); return 3
    if data[:4]!=b"DDS " or struct.unpack_from("<I",data,12)[0]!=H or struct.unpack_from("<I",data,16)[0]!=W:
        out["status"]="FAIL_DDS_HEADER"; print(json.dumps(out,indent=2)); return 4
    if struct.unpack_from("<I",data,28)[0] not in (0,1) or struct.unpack_from("<I",data,88)[0]!=32:
        out["status"]="FAIL_DDS_MODE"; print(json.dumps(out,indent=2)); return 5
    payload=data[128:128+W*H*4]
    pts=[[] for _ in EXPECTED]; outside=0; total=0
    for ry in range(H):
        raw_y=H-1-ry
        row=(raw_y*W)*4
        for x in range(W):
            if payload[row+x*4+3]:
                total+=1; hit=False
                for i,(_,b,_) in enumerate(EXPECTED):
                    if b[0]<=x<=b[2] and b[1]<=ry<=b[3]:
                        pts[i].append((x,ry)); hit=True; break
                if not hit: outside+=1
    regs=[]
    ok=True
    for i,(name,exp,count) in enumerate(EXPECTED):
        got=bbox(pts[i]); n=len(pts[i])
        if got!=exp or n!=count: ok=False
        regs.append({"name":name,"bbox_readable":got,"alpha_pixels":n,
                     "bbox_raw":[got[0],H-1-got[3],got[2],H-1-got[1]],
                     "candidate_safe_bbox_readable":[got[0]+2,got[1]+2,got[2]-2,got[3]-2]})
    out.update({"total_nonzero_alpha_pixels":total,"alpha_outside_regions":outside,
                "regions":regs,"source_text_transform":"flip_y"})
    out["status"]="PASS_EXACT_SOURCE_GEOMETRY" if ok and outside==0 and total==176657 else "FAIL_GEOMETRY"
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out["status"].startswith("PASS") else 6
if __name__=="__main__":
    raise SystemExit(main())
