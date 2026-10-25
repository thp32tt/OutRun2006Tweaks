# Quest APK cockpit: exact runtime provider, vehicle/occupant TLS scopes and glass-flag producer (2026-10-25 KST)

## 0. Evidence and permitted scope
- Requested **immediate forensic research** for the user's own Quest 3 OutRun 2006 APK. Target `thp32tt/OutRun2006Tweaks/vr-d3d9ex-focus`, R26+HUD. **Review-only; no gameplay source edit, no build, no HMD test.**
- User-owned ARM64 ELF `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b6`.
- `BINARY VERIFIED`: original instruction addresses, register / memory operations, symbol signatures, normal + language-unwind cleanup.
- `INDEPENDENT PC CORRELATION`: original Windows ABI `src/game.hpp` and public `r4dius/outrun2-decomp` reimplementation. They do **not** prove that every ARM64/PC operation has the same runtime scheduling.
- `UNKNOWN/UNTESTED`: exact physical seat transform, material/window polygon ID, driver/passenger skeleton, and whether the PC culling override genuinely double-applies a head pose in any hardware frame.

## 1. NEW original APK: exact attach-time GameHost → NativeRuntimeContext → render-frame callback → player/camera bytes

An ELF symbol search exposed the previously unrecognized concrete callback:

| Stage | Original ELF VADDR | Exactly observed behavior |
|---|---|---|
| Attach | `outrun::runtime::attach_pc_scene(GameHost&,NativeRuntimeContext&,RetailAssetStore&,PcD3D9Device&)` **`0x2C720C`** | Saves `NativeRuntimeContext*` in **x21**, allocates new `PcSceneRenderer` in **x20**, stores renderer in `GameHost+0x3C0` (960 bytes) |
| Callback capture | `0x2C7278..0x2C72C0` | `x25 = x21+0x91880`. Writes `std::__function` callback vtable and captured x25 onto stack, then swaps function object into `PcSceneRenderer+0x60` |
| Concrete callback implementation | **`0x2D0C10..0x2D0C3C`** | `attach_pc_scene::$_1::operator()(Bytes& vehicle,Bytes& camera)` obtains captured base, assigns two `Bytes`, returns 1 |
| Vehicle Bytes | `0x2D0C10..0x2D0C24` | `data = NativeRuntimeContext + 0x91880 + 0x16A0 = +0x92F20`, `size=0x10F0` (**4336 bytes**) |
| Camera Bytes | `0x2D0C24..0x2D0C3C` | `data = NativeRuntimeContext + 0x91880 + 0x3090 = +0x94910`, `size=0x400` (**1024 bytes**) |
| Renderer provider dispatch | `PcSceneRenderer::render_frame` **`0x10CBE9C`**, instructions `0x10CBF14..0x10CBF30` | Loads `renderer+0x80` callback object; dispatches virtual +0x30 with two output Bytes |
| Mode gating | `0x10CBF3C..0x10CBF54` | Camera Bytes `size>0x34A` and byte `camera[+0x34A]==1`; only then enable `cockpit_render_active` and body-correction production |

Original instruction excerpt (reference only; not production C++):
```text
ELF 0x2D0C10   ldr x8, [x0,#8]       ; capture NativeRuntimeContext+0x91880
ELF 0x2D0C18   add x8, x8, #0x16a0
ELF 0x2D0C20   stp x8,x9,[x1]        ; vehicle Bytes(data,+0x10F0)
ELF 0x2D0C28   ldr x8,[x0,#8]
ELF 0x2D0C30   add x8,x8,#0x3090
ELF 0x2D0C38   stp x8,x9,[x2]        ; camera Bytes(data,+0x400)
ELF 0x2D0C3C   ret
```
The **returned vehicle size** exactly equals `static_assert(sizeof(EVWORK_CAR)==0x10F0)` in the PC focus `src/game.hpp`. In the same source `offsetof(EVWORK_CAR,matrix_B0)==0xB0`, `offsetof(EVWORK_CAR,matrix_F0)==0xF0`; camera byte `+0x34A` matches `EvWorkCamera::cam_mode_34A`, while Windows camera structure is only `0x3B4` vs Quest-provided 0x400. **Do not assume the meaning of the extra bytes.**

**New implementation gate removed:** the Quest provider's concrete callable identity, memory ownership and full data lengths are now identified. A PC implementation can safely read the known original PC `EVWORK_CAR/ EvWorkCamera` equivalents after validating a stable player identity rather than inventing guest offsets.

## 2. NEW verified original vehicle TLS span, including exceptional cleanup

The **player racing-car** native renderer `PcSceneRenderer::display_race_car` ELF `0x10C8D00`:
1. `0x10C8D2C..0x10C8D54`: calls exactly the renderer+0x80 paired vehicle-camera provider used by `render_frame`.
2. Reads vehicle car model at `vehicle.data[+0x11]`, validates known range, loads car PMT banks if needed; this is a narrower provenance than scanning scene/NPC materials.
3. `0x10C9288`: reads `cockpit_render_active` TLS; `0x10C929C`: resolves `cockpit_vehicle_draw` TLS; `0x10C92AC`: **sets vehicle TLS equal to cockpit-active before rendering**.
4. `0x10C92EC`: invokes `vehicle_race_display_46bd30`, which traverses the player car model.
5. `0x10C932C`: resets `cockpit_vehicle_draw=0` after the normal vehicle display returns.
6. **Previously unrecorded exceptional cleanup:** `0x10C93F4`: also resets `cockpit_vehicle_draw=0` while the C++ unwind handler is destroying the local `PcVehicleDisplayContext`, before eventual `_Unwind_Resume` at `0x10C94EC`.

Thus the vehicle-tagging bit is temporally bounded to the **player race vehicle dispatch**, not the whole scene. This matters because naïvely testing `cockpit_vehicle_draw` at the moment of a **later queue flush** may incorrectly see zero; a per-draw descriptor flag is necessary to preserve the generation-time scope.

## 3. NEW original consumer↔producer correspondence: exact DrawEntry bit 1 for vehicle glass

**Producer — original ARM64 `render_object_405360` ELF `0x10ABC90`:**
- `0x10ABD44..0x10ABD50`: resolves TLS address `cockpit_vehicle_draw`.
- `0x10ABD7C`: `ldrb w9, [x25,x0]` reads its byte.
- `0x10ABD88..0x10ABD94`: constructs descriptor flags:
  `w8 = (argOtherFlag != 0 ? 1 : 0) | (cockpit_vehicle_draw << 1)`.
- `0x10ABDA0`: stores the constructed flag word in the stack-local draw descriptor; the `walk_404d10` callback is invoked at `0x10AC020` to create queue records.
- **Do not confuse this with the separate PMT node `flags&2` (blended-node test) in `render_queue_flush_405890` at `0x10AF778`.** These are different fields, producer sources and semantics.

**Consumer — original ARM64 `Flush::draw_404700` ELF `0x10B9894`:**
- `0x10B98F0`: sets x25 to `DrawEntry&` (from x1).
- `0x10B9F68..0x10B9F78`: reads byte `[DrawEntry+0x34] & 2`, then `DrawEntry.pass +0x20 ==1`.
- Remaining strict render-state predicates: effective destination blend getter `D3DRS20==6`, PMT diffuse alpha within ±0.001 of 0.55 or 0.425, source blend getter `D3DRS19==2 or 5`; qualifying draws set per-draw opacity 0.25 and premultiplied flag iff source blend=2, restoring after draw (see prior `QUEST_APK_GHIDRA_REBASE_COCKPIT_RECOVERY_20261025.md`).

**Queue continuity cross-check:** original ELF `render_queue_flush_405890` at `0x10AF6C4` and `0x10AF7AC` explicitly calls the same `Flush::draw_404700` for opaque/blended passes; independent PC source `r4dius/outrun2-decomp/src/platform/pc_render_queue.cpp::walk_404d10` stores the first **60 bytes** of the descriptor (including `flags+0x34`) into the `DrawEntry` queue using `memcpy`. Native ARM64 producer and end-consumer agree on the same 60-byte schema; the intermediate byte-for-byte native walk-store is *cross-correlated with independent PC code*, not an entirely proved native xref.

**Implementation consequence:** do not sample a live TLS “is cockpit car” at render-queue consumption or simply look for alpha0.55 in every material. Propagate a **player-car-owned draw identity marker** from model queue creation across buffered rendering, then combine with the exact pass/blend/material gate and exact front/side glass primitive ownership. It may be possible to clone the Quest 0.25 scoped-opacity behavior in PCVR **without patching any PMT files**, but only after verifying material identities, blend translation and shader state restoration.

## 4. NEW occupant transform is **draw matrix**, not game camera

Original `Draw::disp_514c30` at `0xD60FD4`:
- `0xD610CC..0xD610E4`: reads `cockpit_render_active` TLS.
- `0xD610E8..0xD610FC`: reads **separate** `cockpit_occupant_draw` TLS.
- If either inactive, jumps to normal draw path `0xD6128C` without using correction.
- If both active, `0xD61124..0xD61144` obtains `cockpit_body_correction[16]` TLS; `0xD61148..0xD61280` performs FP fused multiply/add of that correction with the **current guest occupant model matrix**.
- `0xD61284..0xD612A4` writes the resultant 4×4 draw matrix to stack and calls `pc_matrix_push_load` with the local matrix. The caller does **not** overwrite original game head/camera vectors with this body correction.
- This confirms the Quest cockpit improvement requires **separate scoped player-car model transform, occupant draw transform, and OpenXR eye view transform**, not a universal camera-pose offset.

Separate native `node_visible` checks occupant TLS near `0x10AA3F8..0x10AA410` and can suppress certain node visibility under a context-byte gate `+0x35`; the identity of those nodes remains unproven (avoid hiding passenger/entire car based on the byte alone).

## 5. Precise scope/restoration matrix and implementation priorities

| Owner | Enter | Exit/reset | Windows port gate |
|---|---|---|---|
| Car-camera guest provider | `attach_pc_scene` callback at `0x2D0C10`; first Bytes runtime+0x92F20 and second +0x94910 | callback returns only borrowed regions; no own data writes | capture immutable `EVWORK_CAR`/camera owner + stable frame ID |
| Body correction | render_frame native mode1 and `cockpit_render_active` | restores car `matrix_F0` **16/16** normal `0x10CC78C..D0`, exceptional `0x10CC914..68`; clears active TLS both paths | stage renderer-local `matrix_F0=identity` *only for render pass*, never change persistent simulation unless all exits guaranteed |
| Car draw flag | `display_race_car` puts `cockpit_vehicle_draw = cockpit_render_active` | 0x10C932C normal, 0x10C93F4 exception | tag player draws at producer and keep metadata after TLS reset |
| Occupant draw transform | `disp_514c30` checks both TLS flags | draw-specific matrix stack handles result | exact selected occupant/driver and passenger ownership before suppression |
| Glass draw | `DrawEntry.flags bit1 + pass1 + blend + alpha` | opacity/premult reset after draw; abnormal exit state requires further audit | qualify exact car windshield triangle+texture; preserve both eyes state |
| Eye pose | original XR validates space/view location, two views | at frame boundary, not per texture | coherent latched poseId and referenceSpaceGeneration; no double HMD injection |

**Go/no-go:** Original Quest provider identification and scope mechanics are resolved enough to implement *instrumentation and immutable-frame pure code*. Exact end-to-end physical cockpit still needs seated anchor calibration per vehicle, UI/HUD isolation, exact PMT window mesh IDs, proper driver/passenger/hand bone rig and Quest3/PC visual validation. The existing `DriverSeatView=false` safe default and R26+HUD screen fixes remain untouched.

## 6. Reproduction/analysis scripts, raw code retention
All new disassembly and ELF inspections were executed **now** on the user's N100, under `apk/_analysis_focus/`:
- `quest_vehicle_camera_callable_symbols_20261025.py` finds concrete callback symbol.
- `quest_attach_compact_20261025.py`, `quest_attach_callback_capture_20261025.py` prove capture and offset math.
- `quest_retrace_asm_ranges_20261025.py` verifies frame gate and restore AArch64 instructions.
- `quest_vehicle_tlsscope_walk_20261025.py`, `quest_vehicle_exception_cleanup_20261025.py` verify player vehicle TLS boundaries.
- `quest_glass_flag_producers_20261025.py`, `quest_glass_flag_scope_20261025.py`, `quest_object_entry_append_20261025.py`, `quest_walk_descriptor_queue_20261025.py` verify descriptor flag construction and native queue consumers.
- `quest_occupant_retrace_20261025.py`, `quest_occupant_node_scope_20261025.py` verify occupant draw-matrix/TLS branch.
- No APK/binaries/assets/raw decompiled proprietary source are uploaded to GitHub; only **original research findings and clean-room implementation instructions**.

**Result:** REVIEW_ONLY=YES; PC_GAME_SOURCE_CHANGED=NO; CI=NOT_RUN; QUEST3_HMD=UNTESTED; full behavioral equivalence=NOT_PROVEN.
