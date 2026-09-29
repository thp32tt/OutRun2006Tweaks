#!/usr/bin/env python3
"""Prepare strict text-only Korean generation inputs for queue index 89 / 43B07A77."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"KOREAN_PNG_REVIEW/43B07A77"
METRICS=OUT/"preflight_metrics.json"
SOURCE=OUT/"source_display.png"

def main():
    m=json.loads(METRICS.read_text(encoding="utf-8"))
    if m.get("asset_id")!="43B07A77": raise SystemExit("wrong asset metrics")
    if m.get("source_git_blob_sha")!="ca95f45529f841405c89bf0c00be25abcc0b5802": raise SystemExit("source blob drift")
    if m.get("source_sha256")!="906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175": raise SystemExit("source SHA drift")
    if m.get("display_transform")!="flip_y" or m.get("orientation_status")!="PASS_EXPLICIT_DISPLAY_TRANSFORM":
        raise SystemExit("orientation unresolved")
    sl=m.get("signed_slant",{})
    if m.get("signed_slant_status")!="PASS_MEASURED_IN_READABLE_DISPLAY_COORDINATES":
        raise SystemExit("signed slant unresolved")
    if sl.get("slant_direction")!="right" or float(sl.get("slant_dx_per_dy",0))<=0:
        raise SystemExit("unexpected source slant sign")

    src=Image.open(SOURCE).convert("RGBA")
    if src.size!=(2048,256): raise SystemExit("source display canvas drift")
    alpha=src.getchannel("A")
    # Exact full source text/effect mask, including the source's 3px fringe below
    # the atlas cell. Korean candidate pixels remain constrained to the cell.
    edit=alpha.point(lambda v:255 if v>0 else 0)
    protected=edit.point(lambda v:0 if v else 255)

    clean=src.copy()
    cp=clean.load(); mp=edit.load()
    for y in range(clean.height):
        for x in range(clean.width):
            if mp[x,y]:
                cp[x,y]=(0,0,0,0)

    clean.save(OUT/"clean_plate_display.png",optimize=True)
    edit.save(OUT/"edit_mask.png",optimize=True)
    protected.save(OUT/"protected_mask.png",optimize=True)

    cell=m["cell"]
    source_full_bbox=[1,13,1494,251]  # exact canvas bbox after flip_y from raw [1,5,1494,243]
    candidate_region=[1,13,1494,248] # intersection with display atlas cell [0,0,1496,248]
    spec={
      "asset_id":"43B07A77",
      "source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
      "source_sha256":m["source_sha256"],
      "width":2048,"height":256,
      "raw_orientation":"raw DDS requires flip_y for readable/game display orientation",
      "background_class":"transparent text-only atlas; preserve all unmasked source bytes",
      "alpha_behavior":"erase source English/effect mask exactly; Korean may introduce alpha only inside permitted_region; zero alpha changes outside edit mask",
      "background_instruction":"No invented panel or fill. The clean plate is exact source_display with only nonzero-alpha English/effect pixels cleared to transparent; preserve every unmasked pixel.",
      "protected_regions":[
        "all pixels outside exact source English/effect alpha mask",
        "all pixels outside display atlas cell [0,0,1496,248]",
        "transparent padding/hidden RGB outside the edit mask"
      ],
      "elements":[{
        "source_text":"Game Over",
        "korean":"게임 오버",
        "source_bbox":source_full_bbox,
        "permitted_region":candidate_region,
        "alignment":"center Korean within the original source visual span while remaining wholly inside permitted_region",
        "text_height_px":235,
        "line_count":1,
        "colors":{
          "fill":"sample exact HD source: pale cyan/white upper fill transitioning to saturated blue lower fill",
          "inner_highlight":"thin white highlight",
          "outline":"black/dark charcoal",
          "outer_effect":"muted mauve/pink outer shadow/outline"
        },
        "effects":{
          "layers":["blue-white vertical gradient fill","thin white inner highlight","dark outline","mauve outer shadow/outline"],
          "rule":"match exact source layer order/thickness/offset from source_display; no extra glow"
        },
        "source_text_transform":"flip_y",
        "baseline_vector":[1,0],
        "style_traits":{
          "weight":"heavy bold",
          "width":"wide",
          "corners":"rounded display lettering",
          "italic_geometry":"strong right slant",
          "spacing":"tight source-like",
          "source_effect_bbox":source_full_bbox,
          "candidate_boundary":"must not cross y=248 display-cell bottom even though English source fringe reaches y=251"
        },
        "slant_dx_per_dy":sl["slant_dx_per_dy"],
        "slant_angle_deg":sl["slant_angle_deg"],
        "slant_direction":sl["slant_direction"],
        "display_transform":"flip_y"
      }]
    }
    (OUT/"generation_spec.json").write_text(json.dumps(spec,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    subprocess.run([
      sys.executable,str(ROOT/"tools/localization/build_image_generation_prompt.py"),
      str(OUT/"generation_spec.json"),str(OUT/"generation_prompt.json")
    ],check=True)
    report={
      "schema_version":1,
      "asset_id":"43B07A77",
      "queue_index":89,
      "source":"Game Over",
      "korean":"게임 오버",
      "source_git_blob_sha":m["source_git_blob_sha"],
      "source_sha256":m["source_sha256"],
      "display_transform":"flip_y",
      "orientation_gate":"PASS_EXACT_HD_VISUAL_AND_RAW_PRECHECK",
      "signed_slant_gate":"PASS",
      "signed_slant":sl,
      "source_full_effect_bbox_display":source_full_bbox,
      "candidate_permitted_region_display":candidate_region,
      "source_fringe_outside_atlas_cell_px":3,
      "source_fringe_policy":"erase English source fringe as part of edit mask; do not place Korean candidate pixels below display y=247",
      "clean_plate_status":"PASS_EXACT_ALPHA_MASK_CLEAR_ONLY",
      "candidate_status":"NOT_GENERATED_YET",
      "containment_status":"HOLD_UNTIL_KOREAN_CANDIDATE",
      "runtime_validation":"UNTESTED"
    }
    (OUT/"input_qa_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
