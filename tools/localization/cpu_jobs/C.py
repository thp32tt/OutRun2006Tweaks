#!/usr/bin/env python3
# C251 C2 PRE_INGAME refresh after q54 C3 pass
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, subprocess
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
subprocess.run(["python","tools/localization/export_c_pass_comparison.py"],check=True)
