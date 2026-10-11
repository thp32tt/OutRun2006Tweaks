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
            "D3DFVF_XYZRHW | D3DFVF_DIFFUSE",
            "D3DFVF_XYZ | D3DFVF_DIFFUSE",
            "GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)",
            "GetRenderState(D3DRS_LIGHTING, &lighting)",
            "GetRenderState(D3DRS_VERTEXBLEND, &vertexBlend)",
            "lighting || vertexBlend != D3DVBF_DISABLE",
            "GetTransform(D3DTS_WORLD, &transforms[0])",
            "GetTransform(D3DTS_VIEW, &transforms[1])",
            "GetTransform(D3DTS_PROJECTION, &transforms[2])",
        )
        required_vertices = (
            "const UINT diffuseOffset = pretransformed ? 16u : 12u;",
            "stride < diffuseOffset + (capture.enabled ? 12u : 4u)",
            "std::memcpy(xyz, data, diffuseOffset)",
            "std::memcpy(&diffuse, data + diffuseOffset",
            "next[col] += clip[row] * matrix.m[row][col];",
            "clip[3] <= 0.0f",
            "std::copy(clip.begin(), clip.end(), v.clip);",
        )
        return (all(x in state for x in required_state)
                and all(x in vertices for x in required_vertices)
                and "supported_game_state(game, vp, pretransformed, transforms, capture, output)" in observe
                and "pretransformed, transforms, capture, vertices)" in observe)

    assert object_space_draw_safe(bridge)
    for good, bad in (
        ("D3DFVF_XYZ | D3DFVF_DIFFUSE",
         "D3DFVF_XYZRHW | D3DFVF_DIFFUSE"),
        ("GetTransform(D3DTS_WORLD, &transforms[0])",
         "GetTransform(D3DTS_VIEW, &transforms[0])"),
        ("lighting || vertexBlend != D3DVBF_DISABLE",
         "lighting && vertexBlend != D3DVBF_DISABLE"),
        ("next[col] += clip[row] * matrix.m[row][col];",
         "next[col] += clip[row] * matrix.m[col][row];"),
        ("stride < diffuseOffset + (capture.enabled ? 12u : 4u)", "stride < 20u"),
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
            "pretransformed = (fvf == rhw || fvf == (rhw | D3DFVF_TEX1));",
            "fvf == (rhw | D3DFVF_TEX1)", "fvf == (xyz | D3DFVF_TEX1)",
            "GetTexture(0, tex.GetAddressOf())",
            "tex.As(&capture.texture)",
            "const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
            "const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
            "(!modulate && !selectTexture) || arg != D3DTA_TEXTURE",
            "alphaArg1 != D3DTA_TEXTURE",
            "(modulate && (arg2 != D3DTA_DIFFUSE || alphaArg2 != D3DTA_DIFFUSE))",
            "capture.selectTexture = selectTexture;",
            "coordIndex != 0 || transformFlags != D3DTTFF_DISABLE || srgb",
            "min != mag || mip != D3DTEXF_NONE",
            "nextColorOp != D3DTOP_DISABLE",
        )) and all(x in mirror for x in (
            "info.Pool == D3DPOOL_DEFAULT",
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
            "capture.selectTexture ? s.textureOnlyPs.Get() : s.sampledPs.Get()",
        ))
    assert texture_path_complete(bridge)
    for old, bad in (
        ("fvf == (rhw | D3DFVF_TEX1)", "fvf == rhw"),
        ("const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
         "const bool modulate = op == D3DTOP_MODULATE || alphaOp == D3DTOP_MODULATE;"),
        ("const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
         "const bool selectTexture = op == D3DTOP_SELECTARG1 || alphaOp == D3DTOP_SELECTARG1;"),
        ("(!modulate && !selectTexture) || arg != D3DTA_TEXTURE",
         "(!modulate && !selectTexture) && arg != D3DTA_TEXTURE"),
        ("(modulate && (arg2 != D3DTA_DIFFUSE || alphaArg2 != D3DTA_DIFFUSE))",
         "(modulate && (arg2 != D3DTA_DIFFUSE && alphaArg2 != D3DTA_DIFFUSE))"),
        ("capture.selectTexture = selectTexture;", "capture.selectTexture = false;"),
        ("info.Pool == D3DPOOL_DEFAULT", "info.Pool == D3DPOOL_SYSTEMMEM"),
        ("GetLevelCount() == 0", "GetLevelCount() != 1"),
        ("state.MaxLOD = 0.0f;", "state.MaxLOD = D3D11_FLOAT32_MAX;"),
        ("capture.texture->UnlockRect(0)", "/* missing texture unlock */"),
        ("ctx->PSSetShaderResources(0, 1, &boundView)",
         "/* no native shader texture binding */"),
        ("capture.selectTexture ? s.textureOnlyPs.Get() : s.sampledPs.Get()",
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
    # RGB and alpha must use the *same* supported operation: rejecting mixed
    # SELECTARG1/MODULATE keeps the original game draw authoritative.
    MODULATE, SELECTARG1 = 4, 2
    for color_op, alpha_op, supported in (
        (MODULATE, MODULATE, True),
        (SELECTARG1, SELECTARG1, True),
        (MODULATE, SELECTARG1, False),
        (SELECTARG1, MODULATE, False),
        (0, 0, False),
    ):
        admitted = ((color_op == MODULATE and alpha_op == MODULATE)
                    or (color_op == SELECTARG1 and alpha_op == SELECTARG1))
        assert admitted == supported


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
        consumer = code[code.find("bool submit("):code.find("void observe(")]
        return '#include "packed_texture_16bit.hpp"' in code and all(x in producer for x in (
            "info.Format == D3DFMT_R5G6B5",
            "info.Format == D3DFMT_A1R5G5B5",
            "info.Format == D3DFMT_A4R4G4B4",
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

    print("DX11 live diagnostic TEX1/DXT/packed16/alpha/scissor/COLORWRITE Draw/fallback regression PASS (static only)")


if __name__ == "__main__":
    main()
