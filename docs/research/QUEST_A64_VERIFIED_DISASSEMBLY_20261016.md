# Quest APK ARM64 verified disassembly — projection and cockpit fragment
Date: 2026-10-16 (KST)
Source: user-provided `liboutrun_quest_core.so` ARM64 ELF on N100, SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.

**Execution venue:** N100 did not run a decompiler. GPT received only authorized read-only function-byte chunks, and assembled each into a minimal AArch64 ELF relocatable container in a local GPT container. Verified each byte-slice SHA-256 against N100 `read_file_chunk` before local LLVM 17 disassembly. This document records analyst behavior summaries, not original game source or copied object code. Full ELF inventory is in [quest_function_index](quest_function_index/README.md).

## `outrun::quest::projection_gles(XrFovf const&, float, float)` 0x2d481c, 340 bytes

Function-byte SHA-256: `e44df7a5be99c1636f7a438f5d7530e118c8660b59c8ef33c8da1d5c7c972908`.

Direct AArch64 disassembly shows four float-trigonometry calls (for each FOV angle), then positive near and ordered far plane checks and ordered tangent spans. Specifically, `near > 0`, `far > near`, `tanRight > tanLeft`, `tanUp > tanDown`; invalid values enter an exception path. Matrix terms follow:

```cpp
// Independent behavioral reconstruction; not a copy of the binary's source.
float l = tan(fov.angleLeft), r = tan(fov.angleRight);
float d = tan(fov.angleDown), u = tan(fov.angleUp);
if (!(nearZ > 0 && farZ > nearZ && r > l && u > d)) return false;
float scaleX = 2 / (r-l), scaleY = 2 / (u-d);
float shiftX = (r+l)/(r-l), shiftY = (u+d)/(u-d);
float glZScale = -(nearZ+farZ)/(farZ-nearZ);
float glZBias = -2 * farZ * nearZ / (farZ-nearZ);
```

Explicit PC transfer decision: **do not overwrite R84's existing projection math**. `src/vr/core/matrix.hpp::ProjectionFromOpenXrFov` already implements asymmetric tangent scales/offsets and a transactional nonfinite guard; it preserves the game's existing depth projection coefficients, appropriate for Direct3D depth range, whereas standalone uses OpenGL ES conventions. Potential integration is additional tests/negative cases only.

## `outrun::ps5_runtime::cockpit_fragment(std::string)` 0x2f7734, 376 bytes

Function-byte SHA-256: `a095d0bfded18ec835aa24e7d5036c6732a37e73298db893eaf8d7123a42925d`.

The actual disassembly includes short-string representation checks, search for byte `0x6f` ('o'), 13-byte literal matching, range substitution and string memory handling, and exception-path calls. **Inference (stronger than name-only): shader-source string rewriting, *not* GPU fragment execution itself.** `GlD3D9Device::flush` and constructor contain direct call sites in the previous AArch64 BL graph. This corrects an earlier interpretation of the name as a direct shader executor.

**Not yet proven:** the original `.rodata` pattern and replacement string (which determine exactly how cockpit shader output is rewritten), state scopes and corresponding GL blend setup. Replacing our D3D9 shader or forcing alpha based on this string routine alone would be unsafe.

## Whole-function status

Symbol index: 14,341 **nonzero-size FUNC symbol rows in .symtab/.text**, 14,076 **unique** function start addresses. Earlier ~22K symbol-row scans inadvertently mixed `.dynsym` and `.symtab` and counted some duplicated records; do not equate the raw row counts to independently decompiled implementations.

**Not achieved:** 14,076 full high-level C/C++ decompilations. The local GPT container does not currently have Ghidra or the complete 21MB `.so` mounted; the N100 private network is not reachable from this sandbox. Therefore a handoff kit and Ghidra batch script were prepared in the conversation for later locally mounted binary work rather than falsely claiming completed bulk decompilation. Private decompiler outputs must not go in this public repository.

## Priority porting targets still awaiting verified semantics
`XrSessionHost::make_warp_chain`, `bind_eye`, `GlD3D9Device::flush`, `invalidate_mesh`, `sphere_in_stereo`, `native_race_hud_display`, `shadow_draw_422550`, `native_race_effects_flare_420560`, and the cockpit rendering/vehicle/occupant/glass/body/hand TLS scope. See [full adoption matrix](QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md).

**No new R84 gameplay modification made solely because a Quest function name exists.** RUNTIME_VALIDATION=UNTESTED without a real HMD session.
