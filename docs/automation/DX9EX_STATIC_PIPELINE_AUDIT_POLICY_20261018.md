# DX9Ex R84 — 원본 디컴파일 → 물리 Draw → OpenXR 파이프라인 추적 및 수정 방침

기록: 2026-10-18 KST. 사용자 요청: Quest 3 실기 없이 현재의 원본 EXE/APK 역분석 자료로 가능한 실행 분기를 정적으로 추적하고, 확인한 구조적 위험과 실제 소스 수정을 위한 근거·검증 조건을 개발방침으로 보존한다.

**범위:** `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`의 옵션 없는 **R84 메인(R33→R32→R31→R30→R29)**. 참조 검토 기준은 2026-10-18 GitHub HEAD `7c3b5de3cb225ea46c851fa16e49cdddbb580d32` 및 2026-10-18 N100 정적 자료. DX11 개발·DXVK 동결·R26_SAFE 롤백은 변경하지 않는다. **이 문서는 검사·개발 정책이지 C++ 소스 패치, Windows 빌드 성공 또는 Quest3 실기 해결 증거가 아니다.**

## 1. 증거 수준과 정적 분석의 한계

- 원본 `OR2006C2C.exe` SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`. 직접 x86 CALL **569개**, 기존 고정 앵커 **10/10 일치**, Sprite SZ 141개/내장 DDS 1,623개/교체 DDS 경로 238개.
- N100 Ghidra 결과: 인식된 7,238개 함수의 디컴파일 시도 중 **7,237개 성공**, VA `0x00536D82` 1개 실패. 의사 C 코드의 호출 그래프에 **16,811개 서로 다른 FUN_ 가상 호출 간선**이 있으나 간접 호출·점프 테이블·실제 GPU 제출을 완전히 포괄하지 않는다. 성공 출력도 원본 C++의 의미/ABI를 완전 복구했다는 뜻은 아니다.
- **정적으로 판별 가능한 것:** 원본 producer의 소스 호출 관계, 예상 RenderScope, 현재 훅 진입점, D3DX queue/Flush 가능성, R30/R33 admission/veto/fallback 조건, eye GPU 호출 및 상태 복원 코드의 논리적 경로.
- **정적으로 판별 불가능한 것:** 특정 Quest3 프레임에서 실제 선택된 분기·D3D9 상태·셰이더/pose/RT 세대, HMD에서 보이는 양안 정렬, 실제 FPS와 GPU 타이밍. 호출 가능성 ≠ 실제 GPU route 실행 ≠ Quest3 광학 성공. 검증 안 된 화면은 `RUNTIME_VALIDATION=UNTESTED`; 과거 실패 빌드와 새 미검증 SHA를 구분한다.
- 원본 EXE/APK, 전체 디컴파일 C, 게임 DDS/SZ 및 독점 자산을 GitHub에 올리지 않는다. 로컬 원본은 N100 읽기 전용; GitHub에는 오프셋, 독립 분석 및 모드 구현만 기록한다.

## 2. 한 Draw의 필수 검토 순서

`EXE caller/producer` → `hooks_uiscaling.cpp / hooks_textures.cpp / hooks_graphics.cpp` → `render_semantics.hpp (RenderScope, ProducerToken, queue node+registration serial, queue epoch)` → `outrun_renderer.cpp 원본 game c64 WVP/셔이더/pose provenance` → `R33 네 개 물리 Draw*` → `R30 FVF0x142 / XYZRHW / screen` 또는 `R33 HUD / fast world` 또는 `R29 fallback / 원본 단일 Draw` → `좌안+우안 HRESULT / RT, viewport, depth, stencil, WVP 복원` → `x64 host 동일 frame/poseSequence 및 OpenXR EndFrame`.

검토에서 `Draw()`가 성공했다고 `BOTH_EYES_OK`로 집계하지 않는다. 반드시 두 실제 eye 제출과 state restore를 확인한다. 기존 `R33Dispatch`는 source-owned screen 검증 실패 시 이전 road/world WVP를 빌리지 않고 **원본 Draw 1회**로 보존한다. 이 안전 폴백 자체를 무조건 제거하지 말고, 어떤 admission 증거가 없어서 원본 단일 Draw가 되었는지 복구한다.

`R30SupportTryFixedFunctionProjectedRankIndexed`와 Primitive/PrimitiveUP/IndexedUP의 기존 R84 FVF `0x142` 지원은 **이미 구현된 경로**다. 이전에 없는 것으로 재보고하거나 기존 정확-owner 방식을 전역 2D 강제 스테레오로 바꾸지 않는다. `R30ExecuteXyzrhwStereo`·`R33TryHud`·`R33TryFastWorld`의 원본 결과, 우안 결과, 복원 결과를 구분한다.

## 3. 이번 리뷰에서 확인된 소스 경계 — 개발자가 해결할 검증 과제

### A. `hooks_textures.cpp::TagDirectVrSpriteNodes` 이전 tail 직접 역참조 (구조적 위험, 재현 원인 미확정)
- `SnapshotVrSpriteTails`가 이전 `root->tail_4` 포인터를 저장하고, 이후 `TagDirectVrSpriteNodes`가 `before[prio]->next_0`를 직접 읽는다. 원본 producer가 해당 priority list를 해제·재연결했다면 이전 포인터의 **현재 연결 여부를 증명하지 못한 접근**이다.
- `src/vr/game/sprite_queue_tail_proof.hpp::FirstVerifiedAppendedNode`는 **현재 root부터 bounded walk로 이전 tail 및 새 tail의 연결 여부를 입증**하는 기존 안전 헬퍼다. `hooks_uiscaling.cpp::TagAppendedNodes`는 정확한 +TIME/GOAL/rank producer에 그 헬퍼를 이미 사용한다.
- **수정 조건:** `hooks_textures.cpp`의 일반 직접 태그 경로도 안전한 동일 도달성 증명을 사용하되, 현재 이미 안전하게 동작하는 exact-parent 태그를 유지한다. 리스트 재구성/oldTail 분리·재사용/빈 priority/순환·긴 리스트/새 tail 불일치/동일 노드 재사용 음성 테스트를 우선 작성한다. `FirstVerifiedAppendedNode` 자체와 중복 정책을 무턱대고 다시 구현하지 않는다. 실기에서 노드가 실제 해제되었다고 단정하지 않는다.

### B. `RegisterSpriteNodeScope(node, scope)`의 원본 producer token 공백 (관찰된 소스 호출, 시각 문제 원인 후보)
- `hooks_textures.cpp::TagDirectVrSpriteNodes`에서 scope만 전달하므로 기본 `ProducerToken::None`이다. 이미 존재하는 exact-parent `hooks_uiscaling.cpp` 태깅이 해당 노드를 올바르게 재분류할 수 있으므로, **모든 HUD가 무조건 untagged라는 주장은 금지**한다.
- 정확한 x86 `CALL rel32`/검증된 return RVA 또는 소유자 범위가 확정된 생산자에서만 token을 부여한다. 간접 CALL, 잘못된 `returnAddress - 5`, 공통 문자 함수 `0x004BA9D0` 자체를 전부 동일 producer로 승격하는 조치는 금지한다. `CurrentQueueNode`, `SpriteQueueNodeEpoch`, node registration serial, `CurrentRenderProducerToken`, `CapturePhysicalDrawCommand`에서 실제 물리 Draw까지 연쇄 확인한다.
- 혼합 producer의 D3DX `Draw` → `Flush/End`는 N:1 배치일 수 있다. 원본 source가 살아 있지 않으면 previous road/HUD/GOAL scope를 임의 상속하지 말고 `PROVENANCE_UNKNOWN`으로 기록한다.

### C. R30 조기 stereo 경로의 양안 계측 증거 공백 (확인된 진단 한계)
- `src/vr/game/universal_draw_trace.hpp` 및 `stereo_renderer_r33.cpp`는 R33 HUD 직접 경로의 양안 evidence를 집계한다. R30 FixedFn/XYZRHW **early-exit**의 성공 상태는 R33 callback을 통과하지 않으므로 `noR33EyeEvidence`이며 `mono`라는 뜻이 아니다.
- 기존 route/family 5초 집계와 `tools/analyze_vr_screen_traces.py`는 이미 있으며 재구현 대상이 아니다. 개선 대상은 `R30ExecuteXyzrhwStereo`의 LEFT/RIGHT `HRESULT`, eye RT, WVP/PROJECTION, viewport, Depth/Stencil 복원 결과를 같은 `physical_draw_id`에 연결하는 **선택적 bounded 상세 계측**이다. F11은 외부 ImGui/host 결과를 별도로 합친다.
- `E_NOTIMPL`은 눈 한 개 성공도 실패도 뜻하지 않는다. R30 조기 반환 직후 R33/R29 또는 원본 Draw까지 이어진 실제 최종 분기를 구분한다. StateBlock recording, aux RT, mono/recovery, resync 실패를 화면 결함으로 자동 판정하지 않는다. per-family 집계만으로 1 producer ↔ 1 Draw ↔ 2 eyes ↔ 1 XR frame 귀속을 주장하지 않는다.

## 4. 기능별 원본 생성자 → 정상 의도 경로 및 검사 지점

| 기능/기존 feature | 원본 생산자/자산 근거 | 안전한 VR owner 및 확인할 지점 |
|---|---|---|
| **6th/6** `DX9EX:VIS:HUD_GAMEPLAY` | VA `0x004B9D80`, 첫 `0x2B005F` sprani → 별도 clip digits | `ScreenHud` + native FVF142/VS/XYZRHW 각 분기; 오른쪽 눈도 모든 sibling 제출. 차 위 rank와 합치지 않음 |
| **차 위 1~5위** `DX9EX:VIS:RANK_MARKERS` | VA `0x004BAD20`; `Calc3D2D`/`0x00449940`, 호출 RVA `0xBB0FB` 등 | `ProjectedWorldMarker2D`; 원본 차량 앵커·depth·queue node/pose를 유지하여 eye별 투영; ScreenHud 평면으로 내리지 않음 |
| **+TIME** `DX9EX:VIS:EXTENDED_TIME` | VA `0x00498670`; sprite RVA `0x9898E,0x98A36,0x98AC6`, 숫자 RVA `0x989AD,0x98A89,0x98A10`; `39229D64` | sprite 3종+숫자 3종, immediate/queued/D3DX delayed의 각각 owner; `StageExtensionTime`과 정확 GPU Flush/End 배치의 경계; ordinary GOAL 오염 금지 |
| **GOAL/시간/기록** `DX9EX:VIS:GOAL_PROGRESS` | `0x004973C0` → `0x004B9200`; `0x004974E0` number; `CBF8ECBF`, 결과 패널 `C598919A` | 중간 퍼센트·최종 기록·sprite/글리프 별 ScreenHud 및 source; `ResultProgress`, `ResultTextB9200` 등을 구분 |
| **렌즈 중심점** `DX9EX:VIS:LENS_FLARE_CENTRE` | D3A5→C980→C993, `0x570002`; 원본 VA `0x0040CBC0` 소속 | 정확한 c64 `call/pose/shader/draw` provenance가 있을 때만 WorldBillboard 양안. 외곽 원 C9A0/CABE/SkyGlow는 별도 |
| **ESC 화살표/메뉴** `DX9EX:VIS:ESC_MENU` | 원본 pause SpriteNode/shell | `pause_menu_eye_affine.hpp` exact pause owner의 공통 per-eye optical plane. F11 ImGui는 별도 |
| **F11** `DX9EX:VIS:F11_MENU` | 외부 ImGui overlay | 원본 EXE 스프라이트로 추정하지 않음; font atlas/viewport/optical placement/input hitbox와 host 합성 확인 |
| **메인 메뉴** `DX9EX:VIS:MAIN_MENU` | `SUMO_FE_CVT`, 게임 D3DX matrix | source 4:3/16:9/21:9 containment과 `vrhost/src/main_r23.cpp` menu quad/opticalCoverage의 중복 확대·축소·crop 판별 |
| **차량 선택** `DX9EX:VIS:VEHICLE_SELECT` | `SELECTOR_CVT` 31 DDS/3D 차량 | 원본 UV↔DDS 크기, StateBlock, sampler/sRGB, RT/Depth/alpha 및 full-width 영역; 색상/흰색 원인을 분리 |
| **SkyGlow/하늘** 기존 sky feature | Game world original WVP/c64 | World stereo에서 shader/pose와 RT/Depth restore 확인; ScreenHud flatten 금지 |
| **출발 그림자** 기존 shadow feature | 원본 car shadow producer | 차량 WVP·stencil·depth·texture 복원, scene 전환 시 stale 값 방지, HUD plane으로 이동 금지 |
| **콕핏** 기존 cockpit feature | 원본 게임 camera/mode/seat | NATIVE/CAR basis 전환과 pose/view rebuild epoch, 재센터 및 seat offset의 프레임 간 일관성 검사 |
| **건물/모래/입자 FPS** 기존 성능 feature | World culling/particle/texture upload | CPU visibility와 draw submissions, 양안 중복 GPU 비용, Present/host XR wait를 분리. 72Hz/13.89ms 목표는 HMD 측정 전 성공 아님 |

## 5. 개발 방식과 합격 기준 — 정책만 저장하는 이번 작업은 제외

1. 새로운 defect ID를 임의로 생성하지 말고 GitHub `AGENTS.md`, `docs/VR_WORK_QUEUE.json`, `docs/automation/runs/`에서 **기존 FEATURE_ID/TASK_ID/active lease**를 확인한다. 각 기존 기능은 원본 생성자 → 실제 R84 GPU endpoint → 양안/호스트를 따라가며 **한 완결된 사용자 가시 결함**으로 수정한다. 병렬 writer 충돌 시 기존 소유자를 침범하지 않는다.
2. 관찰한 소스 결함을 정적 반례 또는 fail-before regression으로 증명하고, C++ 실제 구현과 negative tests를 묶는다. 신규 로그만/문서만/조건부 카운터만 작성하고 화면 오류가 고쳐졌다고 종료하지 않는다. 지금 이미 있는 R84 FVF142, strict source WVP, protected sky fallback, Quest sphere visibility helper는 중복 구현하지 않는다.
3. 필수 음성 및 회귀: oldTail unlink/reuse, mixed D3DX batch, unknown caller, node generation/queue epoch 교차 프레임, FVF != 0x142/VS bound, non-game/aux/StateBlock, left OK/right fail, WVP/PROJECTION restore fail, mode/resize/reset/recenter, HUD/World/Lens/SkyGlow 원래 안전한 동작, FFB/input. CPU/GPU 성능 개선은 반복 측정·품질 보존을 별도 요구한다.
4. 최종 **동일 exact SHA**의 DX9Ex Active Win32 x86 game/R84, x64 host, package/selector/R26_SAFE, Domain Isolation, 영향받은 HUD Inspector 및 Full Source Impact, positive/negative/fallback regression을 유지한다. 빌드 성공은 `BUILD_VERIFIED`이며 Quest3/VDXR stereo·화면·FPS는 별도로 `RUNTIME_VALIDATION=UNTESTED` / `NEED_HMD_TEST`이다.
5. 새 git 개발정책 커밋은 별도 Docker/Portainer controller의 배포·hot reload가 아니다. 동일 TASK의 retry/rollover와 이번 docs-only 검토는 새 material 기능 성과가 아니며 **AI2 점수 +0**. 기존 AI1/AI2 점수 혼합 금지.

## 6. 필독 중복방지 참조

- `docs/automation/OUTRUN_VR_REA_RESOURCE_EVIDENCE_20261018.md`: 원본 EXE/APK/디컴파일, 7,237 함수/고유 함수 관계 및 자산 인덱스, N100 위치.
- `docs/automation/R84_UNIVERSAL_GPU_DRAW_TRACE_CONTRACT_20261018.md`: 전체 화면 producer→eye opt-in 계측 계약과 현재 구현 상태.
- `docs/DX9EX_VISUAL_REPAIR_LENS_EXTTIME_20261015.md`: central flare와 +TIME의 좁은 정확 원본 경로, D3DX 스코프 반례.
- `docs/DX9EX_R62_R84_RANK_CALLPATH_AUDIT_20261017.md`: 6th/6와 차량에 붙는 projected rank의 별도 증거.
- `docs/DX9EX_QUEST3_FIELD_REGRESSION_20261017.md`: 테스트한 **구형 SHA의 광학 실패**와 새로운 SHA의 UNTESTED를 구분.
- `docs/DX9EX_R84_MAINLINE_CONTRACT.md`: R84 주 경로와 R26_SAFE 롤백, 정확 SHA CI 규칙.

**결론:** 실기 없이 파이프라인의 정적 분기와 안전성 문제는 점검·수정할 수 있으나, 디컴파일 성공 수나 5초 집계만으로 실제 HMD 경로의 전수 실행/화면 정상화를 선언할 수 없다.
