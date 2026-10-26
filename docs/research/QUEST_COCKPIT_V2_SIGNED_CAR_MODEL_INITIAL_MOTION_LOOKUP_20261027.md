# QuestCockpitV2 — initial driver motion is indexed by a **signed car-model byte**, not the selected driver character (2026-10-27)

**Task:** `QUEST-COCKPIT-V2-20261027-0008-SIGNED-CAR-MODEL-MOTION`  
**Started:** 2026-10-27 00:08:38 KST. **Mode:** REVIEW_ONLY; one independent native static finding, no production edits.  
**Pinned branch HEAD before commit:** `thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus` = `f1d60a37a53dbf158890e074d074cb548b88bbcb`. This is a source snapshot, not a promise that concurrent automation cannot advance HEAD.  
**Binary:** user-owned Quest `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Addresses below are **Quest ELF virtual addresses**, not Windows EXE addresses.

## New independent finding

The original `race_robot_driver_init_4884d0` at Quest ELF `0x3A0144..0x3A05E8` has **two independent driver initialization channels**:
1. `0x3A01A8` calls `race_robot_common_init_487810`, `0x3A01B0` calls `race_robot_driver_chara_487ee0`, and `0x3A01C0` passes that **profile/mode-selected character ID** to `race_robot_set_chara_487c30` (already investigated in previous reports).
2. **After character selection**, the same function reads a **different byte from the active car** to select the **initial motion resource**. The byte is interpreted as a **signed int8**, not uint8, and indexes a 32-bit guest table with a signed scaled offset.

### Exact native provenance and opcode evidence

| ELF instruction | Verified operation | Meaning |
|---|---|---|
| `0x3A016C`, `0x3A0180` | `mov w1,#0x9d18; movk w1,#0x79,lsl#16` | Build guest address `0x799D18`. |
| `0x3A0198`, `0x3A019C` | `bl PcRaceMemory::u32; mov w22,w0` | Read active car guest base into `w22`. |
| `0x3A01D4`, `0x3A01F4` | `add w1,w22,#0x11`; `bl PcRaceMemory::at` with size 1 | Resolve **car+0x11** as a one-byte guest-memory view. |
| **`0x3A01F8`** | **`ldrsb w8,[x0]`** | **Sign-extend the car model byte** to 32-bit signed index. |
| `0x3A01FC`, `0x3A0204` | `mov w9,#0xb80; movk w9,#0x5c,lsl#16` | Build guest motion-table base `0x5C0B80`. |
| **`0x3A0208`** | **`add w1,w9,w8,lsl#2`** | Compute `0x5C0B80 + 4 * int8(car[0x11])` (32-bit wrap semantics). |
| **`0x3A020C`** | **`bl PcRaceMemory::u32`** | Read the motion resource ID from that guest address. |
| `0x3A0214`, `0x3A0238` | `mov w8,w0; str w8,[sp,#24]` | Place fetched motion ID in the native command payload. |
| `0x3A021C`, `0x3A0220`, `0x3A024C` | command ID `0x4F2280`, payload write, service `blr x8` | Submit **SetMotion** using the table-selected ID. |

**No range comparison/clamp appears between the `ldrsb` and the table `u32` call.** That is a statement about this bounded native function only: guest memory mapping or earlier car validation may reject invalid values, and valid runtime model indices are not yet established.

Consequently, a clean V2 port must **not use the character/profile ID as the motion-table index** and must **not replace `ldrsb` with `ldrb`**. These are independent source values: `driver character = profile/mode selection`; `initial motion ID = motion_table[signed car model byte]`.

### Bounded arithmetic fixtures (NOT observed live car models)

| Raw `car+0x11` byte | Signed index | Original computed guest address | Incorrect unsigned address |
|---|---:|---|---|
| `0x00` | 0 | `0x5C0B80` | same |
| `0x01` | 1 | `0x5C0B84` | same |
| `0x7F` | 127 | `0x5C0D7C` | same |
| `0x80` | -128 | `0x5C0980` | `0x5C0D80` |
| `0xFE` | -2 | `0x5C0B78` | `0x5C0F78` |
| `0xFF` | -1 | `0x5C0B7C` | `0x5C0F7C` |

These negative cases show a **conditional lookup-provenance risk**, not proof that a real car has an invalid model byte or that Quest crashes. A byte below `0x80` has the same signed/unsigned address. The true table bounds and valid model-ID domain must be established before choosing a validation policy for V2.

## Independence from prior work

- `QUEST_COCKPIT_V2_DRIVER_CHARACTER_PROFILE_PERMUTATION_20261026.md` proves the **profile-to-character** permutation; it does not establish the **car-model-to-motion** lookup.
- `QUEST_COCKPIT_V2_DRIVER_CHAR_SIGNED_BYTE_BONE_KIND_20261026.md` proves **signed character ID** normalization inside SetChara, a **different field and different table**.
- `QUEST_COCKPIT_V2_CANONICAL_PC_GUEST_DRIVER_TABLE_PROVENANCE_20261026.md` proves six PC **character** table entries, not this `0x5C0B80` motion table.
- `QUEST_COCKPIT_V2_SETCHARA_PREWRITE_NULL_SERVICE_ATOMICITY_20261026.md` concerns **write-before-null-service failure atomicity**, not motion-resource selection.
- The independent public PC reconstruction `r4dius/outrun2-decomp/src/platform/race_robots.cpp` separately models `model_of(car)` as `int8(m.u8(car+0x11))` and calls `SetMotion(m.u32(model_of(car)*4+0x5c0b80))`. It is a **secondary consistency check**; the Quest ELF above is the primary evidence.

## Reproduction and verification

Read-only helper on N100, outside the GitHub game source tree:  
`apk/_analysis_focus/quest_v2_20261027_0008_signed_vehicle_model_motion_verify.py`

It SHA-checks the ELF, disassembles only `0x3A0144..0x3A0250` using AArch64 GNU objdump, asserts **19 exact native address/opcode/operand anchors**, verifies the absence of a local index-range branch between `ldrsb` and table read, and evaluates all **256** possible raw-byte address computations. **Observed: ELF SHA PASS, 19/19 opcode anchors PASS, 256/256 arithmetic fixtures PASS.** No game process, VR device, native render, GitHub Actions or Windows build was run.

Manual equivalent:
```sh
aarch64-linux-gnu-objdump -d -C --start-address=0x3a0144 --stop-address=0x3a0250 liboutrun_quest_core.so
```
Follow `u32(0x799D18) -> car`, `PcRaceMemory::at(car+0x11,1)`, `ldrsb`, `0x5C0B80+4*index`, `PcRaceMemory::u32`, and SetMotion command `0x4F2280`. Compare to the public reconstruction's `model_of` helper only after confirming the original instruction chain.

## Future clean-rebuild contract and next work

In a separately authorized **complete replacement** of legacy DriverSeat with QuestCockpitV2, preserve separate typed values for event-slot work token, driver character ID, signed vehicle model index, motion resource ID and bone kind. Before any table access, validate the *known valid car-model domain and guest mapping* rather than assuming `0..255` or silently clamping an unknown negative model. Preserve original animation timing and avoid touching MOZA R3 physical steering/FFB. Quest tracked hands, VirtualWheel and Touch steering are **out of scope**; this is the game's driver avatar animation selection, not hand tracking.

**Next independent investigation:** establish the actual `0x5C0B80` motion-table size/content from the owned PC executable/Quest guest memory and find all writers/validators of `car+0x11`; determine whether negative signed values can reach `race_robot_driver_init_4884d0`. Do not count the same signed-byte lookup again.

**CONFIRMED:** original binary hash, signed-byte source and lookup, two independent character-vs-motion channels, lack of in-function clamp in this range. **UNCONFIRMED:** valid runtime car model domain, table bounds, motion resource contents, exception behavior for out-of-domain models, visual avatar impact. **QUEST3_HMD=UNTESTED; GAME_RUNTIME=UNTESTED.**

**REVIEW_ONLY=YES | DOCS_ONLY=YES | SRC/DLL/INI/BUILD/DEPLOY=UNCHANGED | MOZA_R3_FFB=UNTOUCHED | HAND_TRACKING/VIRTUALWHEEL=EXCLUDED | R26+HUD=UNCHANGED**
