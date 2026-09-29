#!/usr/bin/env python3
"""Small OutRun patch on top of Detegr/dxvk-openRBRVR.

Upstream already implements the actual Vulkan multiview pipeline, SPIR-V
inspection/patch hooks and layered D3D9 render targets.  OutRun additionally
needs to switch a persistent layered surface between:
  UINT_MAX -> all views (one-draw programmable world multiview)
  0        -> left-only fallback draw
  1        -> right-only fallback draw

The upstream interface exposes SetMultiviewSurfaceLayer but its subresource
implementation is currently a TODO.  This patch completes that method and
invalidates cached image views whenever the selected layer changes.
"""

from pathlib import Path
import sys

p = Path("src/d3d9/d3d9_subresource.h")
if not p.exists():
    raise SystemExit(f"missing {p}; run from dxvk-openRBRVR checkout")

s = p.read_text(encoding="utf-8")

old_face = """    inline UINT GetFace() const {
      const bool isMultiviewResource = m_texture->Desc()->ArraySize > 1 && m_texture->Desc()->ArraySize <= 4;
      return isMultiviewResource ? AllLayers : m_face;
    }"""
new_face = """    inline UINT GetFace() const {
      const bool isMultiviewResource = m_texture->Desc()->ArraySize > 1 && m_texture->Desc()->ArraySize <= 4;
      return isMultiviewResource ? m_multiviewSurfaceLayer : m_face;
    }"""

old_setter = """    inline void SetMultiviewSurfaceLayer(UINT layer) { /* TODO */ }"""
new_setter = """    inline void SetMultiviewSurfaceLayer(UINT layer) {
      const UINT layers = m_texture->Desc()->ArraySize;
      if (layers <= 1 || layers > 4)
        return;
      if (layer != AllLayers && layer >= layers)
        return;
      if (m_multiviewSurfaceLayer == layer)
        return;

      m_multiviewSurfaceLayer = layer;

      // Image views cache the selected layer range, so they must be rebuilt.
      m_sampleView = { };
      m_renderTargetView = { };
      m_depthStencilView = nullptr;
    }"""

old_member = """    UINT                    m_isNull           : 1;
  
    D3D9ColorView           m_sampleView;"""
new_member = """    UINT                    m_isNull           : 1;
    UINT                    m_multiviewSurfaceLayer = std::numeric_limits<uint32_t>::max();
  
    D3D9ColorView           m_sampleView;"""

for old, new, label in [
    (old_face, new_face, "GetFace"),
    (old_setter, new_setter, "SetMultiviewSurfaceLayer"),
    (old_member, new_member, "layer member"),
]:
    if old not in s:
        if new in s:
            print(f"{label}: already patched")
            continue
        raise SystemExit(f"{label}: expected upstream text not found")
    s = s.replace(old, new, 1)
    print(f"{label}: patched")

p.write_text(s, encoding="utf-8")

# Make the build identifiable in support logs and binary string checks.
marker_path = Path("OUTRUN_MULTIVIEW_PROVIDER.txt")
marker_path.write_text(
    "OUTRUN_DXVK_OPENRBRVR_LAYER_SWITCH_V1\n"
    "Base: Detegr/dxvk-openRBRVR (zlib)\n"
    "Patch: layer-selectable 2-view D3D9 surfaces for OutRun2006Tweaks\n",
    encoding="utf-8",
)
print("OutRun dxvk-openRBRVR layer-selection patch applied.")
