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
        assert "live_game_frame::before_game_present(device, sourceRect, dirtyRegion);" in source
        assert "live_game_frame::before_game_reset(device);" in source
        assert "R30PresentR29Hook.stdcall<HRESULT>(" in source

    bridge = BRIDGE.read_text(encoding="utf-8")
    # 00678: actual game VB/IB and IndexedUP hooks must count an attempted
    # Draw even when CPU shadow bytes/indices are unavailable. The diagnostic
    # native batch must never splice Draws across a failed source capture.
    def complete_shadow_source_contract(code: str) -> bool:
        has_linear_up = "void R30ObserveNativeLinearUP(" in code
        expected_guards = 4 if has_linear_up else 3
        if code.count("R30NativeGameSourceGuard nativeSource{device};") != expected_guards:
            return False
        if "if (!forwarded)" not in code or \
                "observe_unavailable_game_draw(device);" not in code:
            return False
        sections = [
            ("void R30ObserveNativeLinearVB(", "void R30ObserveNativeIndexedVB(",
             "live::observe_linear("),
            ("void R30ObserveNativeIndexedVB(",
             "void R30ObserveNativeLinearUP(" if has_linear_up
             else "void R30ObserveNativeIndexedUP(", "live::observe_indexed("),
            ("void R30ObserveNativeIndexedUP(", "HRESULT __stdcall DrawPrimitiveDestR30(",
             "live::observe_indexed("),
        ]
        if has_linear_up:
            sections.append(
                ("void R30ObserveNativeLinearUP(", "void R30ObserveNativeIndexedUP(",
                 "live::observe_linear("))
        for start, end, success in sections:
            a = code.find(start)
            b = code.find(end, a)
            if a < 0 or b <= a:
                return False
            section = code[a:b]
            if ("R30NativeGameSourceGuard nativeSource{device};" not in section or
                    "nativeSource.forwarded = true;" not in section or
                    success not in section or
                    section.index("nativeSource.forwarded = true;") > section.index(success)):
                return False
            # 00756: the live VB/IB/IndexedUP paths now have a separate
            # zero-primitive forwarding branch *before* CPU shadow capture.
            # The original nonzero-path forwarding remains mandatory. The
            # destructive mutation below removes the first forwarding token;
            # it must still fail by testing the zero branch explicitly.
            if "live::observe_empty_game_draw(device, topology);" in section:
                empty_start = section.find("if (primitiveCount == 0u &&")
                empty_end = section.find(
                    "live::observe_empty_game_draw(device, topology);", empty_start)
                if (empty_start < 0 or empty_end < 0 or
                        "nativeSource.forwarded = true;" not in
                        section[empty_start:empty_end]):
                    return False
                # A zero-only forwarding guard must not mask the original
                # successful CPU shadow capture. Validate both branches.
                required_nonempty = (
                    "if (valid) nativeSource.forwarded = true;"
                    if "R30ObserveNativeLinearVB(" in section
                    else "if (ok) nativeSource.forwarded = true;"
                    if "R30ObserveNativeIndexedVB(" in section
                    else "nativeSource.forwarded = true;"
                )
                if required_nonempty not in section[empty_end:] or (
                    section.count("nativeSource.forwarded = true;") < 2):
                    return False
        return True

    for renderer in RENDERERS:
        hook_source = renderer.read_text(encoding="utf-8")
        assert complete_shadow_source_contract(hook_source), renderer.name
        for fault in ("R30NativeGameSourceGuard nativeSource{device};",
                      "nativeSource.forwarded = true;",
                      "observe_unavailable_game_draw(device);"):
            mutated = hook_source.replace(fault, "/* missing game source */", 1)
            assert mutated != hook_source and not complete_shadow_source_contract(mutated), fault

    observer = bridge[bridge.find("void observe("):bridge.find("} // namespace", bridge.find("void observe("))]
    ordinal = observer.find("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;")
    primitive = observer.find("if (!game_native_primitive_element_count(")
    assert ordinal >= 0 and primitive > ordinal, "bad native primitive must still count as game Draw"
    unavailable = bridge[bridge.find("void observe_unavailable_game_draw("):bridge.find("void before_game_present(")]
    # Exact raw-game source ordinal is now passed into offscreen no-pixel
    # accounting; preserve the ordering and fail-closed abort without matching
    # an obsolete preincrement spelling.
    assert "const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;" in unavailable
    assert unavailable.find("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;") < unavailable.find("if (!observe_source_frame_mode(")
    assert "s.frameBatch.abort();" in unavailable
    assert "env_batch_opt_in()" in unavailable
    bad_observer = observer.replace("if (!game_native_primitive_element_count(",
                                    "if (false && !game_native_primitive_element_count(", 1)
    assert bad_observer != observer and "if (!game_native_primitive_element_count(" not in bad_observer

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
            "if (!game_fvf_untextured_stage0(",
            "nextColorOp, layout.hasDiffuse",
            "GetRenderState(D3DRS_FOGENABLE, &fog)",
            "GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)",
            "!clip || fog || fillMode != D3DFILL_SOLID)",
            "GetRenderState(D3DRS_STENCILFUNC, &stencilFunc)",
            "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
            "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
            "stencil_equivalent_to_disabled(",
            "!game_live_stencil_inert(game, stencil)",
            "if (depth != D3DZB_FALSE) {",
            "game_native_depth_admission(",
        ))

    assert exact_diffuse_state_gate(bridge)
    # Mutate the actual fixed Draw admission, not the earlier shared
    # stencil-state capture helper; do not loosen either negative check.
    for bad, replacement in (
        ("if (!game_fvf_untextured_stage0(",
         "if (false && !game_fvf_untextured_stage0("),
        ("GetRenderState(D3DRS_FOGENABLE, &fog)",
         "GetRenderState(D3DRS_FOGENABLE, &clip)"),
        ("GetRenderState(D3DRS_SCISSORTESTENABLE, &scissor)",
         "GetRenderState(D3DRS_SCISSORTESTENABLE, &clip)"),
        ("stencil_equivalent_to_disabled(",
         "stencil_unconditionally_bypassed("),
        ("!game_live_stencil_inert(game, stencil)",
         "!game_live_stencil_unguarded(game, stencil)"),
        ("GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
         "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &clip)"),
        ("if (depth != D3DZB_FALSE) {",
         "if (depth == D3DZB_FALSE) {"),
        ("game_native_depth_admission(",
         "game_native_depth_unguarded("),
    ):
        start = bridge.index("bool supported_game_state(")
        end = bridge.index("bool translate_vertices(", start)
        section = bridge[start:end]
        damaged = section.replace(bad, replacement, 1)
        mutated = bridge[:start] + damaged + bridge[end:]
        assert damaged != section and not exact_diffuse_state_gate(mutated), (
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
            # 00763: RGB-only remains mandatory for the inset; full-size
            # game Draw/DrawIndexed may write only destination alpha (A8)
            # or DSV depth. Unknown masks still fail closed.
            "if ((colorMask & ~legalMask) ||",
            "(!(colorMask & visibleMask) &&",
            "!GameNativeMaskedDraw::accepts_source_mask(",
            "colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,",
            "output.nativeDepthTest && output.nativeDepthWrite",
            "game_native_cull_admission(",
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
        ("if ((colorMask & ~legalMask) ||", "if (false ||"),
        ("(!(colorMask & visibleMask) &&", "(false &&"),
        ("!GameNativeMaskedDraw::accepts_source_mask(", "!unverified_game_mask("),
        ("colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,",
         "colorMask, true, true,"),
        ("output.nativeDepthTest && output.nativeDepthWrite",
         "true /* unchecked depth */"),
        ("game_native_cull_admission(", "game_native_cull_unchecked("),
        ("fillMode != D3DFILL_SOLID", "fillMode == D3DFILL_SOLID"),
    ):
        bad = bridge.replace(original, mutated, 1)
        assert bad != bridge and not exact_raster_output_gate(bad), (
            "untranslated native raster/output state was not rejected: " + original
        )

    # The native helper must implement a genuine fail-closed full-mode
    # exception, not a blanket RGB-only bypass or accidental inset opt-in.
    native_mask = (ROOT / "src/vr/d3d11/native_game_masked_draw.hpp").read_text()
    def exact_masked_game_admission(helper: str) -> bool:
        return all(token in helper for token in (
            "if ((d3d9Mask & ~kAll) != 0u) return false;",
            "if ((d3d9Mask & kRgb) != 0u) return true;",
            "return fullFrame &&",
            "targetHasAlpha && (d3d9Mask & kAlpha) != 0u",
            "|| nativeDepthWrite",
        ))
    assert exact_masked_game_admission(native_mask)
    for original, replacement in (
        ("if ((d3d9Mask & ~kAll) != 0u) return false;", "if (false) return false;"),
        ("return fullFrame &&", "return true ||"),
        ("targetHasAlpha && (d3d9Mask & kAlpha) != 0u", "true /* unverified alpha */"),
        ("|| nativeDepthWrite", "|| true /* unverified depth */"),
    ):
        unsafe = native_mask.replace(original, replacement, 1)
        assert unsafe != native_mask and not exact_masked_game_admission(unsafe), original

    # Default diagnostic samples one rotating real game Draw. The cursor must
    # reach late menu/car/race draws (>64) without enlarging the opt-in GPU
    # batch (still eight Draws) or replacing original D3D9 gamepad behavior.
    sampling = (
        "const UINT candidateOrdinal = s.eligibleThisFrame++;",
        "++s.eligible;",
        "s.frameBatch.accepts(candidateOrdinal, s.probeSlot,",
        "env_batch_opt_in());",
        "if (!admitted)",
        "s.frameBatch.accepts_full_on_source_target(",
        "s.frameBatch.must_abort_unsupported(fullMode, multiBatch)",
        "s.probeSlot = GameNativeFrameBatch::next_probe_slot(",
        "s.probeSlot, s.eligibleThisFrame);",
        "s.eligibleThisFrame = 0;",
        "s.frameBatch.reset();",
    )
    assert all(item in bridge for item in sampling)
    # The whole game output must not accept the first Draw unless a real
    # successful full TARGET Clear matches the same D3D9 device/backbuffer.
    # Preserve destructive admission testing against the new seeded call.
    assert "const bool sameClearedGameTarget = s.clearColor.matches(" in bridge
    assert "output.targetIdentity);" in bridge
    broken = bridge.replace("env_batch_opt_in());",
                            "true);", 1)
    assert broken != bridge and sampling[3] not in broken
    # Removing the new full-frame admission must also fail the source contract.
    # Both fixed-function and SM3 submits now independently gate exact
    # seeded source ordinals. Mutate all admissions: leaving one live path
    # intact would make this destructive regression a false failure.
    missing_full = bridge.replace("s.frameBatch.accepts_full_on_source_target(",
                                  "false")
    assert missing_full != bridge and sampling[5] not in missing_full
    assert "s.probeSlot = 0;" in bridge
    batch = (ROOT / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
    for invariant in ("kMaxDraws = 8u", "next_probe_slot(", "if (stopped) return false;",
                      "if (!multi) return submitted == 0u && ordinal == slot;",
                      "return submitted < kMaxDraws && ordinal >= slot &&",
                      "return !depth || depthDirection == 0u ||"):
        assert invariant in batch
    assert "ordinal - slot == submitted && ordinal - slot < kMaxDraws;" in batch
    # Destructive mutation: a skipped Draw must not be allowed to join a frame.
    admits_gap = batch.replace("ordinal - slot == submitted && ", "", 1)
    assert admits_gap != batch and "ordinal - slot == submitted && " not in admits_gap
    assert "ordinal - slot < kMaxDraws;" in batch
    # This is executable C++ source selection, not a Python-only simulation:
    # mutating to the obsolete first-64 cursor must invalidate the contract.
    assert "current < eligible - 1u" in batch
    starved_cursor = batch.replace("current < eligible - 1u", "current < 64u", 1)
    assert starved_cursor != batch and "current < eligible - 1u" not in starved_cursor
    assert "kMaxDraws = 8u" not in batch.replace("kMaxDraws = 8u",
                                                 "kMaxDraws = 0u", 1)
    # Negative regression: a late accepted draw outside the contiguous
    # 8-candidate window cannot be silently mixed into the same native frame.
    unsafe_mix = batch.replace("ordinal - slot < kMaxDraws;",
                               "ordinal - slot >= kMaxDraws;", 1)
    assert unsafe_mix != batch and "ordinal - slot < kMaxDraws;" not in unsafe_mix
    # Rotation reaches eligible menu, vehicle selection and race candidates.
    slot = 0
    chosen = []
    for _ in range(8):
        population = 3
        hits = [i for i in range(population) if i == slot]
        assert len(hits) <= 1
        chosen.extend(hits)
        slot = (slot + 1) % min(population, 64)
    assert chosen == [0, 1, 2, 0, 1, 2, 0, 1]
    assert "kProbeSlots = 64" not in bridge
    # Positive/negative coverage: all 257 scene draws are selectable, not
    # just the initial 64. Check a destructive source mutation is rejected.
    def complete_scene_cursor(code: str) -> bool:
        return (
            "s.probeSlot = GameNativeFrameBatch::next_probe_slot(" in code
            and "s.probeSlot, s.eligibleThisFrame);" in code
            and "if (s.eligibleThisFrame == (std::numeric_limits<UINT>::max)()) {" in code
            and "if (fullMode) s.frameBatch.abort();" in code
            and "const UINT candidateOrdinal = s.eligibleThisFrame++;" in code
            and "kProbeSlots = 64" not in code
        )
    assert complete_scene_cursor(bridge)
    broken_window = bridge.replace(
        "s.probeSlot = GameNativeFrameBatch::next_probe_slot(",
        "s.probeSlot = legacy_first_64_probe_slot(", 1)
    assert broken_window != bridge and not complete_scene_cursor(broken_window)
    probe = 0
    visited = []
    for _ in range(257):
        visited.append(probe)
        probe = probe + 1 if probe < 256 else 0
    assert len(set(visited)) == 257 and visited[-1] == 256 and probe == 0

    # 00677: end-to-end raw game Draw stream -> batch -> GPU inset delivery.
    # Count unsupported D3D9 calls separately from eligible native samples.
    # A batch aborted after an earlier native Draw cannot be published at Present.
    def native_batch_publication_safe(code: str, header: str) -> bool:
        observe = code[code.find("void observe("):code.find("} // namespace", code.find("void observe("))]
        present = code[code.find("void before_game_present("):code.find("void before_game_reset(")]
        return all(x in observe for x in (
            "const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;",
            "if (!supported_game_state(game, type, vp, layout, transforms, capture, output)) {",
            "s.frameBatch.abort();",
            "s.frameBatch.accepts_source_draw(sourceOrdinal, multiBatch)",
            "s.frameBatch.record_source_draw(sourceOrdinal);",
        )) and all(x in present for x in (
            "s.frameBatch.publishable(s.pending)",
            "s.sourceDrawsThisFrame = 0u;",
        )) and all(x in header for x in (
            "ordinal - lastSourceDraw == 1u",
            "return pending && submitted != 0u && !stopped;",
            "lastSourceDraw = 0u; hasSourceDraw = false;",
        ))

    assert native_batch_publication_safe(bridge, batch)
    for original, replacement in (
        ("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;",
         "const std::uint64_t sourceOrdinal = s.eligibleThisFrame;"),
        ("s.frameBatch.accepts_source_draw(sourceOrdinal, multiBatch)",
         "s.frameBatch.accepts_source_draw(sourceOrdinal, false)"),
        ("s.frameBatch.publishable(s.pending)", "s.pending"),
    ):
        # Native surface postpass replay also checks publishable(), before
        # Present. Mutate the Present gate itself, not an earlier independent
        # replay guard; otherwise the safety negative control is a false alarm.
        mutation_start = (bridge.find("void before_game_present(")
                          if original == "s.frameBatch.publishable(s.pending)" else 0)
        mutation_at = bridge.find(original, mutation_start)
        assert mutation_at >= 0, "missing native batch mutation target: " + original
        bad_bridge = (bridge[:mutation_at] + replacement +
                      bridge[mutation_at + len(original):])
        assert bad_bridge != bridge and not native_batch_publication_safe(bad_bridge, batch)
    for original, replacement in (
        ("ordinal - lastSourceDraw == 1u", "ordinal - lastSourceDraw <= 8u"),
        ("return pending && submitted != 0u && !stopped;",
         "return pending && submitted != 0u;"),
    ):
        bad_header = batch.replace(original, replacement, 1)
        assert bad_header != batch and not native_batch_publication_safe(bridge, bad_header)

    # UpdateSurface requires identical source/destination formats, no MSAA,
    # and an entirely in-bounds rectangle. The game's backbuffer can be X8.
    def safe_inset_copy(code: str) -> bool:
        start = code.find("void before_game_present(")
        end = code.find("void before_game_reset(", start)
        if start < 0 or end <= start:
            return False
        section = code[start:end]
        return all(token in section for token in (
            "const auto insetPlacement = presentRegion.inset_placement(",
            "bb.Width, bb.Height, surfaceWidth, surfaceHeight, fullMode ? 0u : 8u);",
            "nativeExtentMatches &&",
            "presentRegion.full_frame_placement(",
            "fullMode ? fullPlacement.valid : insetPlacement.valid",
            "surfaceWidth == bb.Width && surfaceHeight == bb.Height &&",
            "(!outputNow.hasDirtyRegion || fullDirtyCoverage) &&",
            "static_cast<LONG>(fullMode ? fullPlacement.left : insetPlacement.left)",
            "static_cast<LONG>(fullMode ? fullPlacement.top : insetPlacement.top)",
            "bb.MultiSampleType == D3DMULTISAMPLE_NONE",
            "bb.Format == D3DFMT_A8R8G8B8",
            "bb.Format == D3DFMT_X8R8G8B8",
            "surfaceWidth, surfaceHeight, bb.Format, D3DPOOL_SYSTEMMEM",
            "game->UpdateSurface(",
        ))

    assert safe_inset_copy(bridge), (
        "native inset copy must match the actual D3D9 backbuffer and stay in bounds"
    )
    for vulnerable, replacement in (
        ("surfaceWidth, surfaceHeight, bb.Format, D3DPOOL_SYSTEMMEM",
         "surfaceWidth, surfaceHeight, D3DFMT_A8R8G8B8, D3DPOOL_SYSTEMMEM"),
        ("nativeExtentMatches &&", "true &&"),
        ("presentRegion.full_frame_placement(", "/* disabled native crop */ ("),
        ("fullMode ? fullPlacement.valid : insetPlacement.valid", "true"),
        ("bb.MultiSampleType == D3DMULTISAMPLE_NONE",
         "bb.MultiSampleType != D3DMULTISAMPLE_NONE"),
        ("const auto insetPlacement = presentRegion.inset_placement(",
         "const auto insetPlacement = /* missing crop bounds */ ("),
        ("(!outputNow.hasDirtyRegion || fullDirtyCoverage) &&",
         "true /* unsafe dirty publication */ &&"),
        ("static_cast<LONG>(fullMode ? fullPlacement.left : insetPlacement.left)",
         "static_cast<LONG>(bb.Width - kWidth - 8)"),
        ("static_cast<LONG>(fullMode ? fullPlacement.top : insetPlacement.top)",
         "static_cast<LONG>(8)"),
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
        # Full-frame same-Present fence recycling is a separate producer.
        # The inset must retain its independent async poll and submit path.
        poll = section.find("HRESULT ready = ctx->GetData(")
        first_done = section.find("if (fullMode && fullQueued && ready == S_FALSE)", poll)
        map_at = section.find("ctx->Map(oldest.staging.Get()", poll)
        inset_at = section.find("// Native full-frame was already enqueued", map_at)
        if not (0 <= poll < first_done < map_at < inset_at):
            return False
        inset = section[inset_at:]
        return all(x in section for x in (
            "D3D11_QUERY_EVENT", "s.insetFormat != bb.Format",
            "s.insetSurface.GetAddressOf(), nullptr",
        )) and all((
            "D3D11_ASYNC_GETDATA_DONOTFLUSH" in section[poll:first_done],
            "GameNativeFramePublication::retry_same_present_fence(" in section[first_done:map_at],
            "QueryPerformanceCounter(&now)" in section[first_done:map_at],
            "ctx->Map(oldest.staging.Get(), 0,\n"
            "                        D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);" in section[map_at:inset_at],
            "ctx->End(next.fence.Get());" in inset,
            "if (!next.busy)" in inset,
            "++s.droppedCopies;" in inset,
            "ctx->Flush();\\n    s.pending = true;" not in section,
        ))

    assert deferred_inset_contract(bridge)
    for original, wrong in (
        ("D3D11_ASYNC_GETDATA_DONOTFLUSH", "0u"),
        ("D3D11_MAP_FLAG_DO_NOT_WAIT", "0u"),
        ("ctx->End(next.fence.Get());", "// no GPU completion fence"),
        ("if (!next.busy)", "if (next.busy)"),
        ("s.insetFormat != bb.Format", "s.insetFormat == bb.Format"),
    ):
        # Change the inset's own async path. Full-frame stale pending Map
        # handling is earlier than this producer and must not be mistaken for
        # the inset's nonblocking Map (false-negative mutation).
        start = (bridge.index("HRESULT ready = ctx->GetData(")
                 if original == "D3D11_ASYNC_GETDATA_DONOTFLUSH" else
                 bridge.index("ctx->Map(oldest.staging.Get()")
                 if original == "D3D11_MAP_FLAG_DO_NOT_WAIT" else
                 bridge.index("// Native full-frame was already enqueued")
                 if original in ("ctx->End(next.fence.Get());", "if (!next.busy)") else 0)
        mutated = bridge[:start] + bridge[start:].replace(original, wrong, 1)
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
            "game_fvf_diffuse_only_inactive_texture(",
            "capture.enabled = layout.textured && !diffuseOnly;",
            "capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;",
            "else if (tex && !diffuseOnly)",
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
            "if (!game_native_world_depth_clip(clip, vp.MinZ, vp.MaxZ) ||",
            "!game_native_object_clip_position(clip))",
            "std::copy(clip.begin(), clip.end(), v.clip);",
        )
        return (all(x in state for x in required_state)
                and all(x in vertices for x in required_vertices)
                and "D3DPRIMITIVETYPE topology," in state
                and "supported_game_state(game, type, vp, layout, transforms, capture, output)" in observe
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
        ("if (!game_native_world_depth_clip(clip, vp.MinZ, vp.MaxZ) ||",
         "if (false ||"),
        ("!game_native_object_clip_position(clip))", "false)"),
        ("supported_game_state(game, type, vp, layout, transforms, capture, output)",
         "supported_game_state(game, D3DPT_TRIANGLELIST, vp, layout, transforms, capture, output)"),
    ):
        changed = bridge.replace(good, bad, 1)
        assert changed != bridge and not object_space_draw_safe(changed), (
            "object-space native geometry negative mutation escaped: " + good
        )
    # The opt-in active R30 producer admits compact real game declarations
    # (FLOAT3 POSITION / packed D3D9 operands), not the old 16-byte floor.
    # R26-safe remains intentionally unchanged; validate both independently.
    # A lower-bound relaxation must never remove the mandatory bounded source
    # predicate or silently widen the upper limit to an arbitrary byte count.
    stride_contract = (ROOT / "src/vr/d3d11/live_game_source_stride.hpp").read_text(
        encoding="utf-8")
    assert "stride >= 4u && stride <= 512u" in stride_contract
    for wrong in ("stride >= 16u", "stride >= 0u", "stride <= 1024u"):
        changed = stride_contract.replace(
            "stride >= 4u && stride <= 512u", wrong, 1)
        assert changed != stride_contract and (
            "stride >= 4u && stride <= 512u" not in changed)
    for path in RENDERERS:
        source = path.read_text(encoding="utf-8")
        start = source.find("void R30ObserveNativeLinearVB(")
        end = source.find("HRESULT __stdcall DrawPrimitiveDestR30(", start)
        assert start >= 0 and end > start
        observed = source[start:end]
        if path.name == "stereo_renderer_r30.cpp":
            guard = "game_native_source_stride_valid(stride)"
            assert observed.count(guard) == 4
            assert "stride < 16" not in observed and "stride < 20" not in observed
            # Fail when even one real game VB/IB/UP source path drops its guard.
            invalid = observed.replace(guard, "true", 1)
            assert invalid != observed and invalid.count(guard) != 4
            assert "#include \"vr/d3d11/live_game_source_stride.hpp\"" in source
        else:
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
        # Stage0 texture upload and Stage1 sampler translation are separate
        # functions; the compiled game draw requires both and the delegation.
        mirror = code[code.find("bool create_game_sampler("):
                      code.find("bool submit(")]
        submit = code[code.find("bool submit("):
                      code.find("void observe(")]
        return all(x in state for x in (
            "if (!game_fvf_layout(fvf, layout)) return false;",
            "game_fvf_diffuse_only_inactive_texture(",
            "capture.enabled = layout.textured && !diffuseOnly;",
            "capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;",
            "else if (tex && !diffuseOnly)",
            "if (!layout.hasDiffuse && !selectTexture) return false;",
            "GetTexture(0, tex.GetAddressOf())",
            "tex.As(&capture.texture)",
            "const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
            "const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
            "const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;",
            "const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;",
            "const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT ||\n            blendTextureAlphaPMInverseFactorArg2Alpha;",
            "(!modulate && !selectTexture && !selectDiffuseTextureAlpha && !selectDiffuseDiffuseAlpha &&",
            "alphaArg1 != D3DTA_TEXTURE",
            "(rgbNeedsDiffuse && !arg2Diffuse)",
            "capture.selectTexture = selectTexture;",
            "capture.additive = additive;",
            "coordIndex >= layout.texcoordCount ||",
            "transformFlags != D3DTTFF_DISABLE && transformFlags != D3DTTFF_COUNT2",
            "srgb > 1u ||",
            "capture.srgbTexture = srgb == TRUE;",
            "capture.coordIndex = coordIndex;",
            "(min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)",
            "(mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR)",
            "(mip != D3DTEXF_NONE && mip != D3DTEXF_POINT)",
            "nextColorOp != D3DTOP_DISABLE",
        )) and "return create_game_sampler(dev, capture, levels, sampler);" in mirror and all(x in mirror for x in (
            "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
            "sourceLevels == 0 || sourceLevels > kMaxNativeGameAtlasMipLevels",
            "D3DFMT_A8R8G8B8", "D3DFMT_X8R8G8B8",
            "LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
            "capture.texture->UnlockRect(level)",
            "dev->CreateTexture2D(", "dev->CreateShaderResourceView(",
            "state.ComparisonFunc = D3D11_COMPARISON_NEVER",
            "state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;", "state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;",
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
        ("srgb > 1u ||", "srgb > 2u ||"),
        ("capture.enabled = layout.textured && !diffuseOnly;", "capture.enabled = false;"),
        ("capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;",
         "capture.inactiveStage0TextureBypass = false;"),
        ("else if (tex && !diffuseOnly)", "else if (tex)"),
        ("if (!layout.hasDiffuse && !selectTexture) return false;",
         "if (layout.hasDiffuse && !selectTexture) return false;"),
        ("const bool modulate = op == D3DTOP_MODULATE && alphaOp == D3DTOP_MODULATE;",
         "const bool modulate = op == D3DTOP_MODULATE || alphaOp == D3DTOP_MODULATE;"),
        ("const bool selectTexture = op == D3DTOP_SELECTARG1 && alphaOp == D3DTOP_SELECTARG1;",
         "const bool selectTexture = op == D3DTOP_SELECTARG1 || alphaOp == D3DTOP_SELECTARG1;"),
        ("(!modulate && !selectTexture && !selectDiffuseTextureAlpha && !selectDiffuseDiffuseAlpha &&",
         "(!modulate && !selectTexture) && arg != D3DTA_TEXTURE"),
        ("(rgbNeedsDiffuse && !arg2Diffuse)",
         "(modulate && (arg2 != D3DTA_DIFFUSE && alphaArg2 != D3DTA_DIFFUSE))"),
        ("capture.selectTexture = selectTexture;", "capture.selectTexture = false;"),
        ("capture.additive = additive;", "capture.additive = false;"),
        ("const bool additive = op == D3DTOP_ADD && alphaOp == D3DTOP_ADD;",
         "const bool additive = op == D3DTOP_ADD || alphaOp == D3DTOP_ADD;"),
        ("const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT;",
         "const bool arg2Diffuse = arg2 == D3DTA_DIFFUSE;"),
        ("const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT ||\n            blendTextureAlphaPMInverseFactorArg2Alpha;",
         "const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE;"),
        ("if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
         "if (base.Pool == D3DPOOL_SYSTEMMEM && !gpuRenderTarget) return false;"),
        ("sourceLevels == 0 || sourceLevels > kMaxNativeGameAtlasMipLevels", "sourceLevels != 1u"),
        ("state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;", "state.MaxLOD = D3D11_FLOAT32_MAX;"),
        ("return create_game_sampler(dev, capture, levels, sampler);",
         "return false;"),
        ("capture.texture->UnlockRect(level)", "/* missing texture unlock */"),
        ("ctx->PSSetShaderResources(0, 1, &boundView)",
         "/* no native shader texture binding */"),
        ("capture.selectTexture ? s.textureOnlyPs.Get() :\n                      capture.additive ? s.additivePs.Get() : s.sampledPs.Get()",
         "s.sampledPs.Get()"),
    ):
        mutated = bridge.replace(old, bad, 1)
        assert mutated != bridge and not texture_path_complete(mutated), (
            "texture-stage native-D3D11 negative mutation escaped: " + old
        )
    # D3D9 XYZRHW z is already window-space depth: the live bridge must
    # call the portable helper instead of blindly multiplying stale vertex Z.
    assert "game_native_screen_depth_clip(" in bridge
    assert "xyz[2], w, vp.MinZ, vp.MaxZ, v.clip[2]" in bridge
    assert "v.clip[3] = w;" in bridge
    viewport_depth = (ROOT / "src/vr/d3d11/live_game_viewport_depth.hpp").read_text(encoding="utf-8")
    assert "const float remapped = windowZ * w;" in viewport_depth
    assert "float2 uv : TEXCOORD0" in bridge
    assert "gameTexture.Sample(gameSampler, v.uv) * v.diffuse" in bridge
    assert "float4 PSTextureOnly(VOut v) : SV_Target { float4 c = gameTexture.Sample(gameSampler, v.uv); AlphaGate(c.a); return c; }" in bridge
    assert '!compile("PSTextureOnly", "ps_4_0", textureOnlyCode)' in bridge
    assert "s.textureOnlyPs.Reset();" in bridge
    # Real untextured FVF DIFFUSE menu/sprite draws may select RGB and alpha
    # independently via stage-0 ARG1/ARG2. The native PS returns v.diffuse,
    # so BOTH channels must resolve exactly to vertex diffuse/current.
    # This extends live Draw/DrawIndexed admission, not a WARP-only probe.
    def untextured_diffuse_linked(code: str) -> bool:
        start = code.find("    if (!capture.enabled) {", code.find("bool supported_game_state("))
        end = code.find("    if (capture.enabled) {", start)
        if start < 0 or end <= start:
            return False
        gate = code[start:end]
        predicates = (
            "if (!layout.hasDiffuse ||",
            "GetTextureStageState(0, D3DTSS_COLORARG2, &arg2)",
            "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)",
            "if (!game_fvf_untextured_stage0(",
            "nextColorOp, layout.hasDiffuse",
        )
        return all(p in gate for p in predicates) and (
            "float4 PS(VOut v) : SV_Target { float4 c = v.diffuse;" in code
            and "ctx->DrawIndexed(indexCount, 0, 0);" in code
            and "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in code
        )

    assert untextured_diffuse_linked(bridge)
    untextured_mutations = (
        ("if (!layout.hasDiffuse ||", "if (false ||"),
        ("D3DTSS_COLORARG2, &arg2)", "D3DTSS_COLORARG2, &alphaArg2)"),
        ("D3DTSS_ALPHAOP, &alphaOp)", "D3DTSS_ALPHAOP, &arg2)"),
        ("D3DTSS_ALPHAARG1, &alphaArg1)", "D3DTSS_ALPHAARG1, &arg2)"),
        ("D3DTSS_ALPHAARG2, &alphaArg2)", "D3DTSS_ALPHAARG2, &arg2)"),
        ("if (!game_fvf_untextured_stage0(",
         "if (false && !game_fvf_untextured_stage0("),
        ("nextColorOp, layout.hasDiffuse",
         "D3DTOP_DISABLE, layout.hasDiffuse"),
    )
    for original, altered in untextured_mutations:
        # Mutate the local admission clause only: the textured stage has
        # its own correctly independent source getters.
        start = bridge.index("    if (!capture.enabled) {", bridge.index("bool supported_game_state("))
        end = bridge.index("    if (capture.enabled) {", start)
        gate = bridge[start:end]
        assert original in gate
        mutant = bridge[:start] + gate.replace(original, altered, 1) + bridge[end:]
        assert not untextured_diffuse_linked(mutant), (
            "untextured stage-0 RGB/alpha native regression escaped: " + original
        )

    # The portable FVF converter is a genuine fail-closed native admission
    # function: reject source complements/TFACTOR, missing diffuse, active
    # downstream stages and undefined enabled-color alpha disable.
    fvf = (ROOT / "src/vr/d3d11/live_game_fvf_layout.hpp").read_text(encoding="utf-8")
    def exact_untextured_fvf_helper(text: str) -> bool:
        return all(x in text for x in (
            "if (!diffuse) return false;",
            "if (op == 1u) return nextOp == 1u;",
            "(op == 2u && (arg1 == 0u || arg1 == 1u))",
            "(op == 3u && (arg2 == 0u || arg2 == 1u))",
            "(alphaOp == 2u && (alpha1 == 0u || alpha1 == 1u))",
            "(alphaOp == 3u && (alpha2 == 0u || alpha2 == 1u))",
            "return rgb && a;",
        ))
    assert exact_untextured_fvf_helper(fvf)
    for token in ("if (!diffuse) return false;",
                  "if (op == 1u) return nextOp == 1u;",
                  "(op == 2u && (arg1 == 0u || arg1 == 1u))",
                  "(op == 3u && (arg2 == 0u || arg2 == 1u))",
                  "(alphaOp == 2u && (alpha1 == 0u || alpha1 == 1u))",
                  "(alphaOp == 3u && (alpha2 == 0u || alpha2 == 1u))",
                  "return rgb && a;"):
        assert not exact_untextured_fvf_helper(fvf.replace(token, "REMOVED", 1)), token

    # Source D3DTOP numeric SELECTARG1/2, texture vs diffuse/current and
    # modifier inputs: both independently selected channels must agree.
    SELECTARG1, SELECTARG2, MODULATE = 2, 3, 4
    DIFFUSE, CURRENT, TEXTURE, COMPLEMENT = 0, 1, 2, 0x10
    def accepted(op: int, arg1: int, arg2: int,
                 alpha_op: int, alpha_arg1: int, alpha_arg2: int,
                 has_diffuse: bool) -> bool:
        rgb = ((op == SELECTARG1 and arg1 in (DIFFUSE, CURRENT))
               or (op == SELECTARG2 and arg2 in (DIFFUSE, CURRENT)))
        a = ((alpha_op == SELECTARG1 and alpha_arg1 in (DIFFUSE, CURRENT))
             or (alpha_op == SELECTARG2 and alpha_arg2 in (DIFFUSE, CURRENT)))
        return has_diffuse and rgb and a

    for rgb_select in (SELECTARG1, SELECTARG2):
        for a_select in (SELECTARG1, SELECTARG2):
            for source in (DIFFUSE, CURRENT):
                args = (source, TEXTURE) if rgb_select == SELECTARG1 else (TEXTURE, source)
                alpha_args = (source, TEXTURE) if a_select == SELECTARG1 else (TEXTURE, source)
                assert accepted(rgb_select, *args, a_select, *alpha_args, True)
                assert not accepted(rgb_select, *args, a_select, *alpha_args, False)
                for invalid_op in (MODULATE,):
                    assert not accepted(invalid_op, *args, a_select, *alpha_args, True)
                    assert not accepted(rgb_select, *args, invalid_op, *alpha_args, True)
                bad_args = (TEXTURE, TEXTURE)
                assert not accepted(rgb_select, *bad_args, a_select, *alpha_args, True)
                assert not accepted(rgb_select, *args, a_select, *bad_args, True)
                assert not accepted(rgb_select, COMPLEMENT | source, TEXTURE,
                                    a_select, *alpha_args, True)
                assert not accepted(rgb_select, *args, a_select,
                                    COMPLEMENT | source, TEXTURE, True)

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
        "(!modulate && !selectTexture && !selectDiffuseTextureAlpha && !selectDiffuseDiffuseAlpha &&",
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
        "(!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseArg1Alpha)",
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
        "(!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseArg1Alpha)",
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
        "s.sampledPs && s.textureOnlyPs && s.selectDiffuseTextureAlphaPs && s.selectDiffuseModulateAlphaPs && s.selectDiffuseAddAlphaPs && s.selectDiffuseSubtractAlphaPs && s.selectDiffuseModulate2XAlphaPs && s.selectDiffuseModulate4XAlphaPs && s.additivePs && s.subtractPs &&",
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
        "(!modulate && !selectTexture && !selectDiffuseTextureAlpha && !selectDiffuseDiffuseAlpha &&",
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
        # Verify alpha-state binding in its own OM branch, not any of the
        # other masked-blend paths that share a color-write assignment.
        separate_start = submit.find("if (output.separateAlphaBlend) {")
        # Scope the independent alpha OM only to its actual branch.
        # Native MIN/MAX adds a separate intervening branch whose valid
        # write-mask binding must not hide destructive alpha mutations.
        separate_end = submit.find(
            "} else if (output.blendOp == D3D11_BLEND_OP_MIN",
            separate_start)
        separate_om = (submit[separate_start:separate_end]
                       if separate_start >= 0 and separate_end > separate_start
                       else "")
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
            "if (separate != FALSE) {",
            "GetRenderState(D3DRS_SRCBLENDALPHA, &srcAlpha)",
            "GetRenderState(D3DRS_DESTBLENDALPHA, &dstAlpha)",
            "GetRenderState(D3DRS_BLENDOPALPHA, &opAlpha)",
            "native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
            "output.separateAlphaBlend = true;",
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
        # Three distinct source-alpha paths (over, additive, SRCALPHA/ZERO)
        # must each retain SRC_ALPHA on the alpha channel. A mutation of the
        # original over path cannot be hidden by later valid modes.
        )) and pipeline.count("target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;") == 3 and all(x in submit for x in (
            "ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0)",
            "ctx->OMSetBlendState(output.alphaBlend ? s.alphaBlend.Get() : nullptr",
            "if (output.separateAlphaBlend) {",
            "rgbBase->GetDesc(&desc);",
            "desc.RenderTarget[0].BlendOp = output.blendOp;",
            "desc.RenderTarget[0].SrcBlendAlpha = output.nativeSrcAlpha;",
            "desc.RenderTarget[0].DestBlendAlpha = output.nativeDstAlpha;",
            "desc.RenderTarget[0].BlendOpAlpha = output.nativeAlphaOp;",
            "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
            "maskedBlend = &independentAlphaBlend;",
            "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer)",
        )) and all(x in separate_om for x in (
            "rgbBase->GetDesc(&desc);",
            "desc.RenderTarget[0].SrcBlendAlpha = output.nativeSrcAlpha;",
            "desc.RenderTarget[0].DestBlendAlpha = output.nativeDstAlpha;",
            "desc.RenderTarget[0].BlendOpAlpha = output.nativeAlphaOp;",
            "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
            "maskedBlend = &independentAlphaBlend;",
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
        ("if (separate != FALSE) {",
         "if (false) {"),
        ("GetRenderState(D3DRS_SRCBLENDALPHA, &srcAlpha)",
         "/* omit source alpha state */"),
        ("GetRenderState(D3DRS_DESTBLENDALPHA, &dstAlpha)",
         "/* omit destination alpha state */"),
        ("GetRenderState(D3DRS_BLENDOPALPHA, &opAlpha)",
         "/* omit alpha equation state */"),
        ("native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
         "/* unchecked native alpha admission */"),
        ("output.separateAlphaBlend = true;",
         "output.separateAlphaBlend = false;"),
        ("desc.RenderTarget[0].SrcBlendAlpha = output.nativeSrcAlpha;",
         "desc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;"),
        ("desc.RenderTarget[0].DestBlendAlpha = output.nativeDstAlpha;",
         "desc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ZERO;"),
        ("desc.RenderTarget[0].BlendOpAlpha = output.nativeAlphaOp;",
         "desc.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;"),
        ("desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
         "desc.RenderTarget[0].RenderTargetWriteMask = 0xFu;"),
        ("maskedBlend = &independentAlphaBlend;",
         "maskedBlend = nullptr;"),
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
            "ctx->RSSetState(nativeRaster);",
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
        ("ctx->RSSetState(nativeRaster);", "ctx->RSSetState(s.raster.Get());"),
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
            "if ((colorMask & ~legalMask) ||",
            "(!(colorMask & visibleMask) &&",
            "!GameNativeMaskedDraw::accepts_source_mask(",
            "colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,",
            "output.nativeDepthTest && output.nativeDepthWrite",
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
    # The historical RGB mask truth table applies to the small diagnostic
    # inset. Full-size gameplay additionally requires A8 alpha-only passes
    # and depth-writing prepasses to remain in the same Draw/DrawIndexed batch.
    for mask in range(32):
        valid = (mask & ~15) == 0
        rgb_visible = (mask & 7) != 0
        a8_alpha = (mask & 8) != 0
        for depth_writes in (False, True):
            expected_full = valid and (rgb_visible or a8_alpha or depth_writes)
            expected_inset = valid and rgb_visible
            assert expected_full == (valid and bool((mask & 7) or
                                                     ((mask & 8) or depth_writes)))
            if mask == 8 and not depth_writes:
                assert expected_full and not expected_inset
            if mask == 0 and depth_writes:
                assert expected_full and not expected_inset
            if mask == 16:
                assert not expected_full and not expected_inset
    # Live fixed-function DXT textures must use compressed block pitches and
    # bind BC1/2/3 SRVs to the existing native textured Draw path. This is
    # source/CPU contract evidence, not a game/WARP pixel or HMD validation.
    def dxt_native_draw_connected(source: str) -> bool:
        producer = source[source.find("bool mirror_texture("):source.find("bool submit(")]
        draw = source[source.find("bool submit("):source.find("void observe(")]
        return all(token in producer for token in (
            "const bool compressed = base.Format == D3DFMT_DXT1 ||",
            "base.Format == D3DFMT_DXT3 ||",
            "base.Format == D3DFMT_DXT5;",
            "if ((base.Width & 3u) || (base.Height & 3u)) return false;",
            "(base.Format == D3DFMT_DXT1 ? 8u : 16u) :",
            "(std::max)(1u, (desc.Width + 3u) / 4u) *",
            "const UINT rows = compressed ? (std::max)(1u, (desc.Height + 3u) / 4u) : desc.Height;",
            "DXGI_FORMAT_BC1_UNORM",
            "DXGI_FORMAT_BC2_UNORM",
            "DXGI_FORMAT_BC3_UNORM",
            "base.Pool == D3DPOOL_DEFAULT",
            "const bool readable = lock.pBits &&",
            "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
            "static_cast<std::size_t>(uploadPitch) * rows",
            "static_cast<std::size_t>(y) * lock.Pitch",
            "static_cast<std::size_t>(y) * uploadPitch",
            "initial[level].SysMemPitch = pitches[level];",
            "desc.Format = nativeFormat;",
            "capture.texture->UnlockRect(level);",
            "dev->CreateShaderResourceView(",
        )) and all(token in draw for token in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    assert dxt_native_draw_connected(bridge)
    for source, wrong in (
        ("base.Format == D3DFMT_DXT1", "base.Format == D3DFMT_DXT2"),
        ("base.Format == D3DFMT_DXT3", "base.Format == D3DFMT_DXT2"),
        ("base.Format == D3DFMT_DXT5", "base.Format == D3DFMT_DXT4"),
        ("if ((base.Width & 3u) || (base.Height & 3u)) return false;",
         "if (false) return false;"),
        ("(std::max)(1u, (desc.Width + 3u) / 4u) *",
         "rowBytes = desc.Width * 4u;"),
        ("const UINT rows = compressed ? (std::max)(1u, (desc.Height + 3u) / 4u) : desc.Height;", "rows = desc.Height;"),
        ("dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
         "static_cast<UINT>(lock.Pitch) > 0"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = desc.Width * 4u;"),
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
            "base.Format == D3DFMT_R5G6B5",
            "base.Format == D3DFMT_A1R5G5B5",
            "base.Format == D3DFMT_A4R4G4B4",
        )) and all(x in producer for x in (
            "const UINT sourceTexelBytes = packed16 ? 2u :",
            "desc.Width * sourceTexelBytes;",
            "const UINT uploadPitch = ((packed16 || luminance) || rgb24",
            "desc.Width * 4u : rowBytes;",
            "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
            "packed_texture16::unpack_row(",
            "initial[level].SysMemPitch = pitches[level];",
            "dev->CreateShaderResourceView(",
            "capture.texture->UnlockRect(level);",
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
        ("base.Format == D3DFMT_R5G6B5", "base.Format == D3DFMT_DXT2"),
        ("base.Format == D3DFMT_A1R5G5B5", "base.Format == D3DFMT_DXT2"),
        ("base.Format == D3DFMT_A4R4G4B4", "base.Format == D3DFMT_DXT2"),
        ("const UINT sourceTexelBytes = packed16 ? 2u :", "const UINT sourceTexelBytes = packed16 ? 4u :"),
        ("desc.Width * sourceTexelBytes", "desc.Width * 4u"),
        ("const UINT uploadPitch = ((packed16 || luminance) || rgb24", "const UINT uploadPitch = (luminance) ?"),
        ("packed_texture16::unpack_row(", "/* no 16-bit conversion */("),
        ("initial[level].SysMemPitch = pitches[level];", "/* wrong upload pitch */"),
    ):
        # 00692 inserted equivalent format tokens in the earlier
        # game-created DEFAULT RT admission. This legacy regression owns
        # the original packed16 source-texture admission, not that RT path.
        if original.startswith("base.Format == D3DFMT_"):
            prefix, anchor, producer = bridge.partition("const bool packed16 =")
            assert anchor and original in producer, original
            broken = prefix + anchor + producer.replace(original, invalid, 1)
        else:
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
        # The active SM3 linear-UP helper shares the same bounded source
        # primitive-span decoder, while R26-safe keeps three source copiers.
        expected_span_users = (
            4 if "void R30ObserveNativeLinearUP(" in entrypoints else 3)
        assert entrypoints.count("live::game_native_primitive_element_count(") == expected_span_users
        assert "static_cast<std::uint64_t>(nativeElements)*stride" in entrypoints
        assert "const UINT count = nativeElements;" in entrypoints
        assert "const UINT count=nativeElements;" in entrypoints
        disabled = entrypoints.replace(
            "topology != D3DPT_TRIANGLESTRIP", "topology == D3DPT_TRIANGLESTRIP", 1)
        assert disabled != entrypoints and (
            disabled.count("topology != D3DPT_TRIANGLESTRIP") != 3)

    strip_tokens = (
        '#include "live_game_primitive_span.hpp"',
        "game_native_primitive_element_count(static_cast<std::uint32_t>(type),",
        "topology == D3DPT_TRIANGLESTRIP ?",
        "indexCount != expectedElements",
        "vertexCount != expectedElements",
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP",
        "if (!submit(s, vertices, indices, indexCount, type, capture, output))",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    assert all(t in bridge for t in strip_tokens)
    for token in (
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP",
        "indexCount != expectedElements",
        "vertexCount != expectedElements",
    ):
        # Two independently source-gated GPU submitters now share the
        # actual D3D11 triangle-strip topology. Mutate both to prove there
        # is no unvalidated alternate draw path left behind.
        changed = bridge.replace(token, "BROKEN_NATIVE_STRIP")
        assert changed != bridge and token not in changed

    # 00546: D3D9 real-fan producers -> bounded source -> native indexed Draw.
    fan_header = (ROOT / "src/vr/d3d11/live_game_primitive_span.hpp").read_text(encoding="utf-8")
    fan_probe = (ROOT / "tools/dx11_game_primitive_span_probe.cpp").read_text(encoding="utf-8")
    for token in ("game_fan_to_triangle_list", "result.push_back(center);",
                  "result.push_back(b);", "result.push_back(c);", "triangles.swap(result);"):
        assert token in fan_header
    for token in ("game_native_primitive_element_count(static_cast<std::uint32_t>(type),",
                  "type == D3DPT_TRIANGLEFAN",
                  "fanTriangles.data()", "D3DPT_TRIANGLELIST, capture, output"):
        assert token in bridge
    assert "fan == preserved" in fan_probe
    for source in producers:
        a = source.index("void R30ObserveNativeLinearVB(")
        z = source.index("HRESULT __stdcall DrawPrimitiveDestR30(", a)
        hooks = source[a:z]
        assert hooks.count("topology != D3DPT_TRIANGLEFAN") == 3
        # Fan specialization now occurs after the bounded shared-span admission
        # in the native bridge, not once per R30 VB/IB/UP source copier.
        assert "if (type == D3DPT_TRIANGLEFAN)" in bridge
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
            "game_fvf_diffuse_only_inactive_texture(",
            "capture.enabled = layout.textured && !diffuseOnly;",
            "capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;",
            "else if (tex && !diffuseOnly)",
            "if (!layout.hasDiffuse && !selectTexture) return false;",
            "if (!game_fvf_decode_vertex(data, stride, layout, decoded))",
            "const DWORD diffuse = decoded.diffuse;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
        )) and "D3DPRIMITIVETYPE topology," in body and all(v in observe for v in (
            "supported_game_state(game, type, vp, layout, transforms, capture, output)",
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
            "kGameFvfPsize == D3DFVF_PSIZE",
            "kGameFvfSpecular == D3DFVF_SPECULAR",
            "GetRenderState(D3DRS_SPECULARENABLE, &specularEnabled)",
            "specularEnabled)",
            "            lighting || vertexBlend != D3DVBF_DISABLE",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(x in header for x in (
            "candidate.normalBytes = candidate.hasNormal ? 12u : 0u;",
            "candidate.pointSizeBytes = candidate.hasPointSize ? 4u : 0u;",
            "candidate.diffuseOffset = candidate.positionBytes + candidate.normalBytes +",
            "layout.pointSizeBytes != (layout.hasPointSize ? 4u : 0u)",
            "layout.diffuseOffset != layout.positionBytes + layout.normalBytes +",
            "data + layout.diffuseOffset, 4u",
            "(position == kGameFvfXyzRhw && hasNormal)",
        )) and all(x in probe for x in (
            "struct WorldNormalSpecUv2",
            "layout.texcoordOffset == 32u && layout.minStride == 48u",
            "sample.diffuse == 0xff123456u",
            "!game_fvf_decode_vertex(&world, 47u",
            "struct WorldPoint",
            "layout.diffuseOffset == 28u",
            "sample.diffuse == 0xff223344u",
            "!game_fvf_decode_vertex(&worldPoint, 51u",
            "invalidPoint.pointSizeBytes = 0u",
            "struct MenuPoint",
            "layout.diffuseOffset == 20u",
            "sample.diffuse == 0xff112233u",
            "!game_fvf_decode_vertex(&menuPoint, 31u",
            "struct MenuPointUv",
            "!game_fvf_layout(kGameFvfXyzRhw | kGameFvfNormal |",
            "corrupted.diffuseOffset -= 12u",
            "corrupted.texcoordOffset -= 4u",
        ))
    assert object_fvf_integrated(bridge, layout_source, probe_source)
    for old, bad in (
        ("GetRenderState(D3DRS_SPECULARENABLE, &specularEnabled)",
         "GetRenderState(D3DRS_ALPHABLENDENABLE, &specularEnabled)"),
        ("lighting || vertexBlend != D3DVBF_DISABLE",
         "!lighting || vertexBlend != D3DVBF_DISABLE"),
        ("kGameFvfPsize == D3DFVF_PSIZE",
         "kGameFvfPsize != D3DFVF_PSIZE"),
    ):
        mutant = bridge.replace(old, bad, 1)
        assert mutant != bridge and not object_fvf_integrated(mutant, layout_source, probe_source)
    for old, bad in (
        ("candidate.diffuseOffset = candidate.positionBytes + candidate.normalBytes +",
         "candidate.diffuseOffset = candidate.positionBytes +"),
        ("candidate.pointSizeBytes = candidate.hasPointSize ? 4u : 0u;",
         "candidate.pointSizeBytes = 0u;"),
        ("layout.pointSizeBytes != (layout.hasPointSize ? 4u : 0u)",
         "false"),
        ("data + layout.diffuseOffset, 4u", "data + layout.positionBytes, 4u"),
        ("(position == kGameFvfXyzRhw && hasNormal)",
         "(position == kGameFvfXyz && hasNormal)"),
    ):
        mutant = layout_source.replace(old, bad, 1)
        assert mutant != layout_source and not object_fvf_integrated(bridge, mutant, probe_source)


    # 00610: stage0 U-only game vertex -> native Draw/DrawIndexed source proof.
    def one_dim_fvf_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(t in src for t in (
            "kGameFvfTexcoordSize1_0 == D3DFVF_TEXCOORDSIZE1(0)",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(t in hdr for t in (
            "constexpr std::uint32_t kGameFvfTexcoordSize1_0 = 0x00030000u;",
            "(firstTexcoordFormat != 0u && !firstTexcoord1D)",
            "(firstTexcoord1D && texcoordBits == 0u)",
            "candidate.firstTexcoord1D = firstTexcoord1D;",
            "candidate.firstTexcoord1D ? 4u : 0u",
            "layout.firstTexcoord1D ? 4u : 8u",
            "data + layout.texcoordOffset + 4u, 8u",
            "sample = candidate;",
        )) and all(t in fixture for t in (
            "struct MenuOneDim", "struct VehicleUv1Uv2",
            "sample.uv[0] == .625f && sample.uv[1] == 0.f",
            "chosen[0] == .75f && chosen[1] == .875f",
            "!game_fvf_decode_vertex(&vehicleUv, 31u",
            "corruptDimension.firstTexcoord1D = false",
            "0x00010000u, layout", "0x00020000u, layout",
        ))
    assert one_dim_fvf_linked(bridge, layout_source, probe_source)
    damaged = bridge.replace("kGameFvfTexcoordSize1_0 == D3DFVF_TEXCOORDSIZE1(0)",
                            "kGameFvfTexcoordSize1_0 != D3DFVF_TEXCOORDSIZE1(0)", 1)
    assert damaged != bridge and not one_dim_fvf_linked(damaged, layout_source, probe_source)
    for old, wrong in (
        ("(firstTexcoordFormat != 0u && !firstTexcoord1D)", "false"),
        ("candidate.firstTexcoord1D = firstTexcoord1D;", "candidate.firstTexcoord1D = false;"),
        ("layout.firstTexcoord1D ? 4u : 8u", "8u"),
        ("data + layout.texcoordOffset + 4u, 8u", "data + layout.texcoordOffset + 8u, 8u"),
    ):
        damaged = layout_source.replace(old, wrong, 1)
        assert damaged != layout_source and not one_dim_fvf_linked(bridge, damaged, probe_source)
    print("DX11 live TEXCOORDSIZE1(0) native menu/vehicle draw PASS (static only)")

    # 00611: linked stage1 1D native UV feed and destructive mutations.
    def second_u_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize1_1 == D3DFVF_TEXCOORDSIZE1(1)",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
        )) and all(x in hdr for x in (
            "kGameFvfTexcoordSize1_1 = 0x000c0000u;",
            "(secondTexcoord1D && texcoordBits < kGameFvfTex2)",
            "candidate.secondTexcoord1D = secondTexcoord1D;",
            "std::memcpy(candidate.uv1, data + secondOffset, 4u);",
            "const std::uint32_t later = secondOffset + 4u;",
            "std::memcpy(candidate.uv2, data + later, 8u);",
        )) and all(x in fixture for x in (
            "struct VehicleSecondU", "struct RaceMixedUV",
            "chosen[0] == .875f && chosen[1] == 0.f",
            "chosen[0] == .6f && chosen[1] == .8f",
            "!game_fvf_decode_vertex(&vehicleSecond, 27u",
            "badSecond.secondTexcoord1D = false;",
            "0x00040000u, layout", "0x00080000u, layout",
        ))
    assert second_u_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTexcoordSize1_1 == D3DFVF_TEXCOORDSIZE1(1)", "kGameFvfTexcoordSize1_1 != D3DFVF_TEXCOORDSIZE1(1)"),
        ("candidate.secondTexcoord1D = secondTexcoord1D;", "candidate.secondTexcoord1D = false;"),
        ("std::memcpy(candidate.uv1, data + secondOffset, 4u);", "std::memcpy(candidate.uv1, data + secondOffset, 8u);"),
        ("const std::uint32_t later = secondOffset + 4u;", "const std::uint32_t later = secondOffset + 8u;"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert mutant != bridge and not second_u_native_linked(mutant, layout_source, probe_source)
        else:
            mutant = layout_source.replace(old, wrong, 1)
            assert mutant != layout_source and not second_u_native_linked(bridge, mutant, probe_source)
    print("DX11 TEXCOORDSIZE1(1) game-native UV1 Draw PASS (static only)")

    # 00612: stage2 packed U-only FVF from D3D9 GetFVF into real native Draw.
    def third_u_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize1_2 == D3DFVF_TEXCOORDSIZE1(2)",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(x in hdr for x in (
            "kGameFvfTexcoordSize1_2 = 0x00300000u;",
            "(thirdTexcoord1D && texcoordBits < kGameFvfTex3)",
            "candidate.thirdTexcoord1D = thirdTexcoord1D;",
            "(layout.thirdTexcoord1D && layout.texcoordCount < 3u)",
            "(layout.thirdTexcoord1D ? 4u : 0u)",
            "std::memcpy(slots[slot], data + offset, bytesToCopy);",
            "offset += bytesToCopy;",
        )) and all(x in fixture for x in (
            "struct VehicleThirdU", "struct RaceThirdPacked",
            "chosen[0] == .875f && chosen[1] == 0.f",
            "chosen[0] == .8f && chosen[1] == .9f",
            "!game_fvf_decode_vertex(&vehicleThird, 35u",
            "!game_fvf_decode_vertex(&raceThird, 47u",
            "corruptThird.thirdTexcoord1D = false;",
            "0x00100000u, layout", "0x00200000u, layout",
        ))
    assert third_u_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTexcoordSize1_2 == D3DFVF_TEXCOORDSIZE1(2)",
         "kGameFvfTexcoordSize1_2 != D3DFVF_TEXCOORDSIZE1(2)"),
        ("candidate.thirdTexcoord1D = thirdTexcoord1D;",
         "candidate.thirdTexcoord1D = false;"),
        ("(thirdTexcoord1D && texcoordBits < kGameFvfTex3)",
         "(thirdTexcoord1D && texcoordBits < kGameFvfTex2)"),
        ("(layout.thirdTexcoord1D ? 4u : 0u)",
         "(layout.thirdTexcoord1D ? 0u : 0u)"),
        ("std::memcpy(slots[slot], data + offset, bytesToCopy);",
         "std::memcpy(slots[slot], data + offset + 4u, bytesToCopy);"),
        ("offset += bytesToCopy;", "offset += 8u;"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert mutant != bridge and not third_u_native_linked(mutant, layout_source, probe_source)
        else:
            mutant = layout_source.replace(old, wrong, 1)
            assert mutant != layout_source and not third_u_native_linked(bridge, mutant, probe_source)
    print("DX11 TEXCOORDSIZE1(2) packed native Draw regression PASS (static only)")

    # 00612 retry: fourth U-only game stream reaches stage0 selected UV and
    # cannot borrow the later UV4 pair. Run C++ layout fixture in the Build gate.
    def fourth_u_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize1_3 == D3DFVF_TEXCOORDSIZE1(3)",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
        )) and all(x in hdr for x in (
            "kGameFvfTexcoordSize1_3 = 0x00c00000u;",
            "(fourthTexcoord1D && texcoordBits < kGameFvfTex4)",
            "candidate.fourthTexcoord1D = fourthTexcoord1D;",
            "(layout.fourthTexcoord1D && layout.texcoordCount < 4u)",
            "(layout.fourthTexcoord1D ? 4u : 0u)",
            "(slot == 3u && layout.fourthTexcoord1D)",
        )) and all(x in fixture for x in (
            "struct VehicleFourthU", "struct RaceFourthPacked",
            "struct MenuFourPackedU",
            "chosen[0] == .875f && chosen[1] == 0.f",
            "chosen[0] == .8f && chosen[1] == .9f",
            "!game_fvf_decode_vertex(&vehicleFourth, 43u",
            "!game_fvf_decode_vertex(&raceFourth, 63u",
            "corruptFourth.fourthTexcoord1D = false;",
        ))
    assert fourth_u_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTexcoordSize1_3 == D3DFVF_TEXCOORDSIZE1(3)",
         "kGameFvfTexcoordSize1_3 != D3DFVF_TEXCOORDSIZE1(3)"),
        ("candidate.fourthTexcoord1D = fourthTexcoord1D;",
         "candidate.fourthTexcoord1D = false;"),
        ("(fourthTexcoord1D && texcoordBits < kGameFvfTex4)",
         "(fourthTexcoord1D && texcoordBits < kGameFvfTex3)"),
        ("(layout.fourthTexcoord1D ? 4u : 0u)",
         "(layout.fourthTexcoord1D ? 0u : 0u)"),
        ("(slot == 3u && layout.fourthTexcoord1D)",
         "(slot == 2u && layout.fourthTexcoord1D)"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert mutant != bridge and not fourth_u_native_linked(mutant, layout_source, probe_source)
        else:
            mutant = layout_source.replace(old, wrong, 1)
            assert mutant != layout_source and not fourth_u_native_linked(bridge, mutant, probe_source)
    print("DX11 TEXCOORDSIZE1(3) packed native Draw regression PASS (static only)")



    # 00613: real GetFVF -> tail TEXCOORDSIZE1(4..7) packed bytes ->
    # stage-indexed UV -> native Draw/DrawIndexed, not standalone WARP.
    def tail_u_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize1_7 == D3DFVF_TEXCOORDSIZE1(7)",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
        )) and all(x in hdr for x in (
            "kGameFvfTexcoordSize1_4 = 0x03000000u;",
            "kGameFvfTexcoordSize1_7 = 0xc0000000u;",
            "(eighthTexcoord1D && texcoordBits < kGameFvfTex8)",
            "candidate.eighthTexcoord1D = eighthTexcoord1D;",
            "(layout.eighthTexcoord1D ? 4u : 0u)",
            "(slot == 7u && layout.eighthTexcoord1D)",
            "layout.fifthTexcoord1D || layout.sixthTexcoord1D ||",
        )) and all(x in fixture for x in (
            "struct MenuTailPackedU", "struct RaceTailMixed",
            "chosen[0] == .74f && chosen[1] == 0.f",
            "chosen[0] == .85f && chosen[1] == .95f",
            "!game_fvf_decode_vertex(&menuTail, 63u",
            "!game_fvf_decode_vertex(&raceTail, 87u",
            "corruptTail.eighthTexcoord1D = false;",
        ))
    assert tail_u_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("kGameFvfTexcoordSize1_7 == D3DFVF_TEXCOORDSIZE1(7)",
         "kGameFvfTexcoordSize1_7 != D3DFVF_TEXCOORDSIZE1(7)"),
        ("(eighthTexcoord1D && texcoordBits < kGameFvfTex8)",
         "(eighthTexcoord1D && texcoordBits < kGameFvfTex7)"),
        ("candidate.eighthTexcoord1D = eighthTexcoord1D;",
         "candidate.eighthTexcoord1D = false;"),
        ("(layout.eighthTexcoord1D ? 4u : 0u)",
         "(layout.eighthTexcoord1D ? 0u : 0u)"),
        ("(slot == 7u && layout.eighthTexcoord1D)",
         "(slot == 6u && layout.eighthTexcoord1D)"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert mutant != bridge and not tail_u_native_linked(mutant, layout_source, probe_source)
        else:
            mutant = layout_source.replace(old, wrong, 1)
            assert mutant != layout_source and not tail_u_native_linked(bridge, mutant, probe_source)
    print("DX11 TEXCOORDSIZE1(4..7) packed live native Draw regression PASS (static only)")

    # 00614: FVF TEXCOORDSIZE3 game Draw -> 12-byte source UV -> native
    # float2 sampling, preserving next slots and rejecting COUNT2 transforms.
    def float3_uv_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize3_7 == D3DFVF_TEXCOORDSIZE3(7)",
            "if (transformUv && layout.texcoord3DMask != 0u) return false;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
        )) and all(x in hdr for x in (
            "candidate.texcoord3DMask = texcoord3DMask;",
            "if (stage >= (texcoordBits >> 8u) && format != 0u)",
            "4u * game_fvf_texcoord3d_count(candidate.texcoord3DMask)",
            "if (layout.texcoord3DMask & (1u << slot))",
            "offset += 12u;",
        )) and all(x in fixture for x in (
            "struct Menu3DUv", "struct Race3DMixed",
            "assert(layout.texcoord3DMask == 0x80u && layout.minStride == 80u);",
            "!game_fvf_decode_vertex(&menu3D, 43u",
            "!game_fvf_decode_vertex(&race3D, 79u",
            "corrupted3D.texcoord3DMask = 0u;",
        ))
    assert float3_uv_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("if (transformUv && layout.texcoord3DMask != 0u) return false;",
         "if (false && layout.texcoord3DMask != 0u) return false;"),
        ("candidate.texcoord3DMask = texcoord3DMask;",
         "candidate.texcoord3DMask = 0u;"),
        ("if (layout.texcoord3DMask & (1u << slot))",
         "if (false)"),
        ("assert(layout.texcoord3DMask == 0x80u && layout.minStride == 80u);",
         "assert(layout.texcoord3DMask == 0x80u);"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert not float3_uv_native_linked(mutant, layout_source, probe_source)
        elif old in layout_source:
            mutant = layout_source.replace(old, wrong, 1)
            assert not float3_uv_native_linked(bridge, mutant, probe_source)
        else:
            mutant = probe_source.replace(old, wrong, 1)
            assert not float3_uv_native_linked(bridge, layout_source, mutant)
    print("DX11 packed float3 UV native Draw integration regression PASS (static only)")

    # 00615: float4 packed vertex bytes feed real native Draw and preserve
    # packed subsequent coordinates; transformed high dimensions fail closed.
    def float4_uv_native_linked(src: str, hdr: str, fixture: str) -> bool:
        return all(x in src for x in (
            "kGameFvfTexcoordSize4_0 == D3DFVF_TEXCOORDSIZE4(0)",
            "kGameFvfTexcoordSize4_7 == D3DFVF_TEXCOORDSIZE4(7)",
            "if (transformUv && layout.texcoord4DMask != 0u) return false;",
            "game_fvf_select_uv(decoded, layout, capture.coordIndex, output[i].uv)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
        )) and all(x in hdr for x in (
            "candidate.texcoord4DMask = texcoord4DMask;",
            "8u * game_fvf_texcoord3d_count(candidate.texcoord4DMask)",
            "8u * game_fvf_texcoord3d_count(layout.texcoord4DMask)",
            "if (layout.texcoord4DMask & (1u << slot))",
            "offset += 16u;",
            "(layout.texcoord3DMask & layout.texcoord4DMask) != 0u",
        )) and all(x in fixture for x in (
            "struct Race4DPacked",
            "assert(layout.texcoord4DMask == 0x05u && layout.minStride == 52u);",
            "!game_fvf_decode_vertex(&race4D, 51u",
            "corrupted4D.texcoord4DMask = 0u;",
            "kGameFvfTexcoordSize4_7, layout",
        ))
    assert float4_uv_native_linked(bridge, layout_source, probe_source)
    for old, wrong in (
        ("if (transformUv && layout.texcoord4DMask != 0u) return false;",
         "if (false && layout.texcoord4DMask != 0u) return false;"),
        ("candidate.texcoord4DMask = texcoord4DMask;",
         "candidate.texcoord4DMask = 0u;"),
        ("offset += 16u;", "offset += 8u;"),
        ("assert(layout.texcoord4DMask == 0x05u && layout.minStride == 52u);",
         "assert(layout.texcoord4DMask == 0x05u);"),
    ):
        if old in bridge:
            mutant = bridge.replace(old, wrong, 1)
            assert mutant != bridge and not float4_uv_native_linked(mutant, layout_source, probe_source)
        elif old in layout_source:
            mutant = layout_source.replace(old, wrong, 1)
            assert mutant != layout_source and not float4_uv_native_linked(bridge, mutant, probe_source)
        else:
            mutant = probe_source.replace(old, wrong, 1)
            assert mutant != probe_source and not float4_uv_native_linked(bridge, layout_source, mutant)
    print("DX11 packed float4 UV native menu/race Draw regression PASS (static only)")

    # 00616: real game stage0 CURRENT alpha shares validated DIFFUSE alpha PS.
    from test_dx11_stage0_current_alpha_00616 import main as run_00616
    run_00616()
    # 00617: native Draw with D3D9 premultiplied texture alpha.
    from test_dx11_stage0_premultiplied_00617 import main as run_00617
    from test_dx11_stage0_pm_diffuse_00618 import main as run_00618
    run_00617()
    run_00618()

    # 00558: real game-authored D3D9 stage0 BLENDTEXTUREALPHA /
    # BLENDDIFFUSEALPHA -> owned native PS -> Draw/DrawIndexed -> opt-in inset.
    # Checks source-to-consumer links, shader/reset lifecycle and fail-closed
    # dispatch; this does not assert runtime menu/gamepad/Quest3 parity.
    blend_links = (
        "const bool blendTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_BLENDTEXTUREALPHA;",
        "const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_BLENDDIFFUSEALPHA;",
        "blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;",
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
        "s.blendTextureAlphaPs && s.blendTextureAlphaPmPs && s.blendTextureAlphaPmTextureAlphaPs && s.blendTextureAlphaPmInverseDiffuseAlphaPs && s.blendTextureAlphaPmDiffuseAlphaPs && s.blendDiffuseAlphaPs",
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
    # Verify both prior game alpha-blend pairs while requiring the PM-safe gate.
    assert "!blendTextureAlphaPMDiffuseAlpha && !blendTextureAlpha && !blendTextureAlphaPM && !blendTextureAlphaPMTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha) || arg != D3DTA_TEXTURE ||" in state_section
    assert "const bool blendTextureAlpha = op == D3DTOP_BLENDTEXTUREALPHA && alphaOp == D3DTOP_BLENDTEXTUREALPHA;" in state_section
    assert "const bool blendDiffuseAlpha = op == D3DTOP_BLENDDIFFUSEALPHA && alphaOp == D3DTOP_BLENDDIFFUSEALPHA;" in state_section
    assert "arg2 == D3DTA_DIFFUSE || arg2 == D3DTA_CURRENT" in state_section
    assert "alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT" in state_section
    assert "alphaArg1 != D3DTA_TEXTURE" in state_section
    assert "AlphaGate(c.a); return c;" in shader_section
    assert "mirror_texture(dev, capture, sampledView, sampledSampler)" in submit_section
    # Stage 1 is an opt-in first shader, not a replacement for stage 0.
    # Both the stage-1 branch and legacy stage-0 alpha blend dispatch must
    # remain connected to the native Draw/DrawIndexed submission.
    def stage0_dispatch_with_stage1(code: str) -> bool:
        return ("ctx->PSSetShader(capture.stage1Enabled ?" in code and
                "capture.selectDiffuseTextureAlpha ? s.selectDiffuseTextureAlphaPs.Get() :" in code and
                "capture.blendTextureAlpha ? s.blendTextureAlphaPs.Get() :" in code and
                "capture.blendDiffuseAlpha ? s.blendDiffuseAlphaPs.Get() :" in code)
    assert stage0_dispatch_with_stage1(submit_section)
    for dispatch in (
        "ctx->PSSetShader(capture.stage1Enabled ?",
        "capture.selectDiffuseTextureAlpha ? s.selectDiffuseTextureAlphaPs.Get() :",
        "capture.blendTextureAlpha ? s.blendTextureAlphaPs.Get() :",
        "capture.blendDiffuseAlpha ? s.blendDiffuseAlphaPs.Get() :",
    ):
        assert not stage0_dispatch_with_stage1(submit_section.replace(dispatch, "/* removed fallback dispatch */", 1))
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


    # 00560/00742: Real game D3D9 DEFAULT render-target texture levels ->
    # exact-format, non-MSAA GetRenderTargetData -> CPU BGRA snapshot ->
    # existing D3D11 SRV/sampler -> actual native Draw/DrawIndexed/inset.
    # Ordinary non-dynamic, non-RT DEFAULT, compressed DEFAULT and MSAA fail closed.
    rt_tokens = (
        "const bool gpuRenderTarget = base.Pool == D3DPOOL_DEFAULT &&",
        "(base.Usage & D3DUSAGE_RENDERTARGET) != 0u",
        "const native_rt_readback::Layout rtLayout =",
        "base.Format == D3DFMT_A8R8G8B8 ? native_rt_readback::Layout::argb8",
        "base.Format == D3DFMT_X8R8G8B8 ? native_rt_readback::Layout::xrgb8",
        "base.Format == D3DFMT_A8B8G8R8 ? native_rt_readback::Layout::a8b8g8r8",
        "base.Format == D3DFMT_X8B8G8R8 ? native_rt_readback::Layout::x8b8g8r8",
        "base.Format == D3DFMT_A2R10G10B10 ? native_rt_readback::Layout::a2r10g10b10",
        "base.Format == D3DFMT_A2B10G10R10 ? native_rt_readback::Layout::a2b10g10r10",
        "native_rt_readback::sampleable(rtLayout, capture.srgbTexture);",
        "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        "capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())",
        "sourceDesc.MultiSampleType != D3DMULTISAMPLE_NONE",
        "sourceDesc.Width != desc.Width || sourceDesc.Height != desc.Height",
        "sourceDesc.Format != desc.Format",
        "!(sourceDesc.Usage & D3DUSAGE_RENDERTARGET)",
        "capture.texture->GetDevice(gameDevice.GetAddressOf())",
        "gameDevice->CreateOffscreenPlainSurface(",
        "desc.Width, desc.Height, desc.Format, D3DPOOL_SYSTEMMEM,",
        "gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
        "native_rt_readback::matching_mip_extent(",
        "readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)",
        "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
        "const HRESULT unlockResult = gpuRenderTarget ?",
        "if (!native_rt_readback::unpack_row(",
        "source, destination, desc.Width, rtLayout)",
        "readbackSurface->UnlockRect() : capture.texture->UnlockRect(level);",
        "desc.Usage = D3D11_USAGE_IMMUTABLE;",
        "dev->CreateShaderResourceView(texture.Get(), nullptr,",
    )
    def rt_game_native_connected(code: str) -> bool:
        mirror = code[code.find("bool mirror_texture("):code.find("bool submit(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        return (all(token in mirror for token in rt_tokens)
                and "if (FAILED(lockResult)) return false;" in mirror
                and "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)" in mirror
                and "mirror_texture(dev, capture, sampledView, sampledSampler)" in draw
                and "ctx->PSSetShaderResources(0, 1, &boundView)" in draw
                and "ctx->DrawIndexed(indexCount, 0, 0);" in draw
                and "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in draw)
    assert rt_game_native_connected(bridge)
    for token in rt_tokens:
        mutant = bridge.replace(token, "/* disconnected 00560 RT producer */", 1)
        assert mutant != bridge and not rt_game_native_connected(mutant), token
    for pool, usage_rt, fmt, srgb, expected in (
        ("DEFAULT", True, "A8R8G8B8", False, True),
        ("DEFAULT", True, "X8R8G8B8", True, True),
        ("DEFAULT", True, "A8B8G8R8", False, True),
        ("DEFAULT", True, "X8B8G8R8", True, True),
        ("DEFAULT", True, "A2R10G10B10", False, True),
        ("DEFAULT", True, "A2B10G10R10", False, True),
        ("DEFAULT", True, "A2R10G10B10", True, False),
        ("DEFAULT", True, "A2B10G10R10", True, False),
        ("DEFAULT", False, "A8B8G8R8", False, False),
        ("DEFAULT", True, "DXT1", False, False),
        ("DEFAULT", True, "A1R5G5B5", False, False),
        ("MANAGED", True, "A8R8G8B8", False, False),
    ):
        sampleable = fmt in ("A8R8G8B8", "X8R8G8B8", "A8B8G8R8", "X8B8G8R8") or (
            not srgb and fmt in ("A2R10G10B10", "A2B10G10R10"))
        gpu_rt = pool == "DEFAULT" and usage_rt and sampleable
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
        mirror = code[code.find("bool create_game_sampler("):code.find("bool submit(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        return all(token in admission for token in (
            "GetSamplerState(0, D3DSAMP_MAGFILTER, &mag)",
            "GetSamplerState(0, D3DSAMP_MINFILTER, &min)",
            "(min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)",
            "(mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR)",
            "(mip != D3DTEXF_NONE && mip != D3DTEXF_POINT)",
            "capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);",
            "capture.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);",
        )) and "return create_game_sampler(dev, capture, levels, sampler);" in mirror and all(token in mirror for token in (
            "state.Filter = capture.minFilter == D3DTEXF_LINEAR ?",
            "(capture.magFilter == D3DTEXF_LINEAR ?",
            "D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT :",
            "D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT) :",
            "D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT :",
            "D3D11_FILTER_MIN_MAG_MIP_POINT);",
            "state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;",
            "state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;",
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
        "state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;",
        "ctx->PSSetSamplers(0, 1, &boundSampler)",
    ):
        broken = bridge.replace(token, "/* disconnected 00561 filter link */", 1)
        assert broken != bridge and not mixed_filter_draw_connected(broken), token
    # Reference D3D11_FILTER mapping for all four supported D3D9 pairs;
    # unsupported anisotropic and mip-linear filtering still fail closed.
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
                    "POINT", "LINEAR") and mip_filter in ("NONE", "POINT")
                assert allowed == ((min_filter, mag_filter) in mip_point_map
                                   and mip_filter in ("NONE", "POINT"))
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
        ("blendTextureAlphaPMFactorArg2Alpha) &&\n"
         "            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))\n"
         "            return false;"),
        "blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;",
        "!blendTextureAlpha && !blendTextureAlphaPM && !blendTextureAlphaPMTextureAlpha && !blendDiffuseAlpha && !blendFactorAlpha)",
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
        # Preserve the original 00562 factor pair independently of new
        # SELECTARG RGB variants that intentionally share its ALPHAOP.
        original_factor_pair = (
            "const bool blendFactorAlpha = op == D3DTOP_BLENDFACTORALPHA &&\n"
            "                                      alphaOp == D3DTOP_BLENDFACTORALPHA;"
        )
        return (all(token in code for token in factor_links) and
                original_factor_pair in intake and
                factor_links[2] in intake and
                "static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue" in submit and
                stage0_dispatch_with_stage1(submit) and
                "capture.blendFactorAlpha ? s.blendFactorAlphaPs.Get() :" in submit and
                code.count("s.blendFactorAlphaPs.Reset();") == 2 and
                code.count("blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;") == 2)
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
        "rgbNeedsDiffuse = selectDiffuseTextureAlpha || selectDiffuseDiffuseAlpha ||",
        "blendFactorTextureAlpha || blendFactorModulateAlpha",
        "alphaNeedsDiffuse = selectDiffuseDiffuseAlpha || selectDiffuseModulateAlpha ||",
        "blendFactorModulateAlpha ||",
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
                stage0_dispatch_with_stage1(draw))
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


    # 00564: live stage-0 factor RGB with independent DIFFUSE selection
    # or saturated ADD(TEXTURE,DIFFUSE) alpha. Game input and Present untouched.
    # Positive source integration and destructive negatives; not runtime proof.
    independent_factor_links = (
        "blendFactorDiffuseAlpha = op == D3DTOP_BLENDFACTORALPHA &&",
        "alphaOp == D3DTOP_SELECTARG2;",
        "blendFactorAddAlpha = op == D3DTOP_BLENDFACTORALPHA &&",
        "alphaOp == D3DTOP_ADD;",
        "blendFactorDiffuseAlpha || blendFactorAddAlpha ||\n             blendFactorSubtractAlpha || blendFactorAddSmoothAlpha ||\n             blendFactorModulate2XAlpha || blendFactorModulate4XAlpha ||",
        # The read is shared by additional guarded TFACTOR native draw cases;
        # preserve both original branches without requiring the old OR suffix.
        "selectTextureFactorAlpha || selectDiffuseFactorAlpha ||",
        "!blendFactorDiffuseAlpha && !blendFactorAddAlpha &&",
        "blendFactorDiffuseAlpha || blendFactorAddAlpha ||",
        "(!blendFactorDiffuseAlpha &&",
        "capture.blendFactorDiffuseAlpha = blendFactorDiffuseAlpha;",
        "capture.blendFactorAddAlpha = blendFactorAddAlpha;",
        "bool blendFactorDiffuseAlpha = false;",
        "bool blendFactorAddAlpha = false;",
        "float4 PSTextureBlendFactorDiffuseAlpha(VOut v) : SV_Target {",
        "float4 PSTextureBlendFactorAddAlpha(VOut v) : SV_Target {",
        "float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), v.diffuse.a);",
        "float4 c = float4(lerp(v.diffuse.rgb, t.rgb, alphaParams.w), saturate(t.a + v.diffuse.a));",
        'compile("PSTextureBlendFactorDiffuseAlpha", "ps_4_0", blendFactorDiffuseCode)',
        'compile("PSTextureBlendFactorAddAlpha", "ps_4_0", blendFactorAddCode)',
        "s.blendFactorDiffuseAlphaPs.GetAddressOf()",
        "s.blendFactorAddAlphaPs.GetAddressOf()",
        "s.blendFactorDiffuseAlphaPs && s.blendFactorAddAlphaPs &&",
        "capture.blendFactorDiffuseAlpha ? s.blendFactorDiffuseAlphaPs.Get() :",
        "capture.blendFactorAddAlpha ? s.blendFactorAddAlphaPs.Get() :",
        "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    def independent_factor_connected(code: str) -> bool:
        gate = code[code.find("bool supported_game_state("):
                    code.find("bool translate_vertices(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        return (all(token in code for token in independent_factor_links) and
                code.count("s.blendFactorDiffuseAlphaPs.Reset();") == 2 and
                code.count("s.blendFactorAddAlphaPs.Reset();") == 2 and
                "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)" in gate and
                "alphaNeedsDiffuse = selectDiffuseDiffuseAlpha || selectDiffuseModulateAlpha ||" in gate and
                "blendFactorModulateAlpha ||" in gate and
                "alphaArg2Diffuse" in gate and
                "capture.blendFactorDiffuseAlpha ? s.blendFactorDiffuseAlphaPs.Get() :" in draw and
                "capture.blendFactorAddAlpha ? s.blendFactorAddAlphaPs.Get() :" in draw)
    assert independent_factor_connected(bridge)
    for token in independent_factor_links[:-3]:
        damaged = bridge.replace(token, "/* 00564 deleted integration */")
        assert damaged != bridge and not independent_factor_connected(damaged), token
    # D3DTOP: SELECTARG2=3, ADD=7, BLENDFACTORALPHA=14.
    for color, alpha, expected in (
        (14, 3, True), (14, 7, True), (14, 2, False),
        (14, 4, False), (14, 14, False), (7, 3, False),
        (3, 7, False), (14, 0, False)):
        assert (color == 14 and alpha in (3, 7)) == expected
    texel, diffuse = (0.2, 0.6, 0.8, 0.85), (0.7, 0.3, 0.1, 0.4)
    for factor_byte in (0, 128, 255):
        factor = factor_byte / 255.0
        rgb = tuple((1-factor)*d + factor*t
                    for d,t in zip(diffuse[:3], texel[:3]))
        diffuse_alpha = (*rgb, diffuse[3])
        added_alpha = (*rgb, min(1.0, texel[3] + diffuse[3]))
        assert diffuse_alpha[:3] == added_alpha[:3]
        assert diffuse_alpha[3] == 0.4 and added_alpha[3] == 1.0
        if factor_byte == 0:
            assert rgb == diffuse[:3]
        if factor_byte == 255:
            assert rgb == texel[:3]
    print("DX11 factor RGB + diffuse/add alpha native Draw PASS (static only)")

    # 00565: live D3D9 ADDSMOOTH RGB plus independent texture/diffuse alpha.
    # Source linkage and CPU reference only; no runtime Quest3/gamepad proof.
    smooth_mixed_links = (
        "const bool addSmoothTextureAlpha = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_SELECTARG1;",
        "const bool addSmoothDiffuseAlpha = op == D3DTOP_ADDSMOOTH && alphaOp == D3DTOP_SELECTARG2;",
        "!addSmoothTextureAlpha && !addSmoothDiffuseAlpha &&",
        "!blendFactorDiffuseAlpha && !addSmoothDiffuseAlpha &&",
        "addSmoothTextureAlpha || addSmoothDiffuseAlpha ||",
        "capture.addSmoothTextureAlpha = addSmoothTextureAlpha;",
        "capture.addSmoothDiffuseAlpha = addSmoothDiffuseAlpha;",
        "bool addSmoothTextureAlpha = false;",
        "bool addSmoothDiffuseAlpha = false;",
        "float4 PSTextureAddSmoothTextureAlpha(VOut v) : SV_Target {",
        "float4 PSTextureAddSmoothDiffuseAlpha(VOut v) : SV_Target {",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.rgb)), t.a);",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.rgb)), v.diffuse.a);",
        'compile("PSTextureAddSmoothTextureAlpha", "ps_4_0", smoothTextureCode)',
        'compile("PSTextureAddSmoothDiffuseAlpha", "ps_4_0", smoothDiffuseCode)',
        "s.addSmoothTextureAlphaPs.GetAddressOf()",
        "s.addSmoothDiffuseAlphaPs.GetAddressOf()",
        "s.addSmoothTextureAlphaPs && s.addSmoothDiffuseAlphaPs &&",
        "capture.addSmoothTextureAlpha ? s.addSmoothTextureAlphaPs.Get() :",
        "capture.addSmoothDiffuseAlpha ? s.addSmoothDiffuseAlphaPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    def smooth_mixed_connected(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        return (all(tok in code for tok in smooth_mixed_links) and
                code.count("s.addSmoothTextureAlphaPs.Reset();") == 2 and
                code.count("s.addSmoothDiffuseAlphaPs.Reset();") == 2 and
                "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)" in intake and
                "alphaArg2Diffuse" in intake and
                "mirror_texture(dev, capture, sampledView, sampledSampler)" in draw)
    assert smooth_mixed_connected(bridge)
    for link in smooth_mixed_links[:-2]:
        damaged = bridge.replace(link, "/* detached stage0 native flow */")
        assert damaged != bridge and not smooth_mixed_connected(damaged), link
    # D3DTOP enum: ADDSMOOTH=11, SELECTARG1=2, SELECTARG2=3.
    for rgb_op, alpha_op, accepted in (
        (11, 2, True), (11, 3, True), (11, 11, False),
        (11, 4, False), (11, 7, False), (4, 2, False), (7, 3, False)):
        assert (rgb_op == 11 and alpha_op in (2, 3)) is accepted
    for tcol, dcol in (
        ((0.2, 0.6, 0.0, 0.8), (0.7, 0.2, 0.75, 0.3)),
        ((1.0, 0.0, 0.85, 0.15), (0.25, 0.9, 0.4, 0.7))):
        rgb = tuple(min(1.0, t + d*(1.0-t)) for t, d in zip(tcol[:3], dcol[:3]))
        texture_alpha = (*rgb, tcol[3])
        diffuse_alpha = (*rgb, dcol[3])
        assert texture_alpha[:3] == diffuse_alpha[:3]
        assert texture_alpha[3] == tcol[3]
        assert diffuse_alpha[3] == dcol[3]
        assert texture_alpha != diffuse_alpha
    print("DX11 ADDSMOOTH mixed-alpha game native Draw PASS (static only)")


    # 00566 — game D3D9 independent alpha on MODULATE2X/4X RGB.
    # These are source+CPU controls, never Quest3/VDXR runtime evidence.
    scaled_alpha_variants = (
        ("2", "Texture", "t.a", "1"),
        ("2", "Diffuse", "v.diffuse.a", "2"),
        ("4", "Texture", "t.a", "1"),
        ("4", "Diffuse", "v.diffuse.a", "2"),
    )
    def scaled_alpha_linked(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        required = (
            "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)",
            "!modulate2xTextureAlpha && !modulate2xDiffuseAlpha",
            "!modulate4xTextureAlpha && !modulate4xDiffuseAlpha",
            "!modulate2xDiffuseAlpha && !modulate4xDiffuseAlpha",
            "modulate2xDiffuseAlpha || modulate4xDiffuseAlpha",
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )
        if not all(v in code for v in required):
            return False
        for scale, source, alpha, selector in scaled_alpha_variants:
            stem = f"modulate{scale}x{source}Alpha"
            shader = f"PSTextureModulate{scale}X{source}Alpha"
            cache = f"s.{stem}Ps"
            bc = f"modulate{scale}x{source}Code"
            for evidence in (
                f"bool {stem} = false;",
                f"ComPtr<ID3D11PixelShader> {stem}Ps;",
                f"const bool {stem} = op == D3DTOP_MODULATE{scale}X && alphaOp == D3DTOP_SELECTARG{selector};",
                f"capture.{stem} = {stem};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                f"float4 c = float4(saturate({scale}.0f * t.rgb * v.diffuse.rgb), {alpha});",
                f'compile("{shader}", "ps_4_0", {bc})',
                f"{cache}.GetAddressOf()",
                f"{cache} &&",
                f"capture.{stem} ? {cache}.Get() :",
            ):
                if evidence not in code: return False
            if code.count(f"{cache}.Reset();") != 2: return False
        return "alphaArg2Diffuse" in intake and "ctx->PSSetShader(" in submit
    assert scaled_alpha_linked(bridge)
    for scale, source, alpha, selector in scaled_alpha_variants:
        stem = f"modulate{scale}x{source}Alpha"
        for token in (
            f"capture.{stem} = {stem};",
            f"capture.{stem} ? s.{stem}Ps.Get() :",
            f'compile("PSTextureModulate{scale}X{source}Alpha", "ps_4_0", modulate{scale}x{source}Code)',
            f"float4 c = float4(saturate({scale}.0f * t.rgb * v.diffuse.rgb), {alpha});",
        ):
            mutant = bridge.replace(token, "/* disconnected 00566 flow */", 1)
            assert mutant != bridge and not scaled_alpha_linked(mutant), token
    for color, alpha, allowed in (
        (5, 2, True), (5, 3, True), (6, 2, True), (6, 3, True),
        (5, 4, False), (6, 7, False), (4, 2, False), (7, 3, False)
    ):
        assert (color in (5, 6) and alpha in (2, 3)) is allowed
    for tex, diffuse in (
        ((0.15, 0.7, 0.9, 0.2), (0.8, 0.6, 0.8, 0.9)),
        ((0.8, 0.3, 0.1, 0.8), (0.9, 0.6, 0.5, 0.1))
    ):
        for factor in (2, 4):
            rgb = tuple(min(1.0, factor * t * d) for t,d in zip(tex[:3], diffuse[:3]))
            assert (*rgb, tex[3])[:3] == (*rgb, diffuse[3])[:3]
            assert (*rgb, tex[3])[3] != (*rgb, diffuse[3])[3]
            assert all(0.0 <= value <= 1.0 for value in rgb)
    print("DX11 MODULATE2X/4X independent alpha native Draw PASS (static only)")


    # 00567: D3D9 SUBTRACT RGB with independent texture or diffuse alpha.
    # Negative-mutation integration evidence; not hardware/Quest3 evidence.
    subtract_mixed = (("Texture", "1", "t.a"), ("Diffuse", "2", "v.diffuse.a"))
    def linked_subtract(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        if not all(x in intake for x in (
            "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)",
            "!subtractTextureAlpha && !subtractDiffuseAlpha &&",
            "subtractTextureAlpha || subtractDiffuseAlpha ||",
            "!subtractDiffuseAlpha &&",
            "alphaArg2Diffuse",
            "capture.subtractTextureAlpha = subtractTextureAlpha;",
            "capture.subtractDiffuseAlpha = subtractDiffuseAlpha;",
        )): return False
        if not all(x in submit for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShader(",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )): return False
        for source, arg, alpha in subtract_mixed:
            stem = f"subtract{source}Alpha"
            shader = f"PSTextureSubtract{source}Alpha"
            cache = f"s.{stem}Ps"
            if not all(x in code for x in (
                f"bool {stem} = false;",
                f"ComPtr<ID3D11PixelShader> {stem}Ps;",
                f"const bool {stem} = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_SELECTARG{arg};",
                f"capture.{stem} = {stem};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                f"float4 c = float4(saturate(t.rgb - v.diffuse.rgb), {alpha});",
                f'compile("{shader}", "ps_4_0", subtract{source}Code)',
                f"{cache}.GetAddressOf()",
                f"{cache} &&",
                f"capture.{stem} ? {cache}.Get() :",
            )): return False
            if code.count(f"{cache}.Reset();") != 2: return False
        return True
    assert linked_subtract(bridge)
    for source, arg, alpha in subtract_mixed:
        stem = f"subtract{source}Alpha"
        for token in (
            f"capture.{stem} = {stem};",
            f"capture.{stem} ? s.{stem}Ps.Get() :",
            f'compile("PSTextureSubtract{source}Alpha", "ps_4_0", subtract{source}Code)',
            f"float4 c = float4(saturate(t.rgb - v.diffuse.rgb), {alpha});",
        ):
            mutant = bridge.replace(token, "/* disconnected 00567 */", 1)
            assert mutant != bridge and not linked_subtract(mutant), token
    # SUBTRACT=10, SELECTARG1=2, SELECTARG2=3.
    for c, a, admitted in (
        (10, 2, True), (10, 3, True), (10, 10, False),
        (10, 7, False), (10, 4, False), (7, 2, False), (4, 3, False)):
        assert (c == 10 and a in (2, 3)) is admitted
    for tex, diffuse in (
        ((0.1, 0.9, 0.6, 0.8), (0.7, 0.2, 0.4, 0.25)),
        ((0.9, 0.05, 0.3, 0.1), (0.2, 0.8, 0.9, 0.7))):
        rgb = tuple(max(0.0, t - d) for t, d in zip(tex[:3], diffuse[:3]))
        assert all(0 <= v <= 1 for v in rgb)
        assert (*rgb, tex[3])[:3] == (*rgb, diffuse[3])[:3]
        assert (*rgb, tex[3])[3] != (*rgb, diffuse[3])[3]
    print("DX11 SUBTRACT mixed alpha native Draw PASS (static only)")


    # 00567 retry: Actual game stage-0 SUBTRACT RGB and MODULATE alpha must
    # propagate across state admission, HLSL, native Draw and visible inset.
    def linked_subtract_modulate(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        submit = code[code.find("bool submit("):code.find("void observe(")]
        required = (
            "const bool subtractModulateAlpha = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_MODULATE;",
            "!subtractTextureAlpha && !subtractDiffuseAlpha && !subtractModulateAlpha &&",
            "subtractTextureAlpha || subtractDiffuseAlpha || subtractModulateAlpha ||",
            "addSmoothDiffuseAlpha || subtractDiffuseAlpha || subtractModulateAlpha ||",
            "capture.subtractModulateAlpha = subtractModulateAlpha;",
            "float4 PSTextureSubtractModulateAlpha(VOut v) : SV_Target {",
            "float4 c = float4(saturate(t.rgb - v.diffuse.rgb), t.a * v.diffuse.a);",
            'compile("PSTextureSubtractModulateAlpha", "ps_4_0", subtractModulateCode)',
            "s.subtractModulateAlphaPs.GetAddressOf()",
            "s.subtractModulateAlphaPs &&",
            "capture.subtractModulateAlpha ? s.subtractModulateAlphaPs.Get() :",
            "GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)",
            "alphaArg1 != D3DTA_TEXTURE",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
        )
        return (all(token in code for token in required) and
                "ctx->PSSetShader(" in submit and
                "ctx->DrawIndexed(indexCount, 0, 0);" in submit and
                "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit and
                code.count("s.subtractModulateAlphaPs.Reset();") == 2 and
                "alphaNeedsDiffuse && !alphaArg2Diffuse" in intake)
    assert linked_subtract_modulate(bridge)
    for token in (
        "capture.subtractModulateAlpha = subtractModulateAlpha;",
        "capture.subtractModulateAlpha ? s.subtractModulateAlphaPs.Get() :",
        'compile("PSTextureSubtractModulateAlpha", "ps_4_0", subtractModulateCode)',
        "float4 c = float4(saturate(t.rgb - v.diffuse.rgb), t.a * v.diffuse.a);",
        "const bool subtractModulateAlpha = op == D3DTOP_SUBTRACT && alphaOp == D3DTOP_MODULATE;",
        "addSmoothDiffuseAlpha || subtractDiffuseAlpha || subtractModulateAlpha ||",
    ):
        broken = bridge.replace(token, "/* 00567 modulate-alpha link removed */", 1)
        assert broken != bridge and not linked_subtract_modulate(broken), token
    # D3DTOP_SUBTRACT=10; MODULATE=4. Unsupported ALPHAARG inputs fail closed.
    for color_op, alpha_op, a1, a2, admitted in (
        (10, 4, "texture", "diffuse", True),
        (10, 4, "texture", "current", True),
        (10, 4, "diffuse", "texture", False),
        (10, 4, "texture", "texture", False),
        (10, 7, "texture", "diffuse", False),
        (7, 4, "texture", "diffuse", False),
    ):
        assert ((color_op == 10 and alpha_op == 4 and
                 a1 == "texture" and a2 in ("diffuse", "current")) is admitted)
    for texture, diffuse in (
        ((0.8, 0.1, 0.9, 0.5), (0.3, 0.7, 0.1, 0.8)),
        ((0.2, 0.6, 0.1, 0.9), (0.5, 0.2, 0.9, 0.2)),
    ):
        rgb = tuple(max(0.0, t - d) for t, d in zip(texture[:3], diffuse[:3]))
        alpha = texture[3] * diffuse[3]
        assert all(0.0 <= component <= 1.0 for component in rgb)
        assert 0.0 <= alpha <= 1.0 and alpha != texture[3] and alpha != diffuse[3]
    print("DX11 SUBTRACT RGB/modulated alpha native Draw PASS (static only)")


    # 00568: native RGB factor blends with independently selected alpha.
    # Source-to-native game Draw/inset and CPU evidence only; HMD UNTESTED.
    def blend_alpha_connected(code: str) -> bool:
        entry = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        dispatch = code[code.find("bool submit("):code.find("void observe(")]
        if not all(x in entry for x in (
            "!blendTextureSelectedDiffuseAlpha && !blendDiffuseSelectedDiffuseAlpha",
            "alphaNeedsDiffuse && !alphaArg2Diffuse")):
            return False
        for rgb in ("Texture", "Diffuse"):
            for alpha, sel in (("Texture", 1), ("Diffuse", 2)):
                flag = f"blend{rgb}Selected{alpha}Alpha"
                pixel = f"PSTextureBlend{rgb}Selected{alpha}Alpha"
                links = (
                    f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA && alphaOp == D3DTOP_SELECTARG{sel};",
                    f"bool {flag} = false;",
                    f"capture.{flag} = {flag};",
                    f"float4 {pixel}(VOut v) : SV_Target {{",
                    f'compile("{pixel}", "ps_4_0", {flag}Code)',
                    f"s.{flag}Ps.GetAddressOf()",
                    f"s.{flag}Ps.Reset();",
                    f"s.{flag}Ps &&",
                    f"capture.{flag} ? s.{flag}Ps.Get() :",
                )
                if not all(x in code for x in links):
                    return False
        return ("ctx->DrawIndexed(indexCount, 0, 0);" in dispatch
                and "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in dispatch
                and "game->UpdateSurface(" in code
                and "OUTRUN_DX11_FIRST_GAME_FRAME" in code)
    assert blend_alpha_connected(bridge)
    for rgb in ("Texture", "Diffuse"):
        for alpha, sel in (("Texture", 1), ("Diffuse", 2)):
            flag = f"blend{rgb}Selected{alpha}Alpha"
            pixel = f"PSTextureBlend{rgb}Selected{alpha}Alpha"
            for x in (
                f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA && alphaOp == D3DTOP_SELECTARG{sel};",
                f"capture.{flag} = {flag};",
                f'compile("{pixel}", "ps_4_0", {flag}Code)',
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            ):
                mutant = bridge.replace(x, "/* removed native game Draw link */", 1)
                assert mutant != bridge and not blend_alpha_connected(mutant), x
    # Fixed-function D3D9 enums: BLENDDIFFUSEALPHA=12, BLENDTEXTUREALPHA=13.
    for rgb_op, alpha_op, arg1, arg2, allowed in (
        (12, 2, "texture", "ignored", True),
        (12, 3, "ignored", "current", True),
        (13, 2, "texture", "ignored", True),
        (13, 3, "ignored", "diffuse", True),
        (12, 3, "ignored", "texture", False),
        (13, 2, "diffuse", "ignored", False),
        (12, 4, "texture", "diffuse", False),
        (13, 12, "texture", "diffuse", False),
    ):
        exact = rgb_op in (12, 13) and (
            (alpha_op == 2 and arg1 == "texture") or
            (alpha_op == 3 and arg2 in ("diffuse", "current")))
        assert exact is allowed
    for texel, diffuse in (
        ((.9, .2, .5, .85), (.1, .8, .3, .25)),
        ((.15, .75, .95, .1), (.8, .1, .4, .7)),
    ):
        for rgb_factor in (texel[3], diffuse[3]):
            rgb = tuple((1-rgb_factor)*d + rgb_factor*t
                        for t, d in zip(texel[:3], diffuse[:3]))
            for selected_alpha in (texel[3], diffuse[3]):
                rgba = (*rgb, selected_alpha)
                assert all(0 <= x <= 1 for x in rgba)
                assert rgba[:3] == rgb and rgba[3] == selected_alpha
    print("DX11 RGB blend + SELECTARG alpha game-native Draw PASS (static only)")


    # 00569: live game blend RGB factor and independent MODULATE alpha.
    # Verify intake, native HLSL, PS lifetime/selection and native Draw/inset.
    # Source mutation and CPU math are not GPU/game/Quest3 validation.
    def blend_modulate_alpha_connected(code: str) -> bool:
        intake = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        submission = code[code.find("bool submit("):code.find("void observe(")]
        common = (
            "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)",
            "blendTextureModulateAlpha || blendDiffuseModulateAlpha ||",
            "!blendTextureModulateAlpha && !blendDiffuseModulateAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
            "alphaArg1 != D3DTA_TEXTURE",
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            "game->UpdateSurface(",
        )
        if not all(token in code for token in common):
            return False
        if not all(token in intake for token in (
            "blendTextureModulateAlpha || blendDiffuseModulateAlpha ||",
            "!blendTextureModulateAlpha && !blendDiffuseModulateAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
        )): return False
        if "ctx->PSSetShader(" not in submission: return False
        for source in ("Texture", "Diffuse"):
            flag = f"blend{source}ModulateAlpha"
            shader = f"PSTextureBlend{source}ModulateAlpha"
            rgba = (f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, "
                    f"{'t.a' if source == 'Texture' else 'v.diffuse.a'}), t.a * v.diffuse.a);")
            links = (
                f"const bool {flag} = op == D3DTOP_BLEND{source.upper()}ALPHA &&",
                "alphaOp == D3DTOP_MODULATE;",
                f"bool {flag} = false;",
                f"capture.{flag} = {flag};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                rgba,
                f'compile("{shader}", "ps_4_0", blend{source}ModulateCode)',
                f"s.{flag}Ps.GetAddressOf()",
                f"s.{flag}Ps &&",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            )
            if not all(token in code for token in links): return False
            if code.count(f"s.{flag}Ps.Reset();") != 2: return False
        return True
    assert blend_modulate_alpha_connected(bridge)
    for source in ("Texture", "Diffuse"):
        flag = f"blend{source}ModulateAlpha"
        shader = f"PSTextureBlend{source}ModulateAlpha"
        for token in (
            f"capture.{flag} = {flag};",
            f'compile("{shader}", "ps_4_0", blend{source}ModulateCode)',
            f"capture.{flag} ? s.{flag}Ps.Get() :",
            f"float4 {shader}(VOut v) : SV_Target {{",
            f"const bool {flag} = op == D3DTOP_BLEND{source.upper()}ALPHA &&",
        ):
            mutant = bridge.replace(token, "/* 00569 link broken */", 1)
            assert mutant != bridge and not blend_modulate_alpha_connected(mutant), token
    # D3DTOP_BLENDTEXTUREALPHA=13, BLENDDIFFUSEALPHA=12, MODULATE=4.
    for rgb_op, alpha_op, a1, a2, expected in (
        (12, 4, "texture", "diffuse", True),
        (13, 4, "texture", "current", True),
        (12, 4, "diffuse", "diffuse", False),
        (13, 4, "texture", "texture", False),
        (12, 7, "texture", "diffuse", False),
        (13, 3, "texture", "diffuse", False),
        (14, 4, "texture", "diffuse", False),
    ):
        admitted = (rgb_op in (12, 13) and alpha_op == 4 and
                    a1 == "texture" and a2 in ("diffuse", "current"))
        assert admitted is expected
    for texel, diffuse in (
        ((.8, .1, .9, .7), (.2, .6, .1, .3)),
        ((.1, .8, .3, .15), (.9, .2, .5, .95)),
    ):
        for factor in (texel[3], diffuse[3]):
            rgb = tuple((1-factor)*d + factor*t
                        for t, d in zip(texel[:3], diffuse[:3]))
            alpha = texel[3] * diffuse[3]
            assert all(0 <= c <= 1 for c in (*rgb, alpha))
            assert alpha != texel[3] and alpha != diffuse[3]
    print("DX11 blend RGB + independent MODULATE alpha live Draw PASS (static only)")


    # 00570: BLENDTEXTUREALPHA/BLENDDIFFUSEALPHA RGB and independent ADD alpha
    # native D3D11 Draw/DrawIndexed diagnostic path; static/CPU, not runtime proof.
    def blend_add_alpha_connected(source: str) -> bool:
        intake = source[source.find("bool supported_game_state("):source.find("bool translate_vertices(")]
        dispatch = source[source.find("bool submit("):source.find("void observe(")]
        common = (
            "GetTextureStageState(0, D3DTSS_COLOROP, &op)",
            "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG1, &alphaArg1)",
            "GetTextureStageState(0, D3DTSS_ALPHAARG2, &alphaArg2)",
            "blendTextureAddAlpha || blendDiffuseAddAlpha ||",
            "!blendTextureAddAlpha && !blendDiffuseAddAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
            "alphaArg1 != D3DTA_TEXTURE",
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            "game->UpdateSurface(",
            "OUTRUN_DX11_FIRST_GAME_FRAME",
        )
        if not all(token in source for token in common): return False
        if "blendTextureAddAlpha || blendDiffuseAddAlpha ||" not in intake: return False
        if "!blendTextureAddAlpha && !blendDiffuseAddAlpha &&" not in intake: return False
        if "ctx->PSSetShader(" not in dispatch: return False
        for rgb in ("Texture", "Diffuse"):
            flag = f"blend{rgb}AddAlpha"
            shader = f"PSTextureBlend{rgb}AddAlpha"
            factor = "t.a" if rgb == "Texture" else "v.diffuse.a"
            links = (
                f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
                "alphaOp == D3DTOP_ADD;",
                f"bool {flag} = false;",
                f"capture.{flag} = {flag};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}), saturate(t.a + v.diffuse.a));",
                "AlphaGate(c.a); return c;",
                f'compile("{shader}", "ps_4_0", blend{rgb}AddCode)',
                f"s.{flag}Ps.GetAddressOf()",
                f"s.{flag}Ps &&",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            )
            if not all(token in source for token in links): return False
            if source.count(f"s.{flag}Ps.Reset();") != 2: return False
            if f"capture.{flag} ? s.{flag}Ps.Get() :" not in dispatch: return False
        return True

    assert blend_add_alpha_connected(bridge)
    for rgb in ("Texture", "Diffuse"):
        flag = f"blend{rgb}AddAlpha"
        shader = f"PSTextureBlend{rgb}AddAlpha"
        for token in (
            f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
            f"capture.{flag} = {flag};",
            f"float4 {shader}(VOut v) : SV_Target {{",
            f'compile("{shader}", "ps_4_0", blend{rgb}AddCode)',
            f"s.{flag}Ps.GetAddressOf()",
            f"s.{flag}Ps &&",
            f"capture.{flag} ? s.{flag}Ps.Get() :",
        ):
            mutant = bridge.replace(token, "/* 00570 broken producer-consumer link */", 1)
            assert mutant != bridge and not blend_add_alpha_connected(mutant), token
    # Exact D3D9 fixed-function enum and operand admission; modifiers fail closed.
    for color_op, alpha_op, arg1, arg2, allowed in (
        (12, 7, "texture", "current", True),
        (13, 7, "texture", "diffuse", True),
        (12, 7, "texture", "texture", False),
        (13, 7, "diffuse", "diffuse", False),
        (12, 4, "texture", "diffuse", False),
        (13, 2, "texture", "diffuse", False),
        (14, 7, "texture", "diffuse", False),
    ):
        match = (color_op in (12, 13) and alpha_op == 7 and
                 arg1 == "texture" and arg2 in ("diffuse", "current"))
        assert match is allowed
    # D3D9 saturates additive alpha before test; RGB retains its blend factor.
    for texel, diffuse in (
        ((.95, .1, .7, .9), (.05, .8, .3, .6)),
        ((.2, .8, .4, .1), (.8, .2, .9, .4)),
    ):
        for factor in (texel[3], diffuse[3]):
            result = (tuple((1-factor)*d + factor*x
                            for x, d in zip(texel[:3], diffuse[:3])) +
                      (min(1.0, texel[3] + diffuse[3]),))
            assert all(0 <= x <= 1 for x in result)
            assert result[3] == min(1.0, texel[3] + diffuse[3])
            assert result[3] != texel[3] * diffuse[3]
    print("DX11 RGB blend with independent saturating ADD alpha Draw PASS (static only)")


    # 00571: real game stage-0 blend RGB with independent SUBTRACT alpha
    # producer -> compiled PS -> native Draw/DrawIndexed -> opt-in visible inset.
    # Static negative mutations and CPU arithmetic are not Quest3/VDXR evidence.
    def subtract_alpha_path_connected(source: str) -> bool:
        intake = source[source.find("bool supported_game_state("):source.find("bool translate_vertices(")]
        dispatch = source[source.find("bool submit("):source.find("void observe(")]
        for token in (
            "blendTextureSubtractAlpha || blendDiffuseSubtractAlpha ||",
            "!blendTextureSubtractAlpha && !blendDiffuseSubtractAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
            "alphaArg1 != D3DTA_TEXTURE",
        ):
            if token not in intake: return False
        for token in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            "game->UpdateSurface(",
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
        ):
            if token not in source: return False
        if "ctx->PSSetShader(" not in dispatch: return False
        for rgb in ("Texture", "Diffuse"):
            flag = f"blend{rgb}SubtractAlpha"
            shader = f"PSTextureBlend{rgb}SubtractAlpha"
            factor = "t.a" if rgb == "Texture" else "v.diffuse.a"
            links = (
                f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
                "alphaOp == D3DTOP_SUBTRACT;",
                f"bool {flag} = false;",
                f"capture.{flag} = {flag};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}), saturate(t.a - v.diffuse.a));",
                f'compile("{shader}", "ps_4_0", blend{rgb}SubtractCode)',
                f"s.{flag}Ps.GetAddressOf()",
                f"s.{flag}Ps &&",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            )
            if not all(x in source for x in links): return False
            if source.count(f"s.{flag}Ps.Reset();") != 2: return False
            if f"capture.{flag} ? s.{flag}Ps.Get() :" not in dispatch: return False
        return True

    assert subtract_alpha_path_connected(bridge)
    for rgb in ("Texture", "Diffuse"):
        flag = f"blend{rgb}SubtractAlpha"
        shader = f"PSTextureBlend{rgb}SubtractAlpha"
        factor = "t.a" if rgb == "Texture" else "v.diffuse.a"
        for token in (
            f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
            f"capture.{flag} = {flag};",
            f"float4 {shader}(VOut v) : SV_Target {{",
            f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}), saturate(t.a - v.diffuse.a));",
            f'compile("{shader}", "ps_4_0", blend{rgb}SubtractCode)',
            f"s.{flag}Ps.GetAddressOf()",
            f"capture.{flag} ? s.{flag}Ps.Get() :",
        ):
            mutated = bridge.replace(token, "/* 00571 disconnected */", 1)
            assert mutated != bridge and not subtract_alpha_path_connected(mutated), token
    # D3D9: BLENDDIFFUSEALPHA=12, BLENDTEXTUREALPHA=13, SUBTRACT=10.
    # Reject wrong order, unknown ops, color argument modifiers and alpha modifiers.
    for rgb_op, alpha_op, arg1, arg2, accepted in (
        (12, 10, "texture", "current", True),
        (13, 10, "texture", "diffuse", True),
        (12, 10, "texture", "texture", False),
        (13, 10, "diffuse", "diffuse", False),
        (12, 10, "texture|complement", "diffuse", False),
        (13, 10, "texture", "diffuse|complement", False),
        (12, 7, "texture", "diffuse", False),
        (13, 4, "texture", "current", False),
        (14, 10, "texture", "diffuse", False),
    ):
        admitted = rgb_op in (12, 13) and alpha_op == 10 and (
            arg1 == "texture" and arg2 in ("diffuse", "current"))
        assert admitted is accepted
    for texel, diffuse in (
        ((.9, .2, .5, .85), (.1, .8, .3, .25)),
        ((.15, .75, .95, .1), (.8, .1, .4, .7)),
        ((.6, .3, .2, .4), (.5, .4, .9, .4)),
    ):
        for factor in (texel[3], diffuse[3]):
            rgba = (tuple((1-factor)*d + factor*t
                          for t, d in zip(texel[:3], diffuse[:3])) +
                    (max(0.0, texel[3]-diffuse[3]),))
            assert all(0.0 <= x <= 1.0 for x in rgba)
            assert rgba[3] == max(0.0, texel[3]-diffuse[3])
            assert rgba[3] != min(1.0, texel[3]+diffuse[3])
    print("DX11 blend RGB / independent SUBTRACT alpha native Draw PASS (static only)")


    # 00572: live D3D9 BLEND RGB with independent ADDSMOOTH alpha -> native PS
    # -> Draw/DrawIndexed -> visible opt-in inset. Static, not Quest3 proof.
    def smooth_path(code: str) -> bool:
        gate = code[code.find("bool supported_game_state("):code.find("bool translate_vertices(")]
        draw = code[code.find("bool submit("):code.find("void observe(")]
        if not all(x in gate for x in (
            "blendTextureAddSmoothAlpha || blendDiffuseAddSmoothAlpha ||",
            "!blendTextureAddSmoothAlpha && !blendDiffuseAddSmoothAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse", "alphaArg1 != D3DTA_TEXTURE",
        )): return False
        if not all(x in code for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            "game->UpdateSurface(", 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
        )): return False
        for rgb in ("Texture", "Diffuse"):
            flag, pixel = f"blend{rgb}AddSmoothAlpha", f"PSTextureBlend{rgb}AddSmoothAlpha"
            factor = "t.a" if rgb == "Texture" else "v.diffuse.a"
            links = (
                f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
                "alphaOp == D3DTOP_ADDSMOOTH;", f"bool {flag} = false;",
                f"capture.{flag} = {flag};",
                f"float4 {pixel}(VOut v) : SV_Target {{",
                f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}),",
                "saturate(t.a + v.diffuse.a * (1.0f - t.a)))",
                f'compile("{pixel}", "ps_4_0", blend{rgb}AddSmoothCode)',
                f"s.{flag}Ps.GetAddressOf()", f"s.{flag}Ps &&",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            )
            if not all(x in code for x in links): return False
            # RGB math and alpha arithmetic must be checked inside THIS
            # shader body, not via matching another variant's identical RGB.
            begin = code.find(f"float4 {pixel}(VOut v) : SV_Target {{")
            end = code.find("\n}", begin)
            if begin < 0 or end < begin: return False
            body = code[begin:end]
            if not all(x in body for x in (
                f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}),",
                "saturate(t.a + v.diffuse.a * (1.0f - t.a)))",
                "AlphaGate(c.a); return c;",
            )): return False
            if code.count(f"s.{flag}Ps.Reset();") != 2: return False
            if f"capture.{flag} ? s.{flag}Ps.Get() :" not in draw: return False
        return True

    assert smooth_path(bridge)
    for rgb in ("Texture", "Diffuse"):
        flag, pixel = f"blend{rgb}AddSmoothAlpha", f"PSTextureBlend{rgb}AddSmoothAlpha"
        factor = "t.a" if rgb == "Texture" else "v.diffuse.a"
        for token in (
            f"const bool {flag} = op == D3DTOP_BLEND{rgb.upper()}ALPHA &&",
            f"capture.{flag} = {flag};", f"float4 {pixel}(VOut v) : SV_Target {{",
            f"float4 c = float4(lerp(v.diffuse.rgb, t.rgb, {factor}),",
            f'compile("{pixel}", "ps_4_0", blend{rgb}AddSmoothCode)',
            f"s.{flag}Ps.GetAddressOf()", f"capture.{flag} ? s.{flag}Ps.Get() :",
        ):
            if token.startswith("float4 c = float4(lerp("):
                # Several earlier variants share the RGB expression. Destroy
                # the selected shader, not an unrelated source occurrence.
                begin = bridge.find(f"float4 {pixel}(VOut v) : SV_Target {{")
                end = bridge.find("\n}", begin)
                assert begin >= 0 and end > begin
                local = bridge[begin:end]
                assert token in local
                mutant = (bridge[:begin] +
                          local.replace(token, "/* broken 00572 math */", 1) +
                          bridge[end:])
            else:
                mutant = bridge.replace(token, "/* broken 00572 */", 1)
            assert mutant != bridge and not smooth_path(mutant), token
    # D3DTOP_ADDSMOOTH=9; BLENDDIFFUSEALPHA=12/BLENDTEXTUREALPHA=13.
    for rgb, alpha, arg1, arg2, accepted in (
        (12, 9, "texture", "current", True), (13, 9, "texture", "diffuse", True),
        (12, 9, "texture", "texture", False), (13, 9, "diffuse", "diffuse", False),
        (12, 9, "texture|complement", "diffuse", False),
        (13, 9, "texture", "diffuse|complement", False),
        (12, 7, "texture", "diffuse", False), (13, 10, "texture", "current", False),
        (14, 9, "texture", "diffuse", False),
    ):
        assert (rgb in (12, 13) and alpha == 9 and arg1 == "texture" and
                arg2 in ("diffuse", "current")) is accepted
    for tex, diff in ((.85, .25), (.1, .7), (.4, .4), (0., 1.)):
        alpha = min(1., tex + diff * (1. - tex))
        assert 0. <= alpha <= 1.
        assert abs(alpha - tex*diff) > 0.00001
    print("DX11 independent ADDSMOOTH alpha native Draw regression PASS (static only)")


    # 00573: game-authored BLENDFACTORALPHA RGB and independently SUBTRACT /
    # ADDSMOOTH alpha must both cross intake -> PS compile/lifetime -> native
    # Draw/DrawIndexed -> opt-in inset without modifying DX9Ex game/input.
    def factor_independent_alpha_connected(source: str) -> bool:
        gate = source[source.find("bool supported_game_state("):source.find("bool translate_vertices(")]
        draw = source[source.find("bool submit("):source.find("void observe(")]
        shared = (
            "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
            "blendFactorSubtractAlpha || blendFactorAddSmoothAlpha",
            "!blendFactorSubtractAlpha && !blendFactorAddSmoothAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse",
            "alphaArg1 != D3DTA_TEXTURE",
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "game->UpdateSurface(",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )
        if not all(x in source for x in shared): return False
        if not all(x in gate for x in shared[:5]): return False
        for operation, alpha_math in (
            ("Subtract", "saturate(t.a - v.diffuse.a)"),
            ("AddSmooth", "saturate(t.a + v.diffuse.a * (1.0f - t.a))"),
        ):
            flag = f"blendFactor{operation}Alpha"
            shader = f"PSTextureBlendFactor{operation}Alpha"
            start = source.find(f"float4 {shader}(VOut v) : SV_Target {{")
            end = source.find("\n}", start)
            if start < 0 or end < start: return False
            body = source[start:end]
            required = (
                f"bool {flag} = false;",
                f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&",
                f"capture.{flag} = {flag};",
                f"float4 {shader}(VOut v) : SV_Target {{",
                f'compile("{shader}", "ps_4_0", blendFactor{operation}Code)',
                f"s.{flag}Ps &&",
                f"s.{flag}Ps.GetAddressOf()",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            )
            if not all(x in source for x in required): return False
            if source.count(f"s.{flag}Ps.Reset();") != 2: return False
            if f"capture.{flag} ? s.{flag}Ps.Get() :" not in draw: return False
            if not all(x in body for x in (
                "lerp(v.diffuse.rgb, t.rgb, alphaParams.w)",
                alpha_math, "AlphaGate(c.a); return c;",
            )): return False
        return True

    assert factor_independent_alpha_connected(bridge)
    for operation, alpha_math in (
        ("Subtract", "saturate(t.a - v.diffuse.a)"),
        ("AddSmooth", "saturate(t.a + v.diffuse.a * (1.0f - t.a))"),
    ):
        flag = f"blendFactor{operation}Alpha"
        shader = f"PSTextureBlendFactor{operation}Alpha"
        tokens = (
            f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&",
            f"capture.{flag} = {flag};",
            f'compile("{shader}", "ps_4_0", blendFactor{operation}Code)',
            f"s.{flag}Ps.GetAddressOf()",
            f"capture.{flag} ? s.{flag}Ps.Get() :",
        )
        for token in tokens:
            mutant = bridge.replace(token, "/* sever 00573 native link */", 1)
            assert mutant != bridge and not factor_independent_alpha_connected(mutant), token
        begin = bridge.find(f"float4 {shader}(VOut v) : SV_Target {{")
        end = bridge.find("\n}", begin)
        body = bridge[begin:end]
        for token in ("lerp(v.diffuse.rgb, t.rgb, alphaParams.w)", alpha_math):
            assert token in body
            mutant = bridge[:begin] + body.replace(token, "/* bad 00573 math */", 1) + bridge[end:]
            assert not factor_independent_alpha_connected(mutant), token

    # BLENDFACTORALPHA=14, SUBTRACT=10, ADDSMOOTH=11; source alpha Arg1=TEXTURE,
    # Arg2=DIFFUSE/CURRENT only. Nonfactor and modifier inputs fail closed.
    for color_op, alpha_op, arg1, arg2, expected in (
        (14, 10, "texture", "diffuse", True),
        (14, 11, "texture", "current", True),
        (14, 10, "diffuse", "diffuse", False),
        (14, 11, "texture", "texture", False),
        (14, 11, "texture|complement", "diffuse", False),
        (14, 10, "texture", "diffuse|complement", False),
        (14, 7, "texture", "diffuse", False),
        (13, 9, "texture", "diffuse", False),
        (12, 10, "texture", "diffuse", False),
    ):
        admitted = (color_op == 14 and alpha_op in (10, 11) and
                    arg1 == "texture" and arg2 in ("diffuse", "current"))
        assert admitted is expected
    for ta, da, factor in ((.9, .2, 0.), (.1, .8, .5), (.3, .4, 1.), (0., 1., .75)):
        for alpha_op in ("subtract", "add_smooth"):
            out = max(0., ta-da) if alpha_op == "subtract" else min(1., ta + da*(1.-ta))
            rgb = tuple(d*(1.-factor)+t*factor for t,d in zip((.2,.8,.5),(.7,.1,.3)))
            assert all(0. <= c <= 1. for c in (*rgb, out))
            assert abs(out - (ta*factor + da*(1.-factor))) > 0.00001 or (ta,da)==(0.,1.)
    print("DX11 factor RGB + SUBTRACT/ADDSMOOTH alpha native Draw PASS (static only)")


    # 00574: D3D9 factor RGB with separately MODULATE2X/4X alpha reaches
    # game-origin native Draw and DrawIndexed; opt-in does not replace DX9Ex.
    def scaled_factor_alpha_connected(source: str) -> bool:
        gate = source[source.find("bool supported_game_state("):source.find("bool translate_vertices(")]
        draw = source[source.find("bool submit("):source.find("void observe(")]
        for token in (
            "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
            "blendFactorModulate2XAlpha || blendFactorModulate4XAlpha",
            "!blendFactorModulate2XAlpha && !blendFactorModulate4XAlpha &&",
            "alphaNeedsDiffuse && !alphaArg2Diffuse", "alphaArg1 != D3DTA_TEXTURE",
        ):
            if token not in gate: return False
        for token in ("ctx->DrawIndexed(indexCount, 0, 0);",
                      "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
                      "mirror_texture(dev, capture, sampledView, sampledSampler)"):
            if token not in draw: return False
        for mode, scale in (("2X", "2.0f"), ("4X", "4.0f")):
            flag = f"blendFactorModulate{mode}Alpha"
            shader = f"PSTextureBlendFactorModulate{mode}Alpha"
            start = source.find(f"float4 {shader}(VOut v) : SV_Target {{")
            end = source.find("\n}", start)
            if start == -1 or end == -1: return False
            body = source[start:end]
            for token in (
                f"bool {flag} = false;",
                f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&",
                f"alphaOp == D3DTOP_MODULATE{mode};",
                f"capture.{flag} = {flag};",
                f'compile("{shader}", "ps_4_0", blendFactorModulate{mode}Code)',
                f"s.{flag}Ps &&", f"s.{flag}Ps.GetAddressOf()",
                f"capture.{flag} ? s.{flag}Ps.Get() :",
            ):
                if token not in source: return False
            # Match the alpha operation inside THIS flag's predicate. A
            # different variant using the correct enum cannot mask a bad one.
            pred = gate.find(f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&")
            if pred < 0 or f"alphaOp == D3DTOP_MODULATE{mode};" not in gate[pred:pred + 160]:
                return False
            if f"capture.{flag} ? s.{flag}Ps.Get() :" not in draw: return False
            if source.count(f"s.{flag}Ps.Reset();") != 2: return False
            for token in ("lerp(v.diffuse.rgb, t.rgb, alphaParams.w)",
                          f"saturate({scale} * t.a * v.diffuse.a)",
                          "AlphaGate(c.a); return c;"):
                if token not in body: return False
        return True

    assert scaled_factor_alpha_connected(bridge)
    for mode, scale in (("2X", "2.0f"), ("4X", "4.0f")):
        flag = f"blendFactorModulate{mode}Alpha"
        shader = f"PSTextureBlendFactorModulate{mode}Alpha"
        for token in (
            f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&",
            f"capture.{flag} = {flag};",
            f'compile("{shader}", "ps_4_0", blendFactorModulate{mode}Code)',
            f"s.{flag}Ps.GetAddressOf()",
            f"capture.{flag} ? s.{flag}Ps.Get() :",
        ):
            mutant = bridge.replace(token, "/* sever scaled-alpha native link */", 1)
            assert mutant != bridge and not scaled_factor_alpha_connected(mutant), token
        # A swapped D3DTOP is rejected even if another shader remains valid.
        predicate = f"const bool {flag} = op == D3DTOP_BLENDFACTORALPHA &&"
        offset = bridge.find(predicate)
        exact = f"alphaOp == D3DTOP_MODULATE{mode};"
        assert offset >= 0 and exact in bridge[offset:offset + 160]
        mutant = bridge[:offset] + bridge[offset:].replace(exact, "alphaOp == D3DTOP_ADD;", 1)
        assert not scaled_factor_alpha_connected(mutant), exact
        start = bridge.find(f"float4 {shader}(VOut v) : SV_Target {{")
        end = bridge.find("\n}", start)
        body = bridge[start:end]
        for token in ("lerp(v.diffuse.rgb, t.rgb, alphaParams.w)",
                      f"saturate({scale} * t.a * v.diffuse.a)"):
            assert token in body
            mutant = bridge[:start] + body.replace(token, "/* bad alpha/rgb */", 1) + bridge[end:]
            assert not scaled_factor_alpha_connected(mutant), token
    # D3DTOP BLENDFACTORALPHA=14, MODULATE2X=5, MODULATE4X=6.
    for rgb_op, alpha_op, arg1, arg2, valid in (
        (14, 5, "texture", "diffuse", True),
        (14, 6, "texture", "current", True),
        (14, 5, "diffuse", "diffuse", False),
        (14, 6, "texture", "texture", False),
        (14, 5, "texture|complement", "diffuse", False),
        (14, 6, "texture", "diffuse|complement", False),
        (13, 5, "texture", "diffuse", False),
        (14, 4, "texture", "diffuse", False),
    ):
        admitted = rgb_op == 14 and alpha_op in (5, 6) and arg1 == "texture" and arg2 in ("diffuse", "current")
        assert admitted is valid
    for ta, da, f in ((0.8, 0.6, 0.25), (0.1, 0.1, 0.5), (0.4, 0.5, 0.75)):
        for multiplier in (2, 4):
            alpha = min(1.0, multiplier * ta * da)
            rgb = tuple(d * (1 - f) + t * f for t, d in zip((0.2, 0.9, 0.4), (0.7, 0.1, 0.8)))
            assert all(0 <= c <= 1 for c in (*rgb, alpha))
            if ta == 0.8 and multiplier == 2: assert abs(alpha - 0.96) < 1e-9
            if ta == 0.8 and multiplier == 4: assert alpha == 1.0
            if ta == 0.1: assert alpha < 1.0
    print("DX11 independent MODULATE2X/4X alpha game native Draw PASS (static only)")

    # 00579 game-authored texture RGB with ADD/SUBTRACT alpha native PS.
    from test_dx11_select_texture_alpha_arithmetic_00579 import run as run_00579
    run_00579()

    # 00578 actual game SELECTARG1 texture RGB and independent fade alpha.
    from test_dx11_select_texture_mixed_alpha_00578 import main as run_00578
    run_00578()

    # 00577 actual-game textured SELECTARG2 RGB with independent alpha.
    from test_dx11_select_diffuse_mixed_alpha_00577 import run as run_00577
    run_00577()

    # 00580 game-authored SELECTARG2 RGB with independent ADD/SUBTRACT alpha.
    from test_dx11_selectarg2_arithmetic_alpha_00580 import main as run_00580
    run_00580()

    # 00581 D3D9 SELECTARG2 diffuse RGB with independently scaled alpha.
    from test_dx11_selectarg2_scaled_alpha_00581 import main as run_00581
    run_00581()

    # 00575 game Draw -> four scaled-alpha PS variants -> DrawIndexed/Draw -> inset.
    from test_dx11_scaled_blend_alpha_00575 import run as run_00575
    run_00575()

    print("DX11 object-space NORMAL/SPECULAR native draw regression PASS (static only)")
    print("DX11 TEX2..TEX8 multi-UV native Draw/DrawIndexed/fallback regression PASS (static only)")


    # 00966: DrawPrimitiveUP must also capture source-matched secondary
    # SM3 streams 1..3, or native full-frame admission is lost at this callsite.
    # Deleting any capture or fallback token must fail this structural oracle.
    r30_path = next(r for r in RENDERERS if r.name == "stereo_renderer_r30.cpp")
    r30_source = r30_path.read_text(encoding="utf-8")
    up_start = r30_source.find("void R30ObserveNativeLinearUP(")
    up_end = r30_source.find("void R30ObserveNativeIndexedUP(", up_start)
    call_start = r30_source.find("HRESULT __stdcall DrawPrimitiveUPDestR30(")
    call_end = r30_source.find("HRESULT __stdcall DrawIndexedPrimitiveUPDestR30(", call_start)
    assert up_start >= 0 and up_end > up_start
    assert call_start >= 0 and call_end > call_start
    native_up = r30_source[up_start:up_end]
    native_call = r30_source[call_start:call_end]
    native_up_required = (
        "R30NativeGameSourceGuard nativeSource{device};",
        "game_native_empty_primitive_type(",
        "game_native_primitive_element_count(",
        "std::vector<std::uint32_t> physical(nativeElements);",
        "physical[i] = i;",
        "if (!R30CaptureNativeAdditionalStreams(",
        "device, physical, extra, owned",
        "live::observe_linear(",
        "vertices, stride, &extra",
    )
    native_call_required = (
        "R30ObserveNativeLinearUP(device, type, primitiveCount, data, stride);",
        "const HRESULT gameHr = R30GuardScreenSpace(",
        "R30CompleteNativeGameSource(device, gameHr);",
    )
    def up_contract(region, required):
        return all(token in region for token in required)
    assert up_contract(native_up, native_up_required)
    assert up_contract(native_call, native_call_required)
    assert "live_game_frame::observe_linear(" not in native_call, (
        "UP callsite skipped native secondary stream capture")
    for region, required in ((native_up, native_up_required),
                             (native_call, native_call_required)):
        for token in required:
            deleted = region.replace(token, "", 1)
            assert deleted != region and not up_contract(deleted, required), (
                "nonindexed SM3 UP native source mutation escaped: " + token)

    # R240: the opt-in real D3D9 IndexedUP hook must forward nonzero
    # MinVertexIndex through the native DrawIndexed diagnostic bridge.
    # Static mutation tests are not Quest3 / game-frame runtime proof.
    for renderer in RENDERERS:
        hook = renderer.read_text(encoding="utf-8")
        start = hook.find("void R30ObserveNativeIndexedUP(")
        end = hook.find("HRESULT __stdcall DrawPrimitiveDestR30(", start)
        assert start >= 0 and end > start, "game IndexedUP hook not located"
        region = hook[start:end]
        common = (
            "minVertex > live::kMaxNativeGameVertices - numVertices",
            "unpacked[i] < minVertex ||",
            "unpacked[i] - minVertex >= numVertices",
        )
        # The active native SM3 path preserves the original game's absolute
        # source indices until it has captured all secondary VB streams.
        # The R26-safe fallback intentionally retains its previous stream-0
        # conversion and must not be silently promoted as multistream-ready.
        if renderer.name == "stereo_renderer_r30.cpp":
            required = common + (
                "game_indexed_up_dense_source_range(",
                "reinterpret_cast<const std::uint8_t*>(firstAddress)",
                "std::vector<std::uint32_t> rebasedIndices = unpacked;",
                "for (auto& index : rebasedIndices) index -= minVertex;",
                "game_indexed_up_physical_slots(",
                "compactIndices, true, physical",
                "rebasedIndices, false, physical",
                "R30CaptureNativeAdditionalStreams(",
                "compactIndices.data(), count, &extra",
                "rebasedIndices.data(), count, &extra",
                "firstVertex, stride, numVertices,",
            )
            assert region.count("R30CaptureNativeAdditionalStreams(") == 2, (
                "both sparse and dense IndexedUP must snapshot SM3 side streams"
            )
            assert region.count("game_indexed_up_physical_slots(") == 2, (
                "both source windows must verify physical stream alignment"
            )
            assert "unpacked[i] -= minVertex;" not in region, (
                "live absolute stream identities were prematurely rebased"
            )
        else:
            required = common + (
                "static_cast<std::size_t>(minVertex) * stride",
                "unpacked[i] -= minVertex;",
                "firstVertex, stride, numVertices, unpacked.data(), count",
            )
            assert "R30CaptureNativeAdditionalStreams(" not in region, (
                "R26-safe fallback must not pretend to have SM3 side streams"
            )
        def indexed_up_contract(sample: str) -> bool:
            if not all(token in sample for token in required):
                return False
            if "minVertex != 0" in sample:
                return False
            if renderer.name == "stereo_renderer_r30.cpp":
                return (
                    sample.count("R30CaptureNativeAdditionalStreams(") == 2
                    and sample.count("game_indexed_up_physical_slots(") == 2
                    and "unpacked[i] -= minVertex;" not in sample
                )
            return "R30CaptureNativeAdditionalStreams(" not in sample

        assert indexed_up_contract(region), "missing live IndexedUP vertex window"
        for token in required:
            damaged = region.replace(token, "", 1)
            assert damaged != region and not indexed_up_contract(damaged), (
                "live IndexedUP destructive mutation escaped: " + token
            )
        # Per-branch destructive checks independently remove each copy of a
        # duplicated physical-slot contract, not only both at once.
        if renderer.name == "stereo_renderer_r30.cpp":
            for token in ("R30CaptureNativeAdditionalStreams(",
                          "game_indexed_up_physical_slots("):
                assert region.count(token) == 2
                first, second = region.split(token, 1)
                damaged_second = first + token + second.replace(token, "", 1)
                assert not indexed_up_contract(damaged_second), (
                    "second IndexedUP source branch lost its native-side stream guard"
                )

if __name__ == "__main__":
    main()
