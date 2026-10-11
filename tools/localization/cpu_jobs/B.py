#!/usr/bin/env python3
"""B368 stage P2 corrected digest: native q060 manual Korean stroke geometry and optical comparisons."""
import os,runpy
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
runpy.run_path("tools/localization/recipes/B368_q060_manual_racing_contours.py",run_name="__main__")
