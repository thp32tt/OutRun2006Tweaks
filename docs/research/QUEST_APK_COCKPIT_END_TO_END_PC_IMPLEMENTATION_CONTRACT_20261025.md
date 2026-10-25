# Quest APK → PCVR 운전석 모드: 전 구간 소스 추적 및 구현 명세 (2026-10-25)

## 0. 목적, 증거, 상태
- 사용자 소유 Quest APK의 ELF `liboutrun_quest_core.so`: SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.
- PC 대상 `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`, R26+HUD 안정화 기준. 이 문서는 게임/런타임 소스를 변경하지 않은 `REVIEW_ONLY` 분석과 이행 계획이다.
- 자료: 2026-10-25 REA/Ghidra 7개 ARM64 함수 Evidence, 20개 원본 ELF 함수, Windows 브랜치 `src/hooks_graphics.cpp`, `src/vr/game/outrun_renderer.cpp`, `src/vr/game/driver_seat_*.hpp`, `src/vr/ipc/host_pose_v3.hpp`, `OutRun2006Tweaks.ini`.
- 등급: **BINARY VERIFIED** 원본 ASM/TLS/호출/상수, **PC CODE VERIFIED** 현재 코드의 정적 경로, **HYPOTHESIS** 경로가 실제 동일 프레임에 겹치는지, **UNTESTED** Quest 3/PC HMD 시각 동등성.
- **완료 판정:** 모듈·정확한 구간·데이터 소유권과 구현 순서는 정의할 수 있지만, 차체 보정의 물리 좌표계, 차량별 유리 메시, 손/핸들 본 등은 아직 미확정. 원저작 C++을 그대로 복원했다거나 현재 구현 가능한 모든 상수가 확정됐다는 의미가 아니다.

## 1. Quest 원본의 시작→끝 실행 경로

| 단계 | 원본 ELF 근거 | 소유 상태 / PC 이행 계약 |
|---|---|---|
| 1. 프레임 진입 | `PcSceneRenderer::render_frame` `0x10CBE9C` | 프레임 인자 `(renderFlags & ~2) == 0x10`, 렌더러 `+0x2AD4` 활성, 게임 메모리 getter `+0x80` vtable `+0x30` 성공. 이 렌더러 플래그는 게임 STATE enum과 1:1로 단정 금지 |
| 2. 운전석 소유 모드 | `0x10CBF3C..0x10CBF58` | guest control length `>0x34A`, game camera `[+0x34A] == 1` 조건에서만 native cockpit correction 활성. Windows 카메라 0/1/2 모두 오프셋되는 현행 정책과 다름 |
| 3. 차체 보정 생성 | `0x10CBF6C..0x10CC2FC` | guest frame `+0xB0..+0xEC`와 `+0xF0..+0x12C`의 각각 16개 float로 16-float `cockpit_body_correction` TLS 계산. 별도 211-operation C++ 연구용 복원본 및 3개 합성 fixture 존재 |
| 4. 일시적 변환 중립화 | `0x10CC300..0x10CC36C` | guest `+0xF0..+0x12C` 16 float를 정확한 identity로 바꿔 해당 render 호출 범위에 한정. 게임 시뮬레이션 카메라를 영구 덮어쓰지 않음 |
| 5. 차체 렌더링 | `PcSceneRenderer::display_race_car` `0x10C8D00`, `0x10C9288/0x10C929C` | `cockpit_render_active` / `cockpit_vehicle_draw` TLS로 소유권 구분. 표시 객체가 정확한 player인지 원본 mesh/draw 별 추적 필요 |
| 6. 운전자·승객 | `Draw::disp_514c30` `0xD60FD4`, `0xD610E8/0xD61124` | `cockpit_occupant_draw` 별도 TLS, 16-float correction 소비. 운전자만 선택적으로 숨기고 동승자 유지; 실제 본 인덱스/리그 연결 미복원 |
| 7. 유리 렌더링 | `Flush::draw_404700` `0x10B9894`, 핵심 조건 `0x10B9F68..0x10BA05C` | `DrawEntry.flags&2`, `pass==1`, DSTBLEND 20==6, 알파 0.55/0.425 ±0.001, SRCBLEND 19==2/5. 조건 충족 시 per-draw opacity=0.25, premult flag 별도; 모두 reset. **비트2 생산자 및 유리 메시는 미확정** |
| 8. 최종 GPU shader | `GlD3D9Device::flush` `0x2FCFDC`; shader generator `cockpit_fragment` `0x2F7734` | TLS opacity/premult 읽어 GL shader 적용; Windows에는 D3D9 상태/픽셀셰이더/좌우 눈별 개별 색·깊이 출력을 대응 |
| 9. HMD 위치·양안 | `XrRig::locate` `0x2D69C8` | `xrLocateSpace` 결과/valid flags `&3 ==3`, `xrLocateViews` count=2 + flags `&3==3`일 때 inverse/compose 두 눈에 출력. yaw recenter/orientation option 존재 |
| 10. 정상/예외 종료 | `0x10CC78C..0x10CC7E4`; unwind `0x10CC910..0x10CC97C` | 16/16 guest float 복구 후 cockpit-active TLS=0. 양쪽 종료 경로에서 성공적으로 확인. 기타 TLS의 예외 경로는 추가 조사 필요 |

실제 XR 프레임 취득/제출·네이티브 GPU 패스 호출 순서는 일부 가상 함수/콜백이므로 위 표는 의존성 순서이며 전체 실행 타임라인을 100% 증명한 것이 아니다.

## 2. Windows 현재 코드: 정확한 후킹 지점과 불일치

| 기존 Windows 지점 | 현행 동작 | 구현시 수정 범위 / 위험 |
|---|---|---|
| `src/hooks_graphics.cpp:254-275` `VRDriverSeatCameraEligible` | `PersistentDriverSeatSessionEligible(enabled, gameplay)`가 원래 카메라 모드와 timer를 고려하지 않음 | native mode1의 **착석 anchor 승인**과 사용자가 요청한 session latch를 분리. 모드 0/2에도 bumper/외부 카메라를 강제로 착석 좌표로 옮기지 않는다. 이전처럼 mode/tick 하드 재평가로 화면이 매 프레임 튀지 않도록 presented-frame 단위로 결론을 확정 |
| `src/hooks_graphics.cpp:169-238` `VRDriverSeatCameraPose` | `cam_pos_F8/look_pos_104`에서 매 호출 좌표계 산출; 마지막 정상 좌표는 player 포인터 변경/함수 내부 gameplay false일 때만 초기화 | **현재 OFF일 때는 이 함수를 호출하지 않으므로 gameplay false 분기를 통한 cache 정리는 보장되지 않음.** 같은 vehicle로 OFF→ON 후 invalid 입력 시 이전 pose가 다시 선택될 수 있다. frame ID, owner ID, space generation/차량 변경으로 캐시를 스코프화하고 무기한 재사용 금지 |
| `src/hooks_graphics.cpp:2064-2134` `CalcCameraMatrix_dest` | eligibility를 구한 다음 게임 pos/look를 임시 변경, 원본 `CalcCameraMatrix` 후 복원 | 시뮬레이션 메모리를 수정하지 않는 독립 seat-view staging으로 분리 권고. 차체 렌더·driver suppress·near와 **하나의 프레임 snapshot** 공유 |
| `src/hooks_graphics.cpp:2138-2169` `Clr_SceneEffect_dest` | effect 내부 원래 camera, 종료 후 cockpit view를 다시 생성 | effect/world viewport 경계와 재계산 횟수 로깅. 합성 프레임에서 seat basis 재선택 금지. near plane 및 camera 복원 all-exit 보장 |
| `src/hooks_graphics.cpp:290-384` | `EXE+0x69764` 정확한 player EBX라면 full-car state1; `EXE+0x114C10` driver-heroine 테이블 식별 후 driver만 hide | 이 두 훅의 install atomicity는 유지. 다만 각각 `Active()`가 현재 카메라를 **다시 판정**하므로 frame decision ID를 통일할 것 |
| `src/hooks_graphics.cpp:395-454` | `EXE+0x697BD` temporary display-matrix 1.15x INI scale | Quest 네이티브 고정 1.15배 증거 없음. calibration 전 1.0 우선, player만 변경하고 원본 world/physics 보존 |
| `src/hooks_graphics.cpp:463-509` | `EXE+0x4901` 전체 material path에서 단순 blend candidate 최대 32개 로그 | 후보가 실제 player windshield임을 증명하지 못함. model/object/material/texture/PMT leaf + owner/player + pass/blend + eye ordinal 모두 확정 전 opacity write 금지 |
| `src/vr/game/outrun_renderer.cpp:1325-1379` | `ApplyCullingCameraSync`: HMD pose를 적용한 view로 **동일한** `cam_pos_F8/look_pos_104` 일시 덮어씀 | 이것이 이후 `VRDriverSeatCameraPose`가 읽는 바로 그 필드. 해당 CalcCameraMatrix가 scene 내부 호출되면 head pose가 seat basis로 다시 유입할 수 있음. **위험 정적 확인, 실제 시퀀스 재현 UNTESTED** |
| `src/vr/game/outrun_renderer.cpp:1381-1541` | BeginScene에 host pose 고정, 같은 Present에서 재사용 | owner는 `LatchedPoseEpoch,LatchedPoseSequence,referenceSpaceGeneration,playerID`를 가진 frame snapshot으로 통합. 카메라 원본 수집이 BeginScene 이전인지 정확한 순서 확인 필수 |
| `OutRun2006Tweaks.ini` | DriverSeatView=false; DriverSeatCarSpaceBasis=false; DriverSeatNativeMode=1; **DriverSeatVehicleScale=1.15**; GlassOpacity=0.30 진단뿐 | 최종 옵션/기본값/실제 사용 판정을 하나로 일치시키고, 실패한 차체확대 테스트 설정을 수동 활성화 하지 않도록 한다 |

## 3. 새로 발견된 2개 구조 위험 (PC 소스 VERIFIED)
**A. 컬링 카메라 ↔ 운전석 카메라 교차 변조**
- `ApplyCullingCameraSync`가 `cam_pos_F8/look_pos_104`를 HMD 반영 좌표로 쓰며 `EndScene`에서 원래 카메라로 되돌린다.
- `VRDriverSeatCameraPose`는 같은 두 필드를 seat origin으로 사용한다.
- `Clr_SceneEffect_dest`가 그 스코프에서 `CalcCameraMatrix_dest`를 호출할 수 있다.
- 따라서 runtime 호출 순서가 겹치면 **HMD 위치를 seat anchor에 흡수하고 나서 WVP eye/head transform을 한 번 더 적용**할 구조적 위험이 있다. **호출의 실제 중첩과 진동 원인 확정은 이번 분석으로 증명되지 않았다.** 우선 진단은 `CullingCameraOverridden`, original/borrowed camera hash, `SceneEffectDepth`, game presentEpoch을 동일 로그 이벤트로 남겨 중첩을 재현하는 것이다.

**B. 무기한 last-valid 재사용**
- `VRDriverSeatCameraPose`의 thread_local cache는 *함수 안에서만* 플레이어 포인터 비교 및 gameplay=false reset을 한다.
- 실제 호출자는 `VRDriverSeatCameraEligible`에서 enabled/gameplay 검사에 실패하면 그 함수 자체에 들어오지 않는다.
- 동일 player 주소를 유지하며 OFF→ON이 되고 첫 입력이 무효라면 과거의 last pose가 살아 있고, frame age나 XR/reference-space generation 제한 없이 반환될 수 있다.
- 차기 코드는 cockpit OFF/owner change/recenter/device Reset/scene-invalid에서 명시적으로 cache invalidate해야 한다. 한 프레임 실패한 경우도 타 프레임 stale camera로 조용히 치환 금지.

## 4. 새로운 독립 수치 시험: body-correction 입력은 일반 4×4 모델행렬로 단순 치환 불가
N100 `apk/_analysis_focus/quest_apk_matrix_crossinputs_20261025.py`가 기존 ARM64 211-op reference를 대상으로 old/new 4×4 입력을 조합하여 실행:
- `old=I,new=I` → `diag(-1,-1,-1,1)`.
- `old=I,new=translation(3,4,5)` → 출력 translation `(-3,-4,-5)`.
- `old=translation(3,4,5),new=I` → 출력 translation **`(6,0,10)`**.
- `old=Rz(90°),new=I` → 3×3 출력은 여전히 `-I`, old/new 회전 결합은 직관적 역행렬 합성과 다르게 작동.
- 추가 `quest_matrix_formula_hypothesis_20261025.py`는 회전·이동에 대한 단순 affine 식을 9개 조합으로 반증 (여러 케이스 최대 오차 > 1). **미확정 간단 수식을 소스에 적용하면 안 됨**.
- 핵심: `+0xB0..+0xEC` 및 `+0xF0..+0x12C`가 게임 외부에서 어떤 matrix semantics를 갖는지 Guest/Windows 구조 필드와 결부하는 실증이 필요. 현재 C++ 참조 코드는 FP 산술 실험용이지 차량 seat pose 함수를 대신하지 못한다.

## 5. 구현 준비가 완료되려면 필요한 데이터 구조 (PROPOSED)
```cpp
enum class CockpitPhase { Disabled, Requested, WaitingModeOne, Armed, ActiveFrame };
struct GameFrameSource {
    uint64_t presentEpoch;
    uintptr_t playerIdentity;
    uint64_t vehicleGeneration;
    uint8_t nativeCameraMode;
    uint16_t switchTicks, delayedSwitchTicks;
    bool gameplay, nativeCamValid, bodyValid, sceneEffect;
    Matrix4 originalGameCamera; // never the borrowed culling-camera override
    Matrix4 playerWorld;        // exact player only, unmodified
    Matrix4 guestOldFrame;      // APK offset +0xB0, semantics TBD
    Matrix4 guestNewFrame;      // APK offset +0xF0, semantics TBD
};
struct XrFrameSource {
    uint64_t poseId;
    uint32_t spaceGeneration;
    bool spaceOrientationValid, spacePositionValid;
    bool viewOrientationValid, viewPositionValid;
    unsigned viewCount;
    Pose eyePose[2];
    Fov eyeFov[2];
};
struct CockpitFrameDecision {
    uint64_t presentEpoch, poseId;
    uintptr_t playerIdentity;
    bool active;   // ONE flag consumed by camera/full car/occupant/near/glass
    Matrix4 seatWorld;
    Matrix4 bodyCorrection;
    Matrix4 eyeWorldView[2];
};
```
No project header or ABI offsets are implied by these *proposed* types. Preserve stock on any invalid snapshot; make all outputs immutable after frame commit, including second BeginScene before Present. Native mode1 **arms** in one settled sample; counter pulses after arming must not blink the cockpit; actual mode0/2 transition should exit atomically to stock or use an explicitly designed separate-view mode. Never use prior frame car pose as XR pose. Resolve recenter generation atomically before recalculating.

**Correct integration choice:** keep game simulation camera unmodified; capture its original state before culling override, then apply seat transform only to permitted world/cockpit WVP rendering. `SceneEffect`, 2D HUD/menu and spectator views remain on their established paths. Preserve existing R26+HUD and x86 D3D9 c64 capture rules.

## 6. Stage-by-stage implementation acceptance, test evidence
1. **P0: deterministic trace:** Add bounded log (ring <= 2048 events) with `presentEpoch / hostPoseSequence / playerIdentity / nativeMode / cameraOverrideActive / sceneDepth / originalNativeCam / seatCandidate / seatCommitted / WVPType / eyeOrdinal`; abnormal discontinuity > chosen threshold triggers one dump only, no 16GB verbose default. Create no-headset replay fixtures from recorded sequence.
2. **P0: prove capture order:** Test whether `CalcCameraMatrix` occurs before/after BeginScene and when `Clr_SceneEffect` runs. Confirm camera owner saved/restored and no culling camera doubles into seat. If not proven, block gameplay patch.
3. **P0: atomic owner:** mode0→1→2, pause/resume, START65→GAME→GOAL, recenter, player vehicle replaced, host reset/referenceSpace generation changed: one coherent session/frame decision, driver body and near plane never disagree.
4. **P0: exact matrix:** compare original APK 211-operation reference against independent portable D3D row-vector math for **nonzero translation, yaw/pitch/roll, loop, scale and an arbitrary 6DoF HMD delta**. Verify original guest +0xB0/+0xF0 inputs with field-name/owner reads, and normal/unwind byte-for-byte restore.
5. **P0: actual PCVR camera:** stable Quest3 pose across modes, cockpit forward/right/up calibration per vehicle; driver head not teleported inside player shell, no zoom oscillation. Verify both eyes IPD/cant/FOV, yaw-only recenter, game-time camera unaffected.
6. **P1: player & passenger:** identify exact player car pointer/model and driver/heroine set; full player only, driver only hidden, passenger untouched, NPC unchanged. Catch all game/mode changes, resets and nested callbacks.
7. **P1: glass:** match each actual front/side windshield mesh/texture per car, PMT draw owner + entry flags producer, effective 19/20 blend and color alpha. Only qualified player draw gets 0.25 per-draw factor; restore on skipped/error path. Avoid duplicate per-eye draw and preserve water, smoke, shadow and HUD.
8. **P1: hands/rig:** derive controller grip/steering angle ↔ rig bone, optional hand tracking/fallback steering-wheel controller. Preserve original wheel MOZA R3 FFB/input; original APK XR hands are not proof of complete rig transform.
9. **P1: CI/test package:** only GitHub Actions x86 DLL/x64 host; build & debug packages must contain START_HERE.cmd or RUN_*.bat, PS1, INI, DLL, host EXE. CI exact HEAD/commit, HMD UNTESTED until real headset results.

## 7. Stop/go recommendation
- **GO for bounded diagnostic + pure fixture improvements.** Safe R26+HUD remains default; DriverSeatView remains false.
- **NO-GO for blind live seat/glass source injection** until capture-order data and matrix semantics are confirmed. Turning off `CullingCameraSync` is only an A/B diagnostic, **not** a proven permanent fix, and must not regress widened VR frustum performance.
- Primary immediate target: **one immutable per-Present camera/vehicle/host-pose snapshot and field-owner separation**, then validate actual headset viewport before adding visuals.

Status: `DOCS_ONLY=YES`; `GAME_SOURCE_CHANGED=NO`; `CI_BUILD=NOT_RUN`; `QUEST3_PC_RUNTIME=UNTESTED`.