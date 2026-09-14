from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    'src/vr/settings.cpp',
    'src/vr/game/outrun_renderer.cpp',
    'src/vr/d3d9/stereo_renderer.cpp',
    'src/vr/ipc/protocol.hpp',
    'src/vr_shared.hpp',
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

protocol = (ROOT / 'src/vr/ipc/protocol.hpp').read_text(encoding='utf-8')
for marker in (
    'SharedProtocolVersion = 2', 'RenderFrameProtocolVersion = 2',
    'RenderFrameRingSize = 4', 'HostAdapterLuidValid',
    'clientInteropProbeHandle', 'hostInteropProbeAckToken',
    'SharedRenderFrameRing',
):
    if marker not in protocol:
        raise SystemExit(f'missing protocol invariant: {marker}')

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
    'ResolveDirectTransport', 'OpenXR LOCAL-space metres',
):
    if marker not in stereo:
        raise SystemExit(f'missing D3D9 stereo invariant: {marker}')
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
        raise SystemExit(f'missing host invariant: {marker}')

cmake = (ROOT / 'vrhost/CMakeLists.txt').read_text(encoding='utf-8')
if 'src/main.cpp' not in cmake or 'tests/stereo_shader_smoke.cpp' not in cmake:
    raise SystemExit('host CMake still points at prototype entrypoints')

print('VR architecture boundary verification passed')
