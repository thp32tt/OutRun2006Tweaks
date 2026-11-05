#!/usr/bin/env python3
"""R180 regression: direct DX11 color/depth staging rejects extra OM outputs.

Run exactly once per changed candidate; compiled WARP positive/negative cases
are executed separately by dx11_surface_mirror_probe in DX11 smoke.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/surface_mirror.cpp"
PROBE = ROOT / "tools/dx11_surface_mirror_probe.cpp"

def exact_contract(text: str) -> bool:
    start = text.index("bool NativeSurfaceMirror::copy_color_depth_pair_to_staging(")
    end = text.index("void NativeSurfaceMirror::observe_device_reset()", start)
    body = text[start:end]
    return all(part in body for part in (
        "D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT",
        "observedRtvs[0] == render_target_view()",
        "observedDepth.Get() == depth.depth_stencil_view()",
        "observedRtvs[slot] != nullptr",
        "D3D11_PS_CS_UAV_REGISTER_COUNT - 1",
        "OMGetRenderTargetsAndUnorderedAccessViews(",
        "observedUav != nullptr",
        "if (!exactOm)",
        "return copy_color_to_staging(context, stagingOutput);",
    ))

def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    probe = PROBE.read_text(encoding="utf-8")
    if not exact_contract(source):
        raise SystemExit("R180 source no longer enforces exclusive pair OM staging")
    if not all(item in probe for item in (
        "R180 exclusive color/depth WARP staging was rejected",
        "R180 extra RTV incorrectly allowed pair staging",
        "R180 OM UAV incorrectly allowed pair staging",
    )):
        raise SystemExit("R180 compiled WARP controls were removed")
    # Independent mutation controls: removal of either negative check must
    # make the source contract fail, rather than leaving a false positive.
    for before, after in (
        ("observedRtvs[slot] != nullptr", "false"),
        ("observedUav != nullptr", "false"),
        ("observedRtvs[0] == render_target_view()", "true"),
    ):
        changed = source.replace(before, after, 1)
        if changed == source or exact_contract(changed):
            raise SystemExit("R180 source guard accepted a negative mutation")
    print("DX11 R180 exclusive OM pair staging source + 3 mutants: PASS")

if __name__ == "__main__":
    main()
