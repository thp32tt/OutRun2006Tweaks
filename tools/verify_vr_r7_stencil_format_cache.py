#!/usr/bin/env python3
"""R7 tracked-depth stencil-format GetDesc cache with lifecycle negative tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"


def verify(source: str) -> None:
    assert "bool TrackedStencilFormatKnown = false;" in source
    assert "bool TrackedStencilFormatHasStencil = false;" in source
    fn = source.split("bool SurfaceHasStencil(IDirect3DSurface9* surface)\n", 1)[1]
    fn = fn.split("\n\t\tbool DepthTestActive(", 1)[0]
    required = (
        "if (!surface) return false;",
        "if (surface == TrackedDepthStencil && TrackedStencilFormatKnown)",
        "return TrackedStencilFormatHasStencil;",
        "if (FAILED(surface->GetDesc(&desc))) return false;",
        "const bool hasStencil = FormatHasStencil(desc.Format);",
        "if (surface == TrackedDepthStencil)",
        "TrackedStencilFormatHasStencil = hasStencil;",
        "TrackedStencilFormatKnown = true;",
        "return hasStencil;",
    )
    for part in required:
        assert part in fn, part
    assert fn.index(required[1]) < fn.index(required[3]) < fn.index(required[6])
    assert fn.index(required[6]) < fn.index(required[7]) < fn.index(required[8])
    assert fn.index(required[3]) < fn.index(required[8])
    reset = source.split("void ReleaseStereoResources()\n", 1)[1]
    reset = reset.split("\n\t\tbool CreateRightDepthForTracked(", 1)[0]
    assert reset.index("TrackedStencilFormatKnown = false;") < reset.index(
        "ReleaseCom(TrackedDepthStencil)")
    binding = source.split("HRESULT __stdcall SetDepthStencilSurfaceDest(", 1)[1]
    binding = binding.split("\n\t\tHRESULT __stdcall QueryIssueDest(", 1)[0]
    assert "const bool changed=TrackedDepthStencil!=surface;" in binding
    assert "if(changed) TrackedStencilFormatKnown=false;" in binding
    assert binding.index("if(changed) TrackedStencilFormatKnown=false;") < binding.index(
        "ReplaceSurfaceRef(TrackedDepthStencil,surface);")


if __name__ == "__main__":
    source = SRC.read_text(encoding="utf-8")
    verify(source)
    mutations = (
        ("bool TrackedStencilFormatKnown = false;", "bool TrackedStencilFormatKnown = true;"),
        ("bool TrackedStencilFormatHasStencil = false;", "bool TrackedStencilFormatHasStencil = true;"),
        ("if (!surface) return false;", "if (!surface) return true;"),
        ("if (surface == TrackedDepthStencil && TrackedStencilFormatKnown)", "if (TrackedStencilFormatKnown)"),
        ("return TrackedStencilFormatHasStencil;", "return true;"),
        ("if (FAILED(surface->GetDesc(&desc))) return false;", "if (true) return false;"),
        ("const bool hasStencil = FormatHasStencil(desc.Format);", "const bool hasStencil = true;"),
        ("if (surface == TrackedDepthStencil)", "if (surface != TrackedDepthStencil)"),
        ("TrackedStencilFormatHasStencil = hasStencil;", "TrackedStencilFormatHasStencil = false;"),
        ("TrackedStencilFormatKnown = true;", "TrackedStencilFormatKnown = false;"),
        ("// A Reset can recycle a COM address for a different depth format.\n\t\t\tTrackedStencilFormatKnown = false;",
         "// Reset cache invalidation deliberately deleted."),
        ("if(changed) TrackedStencilFormatKnown=false;", "if(changed) (void)0;"),
    )
    count = 0
    for old, new in mutations:
        assert old in source, "missing negative fixture: " + old
        broken = source.replace(old, new, 1)
        try:
            verify(broken)
        except (AssertionError, IndexError, ValueError):
            count += 1
        else:
            raise AssertionError("mutation survived: " + old)
    assert count == len(mutations)
    print(f"PASS DX9Ex R7 stencil GetDesc hot path: {count} negative mutations")
