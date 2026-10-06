#!/usr/bin/env python3
import runpy
from pathlib import Path
# A144 retry: first worker output exposed fallback-font tofu during controller visual QA.
runpy.run_path(str(Path.cwd()/"tools/localization/user_jpg_rework_20261006.py"),run_name="__main__")
