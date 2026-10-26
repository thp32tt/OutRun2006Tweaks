# Quest APK REA: complete VirtualWheel and HandEntry source-level contracts (2026-10-26, 09:04 KST direct research)

## Scope / preservation
Authorized offline research of the user's own OutRun 2006 Quest3 APK to implement a stable R26+HUD PCVR cockpit. Source `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. **DX9Ex=REVIEW_ONLY**, no game/VR source changes, no local/PC build, no GitHub Actions build and HMD runtime **UNTESTED**. Only hand-authored reverse engineering documentation/reference headers are pushed; original ELF, bulk disassembly and decompiler pseudocode remain private on N100.

Prior independent research includes `QUEST_APK_REA_CAMERA_OVERRIDE_HAND_TLSDESC_20261026.md` (camera override and `cockpit_hand_tracking` TLS). This is a separate, novel analysis of the touch/wheel bridge, the real virtual-wheel state machine and a previously unknown exact HandEntry lookup table.

## 1. Newly executed REA 6.5.0/Ghidra 12.1.4 runs

| Original ARM64 function | Original ELF address, byte extent | REA evidence ID | REA pseudocode chars | Warnings |
|---|---|---|---:|---:|
| `VirtualWheel::update` | `0x2E1E18`, 1248 B | `ev_baa70ecce97e329628fc78178effec1da63c7ec44e44882ec8cf86d8f77c9868` | 4346 | 1 (type propagation) |
| `XrSessionHost::begin` | `0x2D9B18`, 1472 B | `ev_7a3c68584ab8c2b4ad8ebfabe6c8f19a1fcd22524e2a2eca272ef022caf1e4d8` | 9677 | 1 |
| Guest `hands(PcRaceContext,...)` dispatch | `0xD6045C`, 636 B | `ev_81fcbb41eb9f08403678c45b7ab3f378c8f910ae4fed2562972bdab982f4606f` | 2714 | 18 (**not suitable for claims of full logic**) |
| `HandEntry` guest lookup lambda | `0xD62DD0`, 396 B | `ev_013976bd60a1e0c29040a2441fd031d26fd4dc91b52bd984e241bb3f97e75e82` | 2273 | 3 |

The original ELF bytes were captured with `file offset = ELF VADDR - 0x1000` in these ranges and separately SHA256-checked by the REA input. Ghidra fragment imports omit original external definitions; therefore opcode-level cross-checks are authoritative when pseudocode is uncertain.

## 2. NEW exact touch-frame path: XrRig → XrSessionHost → PadSnapshot → VirtualWheel

- **At `XrSessionHost::begin`**: `0x2D9C40` calls `xrWaitFrame`, `0x2D9C68` calls `xrBeginFrame`, `0x2D9CDC` calls `XrRig::locate`; only on successful `locate` does `0x2D9CF8` call `XrRig::locate_hands@plt (0x1221080)`. The latter function initializes `TouchFrame[+0x74,+0x75]` validity to zero at entry and populates left and right XrPosef when hand space tracking succeeds.
- The **exact direct-call site** for `locate_hands@plt` was found by decoding ARM64 `BL` immediates across ELF executable segments; caller `XrSessionHost::begin` at **0x2D9CF8**. Calls to `VirtualWheel::update@plt (0x1221BC0)` were independently found at **0x2E1A2C** within `run_game::$_2::operator() -> PadSnapshot`.
- In the pad callback before wheel update, a TouchFrame pointer is read from the callback state. ARM64 `0x2E191C..0x2E193C` assembles `std::array<WheelPoint,2>`, **each point 3 float32**, using the following memory ranges from that TouchFrame:

| TouchFrame region | Meaning in this observed input path |
|---|---|
| `+0x3C..+0x57` | first 28-byte `XrPosef`: quaternion16 + position12 |
| **`+0x4C,+0x50,+0x54`** | first wheel-hand position XYZ; assembled with D/Q loads and SIMD lane insertion |
| `+0x58..+0x73` | second `XrPosef` |
| **`+0x68,+0x6C,+0x70`** | second wheel-hand position XYZ |
| **`+0x74,+0x75`** | first and second tracked-hand validity booleans |
| **`+0x78..+0x7F`** | two `float32` grip/input-strength channels |

At `0x2E1A24`, x3 is assigned `TouchFrame + 0x74` (bool[2]), and at `0x2E1A28`, x4 is assigned `TouchFrame + 0x78` (float[2]); call `VirtualWheel::update` at `0x2E1A2C`. This makes **TouchFrame-to-wheel hand positions a verified consumer**, not merely an inferred hand pose type. In the user PC port, the analogous extractor is **research-only** `quest_touchframe_wheelpoints_recovered_20261026.hpp`.

The pad callback also checks game guest state `+0x9954==0x10` and camera byte `+0x94C5A==1` near `0x2E19D4..0x2E1A08` to decide whether to enable the virtual wheel. **Do not conflate** guest `+0x94C5A` with `EvWorkCamera::cam_mode_34A` without proving their state correspondence.

**Tracking loss caveat:** `XrSessionHost::begin` skips `locate_hands` on failure of `XrRig::locate`. The entry zeroing inside `locate_hands` consequently does not run on that frame. However `XrSessionHost::begin` copies other input/frame data through the overlapping 0x40..0x7F region before it checks XR success; **this analysis does not prove stale flags are left set, nor that they are always cleared**. PC runtime must require an independently valid current XR frame before accepting any hand points.

## 3. NEW VirtualWheel state-machine recovery: exact machine constants + hysteresis

Original `VirtualWheel::update` ELF `0x2E1E18`, native signature:
`bool update(bool enabled, array<WheelPoint,2> const&, array<bool,2> const&,
 array<float,2> const&, float referenceSteeringAngle, float referenceHeading)`.

- Native `0x2E1E44` branches early for disabled input. `0x2E1F48..0x2E1F54` clears the 2 grab bytes (`state[0,1]`), steering angle float `state[+4]` and pending-grab bytes (`state[+0x10,+0x11]`).
- Native state prefix layout **`[+0,+1]` active hand grabs**, float **`+4` accumulated steering radians**, floats **`+8,+12`** previous sampled angle per hand and **`+0x10,+0x11`** pending/candidate grab flags. This is only a prefix, *not proof of the entire object size or alignment*.
- `sincosf` rotates each WheelPoint into a wheel-local reference plane. Code adds wheel-local offsets **0.32** and **0.55**, evaluates `hypotf` distance and `atan2f` angular position.
- The native logic separately handles left/right hand eligibility using input-validity and per-hand analogue grip value. The REA decompiler shows **0.30** as hand-grip-low guard, **0.65** as higher activation grip, **0.13** distance for engaging, **0.30** distance for disengaging, and approximate wheel-heading discrepancy thresholds **0.10** (engaging) and **0.25** (release). These are independent **hysteresis thresholds**, not generic lerp gains.
- For a participating hand, it calls `remainderf(currentAngle-lastAngle, 2π)` with exact original float32 **2π = `0x40C90FDB`**. Only deltas with `abs(delta)<0.5` are accepted. Two valid hands contribute averaged accepted deltas before updating the accumulated steering angle.
- The final angle is clamped to **±1.308997035 rad** (original float32 `0x3FA78D37`, about ±75°). When neither hand is active, native code clears/centers the steer accumulator. The game-pad callback then maps `VirtualWheel::angle` into its own native steering input with additional scaling and clamping; **input/output calibration in real wheel hardware remains untested**.
- Source opcodes `0x2E1E64` `sincosf`, `0x2E1ED4`/`0x2E20F8` `hypotf`, `0x2E1EE4`/`0x2E2108` `atan2f`, `0x2E2044`/`0x2E2214` `remainderf`, `0x2E2250..0x2E2288` average/clamp. Detailed REA remains `partial` due type-propagation warning: do not claim exact physical grip thresholds are fully proven as separate named input semantics without headset measurement.

## 4. NEW exact HandEntry tables: 2×15 entries (original ELF read-only data)

`Draw::disp_514c30` ELF `0xD61D58..0xD61DA8` converts guest animation phase `guestValue - 5`, **only when index <=14**, to two different static `HandEntry` tables with **12-byte stride**.

| Role by call order (actual anatomical left/right still not proved) | ELF read-only VA | records | full original table SHA256 |
|---|---|---:|---|
| A, first `HandEntry` callback | **0x1AD558** | 15 | `14de4fbef6e2eb566fa48eef4a57d72e668549d060ae912569a2b4b68d41734f` |
| B, second `HandEntry` callback | **0x1AD4A4** | 15 | `89902bfb378237456c3aa47b80adc456aed3c696da7ab94648b44cd6101a5e87` |

Each record is `{ uint8_t requiresDynamicCall, padding[3], uint32_t sourceId0, uint32_t sourceId1 }`.
- For **both** tables: dynamic-conversion flag==1 at slots **2,3,5,7**; flag==0 at the other 11 slots.
- Slots **8,9,10,11** contain *both source IDs = 0xFFFFFFFF*, excluded by native result checks. The other 7 flag0 slots carry direct source identifiers.
- For a flag0 record, `HandEntry` lambda `0xD62DD0` returns its two identifiers directly as a packed 64-bit result.
- For a flag1 record, it constructs two guest-side calls with callback selector **0x448CD0** and each record ID separately, using a virtual dispatch callback `+0x30`; it returns their resolved 32-bit results. Normal failure / C++ exception paths appear in original ARM64.
- These 32-bit numbers can be **guest addresses, encoded identifiers or lookup arguments**, not proven anatomical bone indices. Do not label the table contents “final bone indices” before tracing the guest `0x448CD0` function to its concrete return contract and skeletal node mapping.
- Result fields are stored in the `cockpit_hand_tracking` context at offsets `+0x10C,+0x110,+0x114,+0x118` (when native conditions allow). `Draw::hand_513e40` consumes valid entries to calculate and stage a **64-byte model matrix** with `pc_matrix_push`/`pc_matrix_multiply_current` and explicit fallbacks.

The per-row numeric values are embedded in the **research-only** typed header `docs/research/quest_virtual_wheel_hand_entry_tables_20261026.hpp`, with compile-time wire-layout assertions and guest phase validity `5..19`. This is extracted table metadata, **not** a game source edit or complete author implementation.

## 5. Remaining exact implementation gaps and concrete next probes

1. `TouchFrame` → `VirtualWheel` numerical mapping now largely recovered. Verify world-unit conversion and yaw/steering sign against actual Quest3 and Wheel hardware, keep game-internal PadSnapshot branch ownership.
2. `HandEntry` 2×15 lookup is byte-verified. **Next REA target:** guest callback **0x448CD0** (Windows binary address, not AArch64): reproduce conversion to actual driver skeleton/bone data. It may require the canonical original PC EXE and player model resource lookup; existing N100 executable was already parsed for original vehicle camera ROM.
3. Determine separately who constructs/updates the `cockpit_hand_tracking` context `+0x100..+0x118`, and how it relates to the latest `TouchFrame`. The two consumers demonstrably share XR/game state but a direct copy from `TouchFrame` to that context has **not** been proven.
4. Check XR tracking-loss frame invalidation and avatar fallback with real frame traces. No evidence yet that a stale hand actually renders, and no HMD performance claims.
5. Preserve R26+HUD as stable baseline; do not force `DriverSeatView=true`, no global camera-space or glass modification.

## Audit trail and build verdict
N100 ephemeral review files under `apk/_analysis_focus/`:
- `quest_20261026_rea_wheel_hand_0905.py` → four original function REA JSON and original-byte slice evidence.
- `quest_20261026_hand_xrefs_objdump_0905.py` and `quest_20261026_touch_direct_calls_0905.py` → real native `BL` call sites.
- `quest_20261026_hand_chain_detail_0905.py` → XrSessionHost/VirtualWheel/HandEntry matrix native instructions.
- `quest_20261026_wheel_bounds_and_constants_0905.py` → original float32 bit patterns and state writes.
- `quest_hand_entry_tables_0905.py` and `quest_hand_entries_2x15_20261026.json` → bounded RO-data extraction with SHA256, not raw game files pushed to GitHub.
- Two new research-only C++ contracts: `quest_touchframe_wheelpoints_recovered_20261026.hpp` and `quest_virtual_wheel_hand_entry_tables_20261026.hpp`.

**CODE_CHANGED=NO | RESEARCH_CPP_CREATED=YES | COMPILED=NO | GITHUB_ACTIONS_BUILD=NOT_RUN | HMD_RUNTIME=UNTESTED | COMPLETE_ORIGINAL_SOURCE=NO.**


## 6. NEW cross-verification: A/B are **Pa/Gu** tables, and 448CD0 resolves object NAMES

After the initial review commit, a direct GitHub source search located the independent reconstructed original PC renderer `r4dius/outrun2-decomp`, files:
- `src/platform/rob_disp.cpp`, `src/platform/rob_disp.hpp`;
- `src/platform/object_db.cpp` and `src/platform/object_db.hpp`.

**All 30 native 12-byte table records** independently match the PC decomp's `HandsPa513ba0` and `HandsGu513a30` definitions:

| Verified Quest ELF table | Public reconstruction designation | Separate PC hand callback |
|---|---|---|
| **0x1AD558**, A | `HandsPa513ba0` | `rob_disp_hand_pa_5148f0` |
| **0x1AD4A4**, B | `HandsGu513a30` | `rob_disp_hand_gu_5148d0` |

**Important correction:** A/B are **Pa/Gu character/display variants**, NOT a left-hand vs right-hand designation. *Each* row has two handles/names for first/second hand objects. The table names and record values match external reconstructed Windows game data; semantics of the letters PA/GU need not be invented.

Previously unresolved guest callback **0x448CD0** in `HandEntry` lambda is identified by `object_db`: it delegates to the PC object-name hash lookup (`448B10`) over the game's object database. Name hash uses `h = 0x83*h + uppercase(char)`; success returns the **object handle** (resource in upper 16 bits and object in lower 16 bits), otherwise `0xFFFFFFFF`. Thus the dynamic records' numbers `0x5E****` are **EXE .rdata pointers to object-name strings**, not final bone indices.

### Exact eight name pairs from original PC executable

The name pointers from both native tables were independently decoded from the user-owned canonical PC PE `.rdata`. These are the requested hand-object *identifiers* (not original mesh geometry):

| Guest kind (5..19) | Pa 1st / 2nd object names | Gu 1st / 2nd object names |
|---|---|---|
| **7** | `TEL_DR_GH00_PA` / `TER_DR_GH00_PA` | `TEL_DR_GH00_GU` / `TER_DR_GH00_GU` |
| **8** | `TEL_DR_GH00_PA_USA` / `TER_DR_GH00_PA_USA` | `TEL_DR_GH00_GU_USA` / `TER_DR_GH00_GU_USA` |
| **10** | `TEL_DR_LH00_PA` / `TER_DR_LH00_PA` | `TEL_DR_LH00_GU` / `TER_DR_LH00_GU` |
| **12** | `TEL_DR_MH00_DF` / `TER_DR_MH00_DF` | `TEL_DR_MH00_GU` / `TER_DR_MH00_GU` |

The source hand name `TEL/TER` has left/right-like naming but a concrete mesh/rig ownership binding must be checked before asserting an anatomical interpretation. For all other kinds 5..19 the table entries are either already numeric game handles or `0xFFFFFFFF` placeholders.

Confirmed PC display memory owner: `PcRobDispState::Works` `0x8577D8 + id*0x60`, `+0x58/+0x5C` contain the two resolved hand object handles. `Draw::hand_513e40`'s matrix path can use these handles after the separate guest motion/bone lookup. This means the complete hand display port needs **object DB loaded before dynamic name resolution**, then existing motion-bone matrices; do not assume a hardcoded 32-bit name-address is itself drawable.

**Status update:** guest name-to-handle stage is now identified and cross-verified, but the actual skeletal hand-bone transform and per-vehicle avatar placement are still not fully reconstructed; headset runtime remains UNTESTED.

Public references:
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/rob_disp.cpp
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/rob_disp.hpp
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/object_db.cpp
