#!/usr/bin/env python3
"""Build the mandatory v2 asset-specific first-pass localization prompt."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

CONTRACT="outrun-first-pass-edit-v2"
DEFAULT_SAFETY_INSET_PX=2
DEFAULT_MAX_REFIT_ITERATIONS=8
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
    "alpha changes outside the approved removal/lettering regions",
    "stretched/squashed/clipped text or text escaping the measured safe bbox",
    "shrinking or resampling a flattened rendered text raster to make it fit",
    "single-pass production without native-resolution effect-inclusive bbox measurement",
]

def req(obj,key):
    if key not in obj or obj[key] in (None,"",[]):
        raise SystemExit(f"missing required prompt spec: {key}")
    return obj[key]

def rect(value,name,canvas):
    if not isinstance(value,list) or len(value)!=4:
        raise SystemExit(f"{name} must be [left,top,right,bottom]")
    try:
        r=[int(v) for v in value]
    except Exception as exc:
        raise SystemExit(f"{name} contains a non-integer coordinate") from exc
    l,t,rr,b=r; w,h=canvas
    if not (0<=l<rr<=w and 0<=t<b<=h):
        raise SystemExit(f"{name} out of canvas or empty: {r} canvas={canvas}")
    return r

def inset_rect(r,px):
    return [r[0]+px,r[1]+px,r[2]-px,r[3]-px]

def intersect(a,b):
    r=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    return None if r[0]>=r[2] or r[1]>=r[3] else r

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("spec_json")
    ap.add_argument("output_prompt_json")
    args=ap.parse_args()
    spec=json.loads(Path(args.spec_json).read_text(encoding="utf-8"))
    for key in ("asset_id","source_path","source_sha256","width","height","raw_orientation","background_class","elements","protected_regions"):
        req(spec,key)
    canvas=[int(spec["width"]),int(spec["height"])]
    default_inset=int(spec.get("default_safety_inset_px",DEFAULT_SAFETY_INSET_PX))
    if default_inset<1:
        raise SystemExit("v2 requires default_safety_inset_px >= 1")
    max_refit=int(spec.get("max_refit_iterations",DEFAULT_MAX_REFIT_ITERATIONS))
    if max_refit<1:
        raise SystemExit("max_refit_iterations must be >= 1")

    elements=[]
    for idx,e in enumerate(spec["elements"]):
        for key in ("source_text","korean","source_bbox","permitted_region","alignment","text_height_px","line_count","colors","effects","source_text_transform","baseline_vector","style_traits","slant_dx_per_dy","slant_angle_deg","slant_direction","display_transform"):
            req(e,key)
        source_bbox=rect(e["source_bbox"],f"elements[{idx}].source_bbox",canvas)
        permitted=rect(e["permitted_region"],f"elements[{idx}].permitted_region",canvas)
        safety=int(e.get("safety_inset_px",default_inset))
        if safety<1:
            raise SystemExit(f"elements[{idx}].safety_inset_px must be >= 1 for v2")
        safe_bbox=intersect(inset_rect(source_bbox,safety),inset_rect(permitted,safety))
        if safe_bbox is None:
            raise SystemExit(
                f"elements[{idx}] has no safe bbox after {safety}px inset; "
                "explicitly use 1px if justified, otherwise manual reconstruction is required"
            )
        background=str(spec["background_class"]).lower()
        lettering_method="DETERMINISTIC_REQUIRED" if ("transparent" in background or "text-only" in background) else "DETERMINISTIC_PREFERRED"
        elements.append({
            "element_id":str(e.get("element_id") or f"element_{idx:03d}"),
            "source_text":e["source_text"],
            "approved_korean":e["korean"],
            "source_bbox":source_bbox,
            "permitted_region":permitted,
            "safety_inset_px":safety,
            "candidate_safe_bbox":safe_bbox,
            "alignment":e["alignment"],
            "text_height_px":e["text_height_px"],
            "line_count":e["line_count"],
            "colors":e["colors"],
            "effects":e["effects"],
            "source_text_transform":e["source_text_transform"],
            "baseline_vector":e["baseline_vector"],
            "style_traits":e["style_traits"],
            "slant_dx_per_dy":e["slant_dx_per_dy"],
            "slant_angle_deg":e["slant_angle_deg"],
            "slant_direction":e["slant_direction"],
            "display_transform":e["display_transform"],
            "lettering_method":lettering_method,
            "measurement_basis":"native-resolution RGBA bbox of Korean lettering/effects relative to the approved CLEAN_PLATE; include fill, outline, shadow, glow and antialias fringe",
            "refit_policy":{
                "max_iterations":max_refit,
                "success_condition":"effect-inclusive candidate bbox is fully inside candidate_safe_bbox",
                "iteration_order":[
                    "render from glyph/effect parameters at measured source text height",
                    "measure the native-resolution effect-inclusive bbox",
                    "translate inward when the only failure is positional",
                    "if oversized, reduce font/effect geometry uniformly and re-render from source parameters",
                    "re-measure after every render",
                    "use approved shorter Korean wording only after source-faithful spacing/line break/size attempts",
                ],
                "never":"resize or resample a flattened lettering raster to force containment",
            },
        })

    prompt={
        "contract":CONTRACT,
        "contract_version":2,
        "priority":[
            "CONTAINMENT BEFORE STYLE: a production candidate must first fit inside the measured safety-inset bbox.",
            "EDIT, DO NOT REDESIGN. Treat the exact HD source as authoritative.",
            "Stage 1 is CLEAN_PLATE only: remove the complete source glyph/effect footprint and validate reconstruction before any Korean exists.",
            "Stage 2 starts only from the approved CLEAN_PLATE and adds only approved Korean lettering/effects.",
            "Measure every rendered Korean/effect bbox at native resolution and refit until it is inside candidate_safe_bbox.",
            "Preserve everything outside the approved source-removal mask and Korean permitted regions.",
            "Use exactly the proven raw-coordinate transform, baseline direction and signed slant.",
            "Within the safe bbox, match measured source typography/effects as closely as Korean geometry permits.",
            "If clean reconstruction or safe fitting cannot be proven, emit no production candidate and flag MANUAL_RECONSTRUCTION_REQUIRED.",
        ],
        "asset":{
            "id":spec["asset_id"],"source_path":spec["source_path"],"source_sha256":spec["source_sha256"],
            "canvas":canvas,"raw_orientation":spec["raw_orientation"],"background_class":spec["background_class"],
            "alpha_behavior":spec.get("alpha_behavior","preserve exact source behavior"),
        },
        "stage_order":[
            {"stage":"CLEAN_PLATE","input":"exact English HD source","rules":[
                "change only the complete source glyph/effect removal mask",
                "no Korean lettering is allowed in this stage",
                "validate no source-text residue, box/seam, protected-artwork damage or alpha discontinuity",
                "retain the clean plate as independent QA evidence",
            ]},
            {"stage":"KOREAN_LETTERING","input":"approved CLEAN_PLATE","rules":[
                "add only approved Korean strings and source-faithful effects",
                "never modify the clean background to make Korean fit",
                "transparent/text-only assets require deterministic lettering",
            ]},
            {"stage":"MEASURE_REFIT","rules":[
                "measure native-resolution effect-inclusive bbox after every render",
                "require the configured safety inset on all four sides",
                "translate/re-render smaller instead of resampling flattened text",
                f"stop after at most {max_refit} attempts and return MANUAL_RECONSTRUCTION_REQUIRED",
            ]},
            {"stage":"FINAL_VALIDATE","rules":[
                "zero source-removal changes outside removal mask",
                "zero Korean changes outside permitted lettering regions",
                "zero protected-artwork changes",
                "zero alpha changes outside approved regions",
                "exact DDS dimensions/header/format/mipmap policy",
                "ENGLISH SOURCE vs KOREAN CANDIDATE comparison at identical crop/orientation/scale",
            ]},
        ],
        "elements":elements,
        "protected_regions":spec["protected_regions"],
        "background_instruction":spec.get("background_instruction","Reconstruct only masked source-text pixels from exact neighboring/source structure; no covering panel."),
        "fit_order":[
            "measured safety-inset containment",
            "source-faithful tracking/spacing",
            "source-faithful line break",
            "uniform font/effect geometry reduction with fresh re-render",
            "approved shorter translation only",
        ],
        "style_fit_order":["source-like Korean-capable font","measured affine slant/width adjustment","source-faithful effects","custom/redrawn Korean lettering"],
        "forbidden":NEG,
        "orientation_preflight":"Prove raw source transform, display transform, baseline vector and signed slant before CLEAN_PLATE or lettering.",
        "pre_output_check":[
            "clean plate passed independently before Korean lettering",
            "no source-language text/effect residue",
            "no cover box, patch, seam or invented panel",
            "protected artwork unchanged",
            "each effect-inclusive Korean bbox is inside candidate_safe_bbox with the recorded safety inset",
            "canvas, raw orientation and transparency unchanged",
            "Korean baseline/direction exactly follows source_text_transform",
            "displayed Korean slant sign matches source slant_direction and measured signed angle",
            "style was fitted only after containment; no flattened-raster shrink/resample",
        ],
        "failure_behavior":"Do not produce a production DDS; flag MANUAL_RECONSTRUCTION_REQUIRED.",
    }
    canonical=json.dumps(prompt,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    prompt["prompt_sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    Path(args.output_prompt_json).write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(prompt["prompt_sha256"])

if __name__=="__main__":
    main()
