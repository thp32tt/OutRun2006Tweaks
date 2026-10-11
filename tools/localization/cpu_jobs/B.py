#!/usr/bin/env python3
"""B368 P3: compose source-conditioned face/rim/extrusion/highlight over approved CLEAN, saved DDS trial only."""
import os,runpy
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
runpy.run_path("tools/localization/recipes/B368_q060_separated_metal_material.py",run_name="__main__")
