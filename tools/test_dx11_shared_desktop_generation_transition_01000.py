#!/usr/bin/env python3
"""Negative source-mutation regression for real D3D11/D3D9Ex cross-generation GPU retirement.

Windows Build and real Quest 3/D3D9Ex execution remain separate.
"""
from pathlib import Path

src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d11/native_game_shared_desktop.hpp").read_text(encoding="utf-8")
required = [
    "if (allocationChanged) {",
    "if (shared9_) {",
    "if (faulted_) return false;",
    "if (d3d9ReadPending_) {",
    "d3d9ReadFence_->GetData(",
    "if (consumerDone == S_FALSE) return false;",
    "if (consumerDone != S_OK) {",
    "d3d9ReadPending_ = false;",
    "if (pending_) {",
    "device11_->GetImmediateContext(",
    "previousContext->GetData(",
    "fence_.Get(), nullptr, 0,",
    "D3D11_ASYNC_GETDATA_DONOTFLUSH",
    "if (producerDone == S_FALSE) return false;",
    "if (producerDone != S_OK) {",
    "pending_ = false;",
    "reset();"
]
def correct(s):
    start = s.find("const bool allocationChanged =")
    if start < 0:
        return False
    stop = s.find("D3D11_TEXTURE2D_DESC shared{};", start)
    if stop < 0:
        return False
    t = s[start:stop]
    indices = [t.find(token) for token in required]
    return (all(i >= 0 for i in indices) and indices == sorted(indices)
            and "device11_.Get() != device" in t
            and "game9Ex_.Get() != ex.Get()" in t
            and "width_ != width || height_ != height" in t
            and "generation_ != generation" in t
            and "D3DGETDATA_FLUSH" in t
            and t.count("faulted_ = true;") >= 4
            and t.count("return false;") >= 8)

assert correct(src), "old-generation GPU use can outlive shared allocation"
for token in required[1:-1]:
    start = src.index("const bool allocationChanged =")
    stop = src.index("D3D11_TEXTURE2D_DESC shared{};", start)
    mutant = src[:start] + src[start:stop].replace(
        token, "/* removed transition gate */", 1) + src[stop:]
    assert not correct(mutant), token
print("PASS: D3D9Ex reader and old D3D11 producer retired before generation swap")
