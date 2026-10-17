#!/usr/bin/env python3
"""Static contract checks for DX11 dormant draw-dispatch boundary evidence.

This intentionally does not enable rendering. It verifies that the readiness
lane keeps explicit D3D11 draw dispatch names visible to the boundary analyzer.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    verifier = ROOT / "tools" / "verify_dx11_activation_boundary.py"
    if not verifier.exists():
        raise SystemExit("missing DX11 activation boundary verifier")

    required_dispatch_names = {
        "Draw",
        "DrawIndexed",
        "DrawInstanced",
        "DrawIndexedInstanced",
        "DrawInstancedIndirect",
        "DrawIndexedInstancedIndirect",
        "DrawAuto",
    }

    spec = importlib.util.spec_from_file_location("dx11_activation_boundary", verifier)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load DX11 activation boundary verifier")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    samples = [
        "context->Draw(1, 0)",
        "context->DrawIndexed(1, 0, 0)",
        "context->DrawInstanced(1, 1, 0, 0)",
        "context->DrawIndexedInstanced(1, 1, 0, 0, 0)",
        "context->DrawInstancedIndirect(args, 0)",
        "context->DrawIndexedInstancedIndirect(args, 0)",
        "context->DrawAuto()",
    ]

    missing = [name for name, sample in zip(required_dispatch_names, samples) if not module.DRAW_DISPATCH.search(sample)]
    if missing:
        raise SystemExit("DX11 draw signature coverage missing: " + ", ".join(missing))

    print("DX11 draw dispatch signature contract: OK")


if __name__ == "__main__":
    main()
