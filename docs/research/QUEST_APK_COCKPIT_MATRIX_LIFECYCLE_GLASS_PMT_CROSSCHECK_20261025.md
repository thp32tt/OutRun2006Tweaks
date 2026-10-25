# Quest APK cockpit: verified 4×4 guest-camera neutralization, recovery lifecycle, and glass candidate cross-check (2026-10-25 20:22 KST direct session)

## Provenance, validation, scope
- User-owned native offline Quest APK: `/home/chatgpt-runner/apk/outrun2.apk`; unpacked ELF `apk/_static_out/liboutrun_quest_core.so`.
- SHA-256 **fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6**, checked again in this session against binary bytes.
- Builds on, without rescoring, the earlier source analyses `QUEST_APK_COCKPIT_GLASS_FULL_TRACE_20261025.md` and `QUEST_APK_GHIDRA_REBASE_COCKPIT_RECOVERY_20261025.md`.
- New work: targeted AArch64 opcode analysis + independently executed invariant verification on both normal/unwind paths + offline PMT candidate filtering. No game/runtime source edit, no APK model patch, no build, **HMD_RUNTIME_VALIDATION=UNTESTED**; Ghidra pseudo-C is not original authored source.
- N100 script and evidence: `apk/_analysis_focus/quest20261025_ledger_trace_v2.py`, `quest20261025_matrix_glass_v2_native.json`, `quest20261025_identity_verify.py`, `quest20261025_matrix_lifecycle_verify.py`, `quest20261025_matrix_lifecycle_verified.json`, `quest20261025_material_gate_compare.py`; ARM64 raw and C-like dumps stay on N100. This document includes behavioral observations, not copyrighted binaries or a copy of generated decompiler output.

## NEW 1. Exact guest matrix temporary identity sequence (binary-verified)
Function `PcSceneRenderer::render_frame` at ELF **0x10CBE9C**, Ghidra rebased **0x11CBE9C**. Several consecutive gates before this subpath:
1. `(frameArg & 0xFFFFFFFD) == 0x10` at 0x10CBEEc–0x10CBEFC. This admits values 0x10 or 0x12, not arbitrary gameplay states.
2. `renderer[0x2AD4] != 0` at 0x10CBF08–0x10CBF10.
3. `renderer[0x80]` must exist and its virtual getter at vtable +0x30 return valid guest data at 0x10CBF14–0x10CBF38.
4. The guest camera control Bytes length must exceed **0x34A**, and byte `guestControls[0x34A] == 1` at 0x10CBF3C–0x10CBF54.
5. Under this mode the function sets a cockpit TLS active flag at 0x10CBF58–0x10CBF68, reads the guest render-matrix floats around offsets **0xB0..0x12C** into registers, computes a **separate 16-float cockpit body correction**, and writes that TLS matrix using eight adjacent `stp s,s` at **0x10CC2E0–0x10CC2FC**. Exact layout and multiplication semantics still need independent proof before PC porting.

**Previously not recovered: before issuing frame rendering, the same function actively overwrites the live guest frame's 4×4 matrix at offsets 0xF0..0x12C with the 4×4 identity matrix.** At 0x10CC2BC–0x10CC2DC it constructs a bytewise identity writer:
- loop begins at offset `0xF0`, increments by **4 bytes**, stops when offset reaches **0x130**, i.e., exactly **16 float32 elements**;
- for element `i` the code computes `(uint32_t(i * 0xCCCCCCCD) < 0x33333334)`. Exhaustively checked for `i = 0..15`: predicate is true only at indices **0, 5, 10, 15**;
- it writes low two bytes as zero and bytes 2/3 from either `0x3F800000` (float **1.0**) or zero, little-endian. Consequently all 16 float32 entries are precisely 0/1 in identity order, independent of row- versus column-major nomenclature;
- disassembly: **0x10CC300–0x10CC36C**, especially integer multiply `0x10CC32C`, unsigned comparison `0x10CC338`, `csel` `0x10CC340`, and four byte stores `0x10CC328/33C/354/368`.

Validated pseudocode for the observed storage operation (NOT literal APK source):
```cpp
// Only in the gated Quest mode-1 render-frame path.
float savedGuestTransform[16] = load_f32x16(guestFrameBytes + 0xF0);
float cockpitBodyCorrection[16] = compose_from_game_frame_components(/* not fully solved */);
setThreadLocalCockpitBodyCorrection(cockpitBodyCorrection);
for (unsigned i = 0; i != 16; ++i)
    store_f32(guestFrameBytes + 0xF0 + 4*i, (i%5==0) ? 1.0f : 0.0f);
submitScopedFrameRender(); // actual calls and lifetime are more complex
// Explicit restoration on both traced success/unwind edges; see below.
```

## NEW 2. Normal and exception paths restore the **same full 16 slots**
After frame renderer invocation `frame_render_449050` at ELF **0x10CC718**, both paths restore all 16 matrix entries:
- **Normal cleanup:** `0x10CC78C–0x10CC7D0`, `stp/str` to `[x22,#240..300]`, i.e., game +0xF0..+0x12C.
- **Unwind/exception cleanup:** `0x10CC910–0x10CC968`, same 16 addresses.
- **Both** end with TLS `cockpit_render_active` reset to zero: normal `0x10CC7D4–0x10CC7E4`, exceptional `0x10CC96C–0x10CC97C`; the latter proceeds to `_Unwind_Resume` at `0x10CC994`.
- Only assert what was observed for these two reachable cleanup regions; do not infer safety for an unknown out-of-process crash or a hypothetical longjmp bypassing language unwind.

The independent `quest20261025_matrix_lifecycle_verify.py` parses original objdump range-scoped stores and asserts exact `[0xF0,0xF4,...,0x12C]` set coverage **on both paths**, no duplicates, as well as all 4 identity diagonal indices. Program outcome: `normal_full_coverage=true`, `exception_full_coverage=true`, `identity_verified=true`. This is verified **compiler-visible renderer frame transformation lifecycle**, not a guessed offset, and matters for multi-view shaking. 

**PCVR reproduction implication (PROPOSED, not tested):** preserve immutable camera values for the whole XR frame, generate the cockpit/body correction from one game-frame snapshot, temporarily neutralize only the same owned guest matrix during correctly scoped in-car rendering, guarantee restoration on all exits, and apply HMD left/right views separately exactly once. Do not blindly mutate PC memory at these numeric offsets because the Windows data schema and downstream render orchestration differ. `DriverSeatView=false` remains the stable default until a Quest3 real runtime comparison is available.

## NEW 3. Runtime glass gate vs PMT broad static candidates
The exact `Flush::draw_404700` dynamic gate from prior ASM has material alpha `abs(alpha - 0.55) < 0.001 || abs(alpha - 0.425) < 0.001`, plus `DrawEntry[0x34]&2`, `DrawEntry[0x20]==1`, effective `DESTBLEND(20)==6`, and `SRCBLEND(19)` 2 or 5. Qualifying per-draw opacity scalar is **0.25** with TLS reset to 1.0 after draw; no global glass alpha intervention. Binary gate site `0x10B9F68–0x10BA05C`; draw/reset `0x10B9C64–0x10B9CA0`.

The original user's local PMT strict signature inventory `apk/_quest_strict_glass_catalog.py` was **actually rerun** against the 1.49 GB user APK in this session:
- **31 player-car PMT variants**, **48 dark/tinted material candidates** satisfying broad offline signature.
- Applying just the exact source-alpha subset of the native runtime predicate, **47/48** pass (in **31/31 models**).
- The extra **one** broad offline candidate **does not** qualify for the native 0.55/0.425 code path: `obj_plcar_f50_pmt.sz`, object 0, material 3, PMT RGBA `[0.4,0.4,0.4,0.5]`. This specifically contradicts treating every broad PMT candidate as a native 0.25-opacity draw.
- This filtering is *necessary but not sufficient*: no ownership check, real effective render-state 19/20 state, alpha-tested mesh face or texture polygon identity is confirmed from static PMT alone. PMT attribute blend nibble encoding `(1,5)/(4,5)` is not automatically the same enumeration as effective D3D9 device render state 19/20.

Conservative per-draw reproduction spec:
```text
same player-owned vehicle + identified front/side window geometry + effective blend state
  -> exact native alpha tolerance; no broad offline alpha predicate
  -> scoped TLS opacity and premult flag; one draw per eye
  -> exact postdraw restore, texture/depth/blend state preserved
```
Do not run or install bulk PMT alpha edits from just these results.

## NEW 4. Ghidra oversize root cause checked; no unsupported success claim
The previous Ghidra project uses an ELF-to-Ghidra base delta **+0x100000**, which solved literal `halt_baddata` but 2 short 536-byte functions still yielded 106,845 and 94,745 C-like characters with PIC/CFG warnings.

A new function-scope diagnostic showed Ghidra's persistent image has 1-byte function-body placeholders before temporary repair, and the target camera switch has **10/10 unresolved PLT callee functions**, guest object render **6/12** external call targets unresolved (observed on the isolated in-session bodies). ELF `.plt` spans **0x1220130–0x1235DE0**, with 16-byte jump stubs (not source function bodies). A further trial explicitly defined the affected 16-byte PLT callees as Ghidra functions in a **read-only project session** and decompiled again:
- Camera 106845 → **106845** characters, 24 warnings unchanged.
- Guest object 94745 → **94745** characters, 21 warnings unchanged.

**Therefore merely defining missing PLT call boundaries DID NOT resolve the oversized pseudo-C.** The unresolved PIC/control-flow interpretation cannot honestly be declared fixed. Restrict claims about these two original algorithms to exact AArch64 bounded instruction edges. The protected original Ghidra project and game source were not modified by this trial.

## Completion criteria NOT met
- [x] Verified mode gating, guest camera matrix neutralization, both restorations, normal/unwind TLS lifecycle.
- [x] Validated exact glass alpha numerical gate and identified one false-positive PMT catalog member.
- [ ] Algebraically reduce all 16 cockpit correction matrix components to an independently testable convention (+ coordinate system, inverse/order, units).
- [ ] Recover model-specific player cockpit seat offset, tracking-to-vehicle fusion and temporal ownership; verify 1/2/3 camera views without shaking.
- [ ] Identify actual windshield/side-window draw mesh/face/texture for each car model; trace live D3DRS19/20 and premultiplication to final shader fragment; validate pixels in Quest3.
- [ ] Recover exact driver/passenger/hand skeleton movement and OpenXR per-eye submitted frame ordering.
- [ ] Eliminate or bound decompiler false CFG edges; compare clean-room recreation against authentic hardware behavior.

**This is a new evidence-backed static analysis report, not full original C++ source recovery.** No source code changes and no CI/HMD validation claims.
