# DX9Ex Quest3 2026-10-14 — aspect P0 / performance P1

## Evidence and authority
User's actual Quest3 screenshot feedback: front-end/vehicle-selection theater is oversized, top-shifted and clipped; F11 and gameplay HUD are too small/high; car-relative rank floats too high; lens centre and stage +TIME/result-progress still double. None is optical PASS.
Source-under-test `0b373f76462c6b1e3a629b79b116ea45591c4acd`, with user uploads:
- CURRENT_FOCUS 20261013T150603355Z-70601f8d
- B_HUD 20261013T145126958Z-fb96ea0a
- C_FLARE 20261013T145401563Z-6f473a41.

## Exact measured bottlenecks (not extrapolated hardware fps)
CURRENT_FOCUS: analysis approx 75.6 XR Hz, reported 90Hz period 11.111ms; 6609 XR samples, cached 244 (3.69%); gameRenderCpuMs p95 11.876/p99 16.179ms; gamePresentToHostMs p95 17.991/p99 27.355ms; xrEndFrameMs p95 19.363/p99 33.251ms. 148 logged source frame dips; worst 319.771ms at just 5 Draws (startup/transition, NOT proved dense-scene GPU bound). Max sampled scene Draw count 3298; NVIDIA utilization 39% median and 99% max, sampled across menus and gameplay. Zero reported fence timeouts, 3 direct fallbacks.
B_HUD: approx 90.5 XR Hz; 4542 samples, 63 cached (1.39%); render p95 8.739ms. C_FLARE: approx 74.2 XR Hz; 6618 samples, 275 cached (4.16%); render p95 13.278ms.
Game-side heavy and non-CPU time spikes coexist with occasional GPU saturation. Host copy/render CPU p95 roughly <0.01ms; do not blame raw host copy throughput or equate xrEndFrameMs with GPU execution time. R28 `ThreadCpuMs` is sampled and coarse; `NonCpuMs` includes blocked/wait/scheduling, not measured GPU time.

## Priority
P0-A: theater 4:3 crop optical centre+limited coverage, user.ini game settings precedence, fail-closed input and shared left/right aspect. This commit provides a bounded optical-size adjustment only. It **does not** prove root cause of all top-alignment/cropping.
P0-B: head-lock/F11 HUD/marker Y layout regressions — separate source ownership/visual A/B, do not apply global Y bias and break eye/world marker attachment.
P1: runtime CPU wait source: separate game Draw prep/Present and XR EndFrame with before/after scene-matched windows; inspect shader/material creation and high draw count only when the matching spike proves it. No blind global quality regression.
P1 A/B GPU trial (no codewide quality regression): on the existing DX9Ex VR test build set `AntiAliasing=1` (2x MSAA) vs `AntiAliasing=2` (4x MSAA) for two comparable drive sequences; restart between changes. Keep `AutoRenderResolution=true`; do not change VDXR eye extent or desktop resolution to fake FPS. Compare gameRenderCpuMs p95/p99, DirectGPU cached%, Present and utilization sample, and optical edges.
P2: central lens flare, transient +TIME and incomplete-result stage remain UNTESTED/FAIL as reported; exact original game producer semantics must be preserved.

## Validation
Native C++ menu_content_aspect_smoke needs exact compile/run; build and isolation GitHub Actions must validate the new actual material commit. Quest3/VDXR runtime remains UNTESTED until a new actual test of exactly this SHA.
