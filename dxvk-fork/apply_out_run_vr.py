#!/usr/bin/env python3
"""Apply the OutRun VR compatibility handshake to an upstream DXVK checkout.

Pinned/tested source baseline: DXVK v3.1.1.
This first provider milestone is intentionally fail-closed: it exposes protocol
v1 and diagnostics, but ArmStereoDraw returns S_FALSE until the Vulkan
multiview implementation is compiled in. The game therefore keeps using its
validated two-pass fallback instead of silently producing a one-eye frame.
"""

from __future__ import annotations

import pathlib
import sys


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply_out_run_vr.py <dxvk-source>", file=sys.stderr)
        return 2

    root = pathlib.Path(sys.argv[1]).resolve()
    interfaces = root / "src/d3d9/d3d9_interfaces.h"
    interop_h = root / "src/d3d9/d3d9_interop.h"
    interop_cpp = root / "src/d3d9/d3d9_interop.cpp"
    device_h = root / "src/d3d9/d3d9_device.h"
    device_cpp = root / "src/d3d9/d3d9_device.cpp"

    for path in (interfaces, interop_h, interop_cpp, device_h, device_cpp):
        if not path.is_file():
            raise RuntimeError(f"missing expected DXVK v3.1.1 source: {path}")

    interface_anchor = """/**
 * \\brief D3D9 current output metadata
 */
struct D3D9VkExtOutputMetadata {
"""
    interface_insert = r"""/**
 * \brief OutRun VR private stereo handshake
 *
 * This interface is intentionally private to the OutRun VR experiment.
 * Version 1 is a capability/diagnostic handshake. The initial provider
 * implementation returns S_FALSE from ArmStereoDraw so the client must keep
 * using its proven D3D9 two-pass fallback until true multiview is implemented.
 */
#pragma pack(push, 8)
struct D3D9OutRunVRFrameStateV1 {
  uint32_t size;
  uint32_t version;
  uint64_t poseSequence;
  uint64_t frameId;
  uint32_t flags;
  uint32_t reserved;
};

struct D3D9OutRunVRDrawStateV1 {
  uint32_t size;
  uint32_t version;
  uint64_t poseSequence;
  uint64_t drawToken;
  float leftWvp[16];
  float rightWvp[16];
  uint32_t eligibilityFlags;
  uint32_t reserved;
};

struct D3D9OutRunVRCountersV1 {
  uint32_t size;
  uint32_t version;
  uint64_t armedDraws;
  uint64_t multiviewDraws;
  uint64_t rejectedDraws;
  uint64_t fallbackDraws;
};
#pragma pack(pop)

static_assert(sizeof(D3D9OutRunVRFrameStateV1) == 32);
static_assert(sizeof(D3D9OutRunVRDrawStateV1) == 160);
static_assert(sizeof(D3D9OutRunVRCountersV1) == 40);

MIDL_INTERFACE("b16d40b8-1a79-4e11-9d47-7a50c1f56e62")
ID3D9OutRunVRInterop : public IUnknown {
  virtual HRESULT STDMETHODCALLTYPE GetProtocolVersion(
          uint32_t* version) = 0;

  virtual HRESULT STDMETHODCALLTYPE GetCapabilities(
          uint32_t* flags) = 0;

  virtual HRESULT STDMETHODCALLTYPE SetFrameState(
    const D3D9OutRunVRFrameStateV1* state) = 0;

  virtual HRESULT STDMETHODCALLTYPE ArmStereoDraw(
    const D3D9OutRunVRDrawStateV1* state,
          IUnknown*                rightColorTarget,
          IUnknown*                rightDepthTarget) = 0;

  virtual HRESULT STDMETHODCALLTYPE CancelStereoDraw() = 0;

  virtual HRESULT STDMETHODCALLTYPE GetCounters(
          D3D9OutRunVRCountersV1* counters) = 0;
};


/**
 * \brief D3D9 current output metadata
 */
struct D3D9VkExtOutputMetadata {
"""
    replace_once(interfaces, interface_anchor, interface_insert)

    uuid_anchor = """__CRT_UUID_DECL(ID3D9VkInteropDevice,      0x2eaa4b89,0x0107,0x4bdb,0x87,0xf7,0x0f,0x54,0x1c,0x49,0x3c,0xe0);
"""
    uuid_insert = """__CRT_UUID_DECL(ID3D9VkInteropDevice,      0x2eaa4b89,0x0107,0x4bdb,0x87,0xf7,0x0f,0x54,0x1c,0x49,0x3c,0xe0);
__CRT_UUID_DECL(ID3D9OutRunVRInterop,       0xb16d40b8,0x1a79,0x4e11,0x9d,0x47,0x7a,0x50,0xc1,0xf5,0x6e,0x62);
"""
    replace_once(interfaces, uuid_anchor, uuid_insert)

    class_anchor = """  class D3D9VkExtInterface final : public ID3D9VkExtInterface {
"""
    class_insert = """  class D3D9OutRunVRInterop final : public ID3D9OutRunVRInterop {

  public:

    explicit D3D9OutRunVRInterop(D3D9DeviceEx* pDevice);

    ULONG STDMETHODCALLTYPE AddRef();
    ULONG STDMETHODCALLTYPE Release();

    HRESULT STDMETHODCALLTYPE QueryInterface(
            REFIID                riid,
            void**                ppvObject);

    HRESULT STDMETHODCALLTYPE GetProtocolVersion(
            uint32_t*             version);

    HRESULT STDMETHODCALLTYPE GetCapabilities(
            uint32_t*             flags);

    HRESULT STDMETHODCALLTYPE SetFrameState(
      const D3D9OutRunVRFrameStateV1* state);

    HRESULT STDMETHODCALLTYPE ArmStereoDraw(
      const D3D9OutRunVRDrawStateV1* state,
            IUnknown*                rightColorTarget,
            IUnknown*                rightDepthTarget);

    HRESULT STDMETHODCALLTYPE CancelStereoDraw();

    HRESULT STDMETHODCALLTYPE GetCounters(
            D3D9OutRunVRCountersV1* counters);

  private:

    static constexpr uint32_t ProtocolVersion = 1u;

    D3D9DeviceEx* m_device;
    D3D9OutRunVRFrameStateV1 m_frame = { };
    D3D9OutRunVRCountersV1 m_counters = {
      sizeof(D3D9OutRunVRCountersV1), ProtocolVersion, 0u, 0u, 0u, 0u
    };
  };


  class D3D9VkExtInterface final : public ID3D9VkExtInterface {
"""
    replace_once(interop_h, class_anchor, class_insert)

    impl_anchor = """  D3D9VkExtInterface::D3D9VkExtInterface(D3D9InterfaceEx *pInterface)
"""
    impl_insert = r"""  D3D9OutRunVRInterop::D3D9OutRunVRInterop(D3D9DeviceEx* pDevice)
    : m_device(pDevice) {
  }

  ULONG STDMETHODCALLTYPE D3D9OutRunVRInterop::AddRef() {
    return m_device->AddRef();
  }

  ULONG STDMETHODCALLTYPE D3D9OutRunVRInterop::Release() {
    return m_device->Release();
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::QueryInterface(
          REFIID riid,
          void** ppvObject) {
    return m_device->QueryInterface(riid, ppvObject);
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::GetProtocolVersion(
          uint32_t* version) {
    if (version == nullptr)
      return E_POINTER;

    *version = ProtocolVersion;
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::GetCapabilities(
          uint32_t* flags) {
    if (flags == nullptr)
      return E_POINTER;

    // Milestone 1 advertises no draw-ownership capabilities. This prevents
    // the client from entering the per-draw custom path at all.
    *flags = 0u;
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::SetFrameState(
    const D3D9OutRunVRFrameStateV1* state) {
    if (state == nullptr
     || state->size < sizeof(D3D9OutRunVRFrameStateV1)
     || state->version != ProtocolVersion)
      return D3DERR_INVALIDCALL;

    m_frame = *state;
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::ArmStereoDraw(
    const D3D9OutRunVRDrawStateV1* state,
          IUnknown*                rightColorTarget,
          IUnknown*                rightDepthTarget) {
    if (state == nullptr
     || state->size < sizeof(D3D9OutRunVRDrawStateV1)
     || state->version != ProtocolVersion
     || state->poseSequence == 0u
     || state->poseSequence != m_frame.poseSequence
     || rightColorTarget == nullptr)
      return D3DERR_INVALIDCALL;

    (void)rightDepthTarget;

    m_counters.armedDraws += 1u;

    // Milestone 1 deliberately refuses ownership of the draw. Returning
    // S_FALSE is part of the contract: the OutRun hook executes its already
    // validated two-pass path. Never return S_OK until the DXVK D3D9 draw
    // path has actually emitted both views using the supplied eye matrices.
    m_counters.rejectedDraws += 1u;
    m_counters.fallbackDraws += 1u;
    return S_FALSE;
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::CancelStereoDraw() {
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE D3D9OutRunVRInterop::GetCounters(
          D3D9OutRunVRCountersV1* counters) {
    if (counters == nullptr)
      return E_POINTER;

    if (counters->size < sizeof(D3D9OutRunVRCountersV1)
     || counters->version != ProtocolVersion)
      return D3DERR_INVALIDCALL;

    *counters = m_counters;
    return S_OK;
  }


  D3D9VkExtInterface::D3D9VkExtInterface(D3D9InterfaceEx *pInterface)
"""
    replace_once(interop_cpp, impl_anchor, impl_insert)

    member_anchor = """    D3D9VkInteropDevice             m_d3d9Interop;
    D3D9ON12_ARGS                   m_d3d9On12Args = { };
"""
    member_insert = """    D3D9VkInteropDevice             m_d3d9Interop;
    D3D9OutRunVRInterop             m_outRunVrInterop;
    D3D9ON12_ARGS                   m_d3d9On12Args = { };
"""
    replace_once(device_h, member_anchor, member_insert)

    ctor_anchor = """    , m_d3d9Interop        ( this )
    , m_d3d9On12Args       ( pAdapter->Get9On12Args() )
"""
    ctor_insert = """    , m_d3d9Interop        ( this )
    , m_outRunVrInterop    ( this )
    , m_d3d9On12Args       ( pAdapter->Get9On12Args() )
"""
    replace_once(device_cpp, ctor_anchor, ctor_insert)

    qi_anchor = """    if (riid == __uuidof(ID3D9VkInteropDevice)) {
      *ppvObject = ref(&m_d3d9Interop);
      return S_OK;
    }

    if (riid == __uuidof(IDirect3DDevice9On12)) {
"""
    qi_insert = """    if (riid == __uuidof(ID3D9VkInteropDevice)) {
      *ppvObject = ref(&m_d3d9Interop);
      return S_OK;
    }

    if (riid == __uuidof(ID3D9OutRunVRInterop)) {
      *ppvObject = ref(&m_outRunVrInterop);
      return S_OK;
    }

    if (riid == __uuidof(IDirect3DDevice9On12)) {
"""
    replace_once(device_cpp, qi_anchor, qi_insert)

    print("OutRun VR DXVK protocol-v1 compatibility provider applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
