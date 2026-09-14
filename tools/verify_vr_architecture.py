from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    # Verified OutRun-specific assets retained during reconstruction.
    'src/vr/settings.cpp',
    'src/vr/game/outrun_renderer.cpp',
    'src/vr/d3d9/stereo_renderer.cpp',
    'src/vr/ipc/protocol.hpp',
    # New architecture foundation.
    'src/vr/core/frame_types.hpp',
    'src/vr/core/transport.hpp',
    'src/vr/game/game_adapter.hpp',
    'src/vr/d3d9/stereo_backend.hpp',
    'src/vr/ipc/protocol_v3.hpp',
    'src/vr/ipc/protocol_v3_smoke.cpp',
    'vrhost/src/runtime/vr_runtime.hpp',
    'vrhost/src/frame_source.hpp',
    'vrhost/tests/protocol_v3_smoke.cpp',
    'vrhost/src/main.cpp',
    'vrhost/src/stereo_shader.hpp',
    'vrhost/tests/stereo_shader_smoke.cpp',
    'docs/VR_ARCHITECTURE.md',
]
for rel in required:
    if not (ROOT / rel).is_file():
        raise SystemExit(f'missing architecture file: {rel}')

forbidden = [
    'src/hooks_vr.cpp',
    'src/vr_renderer_probe.cpp',
    'src/vr_stereo.cpp',
    'vrhost/main.cpp',
    'vrhost/main_compat.cpp',
    'vrhost/main_compat_v2.cpp',
    'vrhost/main_compat_v3.cpp',
    'vrhost/main_stereo.cpp',
    'vrhost/shader_compile_patch.hpp',
    'vrhost/shader_smoke_test.cpp',
    'tools/apply_vr_direct_gpu_transport.py',
    'tools/apply_vr_reference_hardening.py',
    'tools/fix_vr_host_interop_block.py',
    '.github/workflows/apply-vr-direct-gpu-transport.yml',
    '.github/workflows/apply-vr-host-hotfix.yml',
    '.github/workflows/apply-vr-reference-hardening.yml',
]
for rel in forbidden:
    if (ROOT / rel).exists():
        raise SystemExit(f'legacy/prototype artifact still present: {rel}')

# v2 remains only as the live compatibility runtime while behavior is moved.
protocol_v2 = (ROOT / 'src/vr/ipc/protocol.hpp').read_text(encoding='utf-8')
for marker in (
    'SharedProtocolVersion = 2', 'RenderFrameProtocolVersion = 2',
    'RenderFrameRingSize = 4', 'HostAdapterLuidValid',
    'clientInteropProbeHandle', 'hostInteropProbeAckToken',
    'SharedRenderFrameRing',
):
    if marker not in protocol_v2:
        raise SystemExit(f'missing live v2 compatibility invariant: {marker}')

# v3 is the target contract. Ownership is explicit and cross-bitness fields are
# fixed width; no reserved-word semantic extensions are allowed.
protocol_v3 = (ROOT / 'src/vr/ipc/protocol_v3.hpp').read_text(encoding='utf-8')
for marker in (
    'ProtocolVersion = 3', 'HostStateName', 'ClientStateName',
    'FrameRingName', 'AckStateName', 'struct HostState',
    'struct ClientState', 'struct FrameRing', 'struct AckState',
    'using WireHandle = std::uint64_t', 'WireHandle leftHandle',
    'WireHandle rightHandle',
):
    if marker not in protocol_v3:
        raise SystemExit(f'missing v3 ownership/cross-bitness invariant: {marker}')
for forbidden_marker in ('reserved[', 'std::uintptr_t interopProbeHandle',
                         'std::uintptr_t leftHandle', 'std::uintptr_t rightHandle'):
    if forbidden_marker in protocol_v3:
        raise SystemExit(f'v3 protocol reintroduced implicit ABI debt: {forbidden_marker}')

core_transport = (ROOT / 'src/vr/core/transport.hpp').read_text(encoding='utf-8')
for marker in ('class IFrameProducer', 'class IFrameConsumer',
               'D3D9ExShared', 'DesktopDuplication', 'Dxvk'):
    if marker not in core_transport:
        raise SystemExit(f'missing transport backend boundary: {marker}')

game_adapter = (ROOT / 'src/vr/game/game_adapter.hpp').read_text(encoding='utf-8')
for marker in ('class IGameAdapter', 'latchRenderPose', 'buildStereoMatrices'):
    if marker not in game_adapter:
        raise SystemExit(f'missing game adapter boundary: {marker}')

stereo_backend = (ROOT / 'src/vr/d3d9/stereo_backend.hpp').read_text(encoding='utf-8')
for marker in ('class IStereoBackend', 'DrawClass', 'drawWorldStereo', 'drawScreenSpaceStereo'):
    if marker not in stereo_backend:
        raise SystemExit(f'missing stereo backend boundary: {marker}')

renderer = (ROOT / 'src/vr/game/outrun_renderer.cpp').read_text(encoding='utf-8')
for marker in (
    'OutRunWvpRegister = 64', 'BeginSceneVtableIndex = 41',
    'EndSceneVtableIndex = 42', 'SetVertexShaderConstantFVtableIndex = 94',
    'Transpose(WorldView*Proj)', 'PresentPoseLocked',
):
    if marker not in renderer:
        raise SystemExit(f'missing OutRun renderer invariant: {marker}')

stereo = (ROOT / 'src/vr/d3d9/stereo_renderer.cpp').read_text(encoding='utf-8')
for marker in (
    'RenderFrameRingSize', 'IDirect3DDevice9Ex', 'GetAdapterLUID',
    'ResolveDirectTransport', 'StereoFailurePoseSequenceMismatch',
):
    if marker not in stereo:
        raise SystemExit(f'missing live D3D9 stereo invariant: {marker}')
for forbidden_call in ('Game::ModeControl()', 'Game::EventControl()', 'WheelFFB_ServiceSafety'):
    if forbidden_call in stereo:
        raise SystemExit(f'VR render backend must not execute game/FFB tick: {forbidden_call}')

host = (ROOT / 'vrhost/src/main.cpp').read_text(encoding='utf-8')
for marker in (
    'XR_KHR_D3D11_ENABLE_EXTENSION_NAME', 'OpenSharedResource',
    'RenderFrameReader', 'ServiceInteropProbe',
    'XrCompositionLayerProjection', 'RenderTheater',
    'DuplicateOutput', 'HostTimings',
):
    if marker not in host:
        raise SystemExit(f'missing live host invariant: {marker}')

runtime_boundary = (ROOT / 'vrhost/src/runtime/vr_runtime.hpp').read_text(encoding='utf-8')
if 'class IVrRuntime' not in runtime_boundary or 'requiredAdapter' not in runtime_boundary:
    raise SystemExit('missing host VR runtime boundary')

frame_source = (ROOT / 'vrhost/src/frame_source.hpp').read_text(encoding='utf-8')
if 'class IFrameSource' not in frame_source or 'TransportKind' not in frame_source:
    raise SystemExit('missing host frame-source boundary')

cmake = (ROOT / 'vrhost/CMakeLists.txt').read_text(encoding='utf-8')
for marker in ('src/main.cpp', 'tests/stereo_shader_smoke.cpp', 'tests/protocol_v3_smoke.cpp'):
    if marker not in cmake:
        raise SystemExit(f'host CMake missing reconstructed target: {marker}')

print('VR reconstructed architecture boundary verification passed')
