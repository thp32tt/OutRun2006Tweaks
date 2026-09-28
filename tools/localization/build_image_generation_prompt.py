#!/usr/bin/env python3
"""Build a strict, asset-specific image-edit prompt for first-pass localization."""
import argparse, hashlib, json
from pathlib import Path

NEG=[
"Korean text over visible English/source text",
"black/white/gray/colored/semitransparent cover rectangles or backing boxes",
"new panels, plaques, ribbons, labels or invented backing shapes",
"blur, smudge or flat patches used to conceal source text",
"any source glyph, outline, shadow, glow or antialias residue",
"changes to protected icons, logos, borders, separators, neighboring sprites or unrelated text",
"redesign, recolor, recomposition, crop, padding, resize or aspect-ratio change",
"invented background replacing the exact source artwork",
"missing-glyph boxes, fallback-font mixing or hallucinated words/icons",
"new readability outlines/shadows/glows absent from the source",
"low-resolution reconstruction followed by upscale",
"alpha changes outside the permitted edit region",
"stretched/squashed/clipped text or text escaping the permitted region",
]
def req(o,k):
    if k not in o or o[k] in (None,"",[]): raise SystemExit(f"missing required prompt spec: {k}")
    return o[k]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("spec_json"); ap.add_argument("output_prompt_json")
    a=ap.parse_args(); s=json.loads(Path(a.spec_json).read_text(encoding="utf-8"))
    for k in ("asset_id","source_path","source_sha256","width","height","raw_orientation","background_class","elements","protected_regions"):
        req(s,k)
    els=[]
    for e in s["elements"]:
        for k in ("source_text","korean","source_bbox","permitted_region","alignment","text_height_px","line_count","colors","effects","source_text_transform","baseline_vector","style_traits"):
            req(e,k)
        els.append({
          "source_text":e["source_text"],"approved_korean":e["korean"],"source_bbox":e["source_bbox"],
          "permitted_region":e["permitted_region"],"alignment":e["alignment"],"text_height_px":e["text_height_px"],
          "line_count":e["line_count"],"colors":e["colors"],"effects":e["effects"],\n          "source_text_transform":e["source_text_transform"],"baseline_vector":e["baseline_vector"],\n          "style_traits":e["style_traits"]})
    prompt={
      "contract":"outrun-first-pass-edit-v1",
      "priority":[
       "EDIT, DO NOT REDESIGN. Treat the exact HD source as authoritative.",
       "Preserve everything outside the specified source-text/effect footprints.",
       "Completely remove each specified source text plus its own outline/shadow/glow/antialias fringe.",
       "Reconstruct the exposed background as a seamless continuation of the exact surrounding source.",
       "Render only the approved Korean strings in the cleared regions.",
       "Match measured source typography, alignment, slant, width, weight, corner character and effects as closely as Korean geometry permits.",\n       "Use exactly the proven raw-coordinate source text transform and baseline direction; never assume the game will correct an upright render.",
       "If faithful reconstruction or fitting is uncertain, emit no production candidate and flag manual reconstruction."
      ],
      "asset":{"id":s["asset_id"],"source_path":s["source_path"],"source_sha256":s["source_sha256"],
               "canvas":[s["width"],s["height"]],"raw_orientation":s["raw_orientation"],
               "background_class":s["background_class"],"alpha_behavior":s.get("alpha_behavior","preserve exact source behavior")},
      "elements":els,"protected_regions":s["protected_regions"],
      "background_instruction":s.get("background_instruction",
        "Reconstruct only masked source-text pixels from exact neighboring/source structure; no covering panel."),
      "fit_order":["source-faithful spacing","source-faithful line break","modest font-size reduction","approved shorter translation only"],
      "forbidden":NEG,
      "orientation_preflight":"Prove raw source transform and baseline vector before production rendering; unresolved orientation blocks generation.",\n      "style_fit_order":["source-like Korean-capable font","measured affine slant/width adjustment","source-faithful effects","custom/redrawn Korean lettering"],\n      "pre_output_check":[
       "no source-language text/effect residue",
       "no cover box, patch, seam or invented panel",
       "protected artwork unchanged",
       "Korean fully inside permitted region and unclipped",
       "canvas, raw orientation and transparency unchanged",\n       "Korean baseline/direction exactly follows source_text_transform",\n       "slant/width/weight/corners/outline/shadow materially match source style"
      ],
      "failure_behavior":"Do not produce a production candidate; flag MANUAL_RECONSTRUCTION_REQUIRED."
    }
    canonical=json.dumps(prompt,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    prompt["prompt_sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    Path(a.output_prompt_json).write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(prompt["prompt_sha256"])
if __name__=="__main__": main()
