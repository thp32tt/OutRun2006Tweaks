#!/usr/bin/env python3
# C247 C1 PRE_INGAME export refresh after q43/q47/q53 exact-SHA C3 promotion.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import subprocess, sys
subprocess.run([sys.executable, "tools/localization/export_c_pass_comparison.py"], check=True)
