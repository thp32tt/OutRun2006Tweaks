# OutRun VR — One-click renderer architecture

## User-facing contract

The packaged development build has one normal entry point:

`START_HERE_VR_TEST.cmd`

It resolves `VR_ONE_CLICK_TARGET.json`, prepares the branch backend, launches
`OR2006C2C.EXE`, lets the game DLL auto-launch the existing x64 OpenXR host,
waits for the game/host lifecycle, seals diagnostics, and returns the real game
failure code only after the diagnostic ZIP has been produced.

Helper selectors remain diagnostic tools, not alternate setup instructions.

## Shared execution pipeline

```text
START_HERE_VR_TEST.cmd
  -> Invoke-OutRunVROneClick.ps1
  -> VR_ONE_CLICK_TARGET.json
  -> Test-OutRunVROneClickPreflight.ps1
       -> VR_ONE_CLICK_PREFLIGHT.json
  -> Select-OutRunVRBackend.ps1
  -> Run-OutRunVRTest.ps1
  -> OR2006C2C.EXE
       -> dinput8.dll
       -> AutoLaunchHost
       -> outrun-vr-host.exe (x64 OpenXR)
  -> Collect-OutRunVRLogs.ps1
  -> OutRun2_VR_ANALYZE_*.zip
```

The ZIP records the development branch, renderer target, stage, source SHA,
backend/profile, EXE identity and DXVK provider version/hash when applicable.

## DX11 development stages

Current branch: `vr-dx11-native-r71`.

The name `dx11` in the current selector still means the proven D3D9Ex game
renderer feeding the x64 D3D11 OpenXR host through DirectGPU. It is the
validation carrier while the native renderer is developed; it does **not**
mean game draws are already rendered by D3D11.

### R71/R72 — observation and bootstrap

- Native D3D11 device/target implementation exists but game draw routing is off.
- Source D3D9Ex adapter LUID is recovered.
- The native D3D11 device must be created on exactly that DXGI adapter.
- One-click performs a passive source-state/resource census.
- Unsupported D3D9 states are explicit and fail closed instead of being
  approximated.
- The common disassembly contract owns View/Projection/WorldView, c64-c67,
  SpriteNode boundaries and critical HUD/world producers.

### R73+ — renderer activation order

1. resource mirrors and fixed-function/programmatic input translation;
2. mono D3D11 draw parity on positively supported draws;
3. stereo eye targets while retaining the proven semantic classifier;
4. full HUD/world-marker/flare/menu graphics gate;
5. shared-eye D3D11 transport through the existing x64 host;
6. only after repeated parity, evaluate direct x86 OpenXR as an optional
   transport simplification.

Direct x86 OpenXR is deliberately not coupled to renderer correctness. VDXR
does ship a Win32 runtime path, and the old `vr-x86-openxr-direct-poc`
contains a useful standalone session probe, but that branch is far behind R70
and has no recorded runtime READY/FAILED result in this repository.

## Native D3D11 -> x64 host transport

A new OpenXR frame ABI is not required for the first native renderer.

The current x64 host already opens the two producer handles as
`ID3D11Texture2D` with `ID3D11Device::OpenSharedResource` and validates the
declared width, height, format, slot and generation. Therefore native D3D11 can
use the existing four-slot `SharedRenderFrameRing` / DirectGpuAck identity
contract.

`NativeSharedEyeRing` creates the matching four-slot, two-eye legacy-shared
D3D11 resource shape. Publication remains disabled until the native renderer
can prove complete stereo frames and producer GPU completion.

## DXVK development stages

Current branch: `vr-dxvk-r71-disasm`.

1. pinned stock DXVK provider;
2. stock DXVK SAFE/two-pass graphics parity;
3. Reset/menu/recenter lifecycle parity;
4. only then recover the old custom multiview ideas;
5. multiview must consume the same disassembly/semantic contract as DX11 and
   the R70 reference renderer.

The stale pre-R70 DXVK PoC is evidence, not a merge base.

## Merge gate

Neither branch is merged into the reference line merely because it builds or
runs faster. The exact runtime build must pass the graphics gate in
`docs/VR_DX11_DXVK_BRANCH_POLICY.md`, including startup, both-eye world
geometry/shadows, menu car rendering, lens flare/projected effects, HUD,
option arrows, goal/time/name, vehicle rank markers, Reset and recenter.

Unknown or unsupported rendering always falls back/fails closed until its game
provenance and translation are known.

## Runtime preflight identity

Before the selector mutates any root payload, the launcher verifies the x86 game EXE, x86 game VR DLL, x64 OpenXR host, source SHA and INI identity. DXVK runs additionally require the pinned x86 provider version and SHA-256 to match branch metadata. The resulting `VR_ONE_CLICK_PREFLIGHT.json` is copied into the diagnostic ZIP so every one-click run has an exact executable/provider identity record.
