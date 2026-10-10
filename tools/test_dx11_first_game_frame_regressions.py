#!/usr/bin/env python3
"""Regression controls for the opt-in *live game* DX11 diagnostic path.

Source-level evidence only: never report a GPU or HMD test as passed here.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERERS = [
    ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp",
    ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"


def indexed_descriptor_safe(source: str) -> bool:
    start = source.find("void R30ObserveNativeIndexedVB(")
    end = source.find("void R30ObserveNativeIndexedUP(", start)
    if start < 0 or end < 0:
        return False
    code = source[start:end]
    getter = code.find("ib->GetDesc(&iDesc)")
    first_read = code.find("iDesc.Format")
    return getter >= 0 and first_read > getter and (
        "SUCCEEDED(ib->GetDesc(&iDesc))" in code
        and "(iDesc.Format == D3DFMT_INDEX16 ||" in code
        and "R30CopyIndexShadow(ib," in code
        and "ib->Release();" in code and "vb->Release();" in code
    )


def main() -> None:
    for path in RENDERERS:
        source = path.read_text(encoding="utf-8")
        assert indexed_descriptor_safe(source), (
            f"{path.name}: D3DINDEXBUFFER_DESC must be initialized before Format reads"
        )
        # Deliberately recreate the previous invalid read; this test must
        # detect it without changing the production branch.
        bad = source.replace(
            "D3DINDEXBUFFER_DESC iDesc{};",
            "D3DINDEXBUFFER_DESC iDesc{};\n"
            "                const UINT speculativeSize = "
            "(iDesc.Format == D3DFMT_INDEX16) ? 2u : 4u;",
            1,
        )
        assert bad != source and not indexed_descriptor_safe(bad), (
            f"{path.name}: unsafe descriptor-read negative control was missed"
        )
        assert "live_game_frame::before_game_present(device);" in source
        assert "live_game_frame::before_game_reset();" in source
        assert "R30PresentR29Hook.stdcall<HRESULT>(" in source

    bridge = BRIDGE.read_text(encoding="utf-8")
    for evidence in (
        'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
        "GetVertexShader(vs.GetAddressOf())",
        "GetPixelShader(ps.GetAddressOf())",
        "GetTexture(0, tex.GetAddressOf())",
        "indices[i] >= vertexCount",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        "ctx->CopyResource(s.staging.Get(), s.backend.color_texture());",
        "game->UpdateSurface(",
        "s.observed, s.issued, s.visible, s.failed, s.presents",
        "s.backend.shutdown();",
    ):
        assert evidence in bridge, "missing diagnostic safety/telemetry: " + evidence
    assert bridge.count("ctx->DrawIndexed(") == 1
    assert bridge.count("ctx->Draw(") == 1

    # A static guard plus a deterministic negative mutation for sampling.
    # It is not GPU/Quest3 evidence. Each frame is still limited to one
    # native submit but cannot permanently pick only the first eligible Draw.
    sampling = (
        "const UINT candidateOrdinal = s.eligibleThisFrame++;",
        "++s.eligible;",
        "if (s.attempted || candidateOrdinal != s.probeSlot) return;",
        "const UINT window = (std::min)(s.eligibleThisFrame, kProbeSlots);",
        "s.probeSlot = window ? (s.probeSlot + 1u) % window : 0u;",
        "s.eligibleThisFrame = 0;",
    )
    assert all(item in bridge for item in sampling)
    broken = bridge.replace("candidateOrdinal != s.probeSlot",
                            "candidateOrdinal != 0u", 1)
    assert broken != bridge and sampling[2] not in broken
    slot = 0
    chosen = []
    for _ in range(8):
        population = 3
        hits = [i for i in range(population) if i == slot]
        assert len(hits) <= 1
        chosen.extend(hits)
        slot = (slot + 1) % min(population, 64)
    assert chosen == [0, 1, 2, 0, 1, 2, 0, 1]
    assert "s.probeSlot = 0;" in bridge  # Reset and failure rollback

    # UpdateSurface requires identical source/destination formats, no MSAA,
    # and an entirely in-bounds rectangle. The game's backbuffer can be X8.
    def safe_inset_copy(code: str) -> bool:
        start = code.find("void before_game_present(")
        end = code.find("void before_game_reset(", start)
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return all(token in section for token in (
            "bb.Width >= kWidth + 8u",
            "bb.Height >= kHeight + 8u",
            "bb.MultiSampleType == D3DMULTISAMPLE_NONE",
            "bb.Format == D3DFMT_A8R8G8B8",
            "bb.Format == D3DFMT_X8R8G8B8",
            "kWidth, kHeight, bb.Format, D3DPOOL_SYSTEMMEM",
            "game->UpdateSurface(",
        ))

    assert safe_inset_copy(bridge), (
        "native inset copy must match the actual D3D9 backbuffer and stay in bounds"
    )
    for vulnerable, replacement in (
        ("kWidth, kHeight, bb.Format, D3DPOOL_SYSTEMMEM",
         "kWidth, kHeight, D3DFMT_A8R8G8B8, D3DPOOL_SYSTEMMEM"),
        ("bb.MultiSampleType == D3DMULTISAMPLE_NONE",
         "bb.MultiSampleType != D3DMULTISAMPLE_NONE"),
        ("bb.Width >= kWidth + 8u", "bb.Width >= kWidth"),
        ("bb.Height >= kHeight + 8u", "bb.Height >= kHeight"),
        ("bb.Format == D3DFMT_X8R8G8B8",
         "bb.Format == D3DFMT_A2R10G10B10"),
    ):
        mutated = bridge.replace(vulnerable, replacement, 1)
        assert mutated != bridge and not safe_inset_copy(mutated), (
            "inset copy safety negative control did not detect " + vulnerable
        )
    print("DX11 live game diagnostic sampling/lifetime/fallback/inset regression PASS (static only)")


if __name__ == "__main__":
    main()
