# OutRun 2006 VR — 외부 오픈소스·원본 모드·논문 교차 연구 (2026-10-16)

- 범위: DX9Ex R84 메인라인 우선, DX11/DXVK는 **읽기 전용 비교 사례**.
- 기준 저장소: `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`; 조사 시작 HEAD `e58d8ed504f20240e35d1f9565ced85102d43b86` (2026-10-16 08:32 KST 확인).
- 증거 구분: **[코드 확인]** 현재/원본 GitHub 소스 또는 원문에 실제 존재, **[설계 근거]** 공식 사양·저자 문서, **[가설]** OutRun 증상에 적용 가능하지만 아직 재현·원인 입증 없음.
- 상태: `RESEARCH_ONLY / NO_RUNTIME_SOURCE_CHANGE / RUNTIME_VALIDATION=UNTESTED`. 이 문서는 실제 수정·성능 향상·HMD 합격·테스트 빌드 결과를 의미하지 않는다. 연구·문서 커밋은 독립 기능 성과 점수에 포함하지 않는다.
- 개발 준수: `AGENTS.md`, `docs/DX9EX_R84_MAINLINE_CONTRACT.md`, `docs/VR_PROBLEM_HISTORY.md`, `docs/DX9EX_VISUAL_REPAIR_LENS_EXTTIME_20261015.md`, `docs/DOMAIN_ISOLATION_POLICY.md`의 **최신 규칙이 본 참고 문서보다 우선**한다. 기존 TASK_ID/FEATURE_ID/lease를 재사용한다.

## 0. 핵심 결론

1. **화면 정확성 P0**: 렌즈 중심광은 원본 C993 producer와 raw VS c64..c67의 일치 여부를 끝까지 증명해야 한다. `+TIME`은 caller-tag부터 D3DX/queue의 **실제 GPU 소비 시점**까지 소유권을 전달해야 한다. 기존 훅/범주화는 이미 존재하므로 재구현하지 않는다.
2. **프레임 드랍 P0**: R33의 기존 비동기 D3D9 GPU query와 R31의 draw-route 통계, 호스트 프레임 ACK/Present 연속성을 같은 frame/pose/generation으로 연결하여 밀집 건물·모래·물·투명 파티클 구간의 CPU/GPU/전송/재투영 병목을 **먼저 분리**한다. 측정 전 모든 alpha를 glass/water라고 단정하지 않는다.
3. **양안 정확성 P1**: UEVR의 '같은 시뮬레이션 tick을 공유하는 양안 렌더링' 원칙과 OpenXR의 predictedDisplayTime/pose 계약은 유효한 비교 기준이다. 그러나 UEVR의 Unreal Native Stereo 구현을 OutRun D3D9Ex로 직접 복사할 수 없으며, 현재 OutRun은 **게임 tick 1회, 증명된 GPU draw만 양안 재실행**이라는 계약을 유지해야 한다.
4. **원본 OutRun 근거 P1**: `emoose/OutRun2006Tweaks/src/hooks_uiscaling.cpp`는 640×480 논리 좌표, `min(screen_scale.x,screen_scale.y)`, 랭크마커의 소수 픽셀 보정과 메뉴의 특례가 실제 코드로 존재한다. 현재 fork의 `src/hooks_uiscaling.cpp`도 해당 알고리즘 및 VR 분기/원본 producer 지식을 **이미 가지고 있다**. 따라서 새 UI 수식 도입보다 기존 2D/3D 분기와 최종 eye-plane/pose를 검증한다.
5. **새 렌더러 대체 보류**: DXVK·3Dmigoto·Geo-11·SuperDepth3D·vrperfkit의 장점을 실험·진단 기법으로 참고하되, DX9Ex 메인 런타임 교체/셰이더 일괄 수정/범용 FFR 투입은 현 단계에서 정당화되지 않는다.

## 1. 연구 원문·프로젝트 맵

| ID | 1차 자료 및 직접 링크 | 근거/핵심 내용 | OutRun 적용 여부 |
|---|---|---|---|
| E01 | [emoose OutRun2006Tweaks — hooks_uiscaling.cpp](https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_uiscaling.cpp), [원본 INI](https://github.com/emoose/OutRun2006Tweaks/blob/master/OutRun2006Tweaks.ini) | [코드 확인] 640×480, 종횡비 containment, 순위 마커 보정, UI 세부 호출지점 | **즉시 비교 A**. 우리 fork의 동일 파일과 producer 단위 diff |
| E02 | [emoose 원본 README](https://github.com/emoose/OutRun2006Tweaks), [원본 릴리스 Known Issues](https://github.com/emoose/OutRun2006Tweaks/releases) | [저자 근거] UI 특례, 미해결 화살표·랭크, `DrawDistanceIncrease`의 높은 설정값에서 LOD 문제, 일부 진동/블루투스 지연 | **회귀기준 A**. 무조건 UI 정상이라고 가정하지 않는다 |
| E03 | [UEVR 공식 소스](https://github.com/praydog/UEVR), [공식 매뉴얼](https://docs.uevr.io/), [VR.hpp](https://github.com/praydog/UEVR/blob/master/src/mods/VR.hpp) | [코드+저자 근거] native stereo/synchronized sequential/AFR, UI 투영, per-game profile | **개념 비교 A**. gameplay tick 재실행 금지; 버그 격리용 모드 비교만 참고 |
| E04 | [GTA V R.E.A.L. mod 원문](https://github.com/LukeRoss00/gta5-real-mod) | [저자 근거] alternate-eye는 시점 차/빠른 이동에서 서로 다른 시각의 눈이 중첩돼 이중상이 발생 | **반례 A**. 프레임 절약만을 위해 시간차 좌/우 제출하지 않는다 |
| E05 | [DXVK D3D9 StateBlock 구현](https://github.com/doitsujin/dxvk/blob/master/src/d3d9/d3d9_stateblock.h), [DXVK repo](https://github.com/doitsujin/dxvk) | [코드 확인] state capture flag, sampler/texture, shader constants, viewport/scissor, stream state 분리 | **진단 비교 A**. native R31 StateBlock cache invalidation 설계 대조; DXVK 코드를 가져오지는 않음 |
| E06 | [Microsoft D3D9 State Blocks](https://learn.microsoft.com/en-us/windows/win32/direct3d9/state-blocks-save-and-restore-state), [Capture API](https://learn.microsoft.com/en-us/windows/win32/api/d3d9helper/nf-d3d9helper-idirect3dstateblock9-capture) | [공식 사양] Apply는 **기록된 상태만** 덮어쓴다; Effect Begin/End도 StateBlock 사용 가능 | **확정 계약 A**. 기록 중/Apply 직후의 shader constant, texture, viewport 및 c64 provenance 비교 |
| E07 | [Khronos OpenXR Frame Submission Guide](https://github.com/KhronosGroup/OpenXR-Guide/blob/main/chapters/frame_submission.md), [규격 소스](https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/rendering.adoc) | [공식 사양] xrWaitFrame→xrBeginFrame→xrEndFrame, predictedDisplayTime/shouldRender, pose 시간 기준 | **확정 계약 A**. 호스트 stale-frame/future-pose/재사용 연속성 검증 |
| E08 | [OpenXR SDK Source — hello_xr](https://github.com/KhronosGroup/OpenXR-SDK-Source/tree/main/src/tests/hello_xr) | [공식 구현] OpenXR loader/validation/sample; 상태/레이어/세션 수명 | **진단 A**. host lifetime & reset/transition 비교 |
| E09 | [3Dmigoto source](https://github.com/bo3b/3Dmigoto), [d3dx.ini shader hunting](https://github.com/bo3b/3Dmigoto/blob/master/Dependencies/d3dx.ini) | [코드 확인] shader/RT hunting, hash, original/mono/highlight 모드, 화면효과 특화 판별 | **기법 A**. 원본 shader fingerprint+RT+producer 매핑; 주로 DX11이므로 D3D9Ex 직접 주입 대상 아님 |
| E10 | [Geo-11 릴리스](https://github.com/ThreeDeeJay/geo-11/releases) | [저자 근거] 특정 효과의 양안 불일치, shader fixes, VRScreenCap/Katanga 활용 | **비교 B**. 정답 양안 스크린샷·비교 룰 참고. 실행 경로 변경 금지 |
| E11 | [SuperDepth3D 소스](https://github.com/BlueSkyDefender/Depth3D/blob/master/Shaders/SuperDepth3D.fx) | [코드 확인] depth 기반 2D→3D 재구성, 사용자별 divergence/zero parallax | **비교 B**. depth 재투영의 가림/투명물체 한계 측정; 진짜 양안 지오메트리 대체 아님 |
| E12 | [vrperfkit](https://github.com/fholger/vrperfkit), [FFR config](https://github.com/fholger/vrperfkit/blob/master/vrperfkit.yml) | [저자 근거] D3D11 + OpenVR/Oculus 대상으로 업스케일/FFR/VRS; 영역별 화질·성능 교환 | **장기 C**. DX9Ex에 즉시 설치해 FPS 해결한다고 주장하지 않는다 |
| E13 | [OpenXR Toolkit](https://github.com/mbucchia/OpenXR-Toolkit/releases) | [저자 발표] 2024년부터 지원 중단 및 새 게임에서 문제 가능성 경고 | **채택 제외**. 오래된 툴을 필수 운영 의존성으로 만들지 않는다 |
| E14 | [van Waveren 2016 — Asynchronous Time Warp](https://doi.org/10.1145/2993369.2993375) | [동료심사 논문] 최신 head tracking 기반 시간 보정·VR 프레임 일정성; 새 객체/가림과 시뮬레이션 시간차를 해결하는 만능 수단은 아님 | **원리 A**. stale frame 재투영과 실제 두 눈 시점 동기화를 구분 |
| E15 | [Shi et al. 2022 — Stereo-consistent SSAO](https://doi.org/10.1145/3522614) | [동료심사 논문] 좌우 독립 screen-space 정보로 얻는 AO 불일치 감소 연구 | **아이디어 B**. 좌우 depth/occlusion 차 검출에 참고; OutRun SSAO 사용 여부는 미확인 |
| E16 | [Wu et al. 2024 — Stereo-consistent SSR](https://doi.org/10.1111/cgf.15159) | [동료심사 논문] 좌우 screen-space reflection/fade/sampling 불일치가 시각적 불편을 유발 | **아이디어 B**. 물/차 유리 등의 문제 진단에 참고; OutRun SSR 존재를 주장하지 않음 |
| E17 | [Microsoft OpenXR best practices](https://learn.microsoft.com/en-us/windows/mixed-reality/develop/native/openxr-best-practices) | [공식 문서] 권장 이미지 크기, eye pose/FOV, layer 및 depth 고려 | **조건부 B**. HoloLens 최적화 수치를 Quest3/VDXR에 무조건 일반화 금지 |
| E18 | [OpenComposite OpenXR upstream](https://gitlab.com/znixian/OpenOVR) | [공개 구현] OpenVR 호출을 OpenXR로 번역하는 호환 계층 | **참고 C**. 현재 native OpenXR 호스트에 중복 번역 계층 추가 금지 |

**출처 선정:** 원저자 프로젝트와 원본 코드, 공식 API, 논문 DOI 위주. 포럼/비공식 벤치마크는 설계 확정 근거에서 제외. 공개 프로젝트 최신 HEAD는 변할 수 있으므로 실제 이식 후보가 생기면 upstream commit SHA와 라이선스/의존성/빌드 타깃을 다시 고정한다. 모든 외부 자료는 **원리·실험 설계 참고**이며 타 프로젝트 코드를 복붙·합병하라는 뜻이 아니다.

## 2. 현재 코드와 교차 검증: 이미 구현된 것을 다시 만들지 말 것

| 현존 구현 [코드 확인] | 연구 연계 | 남은 검증/구현 경계 |
|---|---|---|
| `src/hooks_uiscaling.cpp` + `src/vr/game/rank_marker_fraction.hpp` + `src/vr/ui/ui_side_spacing.hpp` | E01·E02 | 원본 2D UI 수정과 R30 eye transform을 **두 번 적용하지 않는지**, 메뉴/차량선택·HUD/GOAL 경계 분리 확인 |
| `src/vr/d3d9/stereo_renderer_r29.cpp` | E03·E04 | 원본 게임 tick 1회, 동일 frame pose 2안, 안전성 불명 draw의 fail-closed 보장; AFR 도입이 아님 |
| `src/vr/d3d9/stereo_renderer_r31.cpp` | E05·E06 | StateBlock Begin/End/Apply 세대와 shader epoch, c64 원본 및 sampler/sRGB/viewport/RT 전이의 일관성 |
| `src/vr/d3d9/stereo_renderer_r33.cpp` | E05·E06 | 주 draw dispatcher이며 depth/stencil/viewport 추적. 실제 수행 우회경로, 양안 HRESULT+복원 완료 여부 구분 |
| `src/vr/d3d9/gpu_water_profiler.hpp` | E12·E14 | **이미 존재**하는 `OUTRUN_VR_GPU_PROFILE=1` 비동기 query 계측기를 그대로 사용; query GetData는 FLUSH=0. 새 전역 동기화/매 draw GPU readback 금지 |
| `src/vr/d3d9/lens_centre_source_provenance.hpp` | E09·E15 | 이미 raw WVP call/pose/shader epoch/age guard 존재. raw 원본이 실제 생산된 후 정확한 C993 eye path로 소비되었는지 **런타임에서 미증명** |
| `src/vr/d3d9/stage_extension_eye_plane.hpp` | E01·E03 | +TIME 전용 projected XYZRHW 경로 이미 존재. 직접 호출 scope 밖 **지연 D3DX/queue 소비 시점**의 태그 유지가 핵심 |
| `src/vr/d3d9/stereo_completion_gate.hpp` | E07 | 좌우 draw 및 state restore 성공 조건 이미 존재. host 소비·XR 제출까지 연쇄 증명하는지 추가 확인 |
| `docs/VR_ARCHITECTURE.md` | E07·E08 | `IGameAdapter/IStereoBackend/IPC v3` 목표 설계는 존재하지만 **live authority는 `ARCH-V3-GATE-001`로 차단**. 연구 때문에 조기 전환 금지 |

`AGENTS.md`의 2026-10-15 R84 전환이 **과거 R26 기본 패키지 기술을 대체**한다. 옵션 없는 CMake의 R84 본체 `R33→R32→R31→R30→R29`와 x64 host, `CURRENT_FOCUS` 실제 DLL SHA를 항상 확인한다. F11 사용자 보고 정상(2026-10-09)은 별도로 보존하고 새 회귀 증거 없이 결함으로 재분류하지 않는다.

## 3. 우선 구현/분석 가설 — 증상·원본·테스트·롤백까지

### P0-A / `DX9EX:VIS:LENS_FLARE_CENTRE` — lens centre 이중상/헤드락
- **확인된 현황:** `docs/DX9EX_VISUAL_REPAIR_LENS_EXTTIME_20261015.md`에 중심 `D3A5→C980→C993` 및 outer flare 별도 경로, raw c64 WVP ownership 위험 기록. `lens_centre_source_provenance.hpp`는 call/pose/shader 세대 증명을 이미 구현.
- **유력 가설 (미확정):** producer scope와 실제 원본 c64 write, 복원/재호출/지연 draw의 시간 차이; stock이 아닌 head-adjusted c64의 중복 보정. '렌즈 위치'만 바꾸거나 중심을 항상 HUD plane으로 붙이는 해결은 불가.
- **적용 경로:** `src/hooks_graphics.cpp`의 C993 producer → `src/vr/game/render_semantics.hpp` → `src/vr/d3d9/stereo_renderer_r30.cpp`/r33 → `vrhost` 프레임 제출. `shader ID+producer call+present generation+pose epoch+original-c64-write` 한 ID로 결속.
- **검증:** centre 1개 spatial 고정, 외곽 flare 3D·SkyGlow·smoke·rival 변형 없음; c64 write 늦음/누락/같은 shader 다른 객체, Reset/recenter/시점 교차/두 eye HRESULT 음성 테스트.
- **금지:** broad WorldBillboard 스테레오 강제, 모든 alpha 변경, 검증 없이 draw age 무한 연장.

### P0-A / `DX9EX:VIS:EXTENDED_TIME` — stage `+TIME` 글자와 숫자 중복
- **확인된 현황:** 원본 6개 caller hook, `StageExtensionTime` producer/queue replay, XYZRHW eye plane 존재.
- **유력 가설 (미확정):** D3DXSprite::Draw 등록 시점과 End/Flush/실 GPU DrawIndexedPrimitive 시점이 다른 경우 producer scope 소실; sprite와 numeric 각기 다른 경로.
- **적용 경로:** `src/hooks_uiscaling.cpp`의 6 caller → `SpriteNode/SumoUISpriteReplay` → D3DX batch의 begin/owner/flush/end → `r30/r33` 실제 양안 draw.
- **검증:** sprite + 숫자 각각 한 번·동일 eye plane, 서로 다른 texture 섞인 인접 batch, 이전/다음 unrelated HUD, 6 caller, fixed-function/VS/XYZRHW, Reset 후 큐 해제.
- **금지:** 매 Draw Flush, 범용 alpha 태그, 게임 시간값 변경, 숫자만 해결하고 완료 처리.

### P0-B / 고밀도 건물·모래·파티클 FPS 급락 및 '되감기'처럼 튐
- **현존:** R31 high-draw perf counters, R33 비동기 timestamp/query `gpu_water_profiler.hpp`, OpenXR host DirectGPU/ACK.
- **가설 1 CPU:** 많은 draw 호출에 따른 state getters·WVP·StateBlock cache invalidation·스테레오 중복 CPU 처리.
- **가설 2 GPU:** 투명 overdraw/RT 전환/스텐실/large eye target, 많은 오프스크린 패스.
- **가설 3 전송/시간:** DirectGPU producer/host frame ID 불연속, consumer reuse, shouldRender/ACK, 오래된 pose의 xrEndFrame 재제출.
- **실험:** 동일 exact SHA/설정으로 (a) 빈 구간 (b) 건물 (c) 모래 (d) 모래 튐 (e) 물/유리 각각 120초 측정. 기록: app draw-count main/offscreen/HUD/fallback, CPU draw-submit 시간, GPU P50/P95/P99, async query 미완료/invalid 수, L/R pose/frame ID, produced/accepted/ack/reused/late count, xrWaitFrame→xrEndFrame, runtime frame miss. 텔레메트리 enabled/disabled A/B도 수행해 probe 자체 오버헤드 분리.
- **판정:** GPU 시각과 CPU 벽시간을 동일 지표로 혼동하지 말 것. D3D timestamp `Begin/End` 간 GPU 작업 소요엔 idle gap이 섞일 수 있으므로 단일 alpha draw 비용으로 단정 금지. GPU 시간이 spike 없이 stale/reuse만 증가하면 GPU 렌더 최적화 대신 host timing/ACK부터 수정.
- **후속 수정:** 측정상 우세한 단일 원인만 변경. State cache fast-path는 세대 가드 보존, 투명 draw 스킵·품질 저하 금지, 렌더링 결과의 좌우/alpha/depth/sRGB 동일성 검증.
- **성능 목표:** 72 Hz의 프레임 예산은 약 **13.89 ms**. 평균 FPS뿐 아니라 P95/P99 프레임시간과 끊김 연속성을 비교. HMD/VDXR 실측 전 성공 선언 금지.

### P1 / 차량선택 색상·반투명·흰색/갈색 화면
- **기존 관측:** DXVK 기준 이미지 정상이라는 과거 비교와 DX9Ex 네이티브 차이가 있으나, 이것만으로 원인을 확정할 수 없다.
- **외부 근거:** E05·E06 StateBlock 부분 캡처; E09 shader/RT hunting.
- **검증 우선순위:** StateBlock Apply 전후 shader epoch/c64 → texture stage/sampler/sRGB/alpha → RT format/viewports → resolve/copy → host fallback cached image 여부. 메뉴 only/gameplay only 차이, DirectGPU vs fallback 분리.
- **금지:** 전체 색 공간에 상시 gamma 보정, 정상 DXVK 이미지를 강제로 반대편에 복사, shader fingerprint만 같다고 상태가 같다고 판정.

### P1 / 출발선 그림자·렌즈 외곽·투명 효과의 양안 차이
- **근거:** E15·E16은 screen-space 효과를 눈마다 독립 수행할 때 불일치가 생길 수 있음을 보여주는 **일반 원리**. OutRun이 SSAO/SSR을 쓴다는 주장은 아님.
- **측정:** original producer/RT/depth/stencil/cull, alpha & blend, eye WVP, projection, render-target identity를 같은 frame 내 두 눈에서 비교. R29 zero-disparity 'fragile effect'와 full stereo world draw의 정책 선택을 검증.
- **금지:** 화면 분리 = 무조건 zero disparity로 보정, 그림자/물/렌즈 draw 누락을 최적화로 계산.

### P2 / 메뉴 `< >`·rival 마커/차량선택 UI 이동
- **원본 근거:** E01+E02는 메뉴와 월드 projected rank marker가 UI scale만으로 끝나지 않는다고 보여준다. 원본 코드의 integer pixel truncation 보정도 포함.
- **대상:** `src/hooks_uiscaling.cpp`, `src/vr/game/rank_marker_fraction.hpp`, `src/vr/ui/ui_side_spacing.hpp`, R30 HUD semantic eye-plane. 메뉴/차량선택/rival/world marker는 각각 producer와 공간 소유권이 다름.
- **검증:** 4:3·16:9·21:9, 좌우 eye crop/pose, 고정 위치/헤드 회전, 원래 UI 크기와 게임플레이 HUD 82% 목표 분리. F11 정상 동작은 유지.

### 장기 연구 / foveated·reprojection·DX11/DXVK 교차 비교
- E12의 vrperfkit은 **D3D11** OpenVR/Oculus 대상. DX9Ex+OpenXR에 플러그인을 복사해도 호환을 기대할 근거 없음.
- E11 depth 재구성은 투명물체·가림·화면 가장자리 disocclusion, 잘못된 depth 버퍼가 위험. **정식 R84 양안 렌더링의 대체재가 아님**.
- E03 UEVR synchronized sequential은 Unreal 내부 동일 tick 복제 능력에 의존. OutRun에서는 simulation/FFB/input 1회 제한을 유지하고 CPU/GPU 양안 draw만 증명된 경우 최적화 검토.
- DX11/DXVK는 코드 owner가 다르므로 구현을 이 브랜치에 섞지 않고, shared-knowledge에 **텍스트·수치 증거만** 이전한다.

## 4. '열 번마다 결함/최적화 후보' 연구 검토를 위한 반복 체크리스트

각 10회 검토 묶음에 다음 관점 하나씩 차례로 부여하고, 동일 ID 중복 기록 금지.

1. 원본 게임 producer/주소·화면 UI 논리 좌표
2. call/queue/D3DX delayed GPU submission lifetime
3. VS/PS·c64 원본 WVP/pose/frame 세대
4. StateBlock/texture/sampler/sRGB/RT viewport/scissor 복원
5. depth/stencil/shadow/transparent·MRT 위험
6. R29/R30/R31/R33 중복 replay/불필요한 draw·CPU cache
7. x86 game↔x64 host shared memory producer/ACK generation
8. OpenXR wait/begin/end·predictedDisplayTime, compositor miss
9. 성능 측정의 asynchronous query 결과와 오버헤드/false attribution
10. Known-good 화면/음성 테스트/CI 및 HMD exact-SHA 회귀

매 10회 기록에는 `finding_id, symptom_id, candidate_file, prior_implementation, source_evidence_url, hypothesis, disproof_case, affected_feature_id, exact_sha, CI, HMD, rollback`를 필수로 둔다. 증거 없는 신규 해결책을 'FIXED'로 기록하지 않는다.

## 5. 실제 개발용 순서 / 검증 계약

| 단계 | 작업 | 진행 조건 | 완료 증거 |
|---|---|---|---|
| R0 | active lease 및 정확 SHA/실제 R84 DLL·host 확인 | 기존 TASK/feature와 충돌 금지 | 현재 material+package SHA 및 owner |
| R1 | 렌즈/+TIME 중 하나의 producer→GPU sink 계보 확정 | upstream 코드 및 기존 보호 가드 재사용 | 동일 frame/call/pose/eye serial 로그 |
| R2 | 그 결함 1개에 한정한 최소 C++ 변경 | 양안 이전/이후, negative/Reset 검사 추가 | 의미 있는 material commit과 실제 test |
| R3 | default R84 + R26_SAFE Windows x86, host x64, ACTIVE ZIP + selector/rollback + Domain + 영향 HUD/Full Source | exact SHA 필수 | GitHub Actions exact-SHA SUCCESS |
| R4 | Quest 3/VDXR 72Hz 실기에서 중심 렌즈/+TIME/GOAL/메뉴/그림자/입력/밀집 구간 체크 | 같은 SHA 런타임 로그 | `RUNTIME_VALIDATION` 정식 갱신 |
| R5 | 건물/모래/water 병목 하나씩 프로파일링 후 최적화 | 비동기 query/host lag 분리 | FPS P50/P95/P99 및 시각 품질 A/B |

**중요 거부 기준:** ① 새 화면 결함 ② 원본 게임 tick/input/FFB 두 번 호출 ③ 불일치 left/right pose ④ fallback image에 의해 게임화면 갈색/흰색 ⑤ GPU query busy-loop ⑥ Reset/VR toggle 후 stale state ⑦ R26 패치만 했는데 R84 완료로 기재 ⑧ exact-SHA CI만으로 HMD 성공 주장. 발생 시 해당 feature에 묶어 재검증하고 롤백한다.

## 6. 향후 원문 재검증 및 저작권

- 논문은 제목·DOI와 핵심 발견만 요약하며 PDF·타 프로젝트 소스를 리포지터리에 무단 복제하지 않는다.
- 외부 저장소 API/라이선스/최신 커밋 상태와 버전 차이를 **실제 이식 직전** 재확인한다. 특히 UEVR/vrperfkit의 타 엔진·타 API 구현은 문서 사례일 뿐 단일 사용 가능한 패치가 아니다.
- Microsoft HoloLens 가이드는 특정 장치 한정 사례를 포함하므로, Quest3/VDXR로 그대로 일반화하지 않는다.
- 이 기록은 **연구 기반 백로그**. 이미 구현된 보호 코드를 중복 적용하거나 현재 진행 중인 자동 큐의 feature lease를 선점하지 않는다.
