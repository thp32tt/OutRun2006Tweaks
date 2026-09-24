# Wheel / FFB architecture — v0.1

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

This document describes the release architecture of the `wheel-ffb` branch used for **OutRun2006Tweaks Wheel FFB v0.1**.

### Scope

v0.1 was developed primarily around a **MOZA R3** and the tested default path is:

- input: SDL3 raw multi-device input;
- force feedback: Windows DirectInput COM;
- build: Win32 x86;
- game update rate: OutRun's native 60 Hz gameplay loop.

Other DirectInput wheels may work, but the R3 is the main hardware validation target for this release.

### Input ownership

With `UseNewInput=true`, **Input Bindings is the only input-binding owner** for steering, pedals, buttons and menu controls. Wheel, separate pedals, shifter, button box and gamepad can all contribute to one player at the same time.

The older legacy DirectInput path remains available only as a compatibility fallback. The v0.1 release documentation no longer directs users through the old guided Quick Setup flow.

Bindings are live while editing, but manual changes should be persisted with **Save & Return to game**. Named input profiles remain available for complete multi-device layouts.

### FFB ownership

The wheel FFB backend is a single DirectInput COM owner. It pins output to the selected DirectInput device identity instead of whichever similarly named interface is enumerated first.

The main steering model contains:

1. **Physics SAT** — estimates front slip from vehicle motion, steering and yaw, then derives aligning torque from lateral force and total trail.
2. **Natural SAT fallback** — progressive steering-angle-based restoring torque when the physics sample is unavailable or Physics SAT is disabled.
3. **Mechanical / caster trail** — remains active with front lateral load instead of acting as an artificial center spring.
4. **Low-speed spring** — only a stabilizer near low speed; deliberately reduced on the tested R3 feel.
5. **Dynamic damping** — steering-velocity resistance that releases as the front end scrubs or the car slides.
6. **Grip-loss unloading** — reduces steering load as usable front grip falls away.
7. **Road / tire / gear / collision effects** — transient tactile effects layered on top of the structural steering signal.

### Force Feedback UI

The F11 **Force Feedback** page owns output-device selection and game-side tuning. `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT` provide starting profiles, while **Save Force Feedback** persists live edits.

The **Advanced FFB tuning** section exposes supported lower-level values such as Spring Saturation, Weight Transfer, Force Build Slew Rate, Countersteer Release Rate, Pneumatic Trail Response Lead and optional wheel-response correction. These remain live tuning controls; wheel-specific response data is stored with the wheel profile rather than a generic named feel profile.

### MOZA R3 compatibility path

The R3 driver can accept creation/update of a DirectInput sine effect while the physical road texture remains effectively inaudible. v0.1 therefore forces road/slip vibration through the **ConstantForce fallback** on the R3 path.

Road contact is sampled across all four wheels using the game's original surface-mask LUT. The compatibility layer now preserves each wheel's raw surface mask, resolved roughness and stage-specific water classification instead of reducing the road to one maximum scalar. It distinguishes:

- **mixed non-water rough surface** — meaningful spread while part of the car is on a real rough curb/shoulder;
- **fully rough non-water surface** — the sampled non-water wheels are all on a high-roughness surface;
- **stage water** — retained for the original core water/splash response, but deliberately excluded from the fixed curb-strength and SAT/damper-unload compatibility boost;
- **ordinary surface** — no extra tactile override.

This matters on Metropolis, Cape Way and Imperial Avenue (and their reverse variants), where the reconstructed Xbox LUT can map surface mask `0x2` to a high roughness value while also explicitly marking it as water. Treating only the scalar as a curb made those water contacts eligible for the stronger curb envelope. The stage-aware path keeps the water effect while avoiding that false curb classification.

Mixed and fully rough curb states still use the same strong tactile profile so vibration does not disappear when the remaining wheels cross fully onto the curb. Snowy Mountain and Ice Scape (including reverse variants) retain the bounded snow-curb material latch; normal snow remains attenuated while a confirmed curb transition gets the existing short compatibility boost. See `docs/reverse/C2C_STAGE_FFB_MAP.md` for the verified stage IDs and surface-mask table.

### Device selection and safety

- Clean R3 setups auto-match the DirectInput product substring `R3 Racing Wheel`.
- Once a device is selected, the exact DirectInput GUID is persisted.
- Focus loss, state transitions and device loss clear active effects.
- Device reconnect schedules normal DirectInput reinitialization.
- Manual left/right direction tests are hard-capped at 20% and only run during active gameplay.
- A wheel-output owner suppresses duplicate gamepad rumble ownership where required.

### R3 release feel

The release retune intentionally moved away from a heavy artificial spring:

- low-speed spring reduced;
- spring saturation reduced;
- SAT remains the main cornering load;
- road texture is strengthened for the ConstantForce fallback;
- tire-slip buzz is kept low;
- gear-change feedback is made clearly perceptible;
- snow/curb tactile handling is R3-specific and does not globally weaken ordinary cornering.

These are starting values rather than a guarantee for every firmware/Pit House configuration.

### Diagnostics

The wheel backend also keeps the reconstructed Xbox C2C `CalcVibrationValues()` output as a **read-only reference witness**. The logged `origXboxL/origXboxR` (compact log) and `xboxLeft/xboxRight` (10 Hz telemetry) values are the two XInput rumble-motor envelopes; they are not left/right steering torque and do not alter the DirectInput force model. They are intended for correlating current DD-wheel behavior with original game vibration timing and public Lindbergh drive-board observations.

`OutRun2006Tweaks.log` records:

- selected DirectInput FFB identity;
- effect creation/fallback status;
- SAT and final output diagnostics;
- stage-aware road diagnostics including stage ID/name, four raw surface masks, per-wheel roughness, water-wheel mask, non-water min/max roughness, mixed/full-rough state and temporary tactile scaling.

For a useful hardware report, include the full launch → race → exit log plus wheel-base model, driver and firmware version.

### Build and release validation

CI runs:

- `tools/verify_wheel_ffb_current.py` against the consolidated production source;
- the production wheel FFB math test;
- Win32 Release compilation;
- PE32 payload checks and compiled marker verification;
- final artifact upload from the exact release commit.

The v0.1 release workflow waits for the matching successful Build workflow before publishing the ZIP.

### Credits / license

The implementation is based on `emoose/OutRun2006Tweaks` and incorporates design lessons from public OutRun wheel work including `hyp36rmax/multi-device-input` and `d-b-c-e/OutRun2006Tweaks-FFB`.

Repository license details are in `LICENSE.md` and `THIRD_PARTY_NOTICES.md`. The public binary ZIP receives one consolidated `LICENSES.txt` generated from the dependency source trees used for that build.

---

<a id="한국어"></a>
## 한국어

이 문서는 **OutRun2006Tweaks Wheel FFB v0.1**에 사용된 `wheel-ffb` 브랜치의 릴리즈 구조를 설명합니다.

### 범위

v0.1은 주로 **MOZA R3**를 기준으로 개발했으며 기본 검증 경로는 다음과 같습니다.

- 입력: SDL3 Raw 멀티 디바이스 입력
- 포스피드백: Windows DirectInput COM
- 빌드: Win32 x86
- 게임 업데이트 주기: OutRun 기본 60 Hz 게임플레이 루프

다른 DirectInput 휠도 동작할 수 있지만, 이 릴리즈의 주 하드웨어 검증 대상은 R3입니다.

### 입력 처리 구조

`UseNewInput=true`일 때 **Input Bindings가 스티어링, 페달, 버튼, 메뉴 조작에 대한 유일한 바인딩 경로**입니다. 휠, 별도 페달, 시프터, 버튼박스, 게임패드가 동시에 한 플레이어의 입력에 참여할 수 있습니다.

기존 레거시 DirectInput 경로는 호환성 폴백 용도로만 남아 있습니다. v0.1 문서에서는 예전 Guided Quick Setup 흐름을 기본 설정 방법으로 안내하지 않습니다.

바인딩은 편집 중 실시간 적용되지만, 수동 변경 사항은 **Save & Return to game**으로 저장해야 합니다. 완전한 멀티 디바이스 구성을 위한 이름 지정 입력 프로필도 사용할 수 있습니다.

### FFB 처리 구조

휠 FFB 백엔드는 하나의 DirectInput COM 출력 소유자로 동작합니다. 비슷한 이름의 인터페이스 중 먼저 열거된 장치가 아니라 사용자가 선택한 정확한 DirectInput 장치 식별자에 출력을 고정합니다.

주 조향 모델은 다음 요소로 구성됩니다.

1. **Physics SAT** — 차량 움직임, 조향각, yaw에서 전륜 슬립을 추정하고 횡력과 총 trail을 이용해 self-aligning torque를 계산합니다.
2. **Natural SAT fallback** — 물리 샘플을 사용할 수 없거나 Physics SAT를 끈 경우 조향각에 비례해 점진적으로 중앙 복원 토크를 생성합니다.
3. **Mechanical / caster trail** — 인위적인 센터 스프링 대신 전륜 횡하중과 함께 유지되는 기계적/캐스터 트레일 성분입니다.
4. **Low-speed spring** — 저속에서만 안정화용으로 사용하며 테스트한 R3에서는 의도적으로 약하게 설정합니다.
5. **Dynamic damping** — 조향 속도에 대한 저항이며 전륜이 밀리거나 차량이 슬라이드할 때 완화됩니다.
6. **Grip-loss unloading** — 사용 가능한 전륜 그립이 줄어들수록 조향 하중을 줄입니다.
7. **Road / tire / gear / collision effects** — 기본 조향 신호 위에 일시적인 촉각 효과를 추가합니다.

### Force Feedback UI

F11의 **Force Feedback** 화면에서 출력 장치 선택과 게임 내 FFB 튜닝을 담당합니다. `Load MOZA R3 Physics SAT`와 `Load MOZA R3 Natural SAT`는 시작용 프로필이며, **Save Force Feedback**으로 실시간 변경 값을 저장합니다.

**Advanced FFB tuning**에는 Spring Saturation, Weight Transfer, Force Build Slew Rate, Countersteer Release Rate, Pneumatic Trail Response Lead, 선택적 휠 응답 보정 등 하위 수준 조정 값이 노출됩니다. 이 값들은 실시간 튜닝 항목이며, 휠별 응답 데이터는 일반적인 feel 프리셋이 아니라 해당 휠 프로필에 저장됩니다.

### MOZA R3 호환 경로

R3 드라이버는 DirectInput sine effect의 생성/갱신 자체는 정상 처리하더라도 테스트한 장비에서 실제 노면 질감이 거의 느껴지지 않았습니다. 그래서 v0.1의 R3 경로에서는 노면/슬립 진동을 **ConstantForce 폴백**으로 강제합니다.

노면 접촉은 게임 원본의 표면 마스크 LUT를 이용해 네 바퀴를 각각 샘플링합니다. 이제 호환 레이어는 노면을 최대 거칠기 하나로 축약하지 않고 각 바퀴의 원시 표면 마스크, 계산된 거칠기, 스테이지별 물 표면 판정을 함께 보존합니다.

- **mixed non-water rough surface** — 일부 바퀴가 실제 거친 연석/숄더에 올라가 의미 있는 거칠기 차이가 생긴 상태
- **fully rough non-water surface** — 물이 아닌 샘플들이 모두 높은 거칠기의 표면에 올라간 상태
- **stage water** — 게임 원본의 물/스플래시 효과에는 그대로 전달하지만, 고정 연석 강도 및 SAT/댐핑 완화 보정에서는 제외
- **ordinary surface** — 별도 촉각 보정이 필요하지 않은 일반 표면

이 구분은 Metropolis, Cape Way, Imperial Avenue 및 각 역방향 스테이지에서 중요합니다. 재구성한 Xbox LUT에서는 표면 마스크 `0x2`가 높은 거칠기 값으로 계산되는 동시에 물 표면으로 명시될 수 있습니다. 예전처럼 거칠기 값만 보면 물을 연석으로 오인해 강한 연석 보정을 적용할 수 있었지만, 스테이지 인식 경로에서는 물 효과는 유지하면서 이 오분류를 막습니다.

mixed/fully rough 연석은 기존과 동일하게 강한 촉각 프로필을 유지합니다. Snowy Mountain과 Ice Scape 및 역방향 스테이지에는 기존의 제한시간형 snow-curb material latch를 그대로 유지해 일반 눈길은 약하게 두고 실제 연석 전환만 짧게 보강합니다. 검증된 스테이지 ID와 표면 마스크 표는 `docs/reverse/C2C_STAGE_FFB_MAP.md`에 정리했습니다.

### 장치 선택 및 안전 처리

- 초기 R3 환경에서는 DirectInput 제품명 `R3 Racing Wheel` 문자열을 자동 매칭합니다.
- 장치를 한 번 선택하면 정확한 DirectInput GUID를 저장합니다.
- 포커스 손실, 게임 상태 전환, 장치 손실 시 활성 FFB 효과를 정리합니다.
- 장치 재연결 시 정상적인 DirectInput 재초기화를 예약합니다.
- 수동 좌/우 방향 테스트는 최대 20%로 제한되며 실제 게임플레이 중에만 동작합니다.
- 필요한 경우 휠 출력 소유자가 중복 게임패드 럼블 출력을 억제합니다.

### R3 릴리즈 기본 감각

릴리즈 튜닝은 강한 인공 스프링 중심의 느낌에서 의도적으로 벗어났습니다.

- 저속 스프링 감소
- 스프링 포화도 감소
- 코너링 하중의 중심은 SAT가 담당
- ConstantForce 폴백에서 노면 텍스처 강화
- 타이어 슬립 버즈는 낮게 유지
- 기어 변속 피드백은 명확하게 체감되도록 설정
- 눈/연석 촉각 처리는 R3 전용이며 일반 코너링 하중을 전역적으로 약하게 만들지 않음

이 값들은 시작점이며 모든 펌웨어/Pit House 조합에서 동일한 느낌을 보장하지 않습니다.

### 진단 로그

휠 백엔드는 재구성된 Xbox C2C `CalcVibrationValues()` 출력도 **읽기 전용 비교 신호**로 보존합니다. 일반 진단 로그의 `origXboxL/origXboxR`, 10 Hz 텔레메트리의 `xboxLeft/xboxRight`는 XInput의 두 럼블 모터 엔벌로프이며 좌/우 조향 토크가 아닙니다. 따라서 DirectInput 힘 방향에는 섞지 않고, 현재 DD 휠 동작을 원본 게임 진동 타이밍 및 공개된 Lindbergh 드라이브보드 관찰과 대조하는 용도로만 사용합니다.

`OutRun2006Tweaks.log`에는 다음 정보가 기록됩니다.

- 선택된 DirectInput FFB 장치 식별 정보
- 효과 생성 및 폴백 상태
- SAT 및 최종 출력 진단
- 스테이지 ID/이름, 네 바퀴 원시 표면 마스크, 휠별 거칠기, 물 표면 휠 마스크, non-water 최소/최대 거칠기, mixed/full-rough 상태, 임시 촉각 스케일링을 포함한 노면 접촉 진단

하드웨어 문제를 보고할 때는 게임 실행 → 레이스 → 종료까지의 전체 로그와 휠베이스 모델, 드라이버, 펌웨어 버전을 함께 첨부하는 것이 좋습니다.

### 빌드 및 릴리즈 검증

CI는 다음 항목을 실행합니다.

- 통합된 실제 소스를 대상으로 `tools/verify_wheel_ffb_current.py` 검증
- 실제 wheel FFB 수학 테스트
- Win32 Release 컴파일
- PE32 페이로드 및 컴파일된 마커 검증
- 정확한 릴리즈 커밋에서 최종 아티팩트 업로드

v0.1 릴리즈 워크플로는 동일 커밋의 Build 워크플로가 성공한 것을 확인한 뒤 ZIP을 게시합니다.

### 크레딧 / 라이선스

구현은 `emoose/OutRun2006Tweaks`를 기반으로 하며, `hyp36rmax/multi-device-input`과 `d-b-c-e/OutRun2006Tweaks-FFB` 등 공개 OutRun 휠 관련 작업의 설계 경험도 참고했습니다.

저장소 라이선스 세부 내용은 `LICENSE.md`와 `THIRD_PARTY_NOTICES.md`에 있습니다. 공개 바이너리 ZIP에는 해당 빌드에 사용된 의존성 소스 트리에서 생성한 하나의 통합 `LICENSES.txt`가 포함됩니다.
