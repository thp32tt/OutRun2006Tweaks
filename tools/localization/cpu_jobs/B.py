#!/usr/bin/env python3
"""B369 q060 P3 source-derived palette, heavy native contour, separated material layers; unpromoted DDS."""
import os,runpy,sys
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
sys.dont_write_bytecode=True
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
runpy.run_path("tools/localization/recipes/B369_q060_source_condensed_metal_p3.py",run_name="__main__")
