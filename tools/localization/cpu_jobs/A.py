from pathlib import Path
import os, runpy
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
runpy.run_path(str(Path.cwd()/"tools/localization/a144_raw_flip_qa.py"),run_name="__main__")
