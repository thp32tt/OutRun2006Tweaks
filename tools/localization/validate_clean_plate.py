#!/usr/bin/env python3
"""Fail-closed clean-plate/final-candidate QA for localized RGBA images.

This validator does not decide which pixels are English. It enforces edit-mask
containment and detects common patch artifacts. Source/candidate/clean-plate
images must be decoded to identical RGBA PNGs before validation.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

def rgba(path):
    return Image.open(path).convert("RGBA")

def mask(path, size):
    m=Image.open(path).convert("L")
    if m.size != size: raise SystemExit(f"mask size {m.size} != source {size}")
    return m.point(lambda p: 255 if p else 0)

def changed_mask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for band in bands[1:]: m=ImageChops.lighter(m,band)
    return m.point(lambda p:255 if p else 0)

def count(m): return sum(1 for p in m.getdata() if p)

def main():
    ap=argparse.ArgumentParser(description="Validate clean-plate/candidate edits against exact source and permitted mask.")
    ap.add_argument("source_png"); ap.add_argument("candidate_png"); ap.add_argument("edit_mask_png")
    ap.add_argument("--protected-mask")
    ap.add_argument("--baseline-candidate", help="Previous decoded candidate for rework blast-radius QA")
    ap.add_argument("--rework-mask", help="Mask of pixels intentionally allowed to change vs --baseline-candidate")
    ap.add_argument("--report", required=True)
    args=ap.parse_args()
    if bool(args.baseline_candidate) != bool(args.rework_mask):
        raise SystemExit("FAIL: --baseline-candidate and --rework-mask must be provided together")
    s,c=rgba(args.source_png),rgba(args.candidate_png)
    if s.size!=c.size: raise SystemExit("FAIL: candidate dimensions differ from source")
    allowed=mask(args.edit_mask_png,s.size)
    changed=changed_mask(s,c)
    outside=ImageChops.multiply(changed,ImageChops.invert(allowed))
    outside_n=count(outside)
    protected_n=0
    if args.protected_mask:
        protected=mask(args.protected_mask,s.size)
        protected_n=count(ImageChops.multiply(changed,protected))
    sa,ca=s.getchannel("A"),c.getchannel("A")
    alpha_changed=changed_mask(sa.convert("RGBA"),ca.convert("RGBA"))
    alpha_outside=count(ImageChops.multiply(alpha_changed,ImageChops.invert(allowed)))
    bbox=changed.getbbox()
    blast_changed_n=0
    blast_outside_n=0
    blast_bbox=None
    if args.baseline_candidate:
        baseline=rgba(args.baseline_candidate)
        if baseline.size != s.size:
            raise SystemExit("FAIL: baseline candidate dimensions differ from source")
        rework=mask(args.rework_mask,s.size)
        blast_changed=changed_mask(baseline,c)
        blast_outside=ImageChops.multiply(blast_changed,ImageChops.invert(rework))
        blast_changed_n=count(blast_changed)
        blast_outside_n=count(blast_outside)
        blast_bbox=blast_changed.getbbox()
    report={"source":args.source_png,"candidate":args.candidate_png,"size":list(s.size),
      "changed_pixels":count(changed),"changed_bbox":bbox,"changed_pixels_outside_edit_mask":outside_n,
      "changed_pixels_in_protected_mask":protected_n,"alpha_changed_outside_edit_mask":alpha_outside,
      "baseline_candidate":args.baseline_candidate,"rework_mask":args.rework_mask,
      "rework_changed_pixels":blast_changed_n,"rework_changed_bbox":blast_bbox,
      "rework_changed_pixels_outside_mask":blast_outside_n,
      "status":"PASS" if outside_n==0 and protected_n==0 and alpha_outside==0 and blast_outside_n==0 else "REWORK_REQUIRED"}
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if report["status"]!="PASS": raise SystemExit(2)
if __name__=="__main__": main()
