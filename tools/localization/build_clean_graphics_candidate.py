#!/usr/bin/env python3
"""Fail-closed clean-generation orchestrator with v2 measured safe-fit gates."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

HEADER=128
V1="outrun-first-pass-edit-v1"
V2="outrun-first-pass-edit-v2"

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def img(path): return Image.open(path).convert("RGBA")
def binmask(path,size):
    m=Image.open(path).convert("L")
    if m.size!=size: raise SystemExit(f"FAIL mask size {m.size} != {size}")
    return m.point(lambda x:255 if x else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for q in bands[1:]: m=ImageChops.lighter(m,q)
    return m.point(lambda x:255 if x else 0)
def n(m): return sum(1 for x in m.getdata() if x)
def rect_mask(size,rects):
    m=Image.new("L",size,0); draw=ImageDraw.Draw(m)
    for l,t,r,b in rects: draw.rectangle((l,t,r-1,b-1),fill=255)
    return m
def crop_bbox(mask,rect):
    l,t,r,b=rect; bb=mask.crop((l,t,r,b)).getbbox()
    return None if bb is None else [bb[0]+l,bb[1]+t,bb[2]+l,bb[3]+t]
def contained(inner,outer):
    return inner[0]>=outer[0] and inner[1]>=outer[1] and inner[2]<=outer[2] and inner[3]<=outer[3]
def dds_info(path):
    b=Path(path).read_bytes()
    if len(b)<HEADER or b[:4]!=b"DDS ": raise SystemExit("FAIL invalid DDS")
    return {"width":struct.unpack_from("<I",b,16)[0],"height":struct.unpack_from("<I",b,12)[0],
        "mips":struct.unpack_from("<I",b,28)[0] or 1,"fourcc":b[84:88].decode("latin1"),
        "rgb_bits":struct.unpack_from("<I",b,88)[0],"sha256":hashlib.sha256(b).hexdigest(),
        "header_sha256":hashlib.sha256(b[:HEADER]).hexdigest()}
def decode_uncompressed(path):
    b=Path(path).read_bytes(); inf=dds_info(path)
    if inf["fourcc"]!="\x00\x00\x00\x00" or inf["rgb_bits"]!=32:
        raise SystemExit("FAIL compressed DDS needs approved external encoder/decoder round-trip; no silent format conversion")
    w,h=inf["width"],inf["height"]; payload=b[HEADER:HEADER+w*h*4]
    if len(payload)!=w*h*4: raise SystemExit("FAIL unsupported DDS payload/mips")
    out=bytearray(len(payload))
    for i in range(0,len(payload),4):
        B,G,R,A=payload[i:i+4]; out[i:i+4]=bytes((R,G,B,A))
    return Image.frombytes("RGBA",(w,h),bytes(out))
def write_bgra(source_dds,rgba,out):
    b=Path(source_dds).read_bytes(); inf=dds_info(source_dds)
    if inf["fourcc"]!="\x00\x00\x00\x00" or inf["rgb_bits"]!=32:
        raise SystemExit("FAIL writer supports exact-header uncompressed BGRA only")
    if rgba.size!=(inf["width"],inf["height"]): raise SystemExit("FAIL image/source dimensions differ")
    raw=rgba.tobytes(); bgra=bytearray(len(raw))
    for i in range(0,len(raw),4):
        R,G,B,A=raw[i:i+4]; bgra[i:i+4]=bytes((B,G,R,A))
    if len(b)!=HEADER+len(bgra): raise SystemExit("FAIL source has unsupported extra/mip payload")
    Path(out).write_bytes(b[:HEADER]+bgra)
def verify_clean_plate_qa(path,asset_id,source_sha256,clean_sha256):
    if not path: raise SystemExit("FAIL v2 requires --clean-plate-qa")
    qa=json.loads(Path(path).read_text(encoding="utf-8"))
    if qa.get("schema")!="outrun-clean-plate-qa-v1": raise SystemExit("FAIL wrong clean-plate QA schema")
    if str(qa.get("asset_id"))!=str(asset_id): raise SystemExit("FAIL clean-plate QA asset mismatch")
    if qa.get("source_sha256")!=source_sha256: raise SystemExit("FAIL clean-plate QA source SHA mismatch")
    if qa.get("clean_plate_sha256")!=clean_sha256: raise SystemExit("FAIL clean-plate QA image SHA mismatch")
    checks=qa.get("checks") or {}
    required=("no_source_text_residue","no_box_or_seam","protected_artwork_unchanged","alpha_continuity","native_resolution_review")
    bad=[k for k in required if checks.get(k) is not True]
    if bad: raise SystemExit(f"FAIL clean-plate QA missing/failed checks: {bad}")
    return qa

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dds",required=True); ap.add_argument("--source-png",required=True)
    ap.add_argument("--clean-plate",required=True); ap.add_argument("--candidate-png",required=True)
    ap.add_argument("--edit-mask",required=True,help="source glyph/effect REMOVAL mask")
    ap.add_argument("--protected-mask"); ap.add_argument("--clean-plate-qa")
    ap.add_argument("--output-dds",required=True); ap.add_argument("--report",required=True)
    ap.add_argument("--generation-id",required=True); ap.add_argument("--spec-id",required=True)
    ap.add_argument("--prompt-json",required=True)
    a=ap.parse_args()

    prompt=json.loads(Path(a.prompt_json).read_text(encoding="utf-8"))
    contract=prompt.get("contract")
    if contract not in {V1,V2}: raise SystemExit("FAIL wrong/missing strict prompt contract")
    recorded=prompt.get("prompt_sha256",""); unsigned=dict(prompt); unsigned.pop("prompt_sha256",None)
    canonical=json.dumps(unsigned,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    if recorded!=hashlib.sha256(canonical.encode()).hexdigest(): raise SystemExit("FAIL prompt JSON hash mismatch")

    source=img(a.source_png); clean=img(a.clean_plate); cand=img(a.candidate_png)
    if not(source.size==clean.size==cand.size): raise SystemExit("FAIL PNG dimensions differ")
    di=dds_info(a.source_dds)
    if source.size!=(di["width"],di["height"]): raise SystemExit("FAIL decoded source PNG != DDS dimensions")
    pa=prompt.get("asset",{})
    if pa.get("source_sha256")!=di["sha256"]: raise SystemExit("FAIL prompt source SHA does not match DDS")
    if pa.get("canvas")!=[di["width"],di["height"]]: raise SystemExit("FAIL prompt canvas does not match DDS")
    if str(pa.get("id"))!=str(a.spec_id): raise SystemExit("FAIL prompt asset id does not match --spec-id")

    elements=prompt.get("elements",[])
    for pe in elements:
        if pe.get("source_text_transform") not in {"normal","flip_x","flip_y","rotate_180","rotate_90_cw","rotate_90_ccw"}:
            raise SystemExit("FAIL unresolved/invalid source text transform")
        bv=pe.get("baseline_vector")
        if not isinstance(bv,list) or len(bv)!=2 or (float(bv[0])==0 and float(bv[1])==0):
            raise SystemExit("FAIL missing/invalid source baseline vector")
        if not isinstance(pe.get("style_traits"),dict) or not pe["style_traits"]: raise SystemExit("FAIL missing source letterform style traits")
        if pe.get("slant_direction") not in {"left","none","right"}: raise SystemExit("FAIL missing/invalid signed slant direction")
        if not isinstance(pe.get("slant_dx_per_dy"),(int,float)) or not isinstance(pe.get("slant_angle_deg"),(int,float)):
            raise SystemExit("FAIL missing signed slant measurements")
        if not pe.get("display_transform"): raise SystemExit("FAIL missing display transform for slant/orientation QA")

    decoded=decode_uncompressed(a.source_dds)
    if ImageChops.difference(decoded,source).getbbox(): raise SystemExit("FAIL source PNG is not exact DDS decode")

    removal=binmask(a.edit_mask,source.size)
    protected=binmask(a.protected_mask,source.size) if a.protected_mask else None
    cleanchg=diffmask(source,clean)
    cleanalpha=diffmask(source.getchannel("A").convert("RGBA"),clean.getchannel("A").convert("RGBA"))
    clean_outside=n(ImageChops.multiply(cleanchg,ImageChops.invert(removal)))
    clean_alpha_out=n(ImageChops.multiply(cleanalpha,ImageChops.invert(removal)))
    clean_protected=n(ImageChops.multiply(cleanchg,protected)) if protected else 0
    if clean_outside or clean_alpha_out or clean_protected:
        raise SystemExit(f"FAIL clean plate outside_removal={clean_outside} protected={clean_protected} alpha_outside={clean_alpha_out}")

    finalchg=diffmask(source,cand)
    finalalpha=diffmask(source.getchannel("A").convert("RGBA"),cand.getchannel("A").convert("RGBA"))
    v2_metrics=None; clean_qa=None

    if contract==V2:
        clean_qa=verify_clean_plate_qa(a.clean_plate_qa,a.spec_id,di["sha256"],sha(a.clean_plate))
        permitted=[list(map(int,e["permitted_region"])) for e in elements]
        lettering_regions=rect_mask(source.size,permitted)
        final_allowed=ImageChops.lighter(removal,lettering_regions)
        effective_protected=ImageChops.multiply(protected,ImageChops.invert(lettering_regions)) if protected else None

        final_out=n(ImageChops.multiply(finalchg,ImageChops.invert(final_allowed)))
        final_prot=n(ImageChops.multiply(finalchg,effective_protected)) if effective_protected else 0
        final_alpha_out=n(ImageChops.multiply(finalalpha,ImageChops.invert(final_allowed)))
        letteringchg=diffmask(clean,cand)
        letteringalpha=diffmask(clean.getchannel("A").convert("RGBA"),cand.getchannel("A").convert("RGBA"))
        lettering_out=n(ImageChops.multiply(letteringchg,ImageChops.invert(lettering_regions)))
        lettering_alpha_out=n(ImageChops.multiply(letteringalpha,ImageChops.invert(lettering_regions)))
        if final_out or final_prot or final_alpha_out or lettering_out or lettering_alpha_out:
            raise SystemExit(
                f"FAIL v2 stage isolation final_outside={final_out} protected={final_prot} "
                f"final_alpha_outside={final_alpha_out} lettering_outside={lettering_out} lettering_alpha_outside={lettering_alpha_out}"
            )

        rows=[]
        for e in elements:
            permitted_rect=list(map(int,e["permitted_region"]))
            safe=list(map(int,e["candidate_safe_bbox"]))
            bb=crop_bbox(letteringchg,permitted_rect)
            if bb is None: raise SystemExit(f"FAIL no Korean/effect pixels detected for {e.get('element_id')}")
            if not contained(bb,safe):
                raise SystemExit(f"FAIL safety-inset containment {e.get('element_id')} candidate={bb} safe={safe}")
            rows.append({
                "element_id":e.get("element_id"),"source_text":e.get("source_text"),"approved_korean":e.get("approved_korean"),
                "source_bbox":e.get("source_bbox"),"permitted_region":permitted_rect,"candidate_safe_bbox":safe,
                "candidate_effect_bbox":bb,"safety_inset_px":e.get("safety_inset_px"),
                "safe_margins_ltrb":[bb[0]-safe[0],bb[1]-safe[1],safe[2]-bb[2],safe[3]-bb[3]],"containment":"PASS"
            })
        v2_metrics={
            "clean_plate_changed_pixels":n(cleanchg),
            "clean_plate_changed_outside_removal_mask":clean_outside,
            "clean_plate_alpha_changed_outside_removal_mask":clean_alpha_out,
            "clean_plate_changed_in_protected_mask":clean_protected,
            "final_changed_outside_removal_or_lettering_regions":final_out,
            "final_changed_in_effective_protected_mask":final_prot,
            "final_alpha_changed_outside_approved_regions":final_alpha_out,
            "lettering_changed_outside_permitted_regions":lettering_out,
            "lettering_alpha_changed_outside_permitted_regions":lettering_alpha_out,
            "elements":rows,
        }
    else:
        outside=n(ImageChops.multiply(finalchg,ImageChops.invert(removal)))
        prot=n(ImageChops.multiply(finalchg,protected)) if protected else 0
        alphaout=n(ImageChops.multiply(finalalpha,ImageChops.invert(removal)))
        if outside or prot or alphaout: raise SystemExit(f"FAIL containment outside={outside} protected={prot} alpha_outside={alphaout}")

    write_bgra(a.source_dds,cand,a.output_dds)
    roundtrip=decode_uncompressed(a.output_dds)
    if ImageChops.difference(roundtrip,cand).getbbox(): raise SystemExit("FAIL final DDS round-trip differs from candidate PNG")
    odi=dds_info(a.output_dds)
    if odi["header_sha256"]!=di["header_sha256"]: raise SystemExit("FAIL DDS header changed")

    report={
        "schema":"outrun-korean-clean-generation-v2" if contract==V2 else "outrun-korean-clean-generation-v1",
        "status":"PASS","generation_id":a.generation_id,"spec_id":a.spec_id,"asset_id":a.spec_id,
        "source_dds":a.source_dds,"source_sha256":di["sha256"],"source_png_sha256":sha(a.source_png),
        "clean_plate_sha256":sha(a.clean_plate),"prompt_contract":contract,"prompt_sha256":recorded,
        "prompt_json_sha256":sha(a.prompt_json),"orientation_gate":"PASS_INPUT_PROVENANCE",
        "style_generation_gate":"PASS_FINAL_MEASURED_BBOX" if contract==V2 else "PASS_INPUT_PROVENANCE",
        "signed_slant_gate":"PASS","edit_mask_sha256":sha(a.edit_mask),
        "protected_mask_sha256":sha(a.protected_mask) if a.protected_mask else None,
        "candidate_png_sha256":sha(a.candidate_png),"candidate_dds_sha256":odi["sha256"],
        "width":di["width"],"height":di["height"],"mip_count":di["mips"],"fourcc":di["fourcc"],
        "clean_plate_changed_pixels":n(cleanchg),"changed_pixels":n(finalchg),
        "dds_header_preserved":True,"dds_roundtrip_pixel_exact":True,
        "v2_stage_metrics":v2_metrics,
        "clean_plate_qa_sha256":sha(a.clean_plate_qa) if a.clean_plate_qa else None,
        "clean_plate_qa":clean_qa,"runtime_validation":"UNTESTED",
    }
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
