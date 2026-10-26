# QuestCockpitV2 — driver character selection is mode/provider/active-profile dependent, with a non-identity six-slot permutation (2026-10-26)

**Scope:** Independent, new read-only Quest APK research. Target: user-owned OutRun 2006 C2C / Quest3 PCVR / **MOZA R3 physical wheel**. Quest hand tracking, tracked hands and VirtualWheel steering are excluded. Existing DriverSeat is rejected and may be removed only in a separately authorized future atomic QuestCockpitV2 cutover. **No gameplay source, DLL, INI, workflow, build or deployment change.**

**Repository:** `thp32tt/OutRun2006Tweaks` branch `vr-d3d9ex-focus`, observed latest HEAD **`62db29a7bde1b95ea619411e41e20fc210a61bda`** at research pre-commit check (2026-10-26 ~20:06 KST). Concurrent automation can advance the branch. This is a new `docs/research/` file, not a DX9Ex automation result.

**Primary evidence:** Original user-owned Quest ELF `liboutrun_quest_core.so` SHA256 **`fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`**. ARM64 ELF virtual addresses below are not Windows EXE RVAs. Native GNU AArch64 objdump and ELF program-header readback on N100; original decompiled pseudocode from Ghidra is a secondary cross-check.

## New independent finding: event 362's driver *owner* is not a fixed driver *character model*

Earlier research proved the native event-slot 362/363 work-token ownership and the separate occupant forced-visible/LOD0 path. It did **not** determine how the original Quest game chooses the driver character mesh when the driver work is initialized. The original Quest function `race_robot_driver_chara_487ee0(PcRaceContext&)` (ELF **`0x39F33C`**, symbol size 444 bytes) is a **three-route character-ID selector**, and its selected value is passed to `race_robot_set_chara_487c30` at driver initialization. Thus a future V2 must not assume that event-slot identity, a single constant RobDriver mesh, or the active profile's raw slot number equals the character resource ID.

### Exact original ARM64 branch and data-flow evidence

1. **Mode-state override:** `0x39F354/0x39F360` construct guest `0x78026C`; `0x39F370` calls `PcRaceMemory::u32`; `0x39F374` compares with **3**. When equal, `0x39F37C` returns character **12 (`0xC`)**. The later provider/profile selection is not evaluated on this route.
2. **Context provider gate:** Otherwise `0x39F39C` loads a service pointer from `PcRaceContext+0x30`; `0x39F3BC` tests null (the null route throws `std::logic_error` at `0x39F44C..0x39F488`, **not** the character-11 fallback). If present, `0x39F3C0..0x39F3CC` calls its vtable **+0x30** method with an operation request containing guest `0x43F860`. `0x39F3D0` tests the **low byte** of its return; when zero, `0x39F424` returns character **11 (`0xB`)**.
3. **Active-profile index:** If provider succeeds, `0x39F3D8..0x39F3E4` read guest **`0x7C2400`** through `PcRaceMemory::u32`. `0x39F3E8` compares the unsigned index with **6**; `0x39F3EC` branches to the **`std::out_of_range` exception** at `0x39F48C..0x39F4C8` for `index>=6`. This is not clamping, modulo, or fallback character 11.
4. **Non-identity permutation:** `0x39F3F0..0x39F3FC` loads `u32 perm[index]` from native ELF rodata **`0x001A58D4`**. Direct ELF PT_LOAD virtual-address-to-file-offset mapping and six little-endian `u32` reads yielded exactly **`{0,1,2,4,3,5}`**. In particular, profile slot **3 maps to 4** and slot **4 maps to 3**. This array is in **native ELF read-only data**, unlike the next table.
5. **Guest character table:** `0x39F3F8/0x39F400` construct guest **`0x6549B0`**; `0x39F408` computes `0x6549B0+4*perm[index]`; `0x39F40C` calls `PcRaceMemory::u32` to return the actual character ID. The **six table values** at guest `0x6549B0` are **not established by this ELF-only static analysis** and must not be fabricated.
6. **Proven init consumer:** In native `race_robot_driver_init_4884d0` ELF **`0x3A0144`**, `0x3A01B0` calls `race_robot_driver_chara_487ee0@plt`; `0x3A01B4` copies return `w0` to character argument `w2`; `0x3A01C0` calls **`race_robot_set_chara_487c30@plt`**. The original selector is therefore **actually used to choose the driver character at initialization**, not a dormant helper.

The original function can be expressed as a read-only contract, **not a proposed production implementation**:

```text
if (guest_u32(0x78026C) == 3) return character_id 12;
if (context_service == null) throw logic_error;
if ((context_service.call(0x43F860) & 0xff) == 0) return character_id 11;
slot = guest_u32(0x7C2400);
if (slot >= 6) throw out_of_range;
perm = {0, 1, 2, 4, 3, 5};
return guest_u32(0x6549B0 + 4*perm[slot]);
```

### Independent cross-check, with provenance kept separate

Public PC reconstruction `r4dius/outrun2-decomp/src/platform/race_robots.cpp` independently describes the same `race_robot_driver_chara_487ee0` branches, six-element permutation, and its use by `race_robot_driver_init_4884d0`. Its `src/platform/race_robots_runtime.cpp` maps guest `0x7C23E0` to `event_function36.frontend_profiles.active` (so guest `0x7C2400` lies at **+0x20** within that mapped profile data) and guest `0x78026C` to `mode_state.current`. These are **PC reconstruction interpretations**, not a claim that the Quest APK uses an identical in-memory C++ struct or that a particular license name/character ID has been observed on HMD.

**Distinct V2 failure mode:** a port that hardcodes a driver model, uses `slot` rather than `perm[slot]`, or confuses **native event-slot 362's `work_token`** with **guest `0x7C2400` active-profile index** can attach a different character model to a correctly owned near-seat driver draw. That mismatch can affect model/skin/LOD assumptions even when W×C body correction and forced-visible/LOD0 gating are otherwise correctly reproduced. The actual visible symptom has not been reproduced.

### Read-only reproduction

N100 helpers (all outside the game repo, no gameplay modifications):
- `apk/_analysis_focus/quest_20261026_2004_driver_character_original_probe.py` — bounded ELF disassembly of `0x39F33C..0x39F4F8`; symbol cross-check.
- `apk/_analysis_focus/quest_20261026_2004_driver_character_selection_verify.py` — **12/12 original opcode/address assertions PASS**, native SHA256 check, PT_LOAD mapping, and **six rodata words equal `0,1,2,4,3,5`**.
- `apk/_analysis_focus/quest_20261026_2004_driver_init_callsite_verify.py` — native `0x3A01B0` and `0x3A01C0` call sites checked, **2/2 PASS**.

Equivalent disassembly commands:
```sh
aarch64-linux-gnu-objdump -d -C --start-address=0x39f33c --stop-address=0x39f4f8 liboutrun_quest_core.so
aarch64-linux-gnu-objdump -d -C --start-address=0x3a0144 --stop-address=0x3a01c4 liboutrun_quest_core.so
readelf -lW liboutrun_quest_core.so # translate ELF VA 0x1A58D4 to file offset, then read 6 u32
```
Test cases for a future **pure selector**: mode 3 => 12 regardless of provider; mode !=3 with valid service and low-byte-zero response => 11; with success and slots 0..5 => table offsets `0,4,8,16,12,20` bytes from guest `0x6549B0`; slot >=6 => reject/throw; null service => separate failure. Do not run this as a live game hook in REVIEW_ONLY.

### Confidence, unresolved questions, and next task

**BINARY VERIFIED:** original Quest function symbol/size, all branch conditions and return constants, rodata permutation, guest table address, and actual driver-init consumer. **INDEPENDENTLY CORRELATED:** PC reconstruction selector semantics and profile memory mapping. **UNKNOWN:** real six guest character IDs, Quest active-profile values during race, resource-to-PMT mapping, whether driver model changes mid-scene, whether event 363 shares any of these resources, Quest3 visual effect, game/HMD performance.

**Next:** identify the six guest `0x6549B0` character IDs from a trustworthy original-game memory snapshot or static guest-image mapping; trace `race_robot_set_chara_487c30`'s resource lifetime and its PMT/mesh binding. When designing the future V2, snapshot the selected character ID with event-slot owner and generation at init, then validate a new selection after profile/car/scene changes. Keep the actual implementation separate and opt-in.

**REVIEW_ONLY=YES | DOCS_ONLY=YES | SRC/DLL/INI/CI/BUILD/DEPLOY=UNCHANGED | MOZA_R3_FFB=UNCHANGED | R26+HUD=UNCHANGED | QUEST3_HMD=UNTESTED**
