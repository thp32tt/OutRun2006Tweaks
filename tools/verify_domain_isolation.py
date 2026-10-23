#!/usr/bin/env python3
"""Fail CI when VR, localization and FFB branches cross-contaminate source."""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

BRANCH_DOMAIN = {
    "vr-d3d9ex-focus": "VR",
    "korean-localization-prototype": "LOCALIZATION",
    "ffb-arcade-dd-research": "FFB",
}

OWNED_PATTERNS = {
    "VR": [
        "src/vr/**",
        "src/vr_shared.hpp",
        "VR_OPENXR.md",
        "docs/VR_*",
        "tools/*VR*",
        "tools/vr_*",
        ".github/workflows/vr-*",
    ],
    "LOCALIZATION": [
        "localization/**",
        "tools/localization/**",
        "src/hooks_localization.cpp",
        "docs/KOREAN_LOCALIZATION.md",
        ".github/workflows/localization-*",
    ],
    "FFB": [
        "WHEEL_FFB.md",
        "docs/FFB_STANDALONE_BRANCH.md",
        "docs/reverse/C2C_STAGE_FFB_MAP.md",
        "docs/reverse/LINDBERGH_FFB_MAP.md",
        "docs/reverse/PS2_FFB_MAP.md",
        "reverse/ps2/**",
        "src/hooks_wheel_ffb.cpp",
        "src/hooks_wheel_ffb_build.cpp",
        "src/hooks_wheel_r3_device_autoselect.hpp",
        "src/hooks_wheel_vehicle_dynamics.hpp",
        "src/wheel_ffb_math.hpp",
        "src/wheel_profile_store.hpp",
        "src/overlay/wheel_setup_ui.cpp",
        "tools/test_wheel_ffb_current.cpp",
        "tools/verify_ffb_standalone_scope.py",
        "tools/verify_wheel_ffb_current.py",
        "tools/reverse/ps2/**",
        ".github/workflows/release-wheel-*",
    ],
}

SHARED_PREFIX = "docs/shared-knowledge/"
SHARED_EXTENSIONS = {".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml"}


def git(*args: str) -> str:
    p = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.stdout.strip()


def domain_at(commit: str) -> str | None:
    p = subprocess.run(
        ["git", "show", f"{commit}:.project-domain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if p.returncode != 0:
        return None
    value = p.stdout.strip().upper()
    return value if value in {"VR", "LOCALIZATION", "FFB"} else None


def owner_for(path: str) -> str | None:
    for owner, patterns in OWNED_PATTERNS.items():
        if any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
            return owner
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--branch", required=True)
    args = ap.parse_args()

    branch = args.branch.removeprefix("refs/heads/")
    expected = BRANCH_DOMAIN.get(branch)
    if expected is None:
        print(f"domain-isolation: branch {branch!r} is not protected; nothing to do")
        return 0

    marker = Path(".project-domain")
    if not marker.exists():
        print("ERROR: .project-domain is missing", file=sys.stderr)
        return 1

    actual = marker.read_text(encoding="utf-8").strip().upper()
    errors: list[str] = []
    if actual != expected:
        errors.append(f"branch {branch} requires domain {expected}, found {actual!r}")

    base = args.base
    head = args.head
    if re.fullmatch(r"0+", base):
        base = git("rev-parse", f"{head}^")

    changed = [p for p in git("diff", "--name-only", f"{base}..{head}").splitlines() if p]

    for path in changed:
        if path.startswith(SHARED_PREFIX):
            suffix = Path(path).suffix.lower()
            if suffix not in SHARED_EXTENSIONS:
                errors.append(
                    f"shared-knowledge may contain text/data only: {path} "
                    f"(extension {suffix or '<none>'})"
                )
            continue

        owner = owner_for(path)
        if owner is not None and owner != expected:
            errors.append(
                f"foreign domain-owned path changed on {branch}: {path} "
                f"(owner={owner}, target={expected}). "
                f"Copy knowledge only into {SHARED_PREFIX}; do not merge/cherry-pick source."
            )

    commits = [c for c in git("rev-list", "--reverse", f"{base}..{head}").splitlines() if c]
    trailer_re = re.compile(r"(?mi)^Domain:\s*(VR|LOCALIZATION|FFB)\s*$")

    for commit in commits:
        parents = git("show", "-s", "--format=%P", commit).split()
        if len(parents) > 1:
            for secondary in parents[1:]:
                secondary_domain = domain_at(secondary)
                if secondary_domain is not None and secondary_domain != expected:
                    errors.append(
                        f"cross-domain merge commit forbidden: {commit[:12]} merges "
                        f"{secondary_domain} parent {secondary[:12]} into {expected}. "
                        f"Transfer selected knowledge through {SHARED_PREFIX} instead."
                    )

        message = git("show", "-s", "--format=%B", commit)
        trailer = trailer_re.search(message)
        if trailer and trailer.group(1).upper() != expected:
            errors.append(
                f"commit {commit[:12]} declares Domain: {trailer.group(1).upper()} "
                f"but target branch domain is {expected}"
            )

    if errors:
        print("DOMAIN ISOLATION FAILED", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(
        f"DOMAIN ISOLATION PASS: branch={branch} domain={expected} "
        f"changed_files={len(changed)} commits={len(commits)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
