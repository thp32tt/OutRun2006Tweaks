#!/usr/bin/env python3
"""Static regression test for the mandatory graphics generation v2 contract."""
from __future__ import annotations
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
builder=ROOT/"tools/localization/build_image_generation_prompt.py"
clean=ROOT/"tools/localization/build_clean_graphics_candidate.py"
subprocess.run([sys.executable,"-m","py_compile",str(builder),str(clean)],check=True)

spec={
 "asset_id":"TEST0001","source_path":"test/source.dds","source_sha256":"0"*64,
 "width":128,"height":64,"raw_orientation":"normal","background_class":"transparent text-only atlas",
 "protected_regions":["outside source removal mask and lettering region"],
 "elements":[{
  "element_id":"title","source_text":"TEST","korean":"테스트","source_bbox":[10,10,100,50],
  "permitted_region":[8,8,110,60],"alignment":"center","text_height_px":36,"line_count":1,
  "colors":{"fill":"white"},"effects":{"outline":"source measured"},"source_text_transform":"normal",
  "baseline_vector":[1,0],"style_traits":{"weight":"bold"},"slant_dx_per_dy":0.0,
  "slant_angle_deg":0.0,"slant_direction":"none","display_transform":"normal"
 }]
}
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td); src=td/"spec.json"; out=td/"prompt.json"
    src.write_text(json.dumps(spec,ensure_ascii=False),encoding="utf-8")
    subprocess.run([sys.executable,str(builder),str(src),str(out)],check=True)
    prompt=json.loads(out.read_text(encoding="utf-8"))
assert prompt["contract"]=="outrun-first-pass-edit-v2"
assert prompt["contract_version"]==2
assert prompt["elements"][0]["safety_inset_px"]==2
assert prompt["elements"][0]["candidate_safe_bbox"]==[12,12,98,48]
assert prompt["elements"][0]["lettering_method"]=="DETERMINISTIC_REQUIRED"
assert prompt["elements"][0]["refit_policy"]["max_iterations"]==8
assert [x["stage"] for x in prompt["stage_order"]]==["CLEAN_PLATE","KOREAN_LETTERING","MEASURE_REFIT","FINAL_VALIDATE"]
assert "CONTAINMENT BEFORE STYLE" in prompt["priority"][0]
assert "flattened rendered text raster" in "\n".join(prompt["forbidden"])
clean_text=clean.read_text(encoding="utf-8")
for needle in ("clean_outside","lettering_changed_outside_permitted_regions","candidate_safe_bbox","outrun-clean-plate-qa-v1",'V2="outrun-first-pass-edit-v2"'):
    assert needle in clean_text,needle
contract=(ROOT/"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")
policy=(ROOT/"localization/graphics/ORIENTATION_POLICY.md").read_text(encoding="utf-8")
assert "First-pass generation v2" in contract
assert "outrun-first-pass-edit-v2" in policy
print("GENERATION_CONTRACT_V2_OK")
