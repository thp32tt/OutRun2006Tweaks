#!/usr/bin/env python3
# C245 C2 persistent PRE_INGAME export refresh after q26 exact-SHA C3 promotion.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, subprocess, sys
if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
subprocess.run([sys.executable, "tools/localization/export_c_pass_comparison.py"], check=True)
