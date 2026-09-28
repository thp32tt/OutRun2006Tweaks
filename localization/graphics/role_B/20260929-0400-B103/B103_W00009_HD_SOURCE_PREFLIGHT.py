#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, struct, zipfile
from pathlib import Path
from statistics import median
from PIL import Image, ImageDraw

ASSETS=[
{"index":26,"asset":"63C91067","path":"textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds","git_blob_sha":"9f41fe44ecb17a4daba096ddbb9d2c73fa28e8f9","source_sha256":"d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab","dimensions":[2048,2048],"labels":[{"key":"pink","search":[560,140,1160,270]},{"key":"brown","search":[720,1160,1320,1300]}]},
{"index":28,"asset":"A05BF610","path":"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds","git_blob_sha":"1ed3fc83fc0501ac6420c0b3e3c51b7f0c9b1374","source_sha256":"52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129","dimensions":[2048,2048],"labels":[{"key":"green","search":[520,1160,1100,1300]}]},
{"index":30,"asset":"8215FD25","path":"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds","git_blob_sha":"64a92104d3158614283d0d63baee7ec29ca45316","source_sha256":"e8125cb52c6a135dcde0dade0dcf447ea5d806b8a9b2438d7d6732be84c9b66e","dimensions":[4096,2048],"labels":[{"key":"pink","search":[1650,140,2250,270]},{"key":"brown","search":[1800,1160,2400,1300]}]},
{"index":32,"asset":"DCC7B488","path":"textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds","git_blob_sha":"7f8f0d10f2ac8a19bda1933d6a324a37123b48c0","source_sha256":"ecd0607fd021b6aa0c78700bffa05f70546a4d37da6182edc4a35bc41ab5ee4e","dimensions":[2048,1024],"labels":[{"key":"green","search":[520,140,1100,280]}]}
]
def gitsha(b): return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def dds(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise ValueError("not DDS")
    h,w,pitch,mips=struct.unpack_from("<IIII",b,12)
    fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000): raise ValueError("not RGBA32")
    if pitch!=w*4 or len(b)!=128+w*h*4: raise ValueError("payload mismatch")
    return w,h,(mips or 1),Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
def pct(v,p): v=sorted(v); return v[round((len(v)-1)*p)]
def med(rows,i): return int(median([r[i] for r in rows])) if rows else None
def measure(im,lab):
    x0,y0,x1,y1=lab["search"]; px=im.load(); pts=[]; whites=[]; navys=[]
    for y in range(y0,y1):
      for x in range(x0,x1):
        r,g,b,a=px[x,y]
        if a<40: continue
        white=r>=185 and g>=185 and b>=185 and max(r,g,b)-min(r,g,b)<=55
        navy=b>=35 and b>=r*.95 and b>=g*1.15 and r<=65 and g<=80
        if white or navy:
          pts.append((x,y,a)); (whites if white else navys).append((r,g,b,a))
    if not pts: raise ValueError("no decoded Total Rank core")
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; bb=[min(xs),min(ys),max(xs),max(ys)]
    bx0,by0,bx1,by1=bb
    ba=[px[x,y][3] for y in range(by0,by1+1) for x in range(bx0,bx1+1)]
    ring=[]; pad=12
    for y in range(max(0,by0-pad),min(im.height-1,by1+pad)+1):
      for x in range(max(0,bx0-pad),min(im.width-1,bx1+pad)+1):
        if bx0<=x<=bx1 and by0<=y<=by1: continue
        ring.append(px[x,y][3])
    return {"key":lab["key"],"source":"Total Rank","korean":"종합 랭크","search_rect_readable":lab["search"],"foreground_core_bbox_readable":bb,"foreground_core_pixels":len(pts),"white_fill_median_rgba":[med(whites,i) for i in range(4)],"navy_outline_median_rgba":[med(navys,i) for i in range(4)],"bbox_alpha":{"min":min(ba),"p10":pct(ba,.1),"median":pct(ba,.5),"p90":pct(ba,.9),"max":max(ba)},"background_ring_alpha":{"min":min(ring),"p10":pct(ring,.1),"median":pct(ring,.5),"p90":pct(ring,.9),"max":max(ring)},"permitted_full_effect_bbox":None,"containment_state":"HOLD_STRICT_RECHECK"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--zip",required=True,type=Path); ap.add_argument("--out-json",required=True,type=Path); ap.add_argument("--proof",type=Path); a=ap.parse_args()
    out={"schema_version":1,"translation":{"Total Rank":"종합 랭크"},"assets":[]}
    proof=[]
    with zipfile.ZipFile(a.zip) as z:
      names=set(z.namelist())
      for s in ASSETS:
        ms=[n for n in names if n.endswith("/"+s["path"]) or n==s["path"]]
        if len(ms)!=1: raise SystemExit(f"{s['asset']}: source member mismatch")
        b=z.read(ms[0])
        if gitsha(b)!=s["git_blob_sha"] or hashlib.sha256(b).hexdigest()!=s["source_sha256"]: raise SystemExit(f"{s['asset']}: immutable GitHub identity mismatch")
        w,h,m,raw=dds(b)
        if [w,h]!=s["dimensions"] or m!=1: raise SystemExit(f"{s['asset']}: DDS header mismatch")
        im=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        rec={"queue_index":s["index"],"asset":s["asset"],"git_blob_sha":s["git_blob_sha"],"source_sha256":s["source_sha256"],"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"raw_orientation":"mirror_y","labels":[]}
        for lab in s["labels"]:
          lm=measure(im,lab); rec["labels"].append(lm); proof.append((s["asset"],lab["key"],im,lm))
        out["assets"].append(rec)
    out["summary"]={"assets":4,"physical_labels":6,"git_blob_identity_pass":4,"candidate_dds_written":0,"runtime_validation":"UNTESTED","result":"PASS_NEW_DECODED_PIXEL_RECONSTRUCTION_INPUT_HOLD_CANDIDATE"}
    a.out_json.parent.mkdir(parents=True,exist_ok=True); a.out_json.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n","utf-8")
    if a.proof:
      crops=[]
      for asset,key,im,lm in proof:
        x0,y0,x1,y1=lm["search_rect_readable"]; c=im.crop((x0,y0,x1,y1)).convert("RGBA"); d=ImageDraw.Draw(c); bb=lm["foreground_core_bbox_readable"]; d.rectangle((bb[0]-x0,bb[1]-y0,bb[2]-x0,bb[3]-y0),outline="white",width=2); crops.append((asset,key,c))
      W=max(c.width for _,_,c in crops); H=sum(c.height+28 for _,_,c in crops); sheet=Image.new("RGBA",(W,H),(28,28,28,255)); d=ImageDraw.Draw(sheet); y=0
      for asset,key,c in crops:
        d.text((4,y+4),f"{asset} / {key} / ENGLISH HD decoded core bbox",fill="white"); sheet.alpha_composite(c,(0,y+28)); y+=c.height+28
      a.proof.parent.mkdir(parents=True,exist_ok=True); sheet.save(a.proof,optimize=True)
if __name__=="__main__": main()
