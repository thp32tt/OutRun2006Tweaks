# REA-assisted Quest cockpit recovery: XR eye admission, driver dispatch, and guarded arithmetic (2026-10-25)

## What was newly completed
Seven independent **real REA 6.5.0 + Ghidra 12.1.4** raw-AArch64 function reads were performed on native slices obtained from the user's original Quest ELF; exact addresses and SHA256s, all seven REA evidence IDs, function-body coverage and unresolved call counts are recorded in `quest_apk_rea_seven_functions_manifest_20261025.json`. This is distinct from the earlier native whole-ELF Ghidra decompilation.

REA whole-ELF initial analysis **timed out after 260s**; don't imply a successful full ELF REA import. The 7 raw slices total 15,168 bytes; REA classified 14,688 bytes as function body in total (some noncontiguous), with 1,312 outgoing references. Function byte extraction is independently SHA-verified against user ELF `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Each raw-slice result may omit external callee targets and false CFG may truncate pseudocode. Author's original source/comments are not recovered.

## Newly cross-verified: XrRig::locate eye admission
- ELF exact function `outrun::quest::XrRig::locate(long,bool,StereoFrame&)` at **0x2D69C8** (656 bytes), REA evidence ID `ev_870962117da11e023f98360893f89038a723020c0a4febae5cf62b5290b5e854`; REA function body covers all 656 bytes.
- Original full ELF ARM64 call at **0x2D6A34** resolves to **`xrLocateSpace@plt`**. The checked return is followed by flags check at **0x2D6A4C** requiring `(locationFlags & 3) == 3`; invalid space-orientation/position validity rejects the frame.
- The recovered frame-origin branch uses a first-location/recenter condition and computes an `atan2f` yaw then `sincosf(yaw/2)`; another configuration branch substitutes the full located orientation when enabled. Exact signs/axes should not be abstracted away before numerical fixtures.
- ARM64 **0x2D6B68** calls **`xrLocateViews@plt`** and checks the API result. ARM64 **0x2D6B80** requires **viewCount == 2**, then **0x2D6B90** requires `(viewStateFlags & 3) == 3`; otherwise the function returns false.
- Once valid, it calls `outrun::quest::inverse(XrPosef)` at **0x2D6BA0** and `compose(XrPosef,XrPosef)` at **0x2D6BB4** and **0x2D6BDC**. Both transformed eye poses are copied to the `StereoFrame&` output.
- This validity-before-commit behavior is an exact, actionable comparison target for the shaking `DriverSeatView=true` Windows VR path; no runtime Windows cause attribution is yet made.

**Conservative observer-level reconstructed gate** (NOT literal original source):
```cpp
bool admitXrStereoFrame(uint64_t spaceLocationFlags,
                        uint32_t viewCount,
                        uint64_t viewStateFlags) {
    return (spaceLocationFlags & 3u) == 3u &&
           viewCount == 2u &&
           (viewStateFlags & 3u) == 3u;
}
// Original code also checks API call results, XR session availability,
// and computes a recenter transform before writing both eye poses.
```

## Additional REA coverage
- `driver_occupant_draw` exact ELF **0xD60FD4**, input 7676 bytes, REA body 7316 noncontiguous, 248 unresolved calls, evidence `ev_2ac0a21b4a7607f71d031aaf41a3b81c7e49a7bfc755c790a7825ead3ec3b10d`. The decompiler's limits prevent declaring full driver/hand rig reconstructed.
- `race_robot_driver_chara_487ee0` ELF **0x39F33C**, 444/444 bytes, evidence `ev_ec2a549fb087ce80f45bc136b1bbbfbb2bc9990597f3ed87042630db91ae978d`. Observed guest game-mode 3 return 0xC, and other paths use a license/character table with bounds checks; not yet proof of HMD hand movement.
- `ps5_runtime::cockpit_fragment` ELF **0x2F7734**, 376 input bytes, REA recognizes 340 body bytes and signals truncated cross-boundary control flow, evidence `ev_ca6609f0db6d6de53fb9d98700e2ae129df7751268eaad2db603e143914f1ebe`. This is a fragment/program setup helper, not the entire final fragment shader, and requires separate exact shader-source tracing.

## Concrete partial C++ source recovered
- **`quest_cockpit_body_correction_reconstructed_20261025.cpp`** is in this `docs/research/` directory. A source generator walked 229 native AArch64 instructions in ELF `0x10CBF6C..0x10CC2FC` and produced 211 modeled memory/FPU operations (240 C++ assignments), including `std::fma`, from original assembly. All 16 destination slots are populated and no unparsed candidate source-register FP operations were observed by the generator.
- The source is 12,393 chars, SHA256 `5ae6a5f6d1d6ac0259cda307fa9bdd7729ba733e74a5591f845694c7fdba4d0f`. The fixture file `quest_cockpit_body_correction_fixtures_20261025.json` records **three synthetic input cases** (I/I, I/translation, I/rotation). Python float32 instruction-model evaluation passes. It is **not yet compiled, not exact floating-point ULP-equivalent to ARM fused execution for arbitrary inputs, and not Quest 3 hardware-validated**.
- This reference computes only the **body-correction**. The separately observed guest matrix neutralization, normal/unwind restoration and TLS scope must be implemented correctly in any candidate PCVR port.

## Glass tagged render-pass producer remains unresolved
Quest original `Flush::draw_404700` checks `DrawEntry.flags & 2` plus blended `DrawEntry.pass==1`, effective blend and alpha. Raw REA recovered this area with partial external calls only. Native disassembly of `render_queue_flush_405890`, `render_object_405360`, `display_race_car`, `vehicle_race_model_draw` and related body regions was scanned for direct bit/set writes. A `str w0,[x22,#52]` at ELF **0x10AF5A4** was *not* accepted as a `DrawEntry.flags` writer: context `0x10AF4C8` derives x22 from device state, before any `DrawEntry` pointer is loaded. Other matches were literal argument 2, source reads, or unrelated stack fields. **No justified bit1 producer was identified** in this limited scan. Full data-flow/alias tracing is necessary; don't claim to have found the front/side-window owner.

## Status and remaining work
GitHub evidence is source-review-only. `DX9Ex=REVIEW_ONLY`, `CODE_CHANGE=NO`, `BUILD=NOT_RUN`, `RUNTIME_VALIDATION=UNTESTED`. Safe R26+HUD baseline and `DriverSeatView=false` default unchanged. The user-requested goal is original-behavior equivalent C++ across player camera, per-eye OpenXR, driver/hand geometry and all glass materials; this is not yet reached. Do not claim perfect original authored source recovery.
