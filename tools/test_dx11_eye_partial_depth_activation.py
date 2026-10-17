#!/usr/bin/env python3
"""Tamper checks for the audited partial game DSV-only GPU clear admission."""
from pathlib import Path
from verify_dx11_activation_boundary import (
    DRAW_DISPATCH, audit_native_partial_depth_clear,
    audit_native_partial_color_clear, audit_native_offscreen_game_draw,
)

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(
    encoding="utf-8")
probe = (ROOT / "tools/dx11_native_transport_probe.cpp").read_text(
    encoding="utf-8")

assert not audit_native_partial_depth_clear(source, probe), "valid DSV audit failed"
# The timeline's valid bounded Clear must replay through GPU Draw, while its
# negative companion must actually lie outside the eye (not an old valid box).
assert "invalidPartialDepth.entries[1][0].rect = {-1, 1, 4, 4};" in probe
assert "zRect.kind = SourceClear::Kind::FullDepthStencil;" in probe
# Guard all eleven reviewed GPU dispatches: four offscreen game camera
# Draw forms, four true eye commands and three non-evidence GPU triangles.
# A new source Draw still requires explicit owner/activation audit.
expected_dispatches = [
    "->Draw(", "->DrawIndexed(",  # genuine offscreen game source RTV
    "->DrawInstanced(", "->DrawIndexedInstanced(",  # source instanced cameras
    "->Draw(", "->DrawIndexed(",  # genuine eye RTV
    "->DrawInstanced(", "->DrawIndexedInstanced(",
    "->Draw(", "->Draw(", "->Draw(",
]
assert DRAW_DISPATCH.findall(source) == expected_dispatches, (
    "unexpected native Draw dispatch")
# Removing the OM0 unbind would let a helper write a color RTV instead of
# replacing only depth/stencil under exactly scoped per-eye provenance.
assert audit_native_partial_depth_clear(
    source.replace(
        "context->OMSetRenderTargets(0u, nullptr, depthView);",
        "context->OMSetRenderTargets(1u, &target, depthView);", 1),
    probe), "color RTV tamper slipped through"
# A helper which does not preserve full MRT/IA/shader state after the GPU fill
# could corrupt the next game's eye Draw and the original D3D9 fallback.
assert audit_native_partial_depth_clear(
    source.replace("if (!saved.valid()) return false;", "", 1), probe
), "state guard tamper slipped through"
# Source coverage cannot silently lose the negative real-game RECT regression.
assert audit_native_partial_depth_clear(
    source, probe.replace(
        "!encoder.clear_depth_stencil(0.5f, 0u, true, true, &badRect)", ""
    )), "bad-RECT regression removal slipped through"
# Keep the negative mutation on the TRUE eye encoder. An auxiliary game
# camera has a separate clear route, so a first-occurrence global replace
# would mutate only that camera and silently stop testing eye admission.
def tamper_eye(method, original, replacement):
    anchor = "bool NativeGameEyeDrawEncoder::" + method + "("
    prefix, body = source.split(anchor, 1)
    assert original in body, "eye GPU route missing: " + method
    return prefix + anchor + body.replace(original, replacement, 1)

# Reject a real partial HUD/menu Clear being widened into a whole-eye
# DSV operation, and reject deleting the malformed two-eye preflight.
assert audit_native_partial_depth_clear(
    tamper_eye(
        "clear_depth_stencil",
        "route == live_game_stereo::NativeDepthClearRoute::PartialRaster",
        "route == live_game_stereo::NativeDepthClearRoute::FullDsv"),
    probe), "cropped depth-region widening slipped through"
assert audit_native_partial_depth_clear(
    tamper_eye(
        "clear_depth_stencil",
        "route == live_game_stereo::NativeDepthClearRoute::Reject",
        "route == live_game_stereo::NativeDepthClearRoute::FullDsv"),
    probe), "invalid depth-region admission slipped through"
# The caller still owns the boundary: an unauthorized Draw is not made
# legitimate by the narrowly reviewed depth-only callback.
assert DRAW_DISPATCH.findall(source + "\ncontext->Draw(8u, 0u);") != expected_dispatches

# A D3D11.0 source TARGET Clear uses one strictly cropped GPU shader Draw,
# never authorizes unrelated game draws or an unbounded full-eye color Clear.
assert not audit_native_partial_color_clear(source), "valid color audit failed"
assert audit_native_partial_color_clear(
    source.replace(
        "context->OMSetRenderTargets(1u, &target, nullptr);",
        "context->OMSetRenderTargets(0u, nullptr, nullptr);", 1),
), "missing owned eye RTV slipped through"
assert audit_native_partial_color_clear(
    source.replace(
        "context->RSSetState(nullptr); // game Clear ignores saved scissor/cull",
        "", 1),
), "inherited scissor/cull tamper slipped through"
assert audit_native_partial_color_clear(
    source.replace(
        "ds.DepthEnable = FALSE;", "ds.DepthEnable = TRUE;", 1),
), "inherited depth test tamper slipped through"
assert audit_native_partial_color_clear(
    tamper_eye(
        "clear_target_argb",
        "case live_game_stereo::NativeColorClearRoute::ShaderRaster:",
        "case live_game_stereo::NativeColorClearRoute::FullRtv:"),
), "cropped TARGET clear widened into full-eye Clear"
assert audit_native_partial_color_clear(
    source.replace(
        'const bool ready = GetProcAddress(compiler, "D3DCompile") != nullptr;',
        'const bool ready = false;', 1),
), "missing D3D11.0 preflight slipped through"
# The source-owned offscreen camera Draws must never fabricate eye color.
# Test explicit OM binding/alias/device and source chronology tampering.
assert not audit_native_offscreen_game_draw(source, probe), "valid offscreen audit failed"
assert audit_native_offscreen_game_draw(
    source.replace("const bool bound = actual == gameTarget;",
                   "const bool bound = actual != gameTarget;", 1), probe
), "offscreen RTV bound-state tamper slipped through"
assert audit_native_offscreen_game_draw(
    source.replace("sourceResource.Get() == eyeResource.Get()",
                   "sourceResource.Get() != eyeResource.Get()", 1), probe
), "aliased eye texture tamper slipped through"
assert audit_native_offscreen_game_draw(
    source.replace("if (!producer || producer.Get() != sourceOwner.Get()) return false;",
                   "if (!producer) return false;", 1), probe
), "foreign device tamper slipped through"
assert audit_native_offscreen_game_draw(
    source.replace("if (!replay_due_source_clears()) return false;",
                   "return true;", 1), probe
), "source event timeline bypass slipped through"
assert audit_native_offscreen_game_draw(
    source.replace("++drawCount_; // source ordinal, NEVER direct XR color evidence",
                   "++colorDrawCount_; // invalid eye color", 1), probe
), "phantom eye color slipped through"
assert audit_native_offscreen_game_draw(
    source, probe.replace("fixture.offscreenGameColor, &offscreenPatch,", "", 1)
), "missing offscreen camera-to-eye GPU copy proof slipped through"
# Offscreen instancing MUST validate the real game RT and preserve a single
# chronological source command per call, without creating direct eye color.
assert audit_native_offscreen_game_draw(
    source.replace(
        "verticesPerInstance, instanceCount, drawCount_) ||\n"
        "        !prepare_offscreen_game_draw(gameTarget))",
        "verticesPerInstance, instanceCount, drawCount_) ||\n"
        "        false)", 1), probe
), "instanced source target preflight bypass slipped through"
assert audit_native_offscreen_game_draw(
    source.replace(
        "indicesPerInstance, instanceCount, startIndex,\n"
        "        baseVertex, startInstance);\n    ++drawCount_;",
        "indicesPerInstance, instanceCount, startIndex,\n"
        "        baseVertex, startInstance);\n    ++colorDrawCount_;", 1), probe
), "indexed instanced phantom eye color slipped through"
# Offscreen camera color+depth Clear must remain an owned GPU command and
# cannot forge a direct-eye clear/draw. Mutation checks cover both domains.
def camera_clear_contract(code):
    color = code.split("bool NativeGameEyeDrawEncoder::clear_offscreen_game_color(", 1)[-1].split(
        "bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", 1)[0]
    depth = code.split("bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", 1)[-1].split(
        "bool NativeGameEyeDrawEncoder::replay_due_source_clears(", 1)[0]
    return all(t in color for t in (
        "prepare_offscreen_game_draw(gameTarget)",
        "context_->ClearRenderTargetView(gameTarget, rgba);",
    )) and all(t in depth for t in (
        "!prepare_offscreen_game_draw(gameTarget)",
        "boundDepth.Get() != gameDepth",
        "depthResource.Get() == eyeDepthResource.Get()",
        "dd.Width != cd.Width",
        "dd.SampleDesc.Count != cd.SampleDesc.Count",
        "context_->ClearDepthStencilView(gameDepth, flags, depth, stencil);",
    ))
assert camera_clear_contract(source)
assert not camera_clear_contract(source.replace(
    "boundDepth.Get() != gameDepth", "false", 1))
assert not camera_clear_contract(source.replace(
    "depthResource.Get() == eyeDepthResource.Get()", "false", 1))
assert not camera_clear_contract(source.replace(
    "context_->ClearRenderTargetView(gameTarget, rgba);", "", 1))
assert "gameEyeFixture.replayedOffscreenGameClears[0] &&" in probe
assert "gameEyeFixture.replayedOffscreenGameClears[1] &&" in probe
assert "gameEyeFixture.replayedOffscreenGamePartialClears[0] &&" in probe
assert "gameEyeFixture.replayedOffscreenGamePartialClears[1] &&" in probe
assert "encoder.copy_game_surface(" in probe
# Camera rectangle must have the same bounded GPU route and preserved
# offscreen RTV/DSV owner, not an accidental whole-camera wipe.
def offscreen_rect_contract(code, fixture):
    color = code.split("bool NativeGameEyeDrawEncoder::clear_offscreen_game_color(", 1)[1].split(
        "bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", 1)[0]
    depth = code.split("bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", 1)[1].split(
        "bool NativeGameEyeDrawEncoder::replay_due_source_clears(", 1)[0]
    return all(x in color for x in (
        "prepare_offscreen_game_draw(gameTarget)",
        "live_game_stereo::color_clear_route(", 
        "rectContext->ClearView(gameTarget, rgba, region, 1u);",
        "raster_partial_eye_color_clear(",
        "context_->ClearRenderTargetView(gameTarget, rgba);",
    )) and all(x in depth for x in (
        "boundDepth.Get() != gameDepth",
        "dd.Width != cd.Width",
        "live_game_stereo::depth_clear_route(",
        "raster_partial_eye_depth_clear(",
        "context_->ClearDepthStencilView(gameDepth, flags, depth, stencil);",
    )) and all(x in fixture for x in (
        "rejectsCameraRegion && clearsCameraRegion && cameraPatchVisible",
        "ctx->CopyResource(cameraReadback.Get(), fixture.offscreenGameColor);",
        "ctx->OMSetRenderTargets(1u, &gameOffscreen, gameOffscreenDepth);",
    ))
assert offscreen_rect_contract(source, probe)
assert not offscreen_rect_contract(source.replace(
    "rectContext->ClearView(gameTarget, rgba, region, 1u);", "", 1), probe)
assert not offscreen_rect_contract(source.replace(
    "return raster_partial_eye_depth_clear(\n            context_, gameDepth",
    "return missing_partial_depth(\n            context_, gameDepth", 1), probe)
assert not offscreen_rect_contract(source, probe.replace(
    "rejectsCameraRegion && clearsCameraRegion && cameraPatchVisible",
    "true"))

# Both independent game-camera and ring-eye Clear paths must admit a real
# float color shader only for compatible typed D3D11 render-target views.
# The backing allocation can be TYPELESS, but a typeless/integer RTV must
# not be silently accepted or clear the complete camera on D3D11.0.
def typed_partial_color_admission(code):
    part = code.split(
        "[[nodiscard]] bool native_game_partial_color_shader_rtv(", 1)
    if len(part) != 2:
        return False
    helper = part[1].split("\n}\n", 1)[0]
    camera = code.split(
        "bool NativeGameEyeDrawEncoder::clear_offscreen_game_color(", 1)[1].split(
        "bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", 1)[0]
    eye = code.split(
        "bool NativeGameEyeDrawEncoder::clear_target_argb(", 1)[1].split(
        "bool NativeGameEyeDrawEncoder::clear_depth_stencil(", 1)[0]
    return all(token in helper for token in (
        "target->GetDesc(&view);",
        "switch (view.Format)",
        "DXGI_FORMAT_R10G10B10A2_UNORM",
        "DXGI_FORMAT_R16G16B16A16_FLOAT",
        "DXGI_FORMAT_R11G11B10_FLOAT",
        "default:",
        "return false;",
        "CheckFormatSupport(view.Format, &support)",
        "D3D11_FORMAT_SUPPORT_RENDER_TARGET",
    )) and all(token in body for body in (camera, eye) for token in (
        "cropped && !rectContext",
        "native_game_partial_color_shader_rtv(context_,",
        "live_game_stereo::color_clear_route(",
        "case live_game_stereo::NativeColorClearRoute::ShaderRaster:",
        "raster_partial_eye_color_clear(",
    ))
assert typed_partial_color_admission(source), "typed RTV color Clear missing"
assert not typed_partial_color_admission(source.replace(
    "target->GetDesc(&view);", "", 1)), "backing-format fallback accepted"
assert not typed_partial_color_admission(source.replace(
    "(support & D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u;",
    "true;", 1)), "unsupported GPU target accepted"
assert not typed_partial_color_admission(source.replace(
    "native_game_partial_color_shader_rtv(context_, eyeTarget_)",
    "false", 1)), "ring-eye Clear lost"
assert not typed_partial_color_admission(source.replace(
    "native_game_partial_color_shader_rtv(context_, gameTarget)",
    "false", 1)), "offscreen camera Clear lost"

print("DX11 owned offscreen camera color/depth + Draw/Copy: PASS")
