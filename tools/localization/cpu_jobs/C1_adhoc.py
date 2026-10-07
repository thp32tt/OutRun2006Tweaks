#!/usr/bin/env python3
# C247 C1 PRE_INGAME export refresh after q43/q47/q53 exact-SHA C3 promotion.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, subprocess, sys
env=os.environ.copy()
env["OUTRUN_CPU_WORKER"]="github-actions"
env["OUTRUN_CPU_ROLE"]="C"
subprocess.run([sys.executable, "tools/localization/export_c_pass_comparison.py"], check=True, env=env)
