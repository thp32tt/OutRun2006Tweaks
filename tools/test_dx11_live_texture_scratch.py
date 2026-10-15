#!/usr/bin/env python3
"""Regression guard for the production full-resolution native game texture path.

Windows Build compiles this C++ implementation; this test checks critical source
contracts and does not substitute for OutRun/Quest3 runtime verification.
"""
from pathlib import Path

src = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
head, tail = src.split("bool mirror_texture(ID3D11Device* dev, ID3D11DeviceContext* ctx,", 1)
body, submit = tail.split("bool submit(State& s,", 1)
required_head = (
    "std::array<NativeGameTextureScratch, 2> liveTextureSlots",
    "for (auto& slot : s.liveTextureSlots) slot.reset();",
    "width == w && height == h && levels == mips && format == fmt",
)
required_body = (
    "scratch.matches(desc.Width, desc.Height",
    "desc.Usage = D3D11_USAGE_DEFAULT;",
    "ctx->UpdateSubresource(target, level, nullptr, copied[level].data(),",
    "for (UINT level = 0; level < levels; ++level)",
    "if (FAILED(dev->GetDeviceRemovedReason())) return false;",
    "view = scratch.view;",
    "return create_game_sampler(dev, capture, levels, sampler);",
)
required_submit = (
    "s.liveTextureSlots[0], capture",
    "s.liveTextureSlots[1], second",
    "stage1View = sampledView;",
)
for token in required_head:
    assert token in head, token
for token in required_body:
    assert token in body, token
for token in required_submit:
    assert token in submit, token
assert "D3D11_USAGE_IMMUTABLE" not in body
assert "initial.data()" not in body
# Destructive source mutants are rejected by the same contracts.
assert not all(x in submit.replace("s.liveTextureSlots[1], second", "s.liveTextureSlots[0], second", 1) for x in required_submit)
assert not all(x in body.replace("ctx->UpdateSubresource(target, level, nullptr, copied[level].data(),", "// missing upload", 1) for x in required_body)
print("PASS: fresh every-Draw game pixels, separate stage 0/1 native GPU slots and device recreation")
