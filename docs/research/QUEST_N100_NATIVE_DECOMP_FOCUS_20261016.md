# Quest 3 OutRun 2006 APK: N100 핵심 로직 역컴파일 및 PCVR 적용 검토
2026-10-16 KST · 사용자 소유 APK의 오프라인 정적 분석 · 원본 APK 및 기존 DX9Ex/DX11 코드 무수정

## 0. 분석 범위와 재현 경로

| 항목 | 결과 |
|---|---|
| APK | `/home/chatgpt-runner/apk/outrun2.apk` (1,491,573,201 bytes) |
| 주요 ARM64 라이브러리 | `apk/_static_out/liboutrun_quest_core.so` 21,959,856 bytes |
| SHA256 (분석 원본) | `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6` |
| 분석 환경 | N100: Ghidra 12.1.4 + Temurin JDK 25 + AArch64 GNU objdump 2.42 |
| 실제 디스어셈블 | 아래 12개 핵심 함수의 정확 ELF 함수 영역 전체 (각 주소/바이트 수 기준) |
| Ghidra C 유사 코드 | 선별 21개 함수에 시도, 13개 함수 ELF 범위 교정 재시도. 일부 부분 출력. |
| 부하 관리 | 초기 자동 분석의 예외 테이블 경고 때문에 중단하고, 제한된 범위의 -noanalysis/함수 경계 복구 방식으로 전환 |
| 원본/역컴파일 결과 | 바이너리·원본 게임 자산·원시 C 유사 출력은 GitHub에 업로드하지 않음 |
| 관련 분석 파일 | `apk/_analysis_focus/disasm/*.asm`, `apk/_analysis_focus/fixed/manifest.tsv`, `apk/_analysis_focus/fixed/*.c.txt`, `apk/_analysis_focus/run.log`, `apk/_analysis_focus/repaired_run.log` |

**정확도 주의:** 아래 의사코드는 ABI·ARM64 분기·실제 API 호출을 확인한 **독립적 동작 재구성**이며, 원본 C++ 그대로가 아니다. Ghidra의 `decompileCompleted=true`만으로 복원이 성공했다고 보지 않는다. 일부 함수에서는 1바이트 함수 본체 또는 다른 함수와의 예외 구역 겹침이 발생했다. 따라서 불완전한 출력은 로직의 직접 증거로 사용하지 않는다.

## 1. Quest 실행 구조: 확인된 데이터 흐름

```text
Android Native / VR runtime
  ├─ XrRig::initialize / input / view_matrix
  │    └─ XrSessionHost: XR session, eye FOV/pose, frame timing
  ├─ Original driving/game semantics (PcRaceMemory / PcMatrixStack / renderer)
  │    ├─ HUD: sprites, glyph records, navigation, race state
  │    ├─ Effects: lens flare/particles
  │    ├─ Shadows: silhouette, stencil/state reset, texture restore
  │    └─ Cockpit: vehicle/occupant/glass/body/hand TLS scopes
  ├─ PcD3D9 / GlD3D9 compatibility (software-render-like API abstraction)
  │    ├─ mesh cache/invalidations + pooled GPU upload
  │    ├─ bind_target / apply_state / bind_textures / GLSL program
  │    ├─ clip_matrix(eye, current/previous) and GL draws
  │    └─ capture_motion / render_motion (implementation details need validation)
  └─ OpenXR frames: per-eye GLES swapchains → FBO → draw → glFlush
                    → xrReleaseSwapchainImage → xrEndFrame
```

The architecture is inferred from verified symbol names **plus actual direct-call edges**, not a source-code build. It resembles a game-logic-preserving D3D9-command translation layer rather than porting literal Windows D3D9 binary instructions. The native host and platform bindings must not be confused with Windows x86 R84.

## 2. OpenXR eye setup and frame ownership (strong binary evidence)

### `XrSessionHost::make_warp_chain`, ELF 0x2d8bd0, 332 bytes
Direct calls in this function: `xrCreateSwapchain`, **two** `xrEnumerateSwapchainImages` calls, three `check(XrResult,...)` calls; a vector append operation for `XrSwapchainImageOpenGLESKHR`. Independent behavioral sketch:

```text
create OpenGL ES XR swapchain for one eye
query number of swapchain images
resize the typed XrSwapchainImageOpenGLESKHR array
enumerate the actual image handles
check each XR result, retain eye-image ownership
```

**PCVR use:** Compare R84/DX11 image generation, resizing and acquired-image lifetime. Do **not** copy OpenGL ES texture descriptors into D3D11/DX9Ex interoperability.

### `XrSessionHost::bind_eye`, ELF 0x2da1c8, 372 bytes
Confirmed `glBindFramebuffer`, `glFramebufferTexture2D`, `glFramebufferRenderbuffer`, `glCheckFramebufferStatus`, and error-path throw. The color texture and renderbuffer are attached and framebuffer integrity is checked **at eye-target binding**. An indirect BLR is also present, whose target has not been reconstructed.

**PCVR use:** Validate that every eye's **color + depth/stencil + target generation** share one acquisition lifetime; check Reset device-loss and target rebind in R84/R31/R32 and DX11 independently.

### `XrSessionHost::end`, ELF 0x2d904c, 1,904 bytes
Direct API sequence includes `glBindFramebuffer` → `glInvalidateFramebuffer` → `glFlush` → conditional `xrReleaseSwapchainImage` (five static call sites across control-flow branches) → view-pose composition → `xrEndFrame`. It also measures `steady_clock::now`. No **direct** `glFinish` call occurs inside this specific function; this does **not** prove there are no GPU waits elsewhere.

**PCVR use:** Inspect whether DX9Ex host waits on GPU resource fences before or after XR image handoff, whether frame identity persists across skip/cache paths, and whether redundant CPU waits cause a missed 72Hz `13.89 ms` frame period. The source APK banner mentioning 120Hz/60FPS is a string, not observed runtime performance.

## 3. Two-eye sphere culling (high-priority for disappearing buildings)

### `outrun::quest::sphere_in_stereo`, ELF 0x2d49a0, 968 bytes
ARM64 evidence: **two `view_matrix(XrPosef)` calls and eight `tanf` calls**, grouped into four tangent eye-FOV values per eye. For each eye, matrix-transformed sphere center is tested against depth and left/right/top/bottom frustum boundaries, with plane-distance terms `sqrt(1+tan²)*radius`. A `0.1f` float value is added to the tested radius. It branches to eye 1 only if eye 0 failed and **returns visible if either eye accepts the sphere**. Suspicious radius bit-pattern classes take a conservative accept path.

Independent outline (not byte-for-byte code):

```cpp
bool sphere_visible_in_stereo(const Frame& frame, Vec3 center, float radius) {
    if (invalid_radius_class(radius)) return true; // fail open on untrusted input
    float r = radius + 0.1f;
    for (Eye eye : {Left, Right}) {
        Vec3 camera = transform_point(view_matrix(frame.eye[eye].pose), center);
        const auto fov = frame.eye[eye].fov;
        if (intersects_depth_and_all_four_tangent_frustum_planes(camera, r, fov))
            return true;
    }
    return false;
}
```

**PCVR use:** Existing `VRCullingUnionFov` is an *angular union* and R84 includes ScreenEdgeCullFix; Quest uses **eye-specific pose + sphere radius** tests. This may explain why merely widening FOV is inadequate near close buildings or during 6DoF/canted views. Treat it as a candidate for a pure C++ two-eye culling test with original game sphere input and **do not overwrite the live game culling path until HMD A/B verifies no missing road/buildings or CPU overhead**.

## 4. Native HUD producer and stereo/duplicate-control implications

### `native_race_hud_display`, ELF 0x1044820, 5,964 bytes
Verified direct edges from this function include:
- `native_arcade_display_callback`, `native_sprite2d` (multiple calls);
- `sprani_draw_428a10`, `sprani_translation`;
- `native_race_end_gad_display`, `native_race_end_arcade_display`;
- `run_navi_draws` (four call sites), `queue_unmarked_glyphs` (two), `native_sprite2d_glyph_records` (two);
- `NativeRaceHudRuntime` initialization, state `note` and `rebuild`, `drain_sounds`, `navi_pub_display_4beb00`.

Conceptual reconstructed stage separation:

```text
dispatch game state and native race callback
collect typed sprite/animation/marker/glyph producers
draw or queue stage/navigation graphics, retain original producer identity
process unmarked glyphs via explicit fallback queue
rebuild/publish race-HUD frame data and drain HUD sound effects
```

**PCVR use:** R84 already has exact-producer HUD semantics. The Quest graph suggests a real distinction between *race state → sprite/animation generator → glyph records → native draw*. Study missed `+TIME`/result overlays and white/duplicate glyphs at the **producer/queue boundary**, not by indiscriminately making every 2D draw headlocked or projecting all null-VS draws. The decompiler confused some landing pad/branches, so current findings do not prove Quest's stereo HUD coordinate placement or that it solved our P0 visuals.

## 5. Lens flare and shadow (strong source-equivalent call evidence)

### `native_race_effects_flare_420560`, ELF 0x104b8d0, 668 bytes
Confirmed calls `map_memory(NativeRuntimeContext&,PcRaceMemory&,bool)` → **`particles_flare_420560(PcParticleContext&)`** and catch/error propagation `fault_pc`. Ghidra C-like output also exhibits incrementing a per-command counter keyed to original PC command ID `0x4249f0`; classification of that counter requires further runtime tracing. This is an **actual lens-flare particle producer wrapper**, not proof of correctly composited stereo.

**PCVR use:** Separate 3D scene/particle flare generation from lens-space 2D sprite overlays; trace per-eye original producer identity, lifetime and alpha/occlusion semantics in `src/hooks_graphics.cpp` → R84 renderer/host. Avoid doubling stage flares from replayed mono scene-effect textures.

### `shadow_draw_422550`, ELF 0x10d6d60, 5,436 bytes
Verified function edges: read `PcRaceMemory::u32/f32`, read current `PcMatrixStack`, call **`shadow_silhouette_421740`**, then `render_reset_states_408880`, `render_set_matrix_410f90`, and finally direct `restore_textures(PcShadowFrame&,PcD3D9Device&)` followed by another reset-state call. Native diagnostics embedded in ELF include stencil nonzero bounds and shadow shade counts.

**PCVR use:** In the R84/host pipeline, the shadow producer, scene color/depth/stencil, GPU draw-state and texture binding must be returned to the owning pass **per eye**. Test shadow draw after scene effect, camera reset, driver seat change and alpha pass; do not apply a broad state clear without precise scope. Ghidra's decompilation of this huge function failed (landing-pad function overlap), so effects/state details are evidenced by A64 BL edges, not whole high-level code.

## 6. Draw batching, mesh cache and motion data

### `GlD3D9Device::flush`, ELF 0x2fcfdc, 7,936 bytes
Verified pipeline within this function:
`bind_target`, `apply_state`, `bind_textures`, `glUseProgram`, `XrSessionHost::clip_matrix(...)`, `glGetUniformLocation`, `glUniformMatrix4fv`, `glDrawElements`; alternate drawing also includes `glDrawArrays`. Pooled buffer uploads `pooled_upload`, `glBindBufferBase`, `glBindVertexArray`, `glBindVertexBuffer` and `capture_motion` are also present. Multiple `std::map`/comparison paths and `steady_clock::now` calls suggest batching/cache state and instrumentation; **frequency per draw has not been measured**.

### `GlD3D9Device::invalidate_mesh`, ELF 0x2f8524, 1,084 bytes
Observed `std::__tree_remove`, multiple heap allocations/frees, vector maintenance. **No direct `glDeleteBuffers` call in this function**; any GPU object invalidation is indirect or delegated. This means a naive PC translation of this one routine into GPU deletion each time is not grounded.

### `GlD3D9Device::capture_motion`, ELF 0x300100, 5,896 bytes
Verified two `XrSessionHost::clip_matrix` calls, `gpu_vertex_source`, GLSL string manipulation (`memchr`, string replace/insert/append), multiple `texture`, `pooled_upload` and buffer operations. Embedded shader source uses `questOldClip`, `mvCurrent`, `mvPrevious`, `questPrevious`.

**PCVR use:** independently profile CPU `Draw*/shader/uniform/memcpy`, pooled uploads, reset-device cache generation and HMD submit cadence before porting a cache design. Current/previous clip & motion capture is proven present; **not proof that Android spacewarp is enabled**. The PCVR host has its own DirectGPU/IPC identity and XR cadence constraints, so this cannot be copied as an interchangeable renderer.

## 7. Cockpit / driver-seat mode

Detected AArch64 **TLS variables and relocations**:
`cockpit_render_active` (1 byte), `cockpit_vehicle_draw` (1), `cockpit_occupant_draw` (1), `cockpit_glass_opacity` (4), `cockpit_glass_premultiplied` (1), `cockpit_body_correction` (64), `cockpit_hand_tracking` (8).

The 376-byte `cockpit_fragment(std::string)` at `0x2f7734` has direct `memchr` and `std::string::replace` calls and shader-compilation error messages; it is best interpreted as **shader-source transformation**, not direct drawing by itself. Direct callers include `GlD3D9Device::flush` and constructor. `cockpit_body_correction` looks like a 4×4 matrix by size, but this is a hypothesis until writers/readers are recovered. The existence of `cockpit_hand_tracking` does not prove the hand model is usable on Windows.

Current PCVR `VRDriverSeatView` is experimental/off by default; native mode 1, forward -1.35, right -0.32, up 0.65, full-car and configurable robot suppression hooks already exist. Existing [Quest 2026-10-16 implementation](../QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md) unified camera+car/near-plane eligibility. New **porting requirements**:
1. Unify on native camera transition owner, keep simulation camera untouched and suppress only verified player's driver, not the passenger.
2. Identify actual PC car-interior texture/material IDs and blend factors for glass; apply per-eye alpha state and restore after this draw (do not apply blanket transparency).
3. Bind head pose/recenter relative to stable seat anchor and preserve near-plane under head lean; test on 360SP and all selectable vehicles.
4. Hand/steering-wheel animations need proven PC rig and controller/FFB ownership. Do not synthesize controller movement merely from TLS name.

## 8. Concrete PCVR priorities

| Priority | Topic | Recommended implementation gate |
|---|---|---|
| P0 | buildings vanish/flicker / near objects | pure per-eye sphere-vs-frustum test compared with original `VRCullingUnionFov`; static C++ regression for canted-eyes, 6DoF head lean, finite/NaN/radius safety; enable only after HMD A/B |
| P0 | frame drop on sand/buildings | add separate CPU draw count, buffer-upload count, XR swapchain acquire/release duration, per-eye draw/state changes, cached-frame ratio in R84/host; no claimed FPS gains without real GPU timestamps |
| P0 | white/duplicated HUD, transient +TIME/results | capture producer→glyph queue→R84 semantic selection→eye replay / theater, avoid classifying unknown sprite as ScreenHud |
| P0 | lens flare doubled / shadow | verify producer class per eye and reset-specific color/depth/stencil/texture restoration with scoped tests; never use blanket mono copy for world effects |
| P1 | driver-seat parity | native mode lock, player-only model/occupant, camera offset/head relative to seat, windscreen opacity and reset; HMD scene acceptance |
| P1 | persistent-mesh cache | inspect DrawPrimitive/UP/index-buffer unlock, Reset/ResetEx epoch and latest-write invalidation; do not replay stale geometry |
| P2 | motion vector / spacewarp | decode current/previous clip history and XR runtime capabilities; performance benefits conditional, not claimed |

R84 owner remains **R33→R32→R31→R30→R29** with x64 host; R26_SAFE is fallback. DX11 is separate. A new C++ source change requires exact SHA Windows x86 DLL+x64 host/Domain+HUD+package gates; **no new gameplay source modification performed by this research**.

## 9. Evidence/limitations

* Binary targets were read from the user's local ELF and disassembled with AArch64 `objdump` with the **actual shared-object symbol and PLT targets resolved**. N100 files `apk/_analysis_focus/disasm/*.asm` contain the focus disassemblies; `apk/_analysis_focus/fixed/*.c.txt` contains raw Ghidra C-like attempts and their limitations, for user's private research only.
* Ghidra attempted 21 named focus entries and 13 ELF-boundary reanalysis targets. Several outputs were incomplete (e.g. projection/sphere/GLES flush generated 190–200 character stubs; HUD/shadow suffered overlapping landing-pad regions). Such output **is not considered a recovered source implementation**. Shorter flare/HUD subpaths were partially recovered but are still type-uncertain.
* No Quest APK code, shader text, or proprietary game assets copied to public GitHub.
* No headset/frame-time measurements or Windows exact-SHA build executed for this docs-only investigation. Quest/VDXR `RUNTIME_VALIDATION=UNTESTED`; speedup/bugfix status **not claimed**.
