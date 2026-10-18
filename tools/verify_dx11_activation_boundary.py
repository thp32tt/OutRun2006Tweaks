#!/usr/bin/env python3
"""Fail closed if dormant native DX11 readiness work begins routing game draws."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"
ACTIVATION_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inl", ".ipp"}

DRAW_DISPATCH = re.compile(
    r"(?:->|\.)\s*Draw(?:Auto|IndexedInstancedIndirect|InstancedIndirect|IndexedInstanced|Indexed|Instanced)?\s*\("
)


def require_text(path: Path, needles: list[str], label: str) -> str:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{label}: missing dormant-boundary evidence: {missing}")
    return text


def iter_activation_sources() -> list[Path]:
    """Return every C/C++ activation surface under the native DX11 tree."""
    return [
        path
        for path in sorted(DX11.rglob("*"))
        if path.is_file() and path.suffix.lower() in ACTIVATION_SOURCE_SUFFIXES
    ]




def audit_native_partial_color_clear(source: str) -> list[str]:
    """Authorize only a cropped, game-authored D3D11.0 GPU TARGET fill.

    Unlike geometry, this bounded shader triangle never contributes to eye
    drawCount/colorDrawCount. Require independent encoder, two-eye preflight,
    precise color viewport and complete caller pipeline restore.
    """
    helper = source.partition(
        "// A D3D11.0 immediate context has no rectangle-aware ClearView."
    )[2].partition("\n// D3D11 ClearDepthStencilView ignores rectangles.")[0]
    required = [
        "[[nodiscard]] bool raster_partial_eye_color_clear(",
        "rect.left < 0 || rect.top < 0 || rect.right <= rect.left ||",
        "static_cast<std::uint32_t>(rect.right) > width ||",
        "static_cast<std::uint32_t>(rect.bottom) > height)",
        "if (!device) return false;",
        "static std::mutex mutex;",
        "if (cachedDevice.Get() != device.Get()) {",
        "ds.DepthEnable = FALSE;",
        "ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;",
        "ds.StencilEnable = FALSE;",
        "ScopedNativeGameEyeOutput restore(context, width, height);",
        "if (!restore.valid()) return false;",
        "context->OMSetRenderTargets(1u, &target, nullptr);",
        "context->OMSetDepthStencilState(noDepth.Get(), 0u);",
        "context->OMSetBlendState(nullptr, nullptr, 0xffffffffu);",
        "context->RSSetState(nullptr); // game Clear ignores saved scissor/cull",
        "static_cast<float>(rect.right - rect.left)",
        "static_cast<float>(rect.bottom - rect.top)",
        "context->RSSetViewports(1u, &viewport);",
        "context->PSSetConstantBuffers(0u, 1u, &cb);",
        "context->Draw(3u, 0u); // authored Clear, never native game Draw evidence",
    ]
    missing = ["color-raster:" + needle for needle in required
               if needle not in helper]
    if (not helper or DRAW_DISPATCH.findall(helper) != ["->Draw("] or
            "drawCount_++" in helper or "colorDrawCount_++" in helper):
        missing.append("color-raster: one scoped non-evidence GPU fill required")
    encoder = source.partition(
        "bool NativeGameEyeDrawEncoder::clear_target_argb("
    )[2].partition("\nbool NativeGameEyeDrawEncoder::clear_depth_stencil(")[0]
    encoder_required = [
        "if (!eye_targets_bound() || !targetWidth_ || !targetHeight_) return false;",
        "live_game_stereo::color_clear_route(",
        "case live_game_stereo::NativeColorClearRoute::FullRtv:",
        "context_->ClearRenderTargetView(eyeTarget_, rgba);",
        "case live_game_stereo::NativeColorClearRoute::ClearView:",
        "rectContext->ClearView(eyeTarget_, rgba, region, 1u);",
        "case live_game_stereo::NativeColorClearRoute::ShaderRaster:",
        "return raster_partial_eye_color_clear(",
        "default:",
        "return false;",
        "cropped && !rectContext &&",
        "native_game_partial_color_shader_rtv(context_, eyeTarget_);",
    ]
    missing += ["color-encoder:" + n for n in encoder_required if n not in encoder]
    # Never trust a partial GPU clear if only the XR eye or only the game
    # offscreen camera is protected. Check the actual typed RTV view contract,
    # including the negative path for integer/typeless and unsupported GPUs.
    camera = source.partition(
        "bool NativeGameEyeDrawEncoder::clear_offscreen_game_color("
    )[2].partition(
        "\nbool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil("
    )[0]
    typed_rtv = source.partition(
        "[[nodiscard]] bool native_game_partial_color_shader_rtv("
    )[2].partition("\n}\n")[0]
    camera_required = [
        "cropped && !rectContext &&",
        "native_game_partial_color_shader_rtv(context_, gameTarget);",
        "case live_game_stereo::NativeColorClearRoute::ShaderRaster:",
        "return raster_partial_eye_color_clear(",
    ]
    missing += ["color-camera:" + n for n in camera_required if n not in camera]
    typed_required = [
        "target->GetDesc(&view);",
        "switch (view.Format)",
        "DXGI_FORMAT_R8G8B8A8_UNORM:",
        "DXGI_FORMAT_R10G10B10A2_UNORM:",
        "DXGI_FORMAT_R16G16B16A16_FLOAT:",
        "DXGI_FORMAT_R11G11B10_FLOAT:",
        "default:",
        "return false;",
        "CheckFormatSupport(view.Format, &support)",
        "(support & D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u;",
    ]
    missing += ["color-typed-rtv:" + n for n in typed_required
                if n not in typed_rtv]
    preflight = source.partition(
        "bool NativeGameStereoSubmission::render_game_eye_passes("
    )[2].partition("\n    // Allocate separate, full-size native depth")[0]
    preflight_required = [
        "if (needsClearView &&",
        "FAILED(context_->QueryInterface(",
        "for (std::uint32_t eye = 0u; eye < 2u; ++eye) {",
        "native_game_partial_color_shader_rtv(",
        "context_.Get(), ring_.rtv(slot_, eye))",
        'LoadLibraryW(L"d3dcompiler_47.dll")',
        'GetProcAddress(compiler, "D3DCompile")',
        "if (!ready) return false;",
        "rect.right > static_cast<LONG>(ring_.width()) ||",
        "rect.bottom > static_cast<LONG>(ring_.height())",
    ]
    missing += ["color-preflight:" + n for n in preflight_required
                if n not in preflight]
    regression = (ROOT / "tools/dx11_game_stereo_draw_evidence_probe_00873.cpp"
                  ).read_text(encoding="utf-8")
    regression_required = [
        "NativeColorClearRoute::ShaderRaster",
        "NativeColorClearRoute::ClearView",
        "NativeColorClearRoute::FullRtv",
        "NativeColorClearRoute::Reject",
        "color_clear_route(true, -1, 0, 50, 50",
        "color_clear_route(true, 0, 0, 1921, 1080",
    ]
    missing += ["color-regression:" + n for n in regression_required
                if n not in regression]
    return missing


def audit_native_partial_depth_clear(source: str, transport_probe: str) -> list[str]:
    """Allow one scoped DSV-only GPU fill; never authorize a game color Draw.

    Keep this audit independent of the global Draw count: an extra arbitrary
    dispatch remains forbidden even if the depth helper is otherwise valid.
    """
    marker = "// D3D11 ClearDepthStencilView ignores rectangles."
    depth_pass = source.partition(marker)[2].partition("\n} // namespace")[0]
    required = [
        "[[nodiscard]] bool raster_partial_eye_depth_clear(",
        "(!clearDepth && !clearStencil)",
        "rect.right <= rect.left || rect.bottom <= rect.top ||",
        "static_cast<std::uint32_t>(rect.right) > width ||",
        "static_cast<std::uint32_t>(rect.bottom) > height ||",
        "std::isfinite(depth)",
        "static std::mutex mutex;",
        "if (cachedDevice.Get() != device.Get()) {",
        "desc.DepthWriteMask = clearDepth",
        "desc.StencilEnable = clearStencil ? TRUE : FALSE;",
        "desc.FrontFace.StencilPassOp = D3D11_STENCIL_OP_REPLACE;",
        "ScopedNativeGameEyeOutput saved(context, width, height);",
        "if (!saved.valid()) return false;",
        "context->OMSetRenderTargets(0u, nullptr, depthView);",
        "context->OMSetDepthStencilState(states[mode].Get(), stencil);",
        "context->RSSetState(nullptr); // disable inherited game scissor",
        "context->RSSetViewports(1u, &viewport);",
        "context->PSSetShader(pixel.Get(), nullptr, 0u);",
        "context->Draw(3u, 0u);",
    ]
    # The GPU depth shader must bind no RTV, and cannot increment the
    # encoder's game Draw evidence or bypass a missing/null DSV.
    missing = ["depth:" + needle for needle in required if needle not in depth_pass]
    if (not depth_pass or DRAW_DISPATCH.findall(depth_pass) != ["->Draw("] or
            "drawCount_++" in depth_pass or "colorDrawCount_++" in depth_pass):
        missing.append("depth: one DSV-only non-evidence GPU draw required")
    source_requirements = [
        "if (!eye_targets_bound() || (!clearDepth && !clearStencil) ||",
        "return raster_partial_eye_depth_clear(",
        "partial ? &clear.rect : nullptr))",
        # Real game full-eye Z/stencil RECTs now bypass the expensive
        # depth-only raster Draw; cropped regions retain that audited Draw.
        # Route admission is shared by two-eye preflight and GPU execution.
        "const bool hasRect = rect.left || rect.top ||",
        "const auto route = live_game_stereo::depth_clear_route(",
        "route == live_game_stereo::NativeDepthClearRoute::Reject",
        "route == live_game_stereo::NativeDepthClearRoute::PartialRaster",
        "context_->ClearDepthStencilView(eyeDepth_, flags,",
        "rect.right > static_cast<LONG>(ring_.width()) ||",
        "rect.bottom > static_cast<LONG>(ring_.height())",
    ]
    missing += ["timeline:" + needle for needle in source_requirements
                if needle not in source]
    # Never accept an encoder mutation just because the two-eye preflight
    # still contains the same token (or vice versa). Both independent entry
    # points must reject invalid game regions before they touch the DSV.
    encoder_depth = source.partition(
        "bool NativeGameEyeDrawEncoder::clear_depth_stencil("
    )[2].partition("\n// Copy a genuine GPU-resident")[0]
    preflight_depth = source.partition(
        "bool NativeGameStereoSubmission::render_game_eye_passes("
    )[2].partition("\n    // Allocate separate, full-size native depth")[0]
    encoder_guards = [
        "const auto route = live_game_stereo::depth_clear_route(",
        "route == live_game_stereo::NativeDepthClearRoute::Reject",
        "route == live_game_stereo::NativeDepthClearRoute::PartialRaster",
        "return raster_partial_eye_depth_clear(",
        "context_->ClearDepthStencilView(eyeDepth_, flags,",
    ]
    preflight_guards = [
        "const bool hasRect = rect.left || rect.top ||",
        "const auto route = live_game_stereo::depth_clear_route(",
        "route == live_game_stereo::NativeDepthClearRoute::Reject",
    ]
    missing += ["depth-encoder:" + needle for needle in encoder_guards
                if needle not in encoder_depth]
    missing += ["depth-preflight:" + needle for needle in preflight_guards
                if needle not in preflight_depth]
    test_requirements = [
        # Retain the old clipped GPU Copy and eighth scaled postpass, then
        # require a longer mixed Copy/Stretch/Clear scene in both eyes.
        # Real WARP pixels and invalid late-event preflight stay mandatory.
        "partialGameClear.count[0] = partialGameClear.count[1] = 12u;",
        "followCopy.kind = SourceClear::Kind::SourceCopy;",
        "followScale.kind = SourceClear::Kind::SourceStretch;",
        "followClear.kind = SourceClear::Kind::TargetRect;",
        "followArray.sourceArraySlice = eye;",
        "invalidLateOrder.entries[1][11].afterDrawOrdinal = 2u;",
        "invalidEventCapacity.count[1] =",
        "require(expectedCamera(lateCopy) &&",
        "gpuScale.kind = SourceClear::Kind::SourceStretch;",
        "gpuScale.source = gameCopyOnlyArray;",
        "gpuScale.sourceArraySlice = eye;",
        "invalidCopyOnlyStretch.entries[1][7].sourceArraySlice = 2u;",
        "require(realGpuScale,",
        "edgeCopy.kind = SourceClear::Kind::SourceCopy;",
        "edgeCopy.destX = 62u;",
        "edgeCopy.sourceArraySlice = eye;",
        "fixture.replayedClippedSurfaceCopy[eyeIndex] =",
        "fixture.replayedClippedConvertedCopy[eyeIndex] =",
        "fixture.replayedClippedMsaaResolve[eyeIndex] =",
        "!encoder.copy_game_surface(",
        "require(expectedSourceEdge && expectedConvertedEdge &&",
        "zRect.kind = SourceClear::Kind::FullDepthStencil;",
        "fixture.replayedPartialDepthStencil[eyeIndex] =",
        "!encoder.clear_depth_stencil(0.5f, 0u, true, true, &badRect)",
        "encoder.clear_depth_stencil(0.41f, 0u, true, false, &zOnly)",
        "false, true, &zOnly)",
        "gameEyeFixture.replayedPartialDepthStencil[0] &&",
        "gameEyeFixture.replayedPartialDepthStencil[1] &&",
    ]
    missing += ["regression:" + needle for needle in test_requirements
                if needle not in transport_probe]
    return missing



def audit_native_offscreen_game_draw(source: str, transport_probe: str) -> list[str]:
    """Admit four exact source-owned camera draw forms, not eye evidence.

    These are real D3D11 Draws and must remain under the same frame/pose
    submission owner. They only advance chronological source draw ordinals:
    a separately verified game Copy/Stretch supplies XR eye color.
    """
    def section(start: str, end: str) -> str:
        return source.partition(start)[2].partition(end)[0]

    target = section(
        "bool NativeGameEyeDrawEncoder::game_source_target_bound(",
        "\nbool NativeGameEyeDrawEncoder::prepare_offscreen_game_draw(")
    preflight = section(
        "bool NativeGameEyeDrawEncoder::prepare_offscreen_game_draw(",
        "\nbool NativeGameEyeDrawEncoder::draw_offscreen(")
    plain = section(
        "bool NativeGameEyeDrawEncoder::draw_offscreen(",
        "\nbool NativeGameEyeDrawEncoder::draw_offscreen_indexed(")
    indexed = section(
        "bool NativeGameEyeDrawEncoder::draw_offscreen_indexed(",
        "\nbool NativeGameEyeDrawEncoder::draw_offscreen_instanced(")
    instanced = section(
        "bool NativeGameEyeDrawEncoder::draw_offscreen_instanced(",
        "\nbool NativeGameEyeDrawEncoder::draw_offscreen_indexed_instanced(")
    indexed_instanced = section(
        "bool NativeGameEyeDrawEncoder::draw_offscreen_indexed_instanced(",
        "\nvoid NativeGameEyeDrawEncoder::set_source_clear_timeline(")

    source_guards = [
        "if (!context_ || !eyeTarget_ || !gameTarget || gameTarget == eyeTarget_)",
        "context_->OMGetRenderTargets(1u, &actual, nullptr);",
        "const bool bound = actual == gameTarget;",
        "if (!bound) return false;",
        "gameTarget->GetResource(sourceResource.GetAddressOf());",
        "eyeTarget_->GetResource(eyeResource.GetAddressOf());",
        "sourceResource.Get() == eyeResource.Get()",
        "if (FAILED(sourceResource.As(&source)) || !source) return false;",
        "context_->GetDevice(producer.GetAddressOf());",
        "source->GetDevice(sourceOwner.GetAddressOf());",
        "if (!producer || producer.Get() != sourceOwner.Get()) return false;",
        "D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX",
        "D3D11_RESOURCE_MISC_SHARED_NTHANDLE",
        "desc.Usage != D3D11_USAGE_DEFAULT",
        "desc.CPUAccessFlags || (desc.MiscFlags & sharedFlags)",
        "(desc.BindFlags & D3D11_BIND_RENDER_TARGET) == 0u",
        "context_->RSGetViewports(&count, &view);",
        "std::isfinite(view.TopLeftX) && std::isfinite(view.TopLeftY)",
        "view.Width > 0.f && view.Height > 0.f",
        "view.TopLeftX < static_cast<float>(desc.Width)",
        "view.TopLeftY < static_cast<float>(desc.Height)",
        "view.TopLeftX + view.Width > 0.f",
        "view.TopLeftY + view.Height > 0.f;",
    ]
    preflight_guards = [
        "if (!game_source_target_bound(gameTarget) ||",
        "!geometry_outputs_isolated(gameTarget) ||",
        "drawCount_ == (std::numeric_limits<std::uint64_t>::max)())",
        "if (sourceClears_ &&",
        ".afterDrawOrdinal <= drawCount_)",
        "ScopedNativePostpassOutputs restore(context_);",
        "context_->OMSetRenderTargets(1u, &eye, eyeDepth_);",
        "if (!replay_due_source_clears()) return false;",
        "return game_source_target_bound(gameTarget) &&",
        "geometry_outputs_isolated(gameTarget);",
    ]
    plain_guards = [
        "if (!vertexCount || !prepare_offscreen_game_draw(gameTarget))",
        "context_->Draw(vertexCount, startVertex);",
        "++drawCount_;",
    ]
    indexed_guards = [
        "if (!indexCount || !prepare_offscreen_game_draw(gameTarget))",
        "context_->DrawIndexed(indexCount, startIndex, baseVertex);",
        "++drawCount_;",
    ]
    instanced_guards = [
        "if (!live_game_stereo::may_issue_instanced(",
        "verticesPerInstance, instanceCount, drawCount_) ||",
        "!prepare_offscreen_game_draw(gameTarget))",
        "context_->DrawInstanced(",
        "verticesPerInstance, instanceCount, startVertex, startInstance);",
        "++drawCount_;",
    ]
    indexed_instanced_guards = [
        "if (!live_game_stereo::may_issue_instanced(",
        "indicesPerInstance, instanceCount, drawCount_) ||",
        "!prepare_offscreen_game_draw(gameTarget))",
        "context_->DrawIndexedInstanced(",
        "indicesPerInstance, instanceCount, startIndex,",
        "baseVertex, startInstance);",
        "++drawCount_;",
    ]
    proof = [
        "encoder.draw_offscreen(gameOffscreen, 3u, 0u)",
        "encoder.draw_offscreen_indexed(gameOffscreen, 3u, 0u, 0)",
        "!encoder.draw_offscreen(eyeTarget, 3u, 0u)",
        "!encoder.draw_offscreen(nullptr, 3u, 0u)",
        "!encoder.draw(3u, 0u)",
        "encoder.draw_count() == beforeOffscreen + 1u",
        "encoder.color_draw_count() == beforeOffscreenEyeColor",
        "encoder.copy_game_surface(",
        "fixture.offscreenGameColor, &offscreenPatch,",
        "gameEyeFixture.replayedOffscreenGameDraw[0] &&",
        "gameEyeFixture.replayedOffscreenGameDraw[1] &&",
        "instancedCamera.draw_offscreen_instanced(",
        "instancedCamera.draw_offscreen_indexed_instanced(",
        "instancedCamera.draw_count() == 2u",
        "instancedCamera.color_draw_count() == 0u",
        "gameEyeFixture.replayedInstancedOffscreenCamera[0] &&",
        "gameEyeFixture.replayedInstancedOffscreenCamera[1] &&",
    ]
    missing = [
        "offscreen-target:" + token for token in source_guards if token not in target
    ]
    missing += [
        "offscreen-timeline:" + token for token in preflight_guards
        if token not in preflight
    ]
    missing += [
        "offscreen-draw:" + token for token in plain_guards if token not in plain
    ]
    missing += [
        "offscreen-indexed:" + token for token in indexed_guards
        if token not in indexed
    ]
    missing += [
        "offscreen-instanced:" + token for token in instanced_guards
        if token not in instanced
    ]
    missing += [
        "offscreen-indexed-instanced:" + token for token in indexed_instanced_guards
        if token not in indexed_instanced
    ]
    missing += [
        "offscreen-probe:" + token for token in proof if token not in transport_probe
    ]
    for label, block, calls in (
        ("target", target, []),
        ("timeline", preflight, []),
        ("draw", plain, ["->Draw("]),
        ("indexed", indexed, ["->DrawIndexed("]),
        ("instanced", instanced, ["->DrawInstanced("]),
        ("indexed-instanced", indexed_instanced, ["->DrawIndexedInstanced("]),
    ):
        if not block or DRAW_DISPATCH.findall(block) != calls:
            missing.append("offscreen-" + label + ": unexpected GPU Draw dispatch")
        if "colorDrawCount_" in block or "authoredColorPostpassCount_" in block:
            missing.append("offscreen-" + label + ": fabricated eye-color evidence")
    return missing


def main() -> None:
    # Keep every ID3D11DeviceContext Draw* entry point inside the dormant
    # activation boundary. DrawAuto is easy to omit because it has no explicit
    # vertex-count arguments, so fail closed if the matcher ever regresses.
    draw_dispatch_samples = [
        "context->Draw(1, 0)",
        "context->DrawAuto()",
        "context->DrawIndexed(1, 0, 0)",
        "context->DrawInstanced(1, 1, 0, 0)",
        "context->DrawIndexedInstanced(1, 1, 0, 0, 0)",
        "context->DrawInstancedIndirect(args, 0)",
        "context->DrawIndexedInstancedIndirect(args, 0)",
    ]
    unmatched = [
        sample for sample in draw_dispatch_samples
        if not DRAW_DISPATCH.search(sample)
    ]
    if unmatched:
        raise SystemExit(
            "DX11 draw activation matcher drift: " + ", ".join(unmatched)
        )

    if not DX11.is_dir():
        raise SystemExit("native DX11 source directory is missing")

    # R71-R118 may allocate/translate/compile/bind probe resources, but the
    # native backend is still evidence-only. A real D3D11 Draw* dispatch is an
    # explicit activation event and must not arrive accidentally under a
    # readiness/census task.
    activation_sources = iter_activation_sources()
    if not activation_sources:
        raise SystemExit("native DX11 activation source set is empty")

    required_scan_members = [
        DX11 / "native_backend.cpp",
        DX11 / "native_backend.hpp",
        DX11 / "runtime_census.cpp",
        DX11 / "runtime_census.hpp",
    ]
    missing_scan_members = [
        str(path.relative_to(ROOT))
        for path in required_scan_members
        if path not in activation_sources
    ]
    if missing_scan_members:
        raise SystemExit(
            "DX11 activation source coverage drift: " + ", ".join(missing_scan_members)
        )

    violations: list[str] = []
    approved_diagnostic = DX11 / "live_game_frame_bridge.cpp"
    audited_eye_recorder = DX11 / "native_game_stereo_submission.cpp"
    for path in activation_sources:
        text = path.read_text(encoding="utf-8")
        matches = list(DRAW_DISPATCH.finditer(text))
        if path == audited_eye_recorder and matches:
            # This is a narrowly reviewed rendering surface, NOT a blanket
            # activation exemption. The two game Draw emitters and exactly two
            # audited non-evidence GPU postpasses (DSV and Stretch) are allowed.
            # Their callback must be scoped
            # by exact frame/pose ring ownership, independent L/R RTV+DSV and
            # a count matched to issued commands before publication. The
            # normal D3D9 Draw/Present/input/FFB path stays authoritative.
            required_eye_contract = [
                "bool NativeGameEyeDrawEncoder::draw(",
                "bool NativeGameEyeDrawEncoder::draw_indexed(",
                # Game-authored ordinary and hardware-instanced D3D11
                # geometry uses the same exact owned eye and source timeline.
                # Never authorize instancing on a general host/census path.
                "bool NativeGameEyeDrawEncoder::draw_instanced(",
                "bool NativeGameEyeDrawEncoder::draw_indexed_instanced(",
                "if (!live_game_stereo::may_issue_instanced(",
                "!eye_output_bound() || !replay_due_source_clears())",
                "context_->DrawInstanced(",
                "context_->DrawIndexedInstanced(",
                # Color evidence is invalid for a Draw discarded by an
                # asynchronous D3D11 occlusion predicate; retain depth/order
                # history while enforcing at least one real color-eligible draw.
                "bool NativeGameEyeDrawEncoder::unpredicated_color_evidence() const noexcept",
                "context_->GetPredication(&predicate, &comparison);",
                "const bool clear = predicate == nullptr;",
                "live_game_stereo::color_certifiable(",
                "eye_color_writable(), unpredicated_color_evidence());",
                # Count only Draws submitted into the exact
                # per-eye output (not an unbound or desktop OM target).
                "if (!vertexCount || !eye_output_bound() ||",
                "if (!indexCount || !eye_output_bound() ||",
                "bool NativeGameEyeDrawEncoder::eye_output_bound() const noexcept",
                # A real draw must never write a foreign MRT or inherited PS UAV.
                # Enforce both source-eye and auxiliary camera GPU output scopes.
                "bool NativeGameEyeDrawEncoder::geometry_outputs_isolated(",
                "context_->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,",
                "for (UINT i = 1u; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)",
                "context_->OMGetRenderTargetsAndUnorderedAccessViews(",
                "!geometry_outputs_isolated(eyeTarget_)) return false;",
                "context_->OMGetRenderTargets(1u, &actualTarget, &actualDepth);",
                "actualTarget == eyeTarget_ && actualDepth == eyeDepth_",
                "bool NativeGameEyeDrawEncoder::bind_eye_output() noexcept",
                "context_->OMSetRenderTargets(1u, &target, eyeDepth_);",
                "context_->Draw(vertexCount, startVertex);",
                "context_->DrawIndexed(indexCount, startIndex, baseVertex);",
                "ScopedNativeGameEyeOutput output(ctx, invocation.width, invocation.height);",
                "~ScopedNativeGameEyeOutput() noexcept {",
                "context_->OMSetRenderTargets(",
                "NativeGameEyeDrawEncoder encoder(",
                "ctx, targets[eyeIndex], invocation.depth[eyeIndex],",
                "invocation.width, invocation.height);",
                # A bound eye RTV cannot prove a visible pixel if its
                # viewport or enabled scissor is entirely off-target.
                "context_->RSGetViewports(&viewportCount, &view);",
                "viewportCount != 1u || !std::isfinite(view.TopLeftX)",
                "context_->RSGetState(&rasterizer);",
                "scissorEnabled = desc.ScissorEnable != FALSE;",
                "context_->RSGetScissorRects(&count, &rect);",
                "evidence.drawCount != encoder.draw_count() ||",
                "sourcePoseSequence != poseSequence_",
                "ring_.render_eye_pair(context_.Get(), slot_, frameId_,",
                "context_->OMSetRenderTargets(1u, &target, depth);",
            ]
            # Separate audited GPU partial-color raster, partial-depth raster
            # and StretchRect postpasses each perform one non-evidence Draw.
            # The native GPU StretchRect postpass performs exactly one
            # fullscreen-triangle Draw, but it is NOT a game-authored geometry
            # Draw and must never advance source geometry evidence counters.
            # Keep it in this audited file, after the proven scoped eye
            # output guard, with explicit source/device/eye bounds, GPU
            # color and full pipeline restore checks.
            postpass = text.partition(
                "bool NativeGameEyeDrawEncoder::stretch_game_surface("
            )[2].partition("\nvoid NativeGameStereoSubmission::release_local")[0]
            required_postpass = [
                "if (!source || !context_ || !eye_targets_bound()) return false;",
                "eye.Get() == source) return false;",
                "if (!device || device.Get() != owner.Get()) return false;",
                # Legacy code rejected every partially-offscreen destination.
                # The real game now clips the viewport AND adjusts source UVs;
                # rejecting the old guard is not permission to bypass bounds.
                "srcBox.right > mipWidth || srcBox.bottom > mipHeight) return false;",
                # Encoder source mip bounds now come from the SAME audited
                # utility used by preflight for BOTH camera eyes. Removing
                # these calls is never an activation relaxation.
                "const auto sourceMip = native_game_postpass_mip_extent(",
                "sd.Width, sd.Height, sd.MipLevels, sourceMipSlice,",
                "sd.ArraySize, sourceArraySlice, sd.SampleDesc.Count);",
                "if (!sourceMip.valid) return false;",
                "const UINT mipWidth = sourceMip.width;",
                "const UINT mipHeight = sourceMip.height;",
                "const auto clipped = native_game_stretch_clipped_region(",
                "dest.left, dest.top, dest.right, dest.bottom);",
                "if (!clipped.valid) return false;",
                "float(clipped.left), float(clipped.top),",
                "float(clipped.right - clipped.left),",
                "float(clipped.bottom - clipped.top), 0.f, 1.f",
                "clipped.uv.constants.data()",
                "FAILED(device->CheckFormatSupport(sd.Format, &sourceSupport)) ||",
                "FAILED(device->CheckFormatSupport(ed.Format, &eyeSupport)))",
                "(sourceSupport & D3D11_FORMAT_SUPPORT_SHADER_SAMPLE) != 0u,",
                "(eyeSupport & D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u,",
                "(sourceSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u,",
                # UAV-only compute camera sources are copied to a private
                # GPU SRV, not bound directly while their CS writer is live.
                # The old no-bind CopyResource camera path must also remain.
                "(sd.BindFlags == 0u ||",
                "(sd.BindFlags & D3D11_BIND_UNORDERED_ACCESS) != 0u) &&",
                "sd.SampleDesc.Count == 1u);",
                "ScopedNativePostpassOutputs outputs(context_);",
                "if (transfer == NativeGameStretchSourceTransfer::Reject)",
                "sampled.Get() != source",
                "context_->CopySubresourceRegion(",
                "D3D11CalcSubresource(sourceMipSlice, sourceArraySlice,",
                "sourceMipSlice == 0u;",
                "ScopedNativeGameEyeOutput restore(context_, targetWidth_, targetHeight_);",
                "if (!restore.valid()) return false;",
                "context_->OMSetRenderTargets(1u, &target, nullptr);",
                "context_->Draw(3u, 0u); // GPU postpass, not game geometry evidence",
            ]
            # Source-side bound checks must remain real: the helper rejects
            # bad source crop, offscreen/empty destinations, integer overflow
            # and sub-pixel UV collapse before this audited GPU Draw.
            stretch_helper = require_text(
                DX11 / "native_game_stretch_source.hpp",
                [
                    "right > width || bottom > height) return {};",
                    "targetWidth > static_cast<std::uint32_t>(",
                    "destRight <= destLeft || destBottom <= destTop)",
                    "if (x0 >= x1 || y0 >= y1) return {};",
                    "if (!(u1 > u0 && v1 > v0)) return {};",
                    "result.uv.constants[0] += u0 * uv.constants[2];",
                    "result.uv.constants[1] += v0 * uv.constants[3];",
                    "result.uv.constants[2] *= u1 - u0;",
                    "result.uv.constants[3] *= v1 - v0;",
                ],
                "DX11 clipped GPU StretchRect source/UV safety",
            )
            stretch_regression = require_text(
                ROOT / "tools" / "dx11_native_stretch_source_00839.cpp",
                [
                    "constexpr auto cropped = native_game_stretch_clipped_region(",
                    "constexpr auto otherEdge = native_game_stretch_clipped_region(",
                    "static_assert(!native_game_stretch_clipped_region(",
                ],
                "DX11 clipped GPU StretchRect positive/negative regression",
            )
            # Both authentic eyes must reject a cropped SourceCopy/Stretch
            # outside its physical camera mip before the first GPU command.
            # Audit the new *shared* C++ admission itself, not an obsolete
            # inline string which used to be duplicated in two encoders.
            mip_helper = require_text(
                DX11 / "native_game_postpass_replay.hpp",
                [
                    "mip >= 32u || !arraySize || arraySlice >= arraySize ||",
                    "!sampleCount || sampleCount > 32u ||",
                    "(sampleCount != 1u && (mip != 0u || mipLevels != 1u))",
                    "const auto w = width >> mip;",
                    "const auto h = height >> mip;",
                    "right > extent.width || bottom > extent.height) return {};",
                ],
                "DX11 actual game GPU camera mip/array and crop safety",
            )
            required_eye_replay_mip = [
                "const auto sourceMip = native_game_postpass_source_box(",
                "event.sourceMipSlice, desc.ArraySize,",
                "sourceMip.width, sourceMip.height,",
                "needsPostpassShader = true;",
            ]
            if any(token not in text for token in required_eye_replay_mip):
                raise SystemExit("DX11 stereo camera source-mip preflight removed")
            # Kept separate from evidence counters: neither helper nor probe
            # is permitted to authorize a new game-geometry Draw.
            del stretch_helper, stretch_regression, mip_helper
            missing = [token for token in required_eye_contract if token not in text]
            depth_probe = (ROOT / "tools" / "dx11_native_transport_probe.cpp").read_text(
                encoding="utf-8")
            missing += audit_native_partial_depth_clear(text, depth_probe)
            missing += audit_native_partial_color_clear(text)
            missing += audit_native_offscreen_game_draw(text, depth_probe)
            missing += ["postpass:" + token for token in required_postpass
                        if token not in postpass]
            postpass_draws = DRAW_DISPATCH.findall(postpass)
            if (not postpass or postpass_draws != ["->Draw("] or
                    "drawCount_++" in postpass or "colorDrawCount_++" in postpass):
                missing.append("postpass must issue one bounded non-evidence Draw")
            dispatches = [match.group(0).replace(" ", "") for match in matches]
            if missing or dispatches != [
                    "->Draw(", "->DrawIndexed(",  # game-created offscreen RTV
                    "->DrawInstanced(", "->DrawIndexedInstanced(",  # same game RTV
                    "->Draw(", "->DrawIndexed(",  # actual XR eye RTV
                    "->DrawInstanced(", "->DrawIndexedInstanced(",
                    "->Draw(", "->Draw(", "->Draw("]:
                violations.append(
                    f"{path.relative_to(ROOT)}: unauthorized native eye Draw "
                    f"dispatch or missing frame/pose/output/evidence guard: "
                    f"missing={missing}, calls={dispatches}"
                )
            continue
        if path == approved_diagnostic and matches:
            # This is a deliberate, separately audited activation—not an
            # exemption for arbitrary D3D11 Draw or main gameplay promotion.
            from verify_dx11_first_game_frame_boundary import (
                main as review_first_game_frame_diagnostic,
            )
            review_first_game_frame_diagnostic()
            continue
        for match in matches:
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(ROOT)}:{line}:{match.group(0).strip()}")

    if violations:
        raise SystemExit(
            "DX11 native draw activation boundary crossed; explicit activation "
            "review/runtime gate is required before Draw* dispatch is allowed: "
            + "; ".join(violations)
        )

    analyzer = require_text(
        ROOT / "tools" / "analyze_dx11_census.py",
        [
            '"NativeDrawPathActivationAllowed": False',
            '"ActivationProof": False',
            '"ExhaustiveDrawCoverage": exhaustive_draw_coverage',
            '"DiagnosticOnly": True',
            '"EXHAUSTIVE_V1"',
        ],
        "DX11 census analyzer",
    )
    if '"NativeDrawPathActivationAllowed": True' in analyzer:
        raise SystemExit("DX11 census analyzer must not authorize native draws")
    if '"ActivationProof": True' in analyzer:
        raise SystemExit("DX11 census analyzer must not promote diagnostics to activation proof")

    census = require_text(
        DX11 / "runtime_census.cpp",
        [
            "void observe_source_draw(",
            "ExactSamples.fetch_add",
            "signature.fixedFunction &&\n            signature.fixedFunctionStateCoverageExact &&\n            signature.fixedFunctionTranslationReady &&\n            signature.resourceBehaviorExact &&\n            resourcesExact && inputLayoutExact &&\n            signature.outputStateObservationComplete &&\n            signature.shaderReadinessExact &&\n            shaderCompileReadinessExact &&\n            signature.shaderTranslationExact",
            "OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE",
            "census_sample_stride()",
            "census_sampling_scheme()",
        ],
        "DX11 runtime census",
    )
    if DRAW_DISPATCH.search(census):
        raise SystemExit("DX11 census must remain observation-only")

    bridge = require_text(
        ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r7.inc",
        [
            "vr/d3d11/runtime_census.hpp",
            "observe_source_draw",
        ],
        "validated D3D9 draw bridge",
    )
    # The census is diagnostic-only, but every D3D9 draw family that the active
    # bridge hooks must still feed observe_source_draw. Losing one family would
    # silently weaken readiness evidence while the analyzer continues to report
    # non-exhaustive coverage.
    observed_draw_functions = {
        "DrawPrimitiveDest":
            "make_nonindexed_source_draw_observation(",
        "DrawIndexedPrimitiveDest":
            "make_indexed_source_draw_observation(",
        "DrawPrimitiveUPDest":
            "make_nonindexed_up_source_draw_observation(",
        "DrawIndexedPrimitiveUPDest":
            "make_indexed_up_source_draw_observation(",
    }
    missing_observers: list[str] = []
    for function_name, expected_factory in observed_draw_functions.items():
        marker = f"HRESULT __stdcall {function_name}("
        start = bridge.find(marker)
        if start < 0:
            missing_observers.append(function_name + ":missing-function")
            continue
        next_start = bridge.find("HRESULT __stdcall ", start + len(marker))
        block = bridge[start:] if next_start < 0 else bridge[start:next_start]
        if "outrun::vr::dx11::observe_source_draw(" not in block:
            missing_observers.append(function_name + ":missing-observer")
        if expected_factory not in block:
            missing_observers.append(
                function_name + ":wrong-source-draw-identity"
            )
    if missing_observers:
        raise SystemExit(
            "DX11 census source-draw coverage drift: " + ", ".join(missing_observers)
        )

    draw_hook_wiring = [
        "DrawPrimitiveHook=safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex],DrawPrimitiveDest,disabled);",
        "DrawIndexedPrimitiveHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveVtableIndex],DrawIndexedPrimitiveDest,disabled);",
        "DrawPrimitiveUPHook=safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex],DrawPrimitiveUPDest,disabled);",
        "DrawIndexedPrimitiveUPHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveUPVtableIndex],DrawIndexedPrimitiveUPDest,disabled);",
    ]
    missing_hook_wiring = [token for token in draw_hook_wiring if token not in bridge]
    if missing_hook_wiring:
        raise SystemExit(
            "DX11 census D3D9 draw-hook wiring drift: " + ", ".join(missing_hook_wiring)
        )

    forbidden_bridge_tokens = [
        "vr/d3d11/native_backend.hpp",
        "vr/d3d11/native_shared_eye_ring.hpp",
    ]
    leaked = [token for token in forbidden_bridge_tokens if token in bridge]
    if leaked:
        raise SystemExit(
            "validated D3D9 draw bridge gained native DX11 routing dependencies: "
            + ", ".join(leaked)
        )

    print(
        "DX11 dormant activation boundary: OK "
        "(census diagnostic-only; no native D3D11 Draw* dispatch)"
    )


if __name__ == "__main__":
    main()
