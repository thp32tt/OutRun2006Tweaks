#!/usr/bin/env python3
# C234 / TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
# Post-approval PRE_INGAME English-original comparison refresh.
import os, runpy
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
runpy.run_path("tools/localization/export_c_pass_comparison.py", run_name="__main__")
