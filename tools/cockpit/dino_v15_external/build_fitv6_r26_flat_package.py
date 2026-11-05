#!/usr/bin/env python3
"""Build a flat, copy-and-run FitV6 R26 test ZIP.

The archive must contain files at ZIP root so extracting it directly into the
folder containing OR2006C2C.EXE requires no installer and no nested directory.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

REQUIRED = (
    "Dino246_Cockpit_LHD_v15.ovc",
    "OutRun2006Tweaks.ini",
    "OutRun2006Tweaks.lods.ini",
    "RUN_DX9EX_TEST.cmd",
    "Run-DX9ExFocusTest.ps1",
    "dinput8.dll",
    "outrun-vr-host.exe",
)
FORBIDDEN = ("OR2006C2C.EXE",)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--runner", type=Path, default=Path(__file__).with_name("RUN-FITV6-R26.cmd"))
    args = ap.parse_args()

    staging = args.staging.resolve()
    out = args.out.resolve()
    missing = [name for name in REQUIRED if not (staging / name).is_file()]
    if missing:
        raise SystemExit("Missing required staging files: " + ", ".join(missing))
    forbidden = [name for name in FORBIDDEN if (staging / name).exists()]
    if forbidden:
        raise SystemExit("Refusing to package original game files: " + ", ".join(forbidden))
    if not args.runner.is_file():
        raise SystemExit(f"Runner not found: {args.runner}")

    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in staging.iterdir() if p.is_file())
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, arcname=p.name)
        z.write(args.runner, arcname="01-RUN-FITV6-R26.cmd")

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        nested = [n for n in names if "/" in n.rstrip("/")]
        if nested:
            raise SystemExit("Archive is not flat: " + ", ".join(nested))
        for name in REQUIRED + ("01-RUN-FITV6-R26.cmd",):
            if name not in names:
                raise SystemExit(f"Archive missing required root file: {name}")
        if any(name.upper().endswith("OR2006C2C.EXE") for name in names):
            raise SystemExit("Archive unexpectedly contains OR2006C2C.EXE")

    print(f"FITV6_R26_FLAT_PACKAGE_PASS path={out}")
    print(f"sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
