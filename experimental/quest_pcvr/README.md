# Quest-evidence PCVR — independent prototype (NOT a playable mod yet)

This is a **new Windows PCVR mod design based on *observed VR behavior* in the
user's Quest OutRun APK**, not an ARM64-to-x86 executable port. It was branched
from \`master\` to keep the ongoing DX9Ex / DX11 / DXVK VR work unchanged.

## Current functional scope
- C++17 independent portable stereo sphere/frustum visibility with **separate
  OpenXR per-eye pose and asymmetric angular FOV**; conservative radius margin.
- Unknown/nonfinite/invalid scene geometry returns Unknown and **is drawn**, not culled.
- Eye frame stamp validator rejects stale reset/session generations, mixed frame
  IDs, mixed pose samples, missing or aliased eye resources.
- No original APK code/binaries/assets or Ghidra pseudocode included.
- Linux Release CMake/CTest baseline: PASS (1 CTest case, 15 explicit checks).
  This proves only portable functions, not Windows hooks, HMD stereo, or accuracy
  of Quest-to-PC coordinate scale.

## Compile independently
\`\`\`sh
cmake -S experimental/quest_pcvr -B build-quest-pcvr -DCMAKE_BUILD_TYPE=Release
cmake --build build-quest-pcvr
ctest --test-dir build-quest-pcvr --output-on-failure
\`\`\`

## Integration to be built, not claimed
1. **Win32 game adapter** (original Windows game still runs simulation exactly once)
   and D3D9 draw interception/state capture. Only per-eye GPU draw is repeated.
2. **64-bit Windows OpenXR / D3D11 host** for session, predicted time,
   independently acquired XR swapchain images, render pose, eye FOV and submit.
3. **GPU handoff** between x86 D3D9Ex game and x64 D3D11 runtime, explicit adapter
   and device-generation ownership. Unknown draw states fail closed.
4. **Near-player / cockpit** seat anchor + head pose, player-only occupant
   suppression and glass blend verification.
5. **HUD** 2D producer/queue taxonomy and stage marker placement; no indiscriminate
   double-eye HUD replay.
6. **Effects** per-eye flare / stencil shadow, state reset preservation and
   independent GPU performance instrumentation.

The numeric 0.1 sphere margin was observed in the Quest disassembly, but its
PC-game unit equivalence is **UNVERIFIED**, so this path must remain opt-in until
real HMD A/B and PC coordinate checks. Target image identity must describe
the actual session+swapchain+image object, not an image index reused by eyes.

**Status:** PORTABLE_CORE_TESTED, Windows DLL / x64 XR host NOT_IMPLEMENTED,
Quest 3 / Virtual Desktop **RUNTIME_VALIDATION=UNTESTED**.
Refer to [VR-only adoption plan](VR_ONLY_ADOPTION_PLAN.md).
