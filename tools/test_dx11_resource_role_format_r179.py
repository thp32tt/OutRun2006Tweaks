#!/usr/bin/env python3
"""R179 fail-closed native DX11 resource role/format regression (source only).

This test does not prove D3D9/D3D11 gameplay parity or enable the Draw path.
The corresponding compiled WARP probe checks the real translator output.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/resource_translation.cpp"
PROBE = ROOT / "tools/dx11_surface_mirror_probe.cpp"


def safe(source: str, probe: str) -> bool:
    # Bound checks to the actual format translator, not similarly named comments.
    start = source.find("FormatTranslation translate_resource_format(")
    end = source.find("ResourceBehaviorTranslation translate_resource_behavior(", start)
    if start < 0 or end < 0:
        return False
    fn = source[start:end]
    guard = ("if (role != ResourceRole::Color && role != ResourceRole::Texture)"
             "            return {};")
    # Normalize whitespace without erasing the C++ guards.
    compact = " ".join(fn.split())
    return all((
        "if (role != ResourceRole::Color && role != ResourceRole::Texture) return {};" in compact,
        "if (role == ResourceRole::Color &&" in compact,
        "source == D3DFMT_DXT1 ||" in compact,
        "source == D3DFMT_DXT3 ||" in compact,
        "source == D3DFMT_DXT5)) return {};" in compact,
        "translate_resource_format(source, ResourceRole::Texture)" in probe,
        "translate_resource_format(source, ResourceRole::Color)" in probe,
        "R179 compressed texture incorrectly qualifies as RTV" in probe,
        "invalidCompressedTarget.initialize(" in probe,
        "R179 compressed NativeSurfaceMirror owner accepted RTV" in probe,
        "ResourceRole::Vertex).exact" in probe,
    ))


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    probe = PROBE.read_text(encoding="utf-8")
    assert safe(source, probe), "R179 translator/probe exactness guard missing"
    # Negative mutation controls: guard removal must cause rejection.
    mutants = (
        source.replace("if (role != ResourceRole::Color && role != ResourceRole::Texture)",
                       "if (false)", 1),
        source.replace("if (role == ResourceRole::Color &&", "if (false &&", 1),
        source.replace("source == D3DFMT_DXT3 ||", "false ||", 1),
    )
    assert all(not safe(mutant, probe) for mutant in mutants), "R179 negative mutation escaped"
    print("R179_RESOURCE_FORMAT_ROLE_STATIC=PASS")
    print("R179_NEGATIVE_MUTATIONS=3/3_REJECTED")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
