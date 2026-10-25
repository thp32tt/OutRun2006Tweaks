# Quest APK cockpit deep recovery — camera override setter and hand rig TLS producer/consumer (2026-10-26)

## Provenance and status

Research on user-owned Quest APK `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Tools actually executed on N100: REA **6.5.0**, Ghidra **12.1.4**, `readelf -Ws/-rW`, read-only ARM64 ELF disassembly, custom **AArch64 ADRP/GOT TLS reference scan**. Prior REA/Quest/PC reports remain applicable, except the earlier “override always zero” inference is superseded as explained below. No modifications to `src/`, no CI, no headset test.

### Newly generated REA evidence

| Original ELF function | Address/size | Verified REA Evidence ID | REA pseudo characters / warnings |
|---|---|---|---|
| `run_game::$_5::operator()(PcRaceCameraInputs&)` | `0x2E3664` / 124 bytes | `ev_58ae0041f7fb011b01bcd072aa0644918c67053ef02bbe3bc87a12c0d0a9a857` | 850 / 2 |
| `run_game::$_0::operator()(unsigned, unsigned)` | `0x2E315C` / 656 bytes | `ev_6aed23e5e809b20dc867d1d209ed5fb1980820be203573c9ddc1510aba6889d8` | 3052 / 3 |
| `Draw::hand_513e40` | `0xD62F5C` / 2912 bytes | `ev_febd97a27ede30d0f789562871ea639dca79aad19d8bd191174fbe913fa8ca8d` | 15420 / 3 |

All three returned REA exit code 0, and the raw slices are SHA-verified privately. REA pseudo-C carries control-flow warnings due to missing external code; **original ARM64 is authoritative**.

### 1. CRITICAL NEW FINDING — exact producer of optional 3-float seat-camera override

Prior original ARM64 `PcSceneRenderer::invoke` initializes its camera input prefix first byte to zero at ELF `0x10C71F4`. Previously `attach_pc_scene::$_7` was analyzed; that adapter does not set prefix+0. This does **not** mean the optional coordinate override can never be used.

A **second callback** belonging to `run_game(android_app*)`, `run_game::$_5` at ELF `0x2E3664`, **does write all four override fields**. Exact original opcode flow:

1. `0x2E3674..0x2E3688`: obtains `capture+0x30`, calls its vtable +0x30. Failed result → returns false without writing the optional prefix; null callable → throws `bad_function_call`.
2. `0x2E3690..0x2E36B4`: reads toggle byte through `capture+0x40`. When toggle is nonzero, reads 32-bit guest state from `[capture+0x48] -> +0x9954`; sets `enabled = (guestState==0x10)`. When toggle is zero, `enabled=0`.
3. `0x2E36B4..0x2E36C8`: reads a captured coordinate triple through `capture+0x50` and writes `PcRaceCameraInputs[+0x00] = enabled`; copies 3 floats into `+0x04/+0x08/+0x0C` **on any upstream-success path**, even if enabled==0.
4. `0x2E36CC`: forwards upstream success return bit0. The later `race_camera_eye_look_485590` checks prefix+0 in its original view1 branch, using the new XYZ only if nonzero.

**Recovered narrow semantic contract** (see separate C++ reference file `quest_camera_override_and_hand_dispatch_recovered_20261026.hpp`): successful upstream camera callback; `input.enabled = questToggle && guestGameState == 0x10`; `input.xyz[0..2] = capturedXYZ`. Previous documentation suggesting permanently disabled override **must be corrected**. Activation in a particular user's APK session/HMD is still untested; this is a reachable native branch, not a runtime observation.

### 2. NEW — native driver/hand callback scoped TLS transfer

ELF source `run_game::$_0` at `0x2E315C` is a guest-to-native `bool(unsigned,unsigned)` renderer callback.

- `0x2E3198..0x2E31E0`: checks `guestReady`, `(guestStateFlags | 2) == 0x12`, **guest draw callback ID `0x4879B0`**, and one camera-mode byte in game state `+0x94C5A == 1`. All conditions are statically observed branch predicates. The exact game object labels still require guest-structure proof.
- `0x2E3200..0x2E3210`: evaluates an argument-to-guest-value equality. When satisfied the callback selects a captured context pointer at closure `+0x50`; otherwise selects null.
- ELF dynamic symbol `outrun::platform::cockpit_hand_tracking`: **8-byte TLS pointer, TLS offset `0x10338`**, `R_AARCH64_TLSDESC` GOT **`0x12588A8`** and optional TLS-init GOT `0x12588A0`.
- `0x2E3250..0x2E3264`: resolves this TLS descriptor and **temporarily installs the selected pointer** in thread local memory. `0x2E3328..0x2E3340`: on normal callback return clears the pointer to null and clears separate `cockpit_occupant_draw` TLS (GOT `0x12588B8`), avoiding stale per-draw state.
- `0x2E32C4..0x2E3310`: updates `cockpit_occupant_draw` depending on game-state and relative player/driver identity before invoking the dynamically configured output callback at `0x2E3314..0x2E3324`. **Do not reuse cockpit player hand scope for unrelated NPC draws.**
- Exception unwinding exists at the later tail `0x2E33B8+`, but a full all-path TLSDESC restore proof was **not** completed here. Do not claim every nested/exception path restores the exact prior TLS pointer.

### 3. NEW — actual hand draw consumes that TLS; it is not merely raw OpenXR pose

Previously `XrRig::locate_hands` was found to write `TouchFrame[+0x74/+0x75]` hand-valid booleans. New original-ELF cross-references prove the next layer is *not the same frame layout*:

| Function and native site | Exact observation |
|---|---|
| `Draw::disp_514c30` `0xD61D28..0xD61D48` | Resolves the `cockpit_hand_tracking` TLS pointer; checks null; reads a cached guest-state value at **trackingCtx+0x108** and compares with current guest `[sp+28]`. |
| `Draw::disp_514c30` `0xD61D58..0xD61DE4` | Builds up to four `HandEntry`-derived indices from a private entry table and stores them at `trackingCtx+0x10C/+0x110/+0x114/+0x118`, with conditional bypass for invalid values. |
| `Draw::disp_514c30` `0xD61DE8..0xD61E18` | Reads two state flags at **trackingCtx+0x102/+0x103** and selects which stored indices are used later. |
| `Draw::hand_513e40` `0xD62FF4..0xD63018` | Reads TLS through GOT `0x12588A8`; checks pointer and **validity byte at trackingCtx+0x100+slot**; without both it skips hand-specific transform path. |
| `Draw::hand_513e40` `0xD6301C..0xD63078` | Calls `pc_matrix_push`, obtains guest hand bone/transform matrix in **64-byte blocks**, multiplies `PcMatrixStack::current` and uses model source **guest offset +0xB0**. |
| `Draw::hand_513e40` `0xD63084+` | Reads successive float fields from guest/model matrices and computes the local hand transform; full joint mapping and hand-to-wheel relationship still require further evidence. |

The native `Draw::hand_513e40` first bounds-checks a count from guest memory `param_2+0x68`, selects an index and uses stride **0x350** bytes for hand/driver frame records. When tracking is not active, the function can fall through to a separate normal path. **Do not equate `TouchFrame+0x74` with `trackingCtx+0x100`; intermediary data layout/producer remains unproven.**

### 4. Distinct TLS xrefs and confidence

A private AArch64 disassembly-independent scanner inspected original executable `ADRP` / `LDR [GOT]` pairs and mapped:

- `cockpit_hand_tracking` `0x12588A8`: actual instructions in **`run_game::$_0` `0x2E3250`**, **`Draw::disp` `0xD61D28`**, **`Draw::hand` `0xD62FF4`**. These are byte-level checks, not guesses from similar symbol names.
- `cockpit_occupant_draw` `0x12588B8`: in the game wrapper and occupant model draw.
- `cockpit_vehicle_draw` `0x1259030`: in `display_race_car`, queue object writers, morph and palette paths.

Output remains local: `apk/_analysis_focus/quest_20261026_cockpit_hand_tls_xref.json`.

### 5. Implementation contract and tests (not yet a runtime patch)

The accompanying clean-room C++ file `docs/research/quest_camera_override_and_hand_dispatch_recovered_20261026.hpp` defines:
- a 16-byte `CameraInputOverridePrefix` with `static_assert` offsets +0,+4,+8,+12,
- `QuestCameraOverrideEnabled(toggle,guestState)` and a success-only override writer,
- `IsQuestCockpitDriverDispatch(guestReady,guestState,callbackId,cameraMode)`, and
- named tracking-context validity slot offsets `0x100+slot`, **distinct from OpenXR TouchFrame**.
The source is **not compiled** and **not linked into the PC game**. Its compile-time asserts document the expected semantics; they are not a verified CI or runtime result.

**Safe PCVR porting order:** first establish actual quest-side trackingCtx owner and camera input override setting; next synchronize immutable player/car/mode/XR frame state; then port model hand transform with matrix/bone fixtures. Do **not** flip `DriverSeatView` default true, expand hand animation to non-player cars or modify render production until the remaining runtime checks pass.

**Unresolved:** full original authored C++, runtime activation and recenter timing, concrete model joint mapping, TouchFrame→trackingCtx copy/translation, exact cockpit per-car origin/IPD scale, glass mesh identification, hand/wheel interaction and HMD results.

`DX9Ex=REVIEW_ONLY; SOURCE_CHANGED=NO; GH_ACTIONS=NOT_RUN; RUNTIME_VALIDATION=UNTESTED`.
