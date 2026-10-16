# Quest APK evidence → new Windows PC VR mod (experimental)

Uses only verified VR behavior as design evidence, not an Android binary port.
Windows OutRun remains authoritative for physics, input, audio, FFB and assets.
Existing DX9Ex/DX11/DXVK branches are unchanged.

## Implemented
- Per-eye stereo sphere culling and immutable eye/frame generation checks.
- `ParticleStereoBatcher` combines **strictly consecutive** trusted world-space
  smoke/dust/gravel/water-spray triangle draws sharing exact material, state,
  render-target generations and frame stamps. Performs one geometry upload and
  separate physical draws to each eye; retains original transparent triangle order.
- Windows D3D9 dynamic VB adapter: DISCARD/NOOVERWRITE ring reuse, separate
  left/right eye binding callbacks, restores stream 0, Reset invalidation.
- Pre-upload rejection returns NeedsOriginal; any failed eye draw results in
  FrameInvalid (never replay original after partial output).
- Half-resolution policy helper is available for proven smoke/dust **only**;
  **no reduced-resolution compositor is implemented or enabled**.

## Build & tests
```sh
cmake -S experimental/quest_pcvr -B build-quest-pcvr -DCMAKE_BUILD_TYPE=Release
cmake --build build-quest-pcvr --config Release
ctest --test-dir build-quest-pcvr -C Release --output-on-failure
```
Local Linux Release tests: 2/2 PASS. A dedicated workflow runs Linux and
Windows MSVC builds. The C++ Win32 D3D9 adapter has no live game hook yet.

## Integration required
The game adapter must establish **positive producer identity**, copy immutable
ordered triangle command groups, and provide an `IParticleD3D9EyeBinder` that
binds/restores eye RT/depth/stencil/WVP without extra game simulation ticks.
No unknown alpha draw may be relabeled as smoke. See
[implementation and safety gates](PARTICLE_OPTIMIZATION_IMPLEMENTATION.md)
and [prior candidate audit](PARTICLE_ALPHA_OPTIMIZATION_REVIEW_20261016.md).

Status: `PORTABLE_CORE_TESTED`, `D3D9_GAME_HOOK_NOT_CONNECTED`,
`OPENXR_HOST_NOT_CONNECTED`, `RUNTIME_VALIDATION=UNTESTED`.
No FPS speedup has been measured or asserted.
