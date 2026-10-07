#!/usr/bin/env python3
# C249 post-pass persistent PRE_INGAME exporter refresh
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
import subprocess

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

subprocess.run(["python", "tools/localization/export_c_pass_comparison.py"], check=True)
