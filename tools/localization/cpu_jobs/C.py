#!/usr/bin/env python3
# C pre-in-game comparison exporter: English original vs current Korean.
import runpy
from pathlib import Path
repo=Path.cwd()
runpy.run_path(str(repo/"tools/localization/export_c_pass_comparison.py"),run_name="__main__")
