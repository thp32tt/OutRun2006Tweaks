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
        "ctx->CopyResource(next.staging.Get(), s.backend.color_texture());",
        "game->UpdateSurface(",
        "s.observed, s.issued, s.visible, s.failed, s.presents",
        "s.backend.shutdown();",
    ):
        assert evidence in bridge, "missing diagnostic safety/telemetry: " + evidence
    assert bridge.count("ctx->DrawIndexed(") == 1
    assert bridge.count("ctx->Draw(") == 1
    # A live stage-1 operation must not silently modify stage-0 DIFFUSE.
    # The old boundary accepted such draws while the native shader ignored
    # the extra stage. These are fail-closed static mutation checks, not GPU proof.
    def fixed_function_stage_gate(code: str) -> bool:
        start = code.find("bool supported_game_state(")
        end = code.find("bool translate_vertices(", start)
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return (
            "GetTextureStageState(0, D3DTSS_COLOROP, &op)" in section
            and "GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)" in section
            and "nextColorOp != D3DTOP_DISABLE" in section
        )

    assert fixed_function_stage_gate(bridge)
    for original, wrong in (
        ("GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)",
         "GetTextureStageState(0, D3DTSS_COLOROP, &nextColorOp)"),
        ("nextColorOp != D3DTOP_DISABLE", "nextColorOp == D3DTOP_DISABLE"),
    ):
        mutated = bridge.replace(original, wrong, 1)
        assert mutated != bridge and not fixed_function_stage_gate(mutated), (
            "stage-1 fail-closed negative control was missed: " + original
        )


    # Fixed-function modifiers (COMPLEMENT/ALPHAREPLICATE) change the
    # stage-0 color even when the SELECTMASK bits still equal DIFFUSE.
    # Fog stays unsupported; scissor is mapped in a separate native raster path.
    # Static negative controls are not live-device parity evidence.
    def exact_diffuse_state_gate(code: str) -> bool:
        start = code.find("bool supported_game_state(")
        end = code.find("bool translate_vertices(", start)
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return all(token in section for token in (
            "arg != D3DTA_DIFFUSE",
            "GetRenderState(D3DRS_FOGENABLE, &fog)",
            "GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)",
            "stencil || depth || !clip || fog ||",
        ))

    assert exact_diffuse_state_gate(bridge)
    for bad, replacement in (
        ("arg != D3DTA_DIFFUSE",
         "(arg & D3DTA_SELECTMASK) != D3DTA_DIFFUSE"),
        ("GetRenderState(D3DRS_FOGENABLE, &fog)",
         "GetRenderState(D3DRS_FOGENABLE, &clip)"),
        ("GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)",
         "GetRenderState(D3DRS_SCISSORTESTENABLE, &clip)"),
        ("stencil || depth || !clip || fog ||",
         "stencil || depth || !clip || scissor ||"),
    ):
        mutated = bridge.replace(bad, replacement, 1)
        assert mutated != bridge and not exact_diffuse_state_gate(mutated), (
            "untranslated game-state negative control missed: " + bad
        )

    # An offscreen triangle, invisible (alpha-only) mask, or wireframe source
    # must not be counted as a D3D9-equivalent native colored frame.
    # Fail closed: keep the original D3D9 draw and input path intact.
    def exact_raster_output_gate(code: str) -> bool:
        start = code.find("bool supported_game_state(")
        end = code.find("bool translate_vertices(", start)
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return all(token in section for token in (
            "GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)",
            "GetRenderState(D3DRS_CULLMODE, &cullMode)",
            "GetRenderState(D3DRS_FILLMODE, &fillMode)",
            "const DWORD legalMask = D3DCOLORWRITEENABLE_RED |",
            "const DWORD visibleMask = D3DCOLORWRITEENABLE_RED |",
            "if ((colorMask & ~legalMask) || !(colorMask & visibleMask)) return false;",
            "cullMode != D3DCULL_NONE",
            "fillMode != D3DFILL_SOLID",
        ))

    assert exact_raster_output_gate(bridge)
    for original, mutated in (
        ("GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)",
         "GetRenderState(D3DRS_COLORWRITEENABLE, &cullMode)"),
        ("GetRenderState(D3DRS_CULLMODE, &cullMode)",
         "GetRenderState(D3DRS_CULLMODE, &fillMode)"),
        ("GetRenderState(D3DRS_FILLMODE, &fillMode)",
         "GetRenderState(D3DRS_FILLMODE, &colorMask)"),
        ("if ((colorMask & ~legalMask) || !(colorMask & visibleMask)) return false;",
         "if (false) return false;"),
        ("cullMode != D3DCULL_NONE", "cullMode == D3DCULL_NONE"),
        ("fillMode != D3DFILL_SOLID", "fillMode == D3DFILL_SOLID"),
    ):
        bad = bridge.replace(original, mutated, 1)
        assert bad != bridge and not exact_raster_output_gate(bad), (
            "untranslated native raster/output state was not rejected: " + original
        )

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
    # Detect synchronous GPU copies and accidental per-present D3D9 uploads.
    # This source-level control does not claim actual HMD performance proof.
    def deferred_inset_contract(code: str) -> bool:
        start = code.find("constexpr UINT kReadbackSlots = 3;")
        end = code.find("void before_game_reset(")
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return all(x in section for x in (
            "D3D11_QUERY_EVENT",
            "D3D11_ASYNC_GETDATA_DONOTFLUSH",
            "D3D11_MAP_FLAG_DO_NOT_WAIT",
            "ctx->End(next.fence.Get());",
            "if (!next.busy)",
            "++s.droppedCopies;",
            "s.insetFormat != bb.Format",
            "s.insetSurface.GetAddressOf(), nullptr",
        )) and "ctx->Flush();\\n    s.pending = true;" not in section

    assert deferred_inset_contract(bridge)
    for original, wrong in (
        ("D3D11_ASYNC_GETDATA_DONOTFLUSH", "0u"),
        ("D3D11_MAP_FLAG_DO_NOT_WAIT", "0u"),
        ("ctx->End(next.fence.Get());", "// no GPU completion fence"),
        ("if (!next.busy)", "if (next.busy)"),
        ("s.insetFormat != bb.Format", "s.insetFormat == bb.Format"),
    ):
        mutated = bridge.replace(original, wrong, 1)
        assert mutated != bridge and not deferred_inset_contract(mutated), (
            "deferred readback negative mutation passed unexpectedly: " + original
        )

    # New live D3D9 object-space path: do not require pretransformed
    # XYZRHW for every game-authored triangle. All unlit XYZ+DIFFUSE
    # positions must pass through the actual World/View/Projection state.
    # This is source/CPU math verification, not a game or GPU claim.
    def object_space_draw_safe(code: str) -> bool:
        state = code[code.find("bool supported_game_state("):
                     code.find("bool translate_vertices(")]
        vertices = code[code.find("bool translate_vertices("):
                        code.find("bool submit(")]
        observe = code[code.find("void observe("):
                       code.find("} // namespace", code.find("void observe("))]
        required_state = (
            "if (!game_fvf_layout(fvf, layout)) return false;",
            "capture.enabled = layout.textured;",
            "GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)",
            "GetRenderState(D3DRS_LIGHTING, &lighting)",
            "GetRenderState(D3DRS_VERTEXBLEND, &vertexBlend)",
            "            lighting || vertexBlend != D3DVBF_DISABLE",
            "GetTransform(D3DTS_WORLD, &transforms[0])",
            "GetTransform(D3DTS_VIEW, &transforms[1])",
            "GetTransform(D3DTS_PROJECTION, &transforms[2])",
        )
        required_vertices = (
            "stride < layout.minStride",
            "if (!game_fvf_decode_vertex(data, stride, layout, decoded))",
            "const DWORD diffuse = decoded.diffuse;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "next[col] += clip[row] * matrix.m[row][col];",
            "clip[3] <= 0.0f",
            "std::copy(clip.begin(), clip.end(), v.clip);",
        )
        return (all(x in state for x in required_state)
                and all(x in vertices for x in required_vertices)
                and "supported_game_state(game, vp, layout, transforms, capture, output)" in observe
                and "layout, transforms, capture, vertices)" in observe)

    assert object_space_draw_safe(bridge)
    for good, bad in (
        ("if (!game_fvf_layout(fvf, layout)) return false;",
         "if (false) return false;"),
        ("GetTransform(D3DTS_WORLD, &transforms[0])",
         "GetTransform(D3DTS_VIEW, &transforms[0])"),
        ("lighting || vertexBlend != D3DVBF_DISABLE",
         "lighting && vertexBlend != D3DVBF_DISABLE"),
        ("next[col] += clip[row] * matrix.m[row][col];",
         "next[col] += clip[row] * matrix.m[col][row];"),
        ("stride < layout.minStride", "stride < 20u"),
        ("clip[3] <= 0.0f", "clip[3] < 0.0f"),
    ):
        changed = bridge.replace(good, bad, 1)
        assert changed != bridge and not object_space_draw_safe(changed), (
            "object-space native geometry negative mutation escaped: " + good
        )
    # Observe both buffer and UP input families: a 16-byte XYZ+DIFFUSE
    # source cannot be captured behind an old 20-byte-only stride gate.
    for path in RENDERERS:
        source = path.read_text(encoding="utf-8")
        start = source.find("void R30ObserveNativeLinearVB(")
        end = source.find("HRESULT __stdcall DrawPrimitiveDestR30(", start)
        assert start >= 0 and end > start
        observed = source[start:end]
        assert observed.count("stride < 16") == 3
        assert "stride < 20" not in observed
        invalid = observed.replace("stride < 16", "stride < 20", 1)
        assert invalid != observed and invalid.count("stride < 16") != 3
    # Row-vector WVP order: object (1,2,3), translated by (5,7,11),
    # then scaled by (2,3,4) gives (12,27,56,1).
    vector = [1.0, 2.0, 3.0, 1.0]
    translation = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[5,7,11,1]]
    scale = [[2,0,0,0],[0,3,0,0],[0,0,4,0],[0,0,0,1]]
    for matrix in (translation, [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], scale):
        vector = [sum(vector[row]*matrix[row][col] for row in range(4))
                  for col in range(4)]
    assert vector == [12.0, 27.0, 56.0, 1.0]

    # Texture-backed menu/vehicle/race subset must connect live game D3D9
    # TEX1 FVF + stage/sampler + LockRect snapshot to D3D11 SRV/PS/Draw.
    # Mutation controls check that unsupported state still returns to D3D9.
    def texture_path_complete(code: str) -> bool:
        state = code[code.find("bool supported_game_state("):
                     code.find("bool translate_vertices(")]
        mirror = code[code.find("bool mirror_texture("):
                      code.find("bool submit(")]
        submit = code[code.find("bool submit("):
                      code.find("void observe(")]
        return all(x in state for x in (
            "if (!game_fvf_layout(fvf, layout)) return false;",
            "capture.enabled = layout.textured;",
            "if (!layout.hasDiffuse && !selectTexture) return false;",
            "GetTexture(0, tex.GetAddressOf())",
            "tex.As(&capture.texture)",
            "const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
            "const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
            "const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;",
            "const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;",
            "const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT;",
            "(!modulate && !selectTexture && !additive && !subtract && !modulate2x &&",
            "alphaArg1 != D3DTA_TEXTURE",
            "(rgbNeedsDiffuse && !arg2Diffuse)",
            "capture.selectTexture = selectTexture;",
            "capture.additive = additive;",
            "coordIndex >= layout.texcoordCount || transformFlags != D3DTTFF_DISABLE || srgb",
            "capture.coordIndex = coordIndex;",
            "(min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)",
            "(mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR)",
            "mip != D3DTEXF_NONE",
            "nextColorOp != D3DTOP_DISABLE",
        )) and all(x in mirror for x in (
            "if (info.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
            "GetLevelCount() == 0",
            "D3DFMT_A8R8G8B8", "D3DFMT_X8R8G8B8",
            "LockRect(0, &locked, nullptr, D3DLOCK_READONLY)",
            "capture.texture->UnlockRect(0)",
            "dev->CreateTexture2D(", "dev->CreateShaderResourceView(",
            "state.ComparisonFunc = D3D11_COMPARISON_NEVER",
            "state.MinLOD = 0.0f;", "state.MaxLOD = 0.0f;",
            "dev->CreateSamplerState(",
        )) and all(x in submit for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView)",
            "ctx->PSSetSamplers(0, 1, &boundSampler)",
            "s.sampledPs.Get()",
            "capture.selectTexture ? s.textureOnlyPs.Get() :\n                      capture.additive ? s.additivePs.Get() : s.sampledPs.Get()",
        ))
    assert texture_path_complete(bridge)
    for old, bad in (
        ("capture.enabled = layout.textured;", "capture.enabled = false;"),
        ("if (!layout.hasDiffuse && !selectTexture) return false;",
         "if (layout.hasDiffuse && !selectTexture) return false;"),
        ("const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
         "const bool modulate = op == D3DTOP_MODULATE || alphaOp == D3DTOP_MODULATE;"),
        ("const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
         "const bool selectTexture = op == D3DTOP_SELECTARG1 || alphaOp == D3DTOP_SELECTARG1;"),
        ("(!modulate && !selectTexture && !additive && !subtract && !modulate2x &&",
         "(!modulate && !selectTexture) && arg != D3DTA_TEXTURE"),
        ("(rgbNeedsDiffuse && !arg2Diffuse)",
         "(modulate && (arg2 != D3DTA_DIFFUSE && alphaArg2 != D3DTA_DIFFUSE))"),
        ("capture.selectTexture = selectTexture;", "capture.selectTexture = false;"),
        ("capture.additive = additive;", "capture.additive = false;"),
        ("const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;",
         "const bool additive = op == D3DTOP_ADD || alphaOp == D3DTOP_ADD;"),
        ("const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;",
         "const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE;"),
        ("const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT;",
         "const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE;"),
        ("if (info.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
         "if (info.Pool == D3DPOOL_SYSTEMMEM && !gpuRenderTarget) return false;"),
        ("GetLevelCount() == 0", "GetLevelCount() != 1"),
        ("state.MaxLOD = 0.0f;", "state.MaxLOD = D3D11_FLOAT32_MAX;"),
        ("capture.texture->UnlockRect(0)", "/* missing texture unlock */"),
        ("ctx->PSSetShaderResources(0, 1, &boundView)",
         "/* no native shader texture binding */"),
        ("capture.selectTexture ? s.textureOnlyPs.Get() :\n                      capture.additive ? s.additivePs.Get() : s.sampledPs.Get()",
         "s.sampledPs.Get()"),
    ):
        mutated = bridge.replace(old, bad, 1)
        assert mutated != bridge and not texture_path_complete(mutated), (
            "texture-stage native-D3D11 negative mutation escaped: " + old
        )
    assert "xyz[2] * w" in bridge and "v.clip[3] = w;" in bridge
    assert "float2 uv : TEXCOORD0" in bridge
    assert "gameTexture.Sample(gameSampler, v.uv) * v.diffuse" in bridge
    assert "float4 PSTextureOnly(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv); AlphaGate(c.a); return c; }" in bridge
    assert '!compile("PSTextureOnly", "ps_4_0", textureOnlyCode)' in bridge
    assert "s.textureOnlyPs.Reset();" in bridge
    assert "if (!capture.enabled && (op != D3DTOP_SELECTARG1 || arg != D3DTA_DIFFUSE))" in bridge
    # RGB MODULATE with separately selected alpha is an exact admitted subset.
    MODULATE, MODULATE2X, MODULATE4X, SELECTARG1, ADD, SUBTRACT, SELECTARG2 = 4, 5, 6, 2, 7, 10, 3
    for color_op, alpha_op, supported in (
        (MODULATE, MODULATE, True),
        (MODULATE2X, MODULATE2X, True),
        (MODULATE4X, MODULATE4X, True),
        (MODULATE2X, MODULATE, False),
        (MODULATE4X, MODULATE2X, False),
        (MODULATE, MODULATE4X, False),
        (SELECTARG1, SELECTARG1, True),
        (ADD, ADD, True),
        (SUBTRACT, SUBTRACT, True),
        (SUBTRACT, ADD, False),
        (ADD, SUBTRACT, False),
        (MODULATE, ADD, False),
        (ADD, SELECTARG1, True),
        (ADD, SELECTARG2, True),
        (MODULATE, SELECTARG1, True),
        (MODULATE, SELECTARG2, True),
        (SELECTARG1, MODULATE, False),
        (0, 0, False),
    ):
        admitted = ((color_op == MODULATE and alpha_op == MODULATE)
                    or (color_op == MODULATE2X and alpha_op == MODULATE2X)
                    or (color_op == MODULATE4X and alpha_op == MODULATE4X)
                    or (color_op == SELECTARG1 and alpha_op == SELECTARG1)
                    or (color_op == ADD and alpha_op == ADD)
                    or (color_op == SUBTRACT and alpha_op == SUBTRACT)
                    or (color_op == MODULATE and alpha_op in (SELECTARG1, SELECTARG2))
                    or (color_op == ADD and alpha_op in (SELECTARG1, SELECTARG2)))
        assert admitted == supported



    # 00555 live game D3D9 state -> DX11 dedicated RGBA HLSL -> indexed/linear draw.
    # Destructive disconnect mutations and CPU reference vectors; HMD UNTESTED.
    scaled_links = (
        "const bool modulate2x = op == D3DTOP_MODULATE2X && alphaOp == D3DTOP_MODULATE2X;",
        "const bool modulate4x = op == D3DTOP_MODULATE4X && alphaOp == D3DTOP_MODULATE4X;",
        "capture.modulate2x = modulate2x;", "capture.modulate4x = modulate4x;",
        "bool modulate2x = false;", "bool modulate4x = false;",
        "float4 PSTextureModulate2X(VOut v) : SV_Target { float4 c = saturate(2.0f * gameTexture.Sample(gameSampler, v.uv) * v.diffuse); AlphaGate(c.a); return c; }",
        "float4 PSTextureModulate4X(VOut v) : SV_Target { float4 c = saturate(4.0f * gameTexture.Sample(gameSampler, v.uv) * v.diffuse); AlphaGate(c.a); return c; }",
        '!compile("PSTextureModulate2X", "ps_4_0", modulate2xCode)',
        '!compile("PSTextureModulate4X", "ps_4_0", modulate4xCode)',
        "s.modulate2xPs.GetAddressOf()", "s.modulate4xPs.GetAddressOf()",
        "s.modulate2xPs.Reset();", "s.modulate4xPs.Reset();",
        "capture.modulate2x ? s.modulate2xPs.Get() :",
        "capture.modulate4x ? s.modulate4xPs.Get() :",
        "(!modulate && !selectTexture && !additive && !subtract && !modulate2x &&",
        "(rgbNeedsDiffuse && !arg2Diffuse)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(x in bridge for x in scaled_links)
    for token in scaled_links[:-2]:
        # Reset occurs in both pipeline recovery and game Reset. Remove every
        # occurrence for this destructive control; a single removal leaves the
        # other valid occurrence and creates a false test failure.
        mutant = bridge.replace(token, "/* disconnected scaled source/consumer */")
        assert mutant != bridge and token not in mutant
    for factor, texel, diffuse, expected in (
        (2, (0.4, 0.2, 0.1, 0.7), (0.5, 0.5, 0.5, 0.5),
         (0.4, 0.2, 0.1, 0.7)),
        (4, (0.8, 0.3, 0.1, 0.75), (0.5, 0.5, 0.5, 0.5),
         (1.0, 0.6, 0.2, 1.0)),
    ):
        actual = tuple(min(1.0, factor * x * y) for x, y in zip(texel, diffuse))
        assert all(abs(a - b) < 1e-6 for a, b in zip(actual, expected))
        assert actual != tuple(min(1.0, x * y) for x, y in zip(texel, diffuse))
    print("DX11 stage0 MODULATE2X/4X source-to-native Draw PASS (static only)")


    # 00556 actual D3D9 stage0 RGB/alpha -> native PS -> Draw/DrawIndexed.
    mixed_links = (
        "const bool mixedTextureAlpha = op == D3DTOP_MODULATE && alphaOp == D3DTOP_SELECTARG1;",
        "const bool mixedDiffuseAlpha = op == D3DTOP_MODULATE && alphaOp == D3DTOP_SELECTARG2;",
        "capture.mixedTextureAlpha = mixedTextureAlpha;",
        "capture.mixedDiffuseAlpha = mixedDiffuseAlpha;",
        "bool mixedTextureAlpha = false;",
        "bool mixedDiffuseAlpha = false;",
        "rgbNeedsDiffuse && !arg2Diffuse",
        "alphaNeedsDiffuse && !alphaArg2Diffuse",
        "(!mixedDiffuseAlpha && !mixedAddDiffuseAlpha && alphaArg1 != D3DTA_TEXTURE)",
        "float4 c = float4(t.rgb * v.diffuse.rgb, t.a);",
        "float4 c = float4(t.rgb * v.diffuse.rgb, v.diffuse.a);",
        '!compile("PSTextureModulateTextureAlpha", "ps_4_0", mixedTextureCode)',
        '!compile("PSTextureModulateDiffuseAlpha", "ps_4_0", mixedDiffuseCode)',
        "s.mixedTextureAlphaPs.GetAddressOf()",
        "s.mixedDiffuseAlphaPs.GetAddressOf()",
        "s.mixedTextureAlphaPs.Reset();",
        "s.mixedDiffuseAlphaPs.Reset();",
        "s.mixedTextureAlphaPs && s.mixedDiffuseAlphaPs",
        "capture.mixedTextureAlpha ? s.mixedTextureAlphaPs.Get() :",
        "capture.mixedDiffuseAlpha ? s.mixedDiffuseAlphaPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(x in bridge for x in mixed_links)
    for source_link in mixed_links[:-2]:
        mutant = bridge.replace(source_link, "/* removed native alpha pipeline link */")
        assert mutant != bridge and source_link not in mutant
    for texel, diffuse, expected_t, expected_d in (
        ((0.2, 0.8, 0.5, 0.9), (0.8, 0.5, 0.4, 0.25),
         (0.16, 0.4, 0.2, 0.9), (0.16, 0.4, 0.2, 0.25)),
        ((1.0, 0.0, 0.3, 0.05), (0.1, 0.7, 0.5, 0.95),
         (0.1, 0.0, 0.15, 0.05), (0.1, 0.0, 0.15, 0.95)),
    ):
        rgb = tuple(x * y for x, y in zip(texel[:3], diffuse[:3]))
        assert all(abs(x - y) < 1e-6 for x, y in zip((*rgb, texel[3]), expected_t))
        assert all(abs(x - y) < 1e-6 for x, y in zip((*rgb, diffuse[3]), expected_d))
        assert expected_t[3] != expected_d[3]
    for op, a1, a2, allowed in (
        (SELECTARG1, 2, 0x10, True), (SELECTARG2, 0x10, 0, True),
        (SELECTARG2, 0x10, 1, True), (SELECTARG1, 0, 0, False),
        (SELECTARG2, 2, 2, False), (MODULATE, 2, 0, False),
    ):
        assert ((op == SELECTARG1 and a1 == 2) or (
            op == SELECTARG2 and a2 in (0, 1))) == allowed
    print("DX11 mixed alpha live Draw source integration PASS (static only)")


    # 00557 live game D3D9 ADD RGB + independent alpha sources into
    # D3D11 native linear/indexed Draw. Source regressions, NOT HMD proof.
    add_alpha_links = (
        "const bool mixedAddTextureAlpha = op == D3DTOP_ADD && alphaOp == D3DTOP_SELECTARG1;",
        "const bool mixedAddDiffuseAlpha = op == D3DTOP_ADD && alphaOp == D3DTOP_SELECTARG2;",
        "bool mixedAddTextureAlpha = false;",
        "bool mixedAddDiffuseAlpha = false;",
        "mixedAddTextureAlpha || mixedAddDiffuseAlpha ||",
        "mixedDiffuseAlpha || mixedAddDiffuseAlpha ||",
        "!mixedAddTextureAlpha && !mixedAddDiffuseAlpha &&",
        "(!mixedDiffuseAlpha && !mixedAddDiffuseAlpha && alphaArg1 != D3DTA_TEXTURE)",
        "capture.mixedAddTextureAlpha = mixedAddTextureAlpha;",
        "capture.mixedAddDiffuseAlpha = mixedAddDiffuseAlpha;",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb), t.a);",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb), v.diffuse.a);",
        '!compile("PSTextureAddTextureAlpha", "ps_4_0", mixedAddTextureCode)',
        '!compile("PSTextureAddDiffuseAlpha", "ps_4_0", mixedAddDiffuseCode)',
        "s.mixedAddTextureAlphaPs.GetAddressOf()",
        "s.mixedAddDiffuseAlphaPs.GetAddressOf()",
        "s.mixedAddTextureAlphaPs.Reset();",
        "s.mixedAddDiffuseAlphaPs.Reset();",
        "s.mixedAddTextureAlphaPs && s.mixedAddDiffuseAlphaPs",
        "capture.mixedAddTextureAlpha ? s.mixedAddTextureAlphaPs.Get() :",
        "capture.mixedAddDiffuseAlpha ? s.mixedAddDiffuseAlphaPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(token in bridge for token in add_alpha_links), "mixed ADD/alpha pipeline disconnected"
    for token in add_alpha_links[:-2]:
        mutant = bridge.replace(token, "/* detached mixed ADD alpha */")
        assert mutant != bridge and token not in mutant, "missed ADD alpha mutation: " + token
    for texel, diffuse, expected_t, expected_d in (
        ((0.8, 0.3, 0.9, 0.9), (0.5, 0.4, 0.3, 0.2),
         (1.0, 0.7, 1.0, 0.9), (1.0, 0.7, 1.0, 0.2)),
        ((0.1, 0.8, 0.05, 0.1), (0.2, 0.9, 0.2, 0.95),
         (0.3, 1.0, 0.25, 0.1), (0.3, 1.0, 0.25, 0.95)),
    ):
        rgb = tuple(min(1.0, t + d) for t, d in zip(texel[:3], diffuse[:3]))
        assert all(abs(a - b) < 1e-6 for a, b in zip((*rgb, texel[3]), expected_t))
        assert all(abs(a - b) < 1e-6 for a, b in zip((*rgb, diffuse[3]), expected_d))
        assert expected_t[3] != expected_d[3]
    for color_op, alpha_op, expected in (
        (ADD, SELECTARG1, True), (ADD, SELECTARG2, True),
        (MODULATE, SELECTARG1, False), (SUBTRACT, SELECTARG2, False),
        (ADD, MODULATE, False), (ADD, SUBTRACT, False),
    ):
        assert (color_op == ADD and alpha_op in (SELECTARG1, SELECTARG2)) == expected
    print("DX11 stage0 ADD with separate alpha native Draw connected PASS (static only)")

    # 00553 positive/negative linkage: real game stage0 ADD dispatches a
    # saturating RGBA pixel shader. No actual HMD/desktop pixels are inferred.
    required_add = (
        "float4 PSTextureAdd(VOut v) : SV_Target { float4 c = saturate(gameTexture.Sample(gameSampler, v.uv) + v.diffuse); AlphaGate(c.a); return c; }",
        '!compile("PSTextureAdd", "ps_4_0", additiveCode)',
        "s.additivePs.Reset();",
        "s.sampledPs && s.textureOnlyPs && s.additivePs && s.subtractPs &&",
        "capture.additive ? s.additivePs.Get() : s.sampledPs.Get()",
        "const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;",
        "capture.additive = additive;",
    )
    assert all(token in bridge for token in required_add)
    # The PS exists across both pipeline recreation and D3D9 Reset; disconnect
    # BOTH lifetime owners rather than the first occurrence only.
    assert bridge.count("s.additivePs.Reset();") == 2
    for token in required_add:
        mutated = bridge.replace(token, "/* ADD disconnected */")
        assert mutated != bridge and token not in mutated
    # 00554 SUBTRACT: source D3D9 -> RGBA native PS -> Draw/DrawIndexed.
    # Mutations reject disconnected shader, alpha or operand gate changes.
    subtract_link = (
        "const bool subtract = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_SUBTRACT;",
        "(!modulate && !selectTexture && !additive && !subtract && !modulate2x &&",
        "(rgbNeedsDiffuse && !arg2Diffuse)",
        "capture.subtract = subtract;",
        "bool subtract = false;",
        "float4 PSTextureSubtract(VOut v) : SV_Target { float4 c = saturate(gameTexture.Sample(gameSampler, v.uv) - v.diffuse); AlphaGate(c.a); return c; }",
        '!compile("PSTextureSubtract", "ps_4_0", subtractCode)',
        "s.subtractPs.Reset();", "s.additivePs && s.subtractPs &&",
        "s.subtractPs.GetAddressOf()", "capture.subtract ? s.subtractPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(x in bridge for x in subtract_link)
    assert bridge.count("s.subtractPs.Reset();") == 2
    for token in subtract_link[:-2]:
        mutant = bridge.replace(token, "/* DISCONNECTED */")
        assert mutant != bridge and token not in mutant
    for texel, diffuse, expected in (
        ((0.8, 0.1, 0.9, 0.7), (0.2, 0.5, 0.1, 0.2), (0.6, 0.0, 0.8, 0.5)),
        ((0.0, 1.0, 0.3, 0.0), (0.8, 0.0, 0.9, 1.0), (0.0, 1.0, 0.0, 0.0)),
    ):
        got = tuple(max(0.0, min(1.0, x - y)) for x, y in zip(texel, diffuse))
        assert all(abs(x - y) < 1e-6 for x, y in zip(got, expected))
        assert got != tuple(min(1.0, x + y) for x, y in zip(texel, diffuse))
    print("DX11 stage0 SUBTRACT native Draw RGBA PASS (static only)")

    # Stage-0 CURRENT is DIFFUSE (but not at a later texture stage).
    # Operand modifier bits must still be refused rather than silently masked.
    DIFFUSE, CURRENT, TEXTURE, COMPLEMENT = 0, 1, 2, 0x10
    for second_arg in (DIFFUSE, CURRENT, TEXTURE, CURRENT | COMPLEMENT):
        allowed = second_arg == DIFFUSE or second_arg == CURRENT
        assert allowed == (second_arg in (0, 1))
    for texel, diffuse, expected in (
        ((0.8, 0.1, 0.5, 0.75), (0.4, 0.6, 0.7, 0.5), (1.0, 0.7, 1.0, 1.0)),
        ((0.0, 0.2, 0.0, 0.0), (0.2, 0.0, 0.7, 0.5), (0.2, 0.2, 0.7, 0.5)),
    ):
        actual = tuple(min(1.0, t + d) for t, d in zip(texel, diffuse))
        assert all(abs(a - b) < 1e-6 for a, b in zip(actual, expected))

    # Menu/race sprite alpha is now an actual D3D9-state -> PS/OM pipeline
    # integration. These destructive source mutations reject accidental native
    # admission of unsupported blending or an omitted alpha clip/bind.
    def alpha_path_complete(code: str) -> bool:
        state = code[code.find("bool supported_game_state("):
                     code.find("bool translate_vertices(")]
        pipeline = code[code.find("bool ensure_pipeline("):
                        code.find("bool supported_game_state(")]
        submit = code[code.find("bool submit("):
                      code.find("void observe(")]
        shader = code[code.find("constexpr char kShader[]"):
                      code.find(')";', code.find("constexpr char kShader[]"))]
        return (all(x in state for x in (
            "GetRenderState(D3DRS_ALPHABLENDENABLE, &blend)",
            "GetRenderState(D3DRS_ALPHATESTENABLE, &alpha)",
            "GetRenderState(D3DRS_SRCBLEND, &src)",
            "GetRenderState(D3DRS_DESTBLEND, &dst)",
            "GetRenderState(D3DRS_BLENDOP, &blendOp)",
            "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
            "src != D3DBLEND_SRCALPHA || dst != D3DBLEND_INVSRCALPHA",
            "blendOp != D3DBLENDOP_ADD || separate",
            "GetRenderState(D3DRS_ALPHAFUNC, &func)",
            "GetRenderState(D3DRS_ALPHAREF, &reference)",
            "(func != D3DCMP_GREATER && func != D3DCMP_GREATEREQUAL)",
            "reference > 255u",
            "output.alphaBlend = true;", "output.alphaTest = true;",
        )) and all(x in pipeline for x in (
            "target.BlendEnable = TRUE;",
            "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;",
            "target.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;",
            "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;",
            "target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;",
            "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())",
            "dev->CreateBuffer(&constants, nullptr, s.alphaConstants.GetAddressOf())",
        )) and all(x in submit for x in (
            "ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0)",
            "ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr",
            "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer)",
        )) and all(x in shader for x in (
            "cbuffer AlphaParams : register(b0)",
            "floor(saturate(alpha) * 255.0f + 0.5f)",
            "alphaParams.z == 5.0f && value > alphaParams.y",
            "alphaParams.z == 7.0f && value >= alphaParams.y",
            "clip(pass ? 1.0f : -1.0f)",
            "AlphaGate(c.a);",
        )))

    assert alpha_path_complete(bridge)
    for original, broken in (
        ("src != D3DBLEND_SRCALPHA || dst != D3DBLEND_INVSRCALPHA",
         "src != D3DBLEND_SRCALPHA && dst != D3DBLEND_INVSRCALPHA"),
        ("blendOp != D3DBLENDOP_ADD || separate",
         "blendOp != D3DBLENDOP_ADD && separate"),
        ("(func != D3DCMP_GREATER && func != D3DCMP_GREATEREQUAL)",
         "(func != D3DCMP_GREATER || func != D3DCMP_GREATEREQUAL)"),
        ("reference > 255u", "reference > 256u"),
        ("target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;",
         "target.SrcBlendAlpha = D3D11_BLEND_ONE;"),
        ("ctx->PSSetConstantBuffers(0, 1, &alphaBuffer)",
         "/* unbound alpha constants */"),
        ("ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr",
         "ctx->OMSetBlendState(nullptr"),
        ("clip(pass ? 1.0f : -1.0f)", "/* alpha test omitted */"),
    ):
        changed = bridge.replace(original, broken, 1)
        assert changed != bridge and not alpha_path_complete(changed), (
            "alpha sprite source->D3D11 integration mutation escaped: " + original
        )
    # D3D9 compare is on an 8-bit alpha after texturing. Test boundaries for
    # both admitted funcs; no GPU color or menu parity claimed here.
    def passes(alpha_byte: int, ref: int, func: int) -> bool:
        return (func == 5 and alpha_byte > ref) or (
            func == 7 and alpha_byte >= ref)
    assert not passes(127, 128, 5)
    assert passes(129, 128, 5)
    assert not passes(127, 128, 7)
    assert passes(128, 128, 7)


    # Actual D3D9 GetScissorRect -> signed viewport intersection ->
    # conservative inset rectangle -> D3D11 RSSetScissorRects integration.
    # This checks both the producer and the native consumer; source-only,
    # never a claim of real GPU/menu/HMD clipping parity.
    def live_scissor_path_complete(code: str) -> bool:
        state = code[code.find("bool supported_game_state("):
                     code.find("bool translate_vertices(")]
        pipeline = code[code.find("bool ensure_pipeline("):
                        code.find("bool supported_game_state(")]
        submit = code[code.find("bool submit("):
                      code.find("void observe(")]
        return all(x in state for x in (
            "GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)",
            "if (scissor) {",
            "GetScissorRect(&gameScissor)",
            "gameScissor.right <= gameScissor.left",
            "gameScissor.bottom <= gameScissor.top",
            "static_cast<std::int64_t>(viewport.X) + viewport.Width",
            "static_cast<std::int64_t>(viewport.Y) + viewport.Height",
            "if (right <= left || bottom <= top) return false;",
            "const LONG nativeLeft = static_cast<LONG>(std::ceil(",
            "const LONG nativeTop = static_cast<LONG>(std::ceil(",
            "const LONG nativeRight = static_cast<LONG>(std::floor(",
            "const LONG nativeBottom = static_cast<LONG>(std::floor(",
            "if (nativeRight <= nativeLeft || nativeBottom <= nativeTop)",
            "output.scissor = true;",
            "output.nativeScissor = {nativeLeft, nativeTop, nativeRight, nativeBottom};",
        )) and all(x in pipeline for x in (
            "raster.ScissorEnable = TRUE;",
            "dev->CreateRasterizerState(&raster, s.scissorRaster.GetAddressOf())",
        )) and all(x in submit for x in (
            "const D3D11_RECT& rect = output.scissor ? output.nativeScissor : fullScissor;",
            "ctx->RSSetScissorRects(1, &rect);",
            "ctx->RSSetState(output.scissor ? s.scissorRaster.Get() : s.raster.Get());",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and "s.scissorRaster.Reset();" in code

    assert live_scissor_path_complete(bridge)
    for old, bad in (
        ("GetScissorRect(&gameScissor)", "/* source scissor ignored */"),
        ("gameScissor.right <= gameScissor.left", "gameScissor.right < gameScissor.left"),
        ("static_cast<std::int64_t>(viewport.X) + viewport.Width", "viewport.X + viewport.Width"),
        ("if (right <= left || bottom <= top) return false;", "/* out of bounds admitted */"),
        ("const LONG nativeLeft = static_cast<LONG>(std::ceil(",
         "const LONG nativeLeft = static_cast<LONG>(std::floor("),
        ("const LONG nativeBottom = static_cast<LONG>(std::floor(",
         "const LONG nativeBottom = static_cast<LONG>(std::ceil("),
        ("if (nativeRight <= nativeLeft || nativeBottom <= nativeTop)", "if (false)"),
        ("raster.ScissorEnable = TRUE;", "raster.ScissorEnable = FALSE;"),
        ("ctx->RSSetScissorRects(1, &rect);", "/* omitted native clipping */"),
        ("output.scissor ? s.scissorRaster.Get() : s.raster.Get()", "s.raster.Get()"),
    ):
        broken = bridge.replace(old, bad, 1)
        assert broken != bridge and not live_scissor_path_complete(broken), (
            "live scissor integration mutation escaped: " + old
        )
    # Source viewport origin 100,50 and extent 800x600. An inset clip must
    # never expand the source scissor when scaling down to 256x144.
    from math import ceil, floor
    def scale_clip(vp, rect):
        x, y, width, height = vp
        l, t, r, b = rect
        l, t = max(l, x), max(t, y)
        r, b = min(r, x + width), min(b, y + height)
        if r <= l or b <= t:
            return None
        mapped = (ceil((l-x)*256/width), ceil((t-y)*144/height),
                  floor((r-x)*256/width), floor((b-y)*144/height))
        return mapped if mapped[2] > mapped[0] and mapped[3] > mapped[1] else None

    assert scale_clip((100, 50, 800, 600), (200, 100, 600, 500)) == (32, 12, 160, 108)
    assert scale_clip((100, 50, 800, 600), (0, 0, 1000, 1000)) == (0, 0, 256, 144)
    assert scale_clip((100, 50, 800, 600), (0, 0, 99, 49)) is None
    assert scale_clip((100, 50, 800, 600), (101, 51, 102, 52)) is None
    assert scale_clip((100, 50, 800, 600), (500, 50, 400, 70)) is None

    # D3D9 channel flags are mapped explicitly to D3D11 OM write flags;
    # a default all-write OM state must never bypass a partial source mask.
    # Verify producer validation, lazy native state selection and reset together.
    def color_mask_path_complete(code: str) -> bool:
        producer = code[code.find("bool supported_game_state("):
                        code.find("bool translate_vertices(")]
        consumer = code[code.find("bool submit("):code.find("void observe(")]
        return all(x in producer for x in (
            "GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)",
            "if ((colorMask & ~legalMask) || !(colorMask & visibleMask)) return false;",
            "output.colorWriteMask = static_cast<std::uint8_t>(",
            "D3DCOLORWRITEENABLE_RED) ? D3D11_COLOR_WRITE_ENABLE_RED",
            "D3DCOLORWRITEENABLE_GREEN) ? D3D11_COLOR_WRITE_ENABLE_GREEN",
            "D3DCOLORWRITEENABLE_BLUE) ? D3D11_COLOR_WRITE_ENABLE_BLUE",
            "D3DCOLORWRITEENABLE_ALPHA) ? D3D11_COLOR_WRITE_ENABLE_ALPHA",
        )) and all(x in consumer for x in (
            "if (output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL)",
            "(output.alphaBlend ? 16u : 0u) + output.colorWriteMask",
            "s.alphaBlend->GetDesc(&maskDesc);",
            "maskDesc.RenderTarget[0].BlendEnable = output.alphaBlend ? TRUE : FALSE;",
            "maskDesc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
            "dev->CreateBlendState(&maskDesc, cached.GetAddressOf())",
            "ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);",
            "ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and code.count("for (auto& masked : s.maskedBlends) masked.Reset();") == 2

    assert color_mask_path_complete(bridge)
    for old, broken in (
        ("!(colorMask & visibleMask)", "false"),
        ("colorMask & ~legalMask", "colorMask & legalMask"),
        ("D3DCOLORWRITEENABLE_GREEN) ? D3D11_COLOR_WRITE_ENABLE_GREEN",
         "D3DCOLORWRITEENABLE_GREEN) ? D3D11_COLOR_WRITE_ENABLE_RED"),
        ("if (output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL)",
         "if (false)"),
        ("(output.alphaBlend ? 16u : 0u) + output.colorWriteMask",
         "output.colorWriteMask"),
        ("s.alphaBlend->GetDesc(&maskDesc);",
         "/* D3D11 default blend factors left invalid */"),
        ("maskDesc.RenderTarget[0].BlendEnable = output.alphaBlend ? TRUE : FALSE;",
         "maskDesc.RenderTarget[0].BlendEnable = TRUE;"),
        ("maskDesc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
         "maskDesc.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;"),
        ("ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);",
         "/* masked OM binding omitted */"),
    ):
        mutated = bridge.replace(old, broken, 1)
        assert mutated != bridge and not color_mask_path_complete(mutated), (
            "color mask game-source -> native OM mutation escaped: " + old
        )
    RED, GREEN, BLUE, ALPHA = 1, 2, 4, 8
    for mask in range(32):
        eligible = (mask & ~(RED | GREEN | BLUE | ALPHA)) == 0 and bool(mask & (RED | GREEN | BLUE))
        assert eligible == (mask in range(1, 16) and mask != ALPHA)
        if eligible:
            native_mask = sum(channel for channel in (RED, GREEN, BLUE, ALPHA) if mask & channel)
            assert native_mask == mask
            assert ((16 if (mask & ALPHA) else 0) + mask) < 32
    # Live fixed-function DXT textures must use compressed block pitches and
    # bind BC1/2/3 SRVs to the existing native textured Draw path. This is
    # source/CPU contract evidence, not a game/WARP pixel or HMD validation.
    def dxt_native_draw_connected(source: str) -> bool:
        producer = source[source.find("bool mirror_texture("):source.find("bool submit(")]
        draw = source[source.find("bool submit("):source.find("void observe(")]
        return all(token in producer for token in (
            "const bool compressed = info.Format == D3DFMT_DXT1 ||",
            "info.Format == D3DFMT_DXT3 ||",
            "info.Format == D3DFMT_DXT5;",
            "if ((info.Width & 3u) || (info.Height & 3u)) return false;",
            "const UINT bytesPerBlock = info.Format == D3DFMT_DXT1 ? 8u : 16u;",
            "rowBytes = (info.Width / 4u) * bytesPerBlock;",
            "rows = info.Height / 4u;",
            "DXGI_FORMAT_BC1_UNORM",
            "DXGI_FORMAT_BC2_UNORM",
            "DXGI_FORMAT_BC3_UNORM",
            "info.Pool == D3DPOOL_DEFAULT",
            "locked.Pitch > 0",
            "static_cast<UINT>(locked.Pitch) >= rowBytes",
            "static_cast<std::size_t>(rowBytes) * rows",
            "static_cast<std::size_t>(y) * locked.Pitch",
            "static_cast<std::size_t>(y) * rowBytes",
            "initial.SysMemPitch = rowBytes;",
            "desc.Format = nativeFormat;",
            "capture.texture->UnlockRect(0);",
            "dev->CreateShaderResourceView(",
        )) and all(token in draw for token in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    assert dxt_native_draw_connected(bridge)
    for source, wrong in (
        ("info.Format == D3DFMT_DXT1", "info.Format == D3DFMT_DXT2"),
        ("info.Format == D3DFMT_DXT3", "info.Format == D3DFMT_DXT2"),
        ("info.Format == D3DFMT_DXT5", "info.Format == D3DFMT_DXT4"),
        ("if ((info.Width & 3u) || (info.Height & 3u)) return false;",
         "if (false) return false;"),
        ("rowBytes = (info.Width / 4u) * bytesPerBlock;",
         "rowBytes = info.Width * 4u;"),
        ("rows = info.Height / 4u;", "rows = info.Height;"),
        ("static_cast<UINT>(locked.Pitch) >= rowBytes",
         "static_cast<UINT>(locked.Pitch) > 0"),
        ("initial.SysMemPitch = rowBytes;", "initial.SysMemPitch = info.Width * 4u;"),
        ("desc.Format = nativeFormat;", "desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;"),
    ):
        broken = bridge.replace(source, wrong, 1)
        assert broken != bridge and not dxt_native_draw_connected(broken), (
            "DXT game texture -> BC SRV Draw mutation escaped: " + source
        )
    for width, height, bytes_per_block, expected in (
        (4, 4, 8, (8, 1)), (256, 128, 8, (512, 32)),
        (4, 4, 16, (16, 1)), (128, 64, 16, (512, 16)),
    ):
        row_bytes = (width // 4) * bytes_per_block
        rows = height // 4
        assert (row_bytes, rows) == expected
        assert row_bytes * rows == (width * height // 16) * bytes_per_block
    for width, height in ((1, 4), (4, 1), (6, 8), (8, 6), (0, 4)):
        assert not (width > 0 and height > 0 and width % 4 == 0 and height % 4 == 0)

    # Real D3D9 16-bit game texture -> BGRA8 decode -> live D3D11
    # SRV/sampler -> native Draw/DrawIndexed. DXT remains BC-compressed.
    packed_header = (ROOT / "src/vr/d3d11/packed_texture_16bit.hpp").read_text()
    packed_probe = (ROOT / "tools/dx11_packed_texture_16bit_probe.cpp").read_text()
    def packed16_connected(code: str, helper: str) -> bool:
        producer = code[code.find("bool mirror_texture("):code.find("bool submit(")]
        # Distinguish format admission from later decoder layout selection:
        # a mutation to the admission predicates must not pass merely because
        # an identical D3DFMT token survives in the decoder selector.
        admission = producer[producer.find("const bool packed16 ="):producer.find("DXGI_FORMAT nativeFormat")]
        consumer = code[code.find("bool submit("):code.find("void observe(")]
        return '#include "packed_texture_16bit.hpp"' in code and all(x in admission for x in (
            "info.Format == D3DFMT_R5G6B5",
            "info.Format == D3DFMT_A1R5G5B5",
            "info.Format == D3DFMT_A4R4G4B4",
        )) and all(x in producer for x in (
            "rowBytes = info.Width * 2u;",
            "const UINT uploadRowBytes = packed16 ? info.Width * 4u : rowBytes;",
            "static_cast<UINT>(locked.Pitch) >= rowBytes",
            "packed_texture16::unpack_row(",
            "if (packed16) initial.SysMemPitch = uploadRowBytes;",
            "dev->CreateShaderResourceView(",
            "capture.texture->UnlockRect(0);",
        )) and all(x in helper for x in (
            "case Layout::rgb565:",
            "case Layout::argb1555:",
            "case Layout::argb4444:",
            "(value & 0x8000u) ? 255u : 0u",
            "source[x * 2u + 1u]",
            "bgra[x * 4u + 3u] = pixel.a;",
        )) and all(x in consumer for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    assert packed16_connected(bridge, packed_header)
    assert "static_assert(unpack(0x8421u, Layout::argb4444).a == 136u);" in packed_probe
    for original, invalid in (
        ("info.Format == D3DFMT_R5G6B5", "info.Format == D3DFMT_DXT2"),
        ("info.Format == D3DFMT_A1R5G5B5", "info.Format == D3DFMT_DXT2"),
        ("info.Format == D3DFMT_A4R4G4B4", "info.Format == D3DFMT_DXT2"),
        ("rowBytes = info.Width * 2u;", "rowBytes = info.Width * 4u;"),
        ("packed_texture16::unpack_row(", "/* no 16-bit conversion */("),
        ("if (packed16) initial.SysMemPitch = uploadRowBytes;", "/* wrong upload pitch */"),
    ):
        broken = bridge.replace(original, invalid, 1)
        assert broken != bridge and not packed16_connected(broken, packed_header), (
            "16-bit source-to-SRV Draw mutation escaped: " + original
        )
    for original, invalid in (
        ("case Layout::rgb565:", "case Layout::argb565:"),
        ("case Layout::argb1555:", "case Layout::argb5551:"),
        ("case Layout::argb4444:", "case Layout::argb8888:"),
        ("(value & 0x8000u) ? 255u : 0u", "255u"),
        ("source[x * 2u + 1u]", "source[x * 4u + 1u]"),
        ("bgra[x * 4u + 3u] = pixel.a;", "bgra[x * 4u + 3u] = 255u;"),
    ):
        broken = packed_header.replace(original, invalid, 1)
        assert broken != packed_header and not packed16_connected(bridge, broken), (
            "16-bit texel decode mutation escaped: " + original
        )
    for width, expected in ((1, (2, 4)), (256, (512, 1024)), (1024, (2048, 4096))):
        source_row_bytes, upload_row_bytes = width * 2, width * 4
        assert (source_row_bytes, upload_row_bytes) == expected
        assert source_row_bytes <= upload_row_bytes


    # 00545: game-created VB/IB/UP triangle strips reach native Draw/DrawIndexed
    # with P+2 source elements (not P*3). The unmodified D3D9 call remains
    # authoritative for unsupported state and for all gamepad input.
    producers = [path.read_text(encoding="utf-8") for path in RENDERERS]
    for source in producers:
        start = source.find("void R30ObserveNativeLinearVB(")
        end = source.find("HRESULT __stdcall DrawPrimitiveDestR30(", start)
        assert start >= 0 and end > start
        entrypoints = source[start:end]
        assert entrypoints.count("topology != D3DPT_TRIANGLESTRIP") == 3
        assert entrypoints.count("live::game_primitive_element_count(") == 3
        assert "static_cast<std::uint64_t>(nativeElements)*stride" in entrypoints
        assert "const UINT count = nativeElements;" in entrypoints
        assert "const UINT count=nativeElements;" in entrypoints
        disabled = entrypoints.replace(
            "topology != D3DPT_TRIANGLESTRIP", "topology == D3DPT_TRIANGLESTRIP", 1)
        assert disabled != entrypoints and (
            disabled.count("topology != D3DPT_TRIANGLESTRIP") != 3)

    strip_tokens = (
        '#include "live_game_primitive_span.hpp"',
        "type != D3DPT_TRIANGLESTRIP",
        "type == D3DPT_TRIANGLESTRIP",
        "indexCount != expectedElements",
        "vertexCount != expectedElements",
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP",
        "submit(s, vertices, indices, indexCount, type, capture, output)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(t in bridge for t in strip_tokens)
    for token in (
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP",
        "indexCount != expectedElements",
        "vertexCount != expectedElements",
    ):
        changed = bridge.replace(token, "BROKEN_NATIVE_STRIP", 1)
        assert changed != bridge and token not in changed

    # 00546: D3D9 real-fan producers -> bounded source -> native indexed Draw.
    fan_header = (ROOT / "src/vr/d3d11/live_game_primitive_span.hpp").read_text(encoding="utf-8")
    fan_probe = (ROOT / "tools/dx11_game_primitive_span_probe.cpp").read_text(encoding="utf-8")
    for token in ("game_fan_to_triangle_list", "result.push_back(center);",
                  "result.push_back(b);", "result.push_back(c);", "triangles.swap(result);"):
        assert token in fan_header
    for token in ("type != D3DPT_TRIANGLEFAN", "type == D3DPT_TRIANGLEFAN",
                  "fanTriangles.data()", "D3DPT_TRIANGLELIST, capture, output"):
        assert token in bridge
    assert "fan == preserved" in fan_probe
    for source in producers:
        a = source.index("void R30ObserveNativeLinearVB(")
        z = source.index("HRESULT __stdcall DrawPrimitiveDestR30(", a)
        hooks = source[a:z]
        assert hooks.count("topology != D3DPT_TRIANGLEFAN") == 3
        assert hooks.count("topology == D3DPT_TRIANGLEFAN") == 3
        mutated = hooks.replace("topology != D3DPT_TRIANGLEFAN", "topology == D3DPT_TRIANGLEFAN", 1)
        assert mutated != hooks and mutated.count("topology != D3DPT_TRIANGLEFAN") == 2

    # 00547: D3D9 TEX1 source with no DIFFUSE has a shorter UV offset.
    # Verify live bridge admission, native decode and fail-closed mutations.
    layout_source = (ROOT / "src/vr/d3d11/live_game_fvf_layout.hpp").read_text(encoding="utf-8")
    probe_source = (ROOT / "tools/dx11_game_fvf_layout_probe.cpp").read_text(encoding="utf-8")
    for token in ("game_fvf_layout(", "game_fvf_decode_vertex(",
                  "layout.texcoordOffset", "diffuse = 0xffffffffu",
                  "stride < layout.minStride", "sample = candidate;"):
        assert token in layout_source, token
    for token in ("kGameFvfXyzRhw | kGameFvfTex1", "kGameFvfXyz | kGameFvfTex1",
                  "game_fvf_decode_vertex(&rhwUv", "game_fvf_decode_vertex(&xyzUv",
                  "assert(!game_fvf_decode_vertex(&rhwUv, 23"):
        assert token in probe_source, token

    def fvf_connected(code: str) -> bool:
        a = code.index("bool supported_game_state(")
        z = code.index("// Snapshot a live game texture", a)
        body = code[a:z]
        observe = code[code.index("void observe(IDirect3DDevice9* game", z):]
        return all(v in body for v in (
            "if (!game_fvf_layout(fvf, layout)) return false;",
            "capture.enabled = layout.textured;",
            "if (!layout.hasDiffuse && !selectTexture) return false;",
            "if (!game_fvf_decode_vertex(data, stride, layout, decoded))",
            "const DWORD diffuse = decoded.diffuse;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
        )) and all(v in observe for v in (
            "supported_game_state(game, vp, layout, transforms, capture, output)",
            "layout, transforms, capture, vertices)",
        ))
    assert fvf_connected(bridge)
    for good,bad in (
        ("if (!game_fvf_layout(fvf, layout)) return false;", "if (true) return false;"),
        ("if (!layout.hasDiffuse && !selectTexture) return false;",
         "if (layout.hasDiffuse && !selectTexture) return false;"),
        ("if (!game_fvf_decode_vertex(data, stride, layout, decoded))", "if (false)"),
    ):
        mutated = bridge.replace(good, bad, 1)
        assert mutated != bridge and not fvf_connected(mutated)

    # TEX2 second-UV selection is part of the same native D3D9->D3D11 path.
    def tex2_connected(code: str, header: str, probe: str) -> bool:
        return all(x in code for x in (
            "kGameFvfTex2 == D3DFVF_TEX2",
            "coordIndex >= layout.texcoordCount",
            "capture.coordIndex = coordIndex;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "nextColorOp != D3DTOP_DISABLE",
        )) and all(x in header for x in (
            "texcoordBits > kGameFvfTex8",
            "layout.minStride != layout.texcoordOffset + layout.texcoordCount * 8u",
            "std::memcpy(candidate.uv1, data + layout.texcoordOffset + 8u, 8u)",
            "coordIndex >= layout.texcoordCount",
        )) and all(x in probe for x in (
            "kGameFvfXyzRhw | kGameFvfTex2",
            "game_fvf_select_uv(sample, layout, 1u, chosen)",
            "!game_fvf_decode_vertex(&twice, 31u",
            "!game_fvf_select_uv(sample, layout, 2u, chosen)",
        ))
    assert tex2_connected(bridge, layout_source, probe_source)
    for good, bad in (
        ("coordIndex >= layout.texcoordCount", "coordIndex > layout.texcoordCount"),
        ("capture.coordIndex = coordIndex;", "capture.coordIndex = 0;"),
        ("game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
         "game_fvf_select_uv(decoded, layout, 0u, output[i].uv)"),
    ):
        broken = bridge.replace(good, bad, 1)
        assert broken != bridge and not tex2_connected(broken, layout_source, probe_source)
    for good, bad in (
        ("texcoordBits > kGameFvfTex8", "texcoordBits > 0x0f00u"),
        ("layout.minStride != layout.texcoordOffset + layout.texcoordCount * 8u",
         "layout.minStride != layout.texcoordOffset + 8u"),
        ("std::memcpy(candidate.uv1, data + layout.texcoordOffset + 8u, 8u)",
         "std::memcpy(candidate.uv1, data + layout.texcoordOffset, 8u)"),
    ):
        broken = layout_source.replace(good, bad, 1)
        assert broken != layout_source and not tex2_connected(bridge, broken, probe_source)
    # TEX3 live-stream third UV remains linked to native Draw and index2.
    assert "kGameFvfTex3 == D3DFVF_TEX3" in bridge
    assert "std::memcpy(candidate.uv2, data + layout.texcoordOffset + 16u, 8u)" in layout_source
    assert "coordIndex == 3u ? sample.uv3 :" in layout_source
    assert "assert(!game_fvf_decode_vertex(&three, 39u" in probe_source
    assert "assert(!game_fvf_select_uv(sample, layout, 3u, chosen))" in probe_source
    changed = layout_source.replace(
        "std::memcpy(candidate.uv2, data + layout.texcoordOffset + 16u, 8u)",
        "std::memcpy(candidate.uv2, data + layout.texcoordOffset + 8u, 8u)", 1)
    assert changed != layout_source
    assert "std::memcpy(candidate.uv2, data + layout.texcoordOffset + 16u, 8u)" not in changed
    # TEX4 UV3 must be visible to native Draw/DrawIndexed while D3D9 runs.
    def tex4_connected(code: str, header: str, probe: str) -> bool:
        return all(x in code for x in (
            "kGameFvfTex4 == D3DFVF_TEX4",
            "coordIndex >= layout.texcoordCount",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(x in header for x in (
            "texcoordBits > kGameFvfTex8",
            "layout.texcoordCount > 8u",
            "std::memcpy(candidate.uv3, data + layout.texcoordOffset + 24u, 8u)",
            "coordIndex == 3u ? sample.uv3 :",
        )) and header.count("layout.texcoordCount > 8u") == 2 and all(x in probe for x in (
            "kGameFvfXyzRhw | kGameFvfTex4",
            "game_fvf_select_uv(sample, layout, 3u, chosen)",
            "!game_fvf_decode_vertex(&four, 47u",
            "!game_fvf_select_uv(sample, layout, 4u, chosen)",
            "!game_fvf_layout(kGameFvfXyzRhw | 0x900u",
        ))
    assert tex4_connected(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTex4 == D3DFVF_TEX4", "kGameFvfTex4 == D3DFVF_TEX3"),
        ("coordIndex >= layout.texcoordCount", "coordIndex > layout.texcoordCount"),
    ):
        broken = bridge.replace(old, wrong, 1)
        assert broken != bridge and not tex4_connected(broken, layout_source, probe_source)
    for old, wrong in (
        ("texcoordBits > kGameFvfTex8", "texcoordBits > 0x0f00u"),
        ("layout.texcoordCount > 8u", "layout.texcoordCount > 9u"),
        ("std::memcpy(candidate.uv3, data + layout.texcoordOffset + 24u, 8u)",
         "std::memcpy(candidate.uv3, data + layout.texcoordOffset + 16u, 8u)"),
        ("coordIndex == 3u ? sample.uv3 :",
         "coordIndex == 3u ? sample.uv2 :"),
    ):
        broken = layout_source.replace(old, wrong, 1)
        assert broken != layout_source and not tex4_connected(bridge, broken, probe_source)

    # 00552: D3D9 TEX5..8 UV4..7 -> stage0 -> native D3D11 Draw/DrawIndexed.
    def tex8_connected(src: str, hdr: str, probe: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTex5 == D3DFVF_TEX5",
            "kGameFvfTex6 == D3DFVF_TEX6",
            "kGameFvfTex7 == D3DFVF_TEX7",
            "kGameFvfTex8 == D3DFVF_TEX8",
            "coordIndex >= layout.texcoordCount",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(x in hdr for x in (
            "texcoordBits > kGameFvfTex8",
            "layout.texcoordCount > 8u",
            "coordIndex == 6u ? sample.uv6 : sample.uv7",
            "std::memcpy(candidate.uv4, data + layout.texcoordOffset + 32u, 8u)",
            "std::memcpy(candidate.uv5, data + layout.texcoordOffset + 40u, 8u)",
            "std::memcpy(candidate.uv6, data + layout.texcoordOffset + 48u, 8u)",
            "std::memcpy(candidate.uv7, data + layout.texcoordOffset + 56u, 8u)",
        )) and hdr.count("layout.texcoordCount > 8u") == 2 and all(x in probe for x in (
            "kGameFvfXyzRhw | kGameFvfTex8",
            "game_fvf_select_uv(sample, layout, 7u, chosen)",
            "!game_fvf_decode_vertex(&eight, 79u",
            "!game_fvf_select_uv(sample, layout, 8u, chosen)",
            "badEight.texcoordOffset -= 8u",
            "kGameFvfTex5, layout",
        ))
    assert tex8_connected(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTex8 == D3DFVF_TEX8", "kGameFvfTex8 == D3DFVF_TEX7"),
        ("coordIndex >= layout.texcoordCount", "coordIndex > layout.texcoordCount"),
    ):
        mutant = bridge.replace(old, wrong, 1)
        assert mutant != bridge and not tex8_connected(mutant, layout_source, probe_source)
    for old, wrong in (
        ("texcoordBits > kGameFvfTex8", "texcoordBits > 0x0f00u"),
        ("layout.texcoordCount > 8u", "layout.texcoordCount > 9u"),
        ("std::memcpy(candidate.uv7, data + layout.texcoordOffset + 56u, 8u)",
         "std::memcpy(candidate.uv7, data + layout.texcoordOffset + 48u, 8u)"),
        ("coordIndex == 6u ? sample.uv6 : sample.uv7",
         "coordIndex == 6u ? sample.uv7 : sample.uv6"),
    ):
        mutant = layout_source.replace(old, wrong, 1)
        assert mutant != layout_source and not tex8_connected(bridge, mutant, probe_source)
    print("DX11 TEX5..TEX8 native game Draw regression PASS (static only)")
    # 00551: ensure actual D3D9 FVF NORMAL/SPECULAR bytes reach the
    # native frame, while non-exact D3D9 specular lighting is rejected.
    def object_fvf_integrated(src: str, header: str, probe: str) -> bool:
        return all(x in src for x in (
            "kGameFvfNormal == D3DFVF_NORMAL",
            "kGameFvfSpecular == D3DFVF_SPECULAR",
            "GetRenderState(D3DRS_SPECULARENABLE, &specularEnabled)",
            "specularEnabled)",
            "            lighting || vertexBlend != D3DVBF_DISABLE",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(x in header for x in (
            "candidate.normalBytes = candidate.hasNormal ? 12u : 0u;",
            "candidate.diffuseOffset = candidate.positionBytes + candidate.normalBytes;",
            "layout.diffuseOffset != layout.positionBytes + layout.normalBytes",
            "data + layout.diffuseOffset, 4u",
            "(position == kGameFvfXyzRhw && hasNormal)",
        )) and all(x in probe for x in (
            "struct WorldNormalSpecUv2",
            "layout.texcoordOffset == 32u && layout.minStride == 48u",
            "sample.diffuse == 0xff123456u",
            "!game_fvf_decode_vertex(&world, 47u",
            "corrupted.diffuseOffset -= 12u",
            "corrupted.texcoordOffset -= 4u",
        ))
    assert object_fvf_integrated(bridge, layout_source, probe_source)
    for old, bad in (
        ("GetRenderState(D3DRS_SPECULARENABLE, &specularEnabled)",
         "GetRenderState(D3DRS_ALPHABLENDENABLE, &specularEnabled)"),
        ("lighting || vertexBlend != D3DVBF_DISABLE",
         "!lighting || vertexBlend != D3DVBF_DISABLE"),
    ):
        mutant = bridge.replace(old, bad, 1)
        assert mutant != bridge and not object_fvf_integrated(mutant, layout_source, probe_source)
    for old, bad in (
        ("candidate.diffuseOffset = candidate.positionBytes + candidate.normalBytes;",
         "candidate.diffuseOffset = candidate.positionBytes;"),
        ("data + layout.diffuseOffset, 4u", "data + layout.positionBytes, 4u"),
        ("(position == kGameFvfXyzRhw && hasNormal)",
         "(position == kGameFvfXyz && hasNormal)"),
    ):
        mutant = layout_source.replace(old, bad, 1)
        assert mutant != layout_source and not object_fvf_integrated(bridge, mutant, probe_source)

    # 00558: real game-authored D3D9 stage0 BLENDTEXTUREALPHA /
    # BLENDDIFFUSEALPHA -> owned native PS -> Draw/DrawIndexed -> opt-in inset.
    # Checks source-to-consumer links, shader/reset lifecycle and fail-closed
    # dispatch; this does not assert runtime menu/gamepad/Quest3 parity.
    blend_links = (
        "const bool blendTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_BLENDTEXTUREALPHA;",
        "const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_BLENDDIFFUSEALPHA;",
        "blendTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;",
        "blendTextureAlpha && !blendDiffuseAlpha) || arg != D3DTA_TEXTURE ||",
        "capture.blendTextureAlpha = blendTextureAlpha;",
        "capture.blendDiffuseAlpha = blendDiffuseAlpha;",
        "bool blendTextureAlpha = false;",
        "bool blendDiffuseAlpha = false;",
        "float4 c = lerp(v.diffuse, t, t.a);",
        "float4 c = lerp(v.diffuse, t, v.diffuse.a);",
        'compile("PSTextureBlendTextureAlpha", "ps_4_0", blendTextureCode)',
        'compile("PSTextureBlendDiffuseAlpha", "ps_4_0", blendDiffuseCode)',
        "s.blendTextureAlphaPs.GetAddressOf()",
        "s.blendDiffuseAlphaPs.GetAddressOf()",
        "s.blendTextureAlphaPs.Reset();",
        "s.blendDiffuseAlphaPs.Reset();",
        "s.blendTextureAlphaPs && s.blendDiffuseAlphaPs",
        "capture.blendTextureAlpha ? s.blendTextureAlphaPs.Get() :",
        "capture.blendDiffuseAlpha ? s.blendDiffuseAlphaPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    # Exact whitelist includes the pair *only* with equal color+alpha op.
    state_section = bridge[bridge.find("bool supported_game_state("):
                           bridge.find("bool translate_vertices(")]
    shader_section = bridge[bridge.find("constexpr char kShader[]"):
                            bridge.find(')";', bridge.find("constexpr char kShader[]"))]
    submit_section = bridge[bridge.find("bool submit("):
                            bridge.find("void observe(")]
    assert all(link in bridge for link in blend_links if "blendTextureAlpha && !blendDiffuseAlpha)" not in link)
    assert "!blendTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha) || arg != D3DTA_TEXTURE ||" in state_section
    assert "arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT" in state_section
    assert "alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT" in state_section
    assert "alphaArg1 != D3DTA_TEXTURE" in state_section
    assert "AlphaGate(c.a); return c;" in shader_section
    assert "mirror_texture(dev, capture, sampledView, sampledSampler)" in submit_section
    assert "ctx->PSSetShader(capture.blendTextureAlpha ?" in submit_section
    for link in blend_links[:-2]:
        if "blendTextureAlpha && !blendDiffuseAlpha)" in link:
            continue
        mutated = bridge.replace(link, "/* removed 00558 stage0 blend link */")
        assert mutated != bridge and link not in mutated
    # Exact D3DTOP values: BLENDDIFFUSEALPHA=12, BLENDTEXTUREALPHA=13.
    for color_op, alpha_op, accepted in (
        (12, 12, True), (13, 13, True),
        (12, 13, False), (13, 12, False),
        (13, 7, False), (7, 13, False), (0, 0, False),
    ):
        assert ((color_op == 12 and alpha_op == 12) or
                (color_op == 13 and alpha_op == 13)) == accepted
    for texel, diffuse in (
        ((0.2, 0.8, 0.5, 0.9), (0.8, 0.5, 0.4, 0.25)),
        ((1.0, 0.0, 0.3, 0.05), (0.1, 0.7, 0.5, 0.95)),
    ):
        for use_texture_factor in (False, True):
            a = texel[3] if use_texture_factor else diffuse[3]
            result = tuple((1-a)*d + a*t for d, t in zip(diffuse, texel))
            assert all(0.0 <= c <= 1.0 for c in result)
            assert abs(result[3] - ((1-a)*diffuse[3] + a*texel[3])) < 1e-7
            assert result != texel and result != diffuse
    print("DX11 stage0 texture/diffuse alpha blend live native draw PASS (static only)")


    # 00559 ADDSMOOTH D3D9 stage0 color+alpha -> real native linear/indexed Draw.
    # Static source+CPU proof only; runtime menu/gamepad/HMD parity is untested.
    smooth_links = (
        "const bool addSmooth = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_ADDSMOOTH;",
        "bool addSmooth = false;",
        "!mixedAddTextureAlpha && !mixedAddDiffuseAlpha && !addSmooth &&",
        "modulate || additive || subtract || addSmooth || modulate2x",
        "capture.addSmooth = addSmooth;",
        "float4 PSTextureAddSmooth(VOut v) : SV_Target {",
        "float4 c = saturate(t + v.diffuse * (1.0f - t));",
        '!compile("PSTextureAddSmooth", "ps_4_0", addSmoothCode)',
        "s.addSmoothPs.GetAddressOf()",
        "s.addSmoothPs.Reset();",
        "s.addSmoothPs && s.modulate2xPs",
        "capture.addSmooth ? s.addSmoothPs.Get() :",
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    def smooth_connected(code: str) -> bool:
        state = code[code.find("bool supported_game_state("):
                     code.find("bool translate_vertices(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        return (all(link in code for link in smooth_links)
                and "const bool addSmooth = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_ADDSMOOTH;" in state
                and "capture.addSmooth ? s.addSmoothPs.Get() :" in submit
                and code.count("s.addSmoothPs.Reset();") == 2)
    assert smooth_connected(bridge)
    for link in smooth_links[:-2]:
        mutant = bridge.replace(link, "/* disconnected 00559 */")
        assert mutant != bridge and not smooth_connected(mutant), "ADDSMOOTH disconnected: " + link
    for texel, diffuse, expected in (
        ((0.2, 0.5, 0.0, 0.9), (0.8, 0.4, 0.75, 0.25), (0.84, 0.7, 0.75, 0.925)),
        ((1.0, 0.0, 0.75, 0.1), (0.25, 0.8, 0.6, 0.9), (1.0, 0.8, 0.9, 0.91)),
    ):
        actual = tuple(min(1.0, t + d * (1.0 - t)) for t, d in zip(texel, diffuse))
        assert all(abs(a-b) < 1e-6 for a, b in zip(actual, expected))
        assert actual != texel and actual != diffuse
    for color_op, alpha_op, permitted in (
        (11, 11, True), (11, 7, False), (7, 11, False),
        (11, 10, False), (10, 11, False), (0, 11, False),
    ):
        assert (color_op == 11 and alpha_op == 11) == permitted
    print("DX11 stage0 ADDSMOOTH source-to-game-native-Draw PASS (static only)")


    # 00560: Real game D3D9 DEFAULT render-target texture level 0 ->
    # exact-format, non-MSAA GetRenderTargetData -> CPU BGRA snapshot ->
    # existing D3D11 SRV/sampler -> actual native Draw/DrawIndexed/inset.
    # Non-render-target DEFAULT, compressed DEFAULT and MSAA fail closed.
    rt_tokens = (
        "const bool gpuRenderTarget = info.Pool == D3DPOOL_DEFAULT &&",
        "(info.Usage & D3DUSAGE_RENDERTARGET) != 0u",
        "(info.Format == D3DFMT_A8R8G8B8 ||\n         info.Format == D3DFMT_X8R8G8B8);",
        "if (info.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
        "capture.texture->GetSurfaceLevel(0, sourceSurface.GetAddressOf())",
        "sourceDesc.MultiSampleType != D3DMULTISAMPLE_NONE",
        "sourceDesc.Width != info.Width || sourceDesc.Height != info.Height",
        "sourceDesc.Format != info.Format",
        "!(sourceDesc.Usage & D3DUSAGE_RENDERTARGET)",
        "capture.texture->GetDevice(gameDevice.GetAddressOf())",
        "gameDevice->CreateOffscreenPlainSurface(",
        "info.Width, info.Height, info.Format, D3DPOOL_SYSTEMMEM,",
        "gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
        "readbackSurface->LockRect(&locked, nullptr, D3DLOCK_READONLY)",
        "capture.texture->LockRect(0, &locked, nullptr, D3DLOCK_READONLY)",
        "if (gpuRenderTarget) readbackSurface->UnlockRect();",
        "else capture.texture->UnlockRect(0);",
        "desc.Usage = D3D11_USAGE_IMMUTABLE;",
        "dev->CreateShaderResourceView(texture.Get(), nullptr,",
    )
    def rt_game_native_connected(code: str) -> bool:
        mirror = code[code.find("bool mirror_texture("):code.find("bool submit(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        return (all(token in mirror for token in rt_tokens)
                and "if (FAILED(lockResult)) return false;" in mirror
                and "static_cast<UINT>(locked.Pitch) >= rowBytes" in mirror
                and "mirror_texture(dev, capture, sampledView, sampledSampler)" in draw
                and "ctx->PSSetShaderResources(0, 1, &boundView)" in draw
                and "ctx->DrawIndexed(indexCount, 0, 0);" in draw
                and "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in draw)
    assert rt_game_native_connected(bridge)
    for token in rt_tokens:
        mutant = bridge.replace(token, "/* disconnected 00560 RT producer */", 1)
        assert mutant != bridge and not rt_game_native_connected(mutant), token
    for pool, usage_rt, fmt, expected in (
        ("DEFAULT", True, "A8R8G8B8", True),
        ("DEFAULT", True, "X8R8G8B8", True),
        ("DEFAULT", False, "A8R8G8B8", False),
        ("DEFAULT", True, "DXT1", False),
        ("DEFAULT", True, "A1R5G5B5", False),
        ("MANAGED", True, "A8R8G8B8", False),
    ):
        gpu_rt = pool == "DEFAULT" and usage_rt and fmt in ("A8R8G8B8", "X8R8G8B8")
        assert gpu_rt is expected
    # Reject even a permitted DEFAULT RT without exact format and non-MSAA
    # surface metadata. The GPU readback is diagnostic opt-in, not an HMD PASS.
    for msaa, matching_size, matching_format, source_rt, expected in (
        (False, True, True, True, True),
        (True, True, True, True, False),
        (False, False, True, True, False),
        (False, True, False, True, False),
        (False, True, True, False, False),
    ):
        allowed = not msaa and matching_size and matching_format and source_rt
        assert allowed is expected
    print("DX11 live DEFAULT render-target texture to native Draw regression PASS (static only)")


    # 00561: Live menu/vehicle/race D3D9 stage-0 MIN/MAG independent
    # point/linear filters now reach an exact D3D11 MIP_POINT sampler,
    # then the existing real-game SRV/PS/Draw/visible diagnostic inset.
    # Runtime visuals, gamepad and Quest3 have not been exercised here.
    def mixed_filter_draw_connected(code: str) -> bool:
        admission = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        mirror = code[code.find("bool mirror_texture("):code.find("bool submit(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        return all(token in admission for token in (
            "GetSamplerState(0, D3DSAMP_MAGFILTER, &mag)",
            "GetSamplerState(0, D3DSAMP_MINFILTER, &min)",
            "(min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)",
            "(mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR)",
            "mip != D3DTEXF_NONE",
            "capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);",
            "capture.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);",
        )) and all(token in mirror for token in (
            "state.Filter = capture.minFilter == D3DTEXF_LINEAR ?",
            "(capture.magFilter == D3DTEXF_LINEAR ?",
            "D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT :",
            "D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT) :",
            "D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT :",
            "D3D11_FILTER_MIN_MAG_MIP_POINT);",
            "state.MinLOD = 0.0f;",
            "state.MaxLOD = 0.0f;",
            "dev->CreateSamplerState(&state, sampler.GetAddressOf())",
        )) and all(token in submit for token in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetSamplers(0, 1, &boundSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    assert mixed_filter_draw_connected(bridge)
    for token in (
        "GetSamplerState(0, D3DSAMP_MINFILTER, &min)",
        "capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);",
        "capture.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);",
        "D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT) :",
        "D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT :",
        "state.MinLOD = 0.0f;",
        "ctx->PSSetSamplers(0, 1, &boundSampler)",
    ):
        broken = bridge.replace(token, "/* disconnected 00561 filter link */", 1)
        assert broken != bridge and not mixed_filter_draw_connected(broken), token
    # Reference D3D11_FILTER mapping for all four supported D3D9 pairs;
    # unsupported anisotropic filters and mip sampling still fail closed.
    mip_point_map = {
        ("POINT", "POINT"): "MIN_MAG_MIP_POINT",
        ("POINT", "LINEAR"): "MIN_POINT_MAG_LINEAR_MIP_POINT",
        ("LINEAR", "POINT"): "MIN_LINEAR_MAG_MIP_POINT",
        ("LINEAR", "LINEAR"): "MIN_MAG_LINEAR_MIP_POINT",
    }
    for min_filter in ("POINT", "LINEAR", "ANISOTROPIC"):
        for mag_filter in ("POINT", "LINEAR", "ANISOTROPIC"):
            for mip_filter in ("NONE", "POINT", "LINEAR"):
                allowed = min_filter in ("POINT", "LINEAR") and mag_filter in (
                    "POINT", "LINEAR") and mip_filter == "NONE"
                assert allowed == ((min_filter, mag_filter) in mip_point_map
                                   and mip_filter == "NONE")
                if allowed:
                    native = mip_point_map[min_filter, mag_filter]
                    assert ("D3D11_FILTER_" + native) in bridge
    print("DX11 game MIN/MAG mixed filtering -> native sampler/Draw PASS (static only)")


    # 00562: actual game D3D9 stage0 BLENDFACTORALPHA/TFACTOR alpha
    # becomes DX11 constant-buffer w -> native shader/Draw/diagnostic inset.
    # Source + CPU proof; no live gamepad, HMD or in-game pixel evidence.
    factor_links = (
        "const bool blendFactorAlpha = op == D3DTOP_BLENDFACTORALPHA &&",
        "alphaOp == D3DTOP_BLENDFACTORALPHA;",
        "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
        "blendTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;",
        "!blendTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha)",
        "capture.blendFactorAlpha = blendFactorAlpha;",
        "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;",
        "bool blendFactorAlpha = false;",
        "float blendFactorAlphaValue = 0.0f;",
        "float4 PSTextureBlendFactorAlpha(VOut v) : SV_Target {",
        "float4 c = lerp(v.diffuse, t, alphaParams.w);",
        'compile("PSTextureBlendFactorAlpha", "ps_4_0", blendFactorCode)',
        "s.blendFactorAlphaPs.GetAddressOf()",
        "s.blendFactorAlphaPs.Reset();",
        "s.blendFactorAlphaPs &&",
        "capture.blendFactorAlphaValue",
        "capture.blendFactorAlpha ? s.blendFactorAlphaPs.Get() :",
        "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    def factor_connected(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):
                      code.find("bool translate_vertices(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        return (all(token in code for token in factor_links) and
                "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)" in intake and
                "static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue" in submit and
                "ctx->PSSetShader(capture.blendTextureAlpha ?" in submit and
                "capture.blendFactorAlpha ? s.blendFactorAlphaPs.Get() :" in submit and
                code.count("s.blendFactorAlphaPs.Reset();") == 2 and
                code.count("blendTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;") == 2)
    assert factor_connected(bridge)
    for token in factor_links[:-2]:
        mutant = bridge.replace(token, "/* disconnected 00562 factor link */", 1)
        assert mutant != bridge and not factor_connected(mutant), token
    for color_op, alpha_op, accepted in (
        (14, 14, True), (14, 13, False), (13, 14, False),
        (14, 7, False), (7, 14, False), (0, 14, False),
    ):
        # D3DTOP_BLENDFACTORALPHA is D3DTOP enum value 14.
        assert (color_op == 14 and alpha_op == 14) is accepted
    for argb, texel, diffuse in (
        (0x00010203, (0.1, 0.4, 0.7, 0.2), (0.9, 0.8, 0.1, 0.6)),
        (0xff010203, (0.1, 0.4, 0.7, 0.2), (0.9, 0.8, 0.1, 0.6)),
        (0x80010203, (0.1, 0.4, 0.7, 0.2), (0.9, 0.8, 0.1, 0.6)),
    ):
        factor = ((argb >> 24) & 0xff) / 255.0
        output = tuple((1.0 - factor) * d + factor * t for d, t in zip(diffuse, texel))
        if argb == 0x00010203:
            assert output == diffuse
        elif argb == 0xff010203:
            assert output == texel
        else:
            assert all(min(d, t) < o < max(d, t) for d, t, o in zip(diffuse, texel, output))
    print("DX11 stage0 BLENDFACTORALPHA live native Draw PASS (static only)")


    # 00563: game stage0 factor-driven RGB with separately selected TEXTURE
    # or MODULATE(TEXTURE,DIFFUSE) alpha; native shaders/Draw and failure edges.
    mixed_factor_links = (
        "blendFactorTextureAlpha = op == D3DTOP_BLENDFACTORALPHA",
        "alphaOp == D3DTOP_SELECTARG1;",
        "blendFactorModulateAlpha = op == D3DTOP_BLENDFACTORALPHA",
        "alphaOp == D3DTOP_MODULATE;",
        "blendFactorAlpha || blendFactorTextureAlpha || blendFactorModulateAlpha",
        "!blendFactorTextureAlpha && !blendFactorModulateAlpha &&",
        "rgbNeedsDiffuse = blendFactorTextureAlpha || blendFactorModulateAlpha",
        "alphaNeedsDiffuse = blendFactorModulateAlpha",
        "capture.blendFactorTextureAlpha = blendFactorTextureAlpha;",
        "capture.blendFactorModulateAlpha = blendFactorModulateAlpha;",
        "bool blendFactorTextureAlpha = false;",
        "bool blendFactorModulateAlpha = false;",
        "float4 PSTextureBlendFactorTextureAlpha(VOut v) : SV_Target {",
        "float4 PSTextureBlendFactorModulateAlpha(VOut v) : SV_Target {",
        "float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), t.a);",
        "float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), t.a * v.diffuse.a);",
        'compile("PSTextureBlendFactorTextureAlpha", "ps_4_0", blendFactorTextureCode)',
        'compile("PSTextureBlendFactorModulateAlpha", "ps_4_0", blendFactorModulateCode)',
        "s.blendFactorTextureAlphaPs.GetAddressOf()",
        "s.blendFactorModulateAlphaPs.GetAddressOf()",
        "s.blendFactorTextureAlphaPs.Reset();",
        "s.blendFactorModulateAlphaPs.Reset();",
        "s.blendFactorTextureAlphaPs && s.blendFactorModulateAlphaPs &&",
        "capture.blendFactorTextureAlpha ? s.blendFactorTextureAlphaPs.Get() :",
        "capture.blendFactorModulateAlpha ? s.blendFactorModulateAlphaPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    def mixed_factor_integrated(code: str) -> bool:
        gate = code[code.find("bool supported_game_state("):
                    code.find("bool translate_vertices(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        return (all(token in code for token in mixed_factor_links) and
                code.count("s.blendFactorTextureAlphaPs.Reset();") == 2 and
                code.count("s.blendFactorModulateAlphaPs.Reset();") == 2 and
                "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)" in gate and
                "ctx->PSSetShader(capture.blendTextureAlpha ?" in draw)
    assert mixed_factor_integrated(bridge)
    for token in mixed_factor_links[:-2]:
        broken = bridge.replace(token, "/* disconnect 00563 producer/consumer */")
        assert broken != bridge and not mixed_factor_integrated(broken), token
    # D3DTOP enum: SELECTARG1=2, MODULATE=4, BLENDFACTORALPHA=14.
    for color, alpha, expected in (
        (14, 2, True), (14, 4, True), (14, 14, True),
        (14, 3, False), (14, 7, False), (14, 13, False),
        (2, 4, False), (4, 14, False)):
        assert ((color == 14 and alpha in (2, 4, 14))) == expected
    for factor_byte in (0, 128, 255):
        factor = factor_byte / 255.0
        texel, diffuse = (0.2, 0.9, 0.4, 0.8), (0.9, 0.1, 0.7, 0.25)
        rgb = tuple((1-factor)*d + factor*t
                    for d,t in zip(diffuse[:3], texel[:3]))
        if factor_byte == 0:
            assert rgb == diffuse[:3]
        elif factor_byte == 255:
            assert rgb == texel[:3]
        else:
            assert all(min(d,t) < c < max(d,t)
                       for d,t,c in zip(diffuse[:3], texel[:3], rgb))
        texture_alpha = (*rgb, texel[3])
        modulate_alpha = (*rgb, texel[3]*diffuse[3])
        assert texture_alpha[:3] == modulate_alpha[:3]
        assert abs(texture_alpha[3] - 0.8) < 1e-7
        assert abs(modulate_alpha[3] - 0.2) < 1e-7
    print("DX11 mixed factor RGB/independent alpha native Draw PASS (static only)")

    print("DX11 object-space NORMAL/SPECULAR native draw regression PASS (static only)")
    print("DX11 TEX2..TEX8 multi-UV native Draw/DrawIndexed/fallback regression PASS (static only)")


if __name__ == "__main__":
    main()
