# QuestCockpitV2 — original robot-driver light-work mutation is **not** a model-scale hook (2026-10-26)

**Research mode:** REVIEW_ONLY; Quest3 PCVR + physical MOZA R3. No Quest tracked-hand or VirtualWheel input. No game source, INI, DLL, workflow, build or deployed artifact changed.

**Start:** 2026-10-26 16:01:41 KST. **Source-of-truth branch:** `thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus`, pinned initial HEAD `0a32d1e5bada498bada7b2e4b6b79a7285263e5e`. Concurrent DX9Ex reviews may advance this branch. **Original binary:** user's Quest `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.

## 1. Independent new finding: robot-driver draw temporarily scales a LIGHT record, not the robot mesh

The native Quest `race_robot_display_487880(PcRaceContext&,unsigned)` is ELF `0x39F9CC..0x39FD03`, 824 bytes / 206 AArch64 instructions. Original opcodes show a second mutable draw-scope distinct from both the previously traced vehicle `matrix_F0` identity staging and the `Draw::disp_514c30` occupant root model correction `W × C`:

1. **Source owner:** `0x39F9F8..0x39FA14` reads the guest current-car pointer via `PcRaceMemory::u32(0x799D18)`. At `0x39FA70..0x39FA88` the scalar **`scale = guest.f32(car + 0x58)`** is loaded into `s8`. This is a dynamic original game field, not a hard-coded `1.15` user setting.
2. **Destination owner:** The first indirect renderer service callback, staged at `0x39FA18..0x39FA68`, requests PC leaf **`0x4082B0(2,0,0)`**, `GetLightWorkAddress`, and its returned guest address becomes `w22`. This is a **light-work record**. The independent PC reimplementation's `src/platform/race_robots_runtime.cpp` routes `0x4082B0` with `b==0` to `0x899B98 + (a+c)*0xA0`; for `(2,0,0)`, the record starts at **`0x899CD8`**. The native return pointer is dynamic; this concrete VA is an independently reconstructed PC layout, not a claim about every Quest runtime allocation.
3. **Four-word exact snapshot:** Native `0x39FA7C..0x39FAC8` loads original **four u32 words** at `light+8,+0xC,+0x10,+0x14` into saved registers `w23..w26`. The first three words are re-read as floats for multiplication.
4. **Only three light floats modified:** `0x39FACC..0x39FB14` computes and calls `PcRaceMemory::putf` for **`light[+8,+0xC,+0x10] *= car[+0x58]`**. The fourth word `light+0x14` is saved but **not scaled**. This is NOT `matrix_B0`, `matrix_F0`, the robot work model matrix `work+0x10`, or the game's vehicle render transform.
5. **Scoped environment and robot calls:** `0x39FB18..0x39FB50` dispatches `SceneEnvironment 0x40D840(2)`; `0x39FB54..0x39FB90` dispatches `rob_disp_disp_514E60(work)`. The mutated light values are thus live during these two renderer calls.
6. **Normal restore and environment refresh:** `0x39FB94..0x39FBD0` writes the saved **four original raw u32 words** back with `PcRaceMemory::put32` (not recomputed reciprocal floats), then `0x39FBD4..0x39FC04` invokes `SceneEnvironment 0x40D840(2)` **again**. The second environment call occurs after the original light values are restored.

**Semantic order (native-opcode-backed, pseudocode only):**
```cpp
const uint32_t car = memory.u32(0x799D18);
const float factor = memory.f32(car + 0x58);
const uint32_t light = service(0x4082B0, {2, 0, 0});
const uint32_t original[4] = {
    memory.u32(light+8), memory.u32(light+12),
    memory.u32(light+16), memory.u32(light+20)};
for (int k=0; k<3; ++k)
    memory.putf(light+8+4*k, memory.f32(light+8+4*k)*factor);
service(0x40D840, {2});       // environment with temporary light
service(0x514E60, {work});    // robot/occupant display
for (int k=0; k<4; ++k)
    memory.put32(light+8+4*k, original[k]); // exact bits
service(0x40D840, {2});       // environment with restored light
```

**Novel distinction:** The previous V2 reports proved a right-multiplied model correction `W×C` and temporary vehicle `matrix_F0` identity, but did **not** trace this **separate, light-record mutation and two-pass environment restoration**. A Windows implementation that interprets this native `scale` as a car-mesh/driver-mesh `1.15×` transform would act on the wrong subsystem. Current legacy `src/hooks_graphics.cpp` separately scales a player-car **model matrix** in `VRDriverSeatVehicleScaleRenderHook` at `EXE RVA 0x697BD`; that is a different, explicitly rejected experiment and should not be justified by the original light-work opcode.

## 2. New conditional cleanup hazard (static, NOT a runtime bug report)

In the same native function, the visible exception cleanup `0x39FCD8..0x39FCFC` calls `__cxa_free_exception` / `_Unwind_Resume`, but **contains no `PcRaceMemory::put32` restoration of the four light words**. On a throw during either indirect renderer callback after the light values are scaled and before `0x39FB94`, the local normal restoration block is not executed. The effect on later frames depends on caller/renderer recovery and is **not proven** to manifest on Quest3. Do not assert a crash, light leak, flicker or real-world reproducibility.

For future QuestCockpitV2, the safe independent porting contract is stronger than the original native exception cleanup: either operate on a renderer-local copy of the light record and environment state, or use a non-reentrant scope guard that restores all four original raw words on **every** exit (including exceptions) and restores the environment owner. Do not add this behavior to the production renderer now.

## 3. Reproduction and cross-check

- N100 bounded **read-only** script: `apk/_analysis_focus/quest_v2_20261026_1601_light_scope_probe.py`.
- Input: original ELF hash above; `aarch64-linux-gnu-objdump -d -C --start-address=0x39f9cc --stop-address=0x39fd04`; the script asserted **206 instruction addresses** and sampled the exact source, three float writes, four raw restores, two callback sites and exception cleanup.
- Synthetic 6-factor fixtures `{0, 0.5, 1, 1.25, 2, -1}` with light values `{0.8,-0.6,0.4,123.25}` confirmed: the first three are temporarily scaled, the fourth remains unchanged, and the saved four u32 words are **bitwise identical after restoration**. These are clean-room arithmetic fixtures, **not** original Quest runtime traces.
- Independently cross-checked public PC reconstruction `r4dius/outrun2-decomp`:
  - `src/platform/race_robots.cpp::race_robot_display_487880` uses `p.car()`, `m.f32(car+0x58)`, `p.call(0x4082b0,{2,0,0})`, three `putf` writes, `0x40d840`/ `0x514e60`, four `put32` restores, and second `0x40d840`.
  - `src/platform/race_robots_runtime.cpp` maps the `GetLightWorkAddress` service to the original PC environment light-work array.
- Direct native disassembly is primary proof; independent PC reconstruction is a secondary check and is not original authored Quest source.

## 4. Implementation boundary and next independent research

**Proposed V2 separation:** keep three unrelated scopes and their owners explicit: `vehicle matrix_F0` temporary identity; `occupant model W×C` only under both cockpit TLS gates; `robot light-work(+8,+C,+10)` temporary scale and exact raw restore. Preserve `SceneEnvironment` reapplication after the light scope. Do not reintroduce the legacy `DriverSeatVehicleScale=1.15` hack, alter car physics, wheel FFB, global scene lighting, glass alpha or the HMD view basis.

**Next:** verify whether the original PC/Quest robot-driver display path is entered during the same native mode-1 player-car callback and whether `0x40D840` synchronously consumes the modified light work or queues a copy; trace actual draw owner and event ID before deciding whether a new V2 light scope is needed. Inspect exception unwinding with a bounded native test only if justified; do not induce faults in the user's gameplay.

**Uncertainty:** native light-record mutation and normal restoration are BINARY VERIFIED. PC address mapping is independently CORRELATED. Exception-side missing *local* restore is STATIC CONDITIONAL. Real frame frequency, visual impact, Quest3 HMD output and Windows PCVR parity are **UNTESTED**.

**CODE_CHANGE=NO | R26+HUD=UNCHANGED | HAND_TRACKING=OUT_OF_SCOPE | MOZA_R3_FFB=UNTOUCHED | CI=NOT_RUN | QUEST3_HMD=UNTESTED**.
