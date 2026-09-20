#!/usr/bin/env python3
"""Fail-before/pass-after verifier for R33 XYZRHW dispatch and R30 SkyGlow.

The default mode proves the two current integration gaps.  ``--require-fixed``
is intended for an isolated B candidate and fails until both contracts are fixed.
It is source-flow evidence only; visual correctness remains an HMD gate.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


DRAW_CONTRACTS = {
    "DrawPrimitiveDestR33": "R30TryXyzrhwPrimitiveVB",
    "DrawIndexedPrimitiveDestR33": "R30TryXyzrhwIndexedPrimitiveVB",
    "DrawPrimitiveUPDestR33": "R30TryXyzrhwPrimitiveUP",
    "DrawIndexedPrimitiveUPDestR33": "R30TryXyzrhwIndexedPrimitiveUP",
}


def git_text(repo: Path, ref: str, rel: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{rel}"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode("utf-8")


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", text, re.S)
    if not match:
        raise AssertionError(f"function not found: {name}")
    opening = text.find("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def dispatch_state(r33: str) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for function, helper in DRAW_CONTRACTS.items():
        body = function_body(r33, function)
        helper_pos = body.find(helper)
        dispatch_pos = body.find("R33Dispatch")
        handled_return = re.search(
            r"if\s*\(\s*\w+\s*!=\s*E_NOTIMPL\s*\)\s*return\s+\w+\s*;",
            body,
            re.S,
        )
        result[function] = (
            helper_pos >= 0
            and dispatch_pos >= 0
            and helper_pos < dispatch_pos
            and handled_return is not None
            and "DestR30" not in body
        )
    return result


def skyglow_state(r30: str) -> dict[str, bool]:
    body = function_body(r30, "R30ApplyStereoSkyGlow")
    compact = normalized(body)
    current_one_step = bool(re.search(
        r"IDirect3DTexture9\s*\*\s*compositeSource\s*=\s*R30SkyGlow\.temp\[eye\]", compact
    ))
    current_two_step = bool(re.search(
        r"if\s*\(effectiveTwoStep\).*?compositeSource\s*=\s*R30SkyGlow\.reduced\[eye\]",
        compact,
    ))
    fixed_one_step = bool(re.search(
        r"IDirect3DTexture9\s*\*\s*compositeSource\s*=\s*R30SkyGlow\.reduced\[eye\]", compact
    ))
    fixed_two_step = bool(re.search(
        r"if\s*\(effectiveTwoStep\).*?compositeSource\s*=\s*R30SkyGlow\.temp\[eye\]",
        compact,
    ))
    return {
        "currentOneStepUsesPreBlurTemp": current_one_step,
        "currentTwoStepUsesHorizontalReduced": current_two_step,
        "fixedOneStepUsesHorizontalReduced": fixed_one_step,
        "fixedTwoStepUsesVerticalTemp": fixed_two_step,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ref", required=True)
    parser.add_argument("--require-fixed", action="store_true")
    args = parser.parse_args()

    r33 = git_text(args.repo, args.ref, "src/vr/d3d9/stereo_renderer_r33.cpp")
    r30 = git_text(args.repo, args.ref, "src/vr/d3d9/stereo_renderer_r30.cpp")
    dispatch = dispatch_state(r33)
    skyglow = skyglow_state(r30)

    if args.require_fixed:
        if not all(dispatch.values()):
            missing = [name for name, fixed in dispatch.items() if not fixed]
            raise AssertionError(f"R33 XYZRHW pre-dispatch missing/unsafe: {missing}")
        if not (
            skyglow["fixedOneStepUsesHorizontalReduced"]
            and skyglow["fixedTwoStepUsesVerticalTemp"]
            and not skyglow["currentOneStepUsesPreBlurTemp"]
            and not skyglow["currentTwoStepUsesHorizontalReduced"]
        ):
            raise AssertionError(f"SkyGlow composite flow not fixed: {skyglow}")
        mode = "fixed-contract-pass"
    else:
        if any(dispatch.values()):
            raise AssertionError("integration is no longer a clean XYZRHW fail-before baseline")
        if not (
            skyglow["currentOneStepUsesPreBlurTemp"]
            and skyglow["currentTwoStepUsesHorizontalReduced"]
        ):
            raise AssertionError(f"integration SkyGlow fail-before signature changed: {skyglow}")
        mode = "fail-before-confirmed"

    print(json.dumps({
        "ref": args.ref,
        "mode": mode,
        "r33XyzrhwPreDispatch": dispatch,
        "skyGlow": skyglow,
        "runtimeClaim": "not-tested",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"DX9Ex dispatch/SkyGlow validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
