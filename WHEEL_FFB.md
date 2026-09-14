# Wheel / FFB architecture — v0.1.1

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

This document describes the wheel-input and force-feedback architecture used by **OutRun2006Tweaks Wheel FFB v0.1.1**.

### Scope

The current release path is:

- input: SDL3 raw multi-device input;
- force feedback: Windows DirectInput COM;
- build: Win32 x86;
- game update rate: OutRun's native 60 Hz gameplay loop.

Development and regression testing are performed primarily with **MOZA R3**. v0.1.1 also contains compatibility work for wheelbases whose Windows drivers expose multiple DirectInput interfaces, and community testing has included **Simucube 3** and Fanatec-style multi-interface layouts.

### Input ownership

With `UseNewInput=true`, **Input Bindings is the main input-binding owner** for steering, pedals, shifter, buttons and menu controls. Wheel, separate pedals, shifter, button box and gamepad can all contribute to one player at the same time.

The older legacy DirectInput input path remains available as a compatibility fallback. Bindings are live while editing, but manual changes should be persisted with **Save & Return to game**. Named input profiles remain available for complete multi-device layouts.

### FFB ownership

The wheel FFB backend has a single DirectInput COM output owner. Output is pinned to the selected physical FFB device identity instead of whichever similarly named Windows interface happens to enumerate first.

The runtime keeps device selection separate from named FFB feel profiles. Loading a feel profile therefore changes tuning values without silently selecting a different physical wheel interface.

### Steering-force model

The main steering model contains:

1. **Physics SAT** — estimates front slip from vehicle motion, steering and yaw, then derives aligning torque from lateral-force response and total trail.
2. **Natural SAT fallback** — progressive steering-angle-based restoring torque when the physics sample is unavailable or Physics SAT is disabled.
3. **Mechanical / caster trail** — remains active with front lateral load instead of acting as a standalone artificial center spring.
4. **Pneumatic trail** — changes with front slip so steering load can reduce as the tire moves deeper into understeer.
5. **Low-speed spring** — only a stabilizer near low speed; SAT remains the main cornering return force.
6. **Dynamic damping** — steering-velocity resistance that releases as the front end scrubs or the car slides.
7. **Grip-loss unloading** — reduces steering load as usable front grip falls away.
8. **Road / tire / gear / collision effects** — transient tactile effects layered on top of the structural steering signal.

Physics SAT samples are validated before they are allowed to drive the structural steering signal. If the physics path is not valid, the implementation falls back to Natural SAT rather than holding stale torque.

### DirectInput device discovery

Some wheelbases expose more than one Windows/DirectInput interface. v0.1.1 therefore does not assume that the first matching name is the correct FFB endpoint.

The compatibility path can:

- keep the saved DirectInput GUID as the preferred identity;
- compare DirectInput product identity and VID/PID information;
- use FFB driver/vendor information when available;
- probe compatible interfaces belonging to the same physical device;
- enumerate reported force-actuator axes;
- attempt ConstantForce creation on candidate actuator axes;
- validate a live zero-force update before treating the candidate as usable;
- quarantine unusable candidates and continue to the next compatible interface;
- schedule safe reinitialization after transient device/update failures.

This is intended to support real driver layouts rather than depending on device-name order.

### Hot reconnect and runtime ownership

The FFB output device is acquired for gameplay and released when appropriate during menu/state transitions. Menu-time `waiting / released / inactive` can therefore be a normal pending state, not a hardware failure.

If a working device is disconnected during gameplay, the runtime clears active effects and schedules DirectInput reinitialization. When the driver exposes the device again correctly, output can be reacquired without requiring a game restart.

Community testing on **Simucube 3** confirmed successful intentional disconnect/reconnect recovery during gameplay.

### Force Feedback UI

The F11 **Force Feedback** page owns output-device selection and game-side tuning.

Important status behavior in v0.1.1:

- `[..] FFB device (starts in gameplay)` means the selected device is waiting for gameplay acquisition; it is not an error by itself.
- `[..] Direction test (not run)` means the safe direction test has not been executed yet.
- a real initialization/output failure is shown separately from those pending states.

The manual left/right direction tests are hard-capped at 20% and are intended to confirm force direction before increasing wheel-base torque.

The **Advanced FFB tuning** section exposes supported lower-level values such as Spring Saturation, Weight Transfer, Force Build Slew Rate, Countersteer Release Rate, Pneumatic Trail Response Lead, output headroom/clipping controls and optional wheel-response correction.

### Named FFB profiles

Named feel profiles are stored under:

`<game folder>\OutRun2006Tweaks.profiles\FFB\<profile name>.ini`

The profile contains game-side FFB feel/tuning values. It does not silently replace the selected physical DirectInput FFB output device.

v0.1.1 profile saving uses:

1. staged write to a temporary file;
2. backup-on-overwrite for an existing profile;
3. normal rename/replace where Windows allows it;
4. `copy_file` fallback for filesystem/filter/driver edge cases;
5. final destination-file verification;
6. full destination-path and filesystem-error reporting on failure.

The Windows first-save path is also fixed: a destination `.ini` or `.bak` that does not exist yet is treated as the normal new-profile state rather than as a save error.

### Road and tactile effects

Road contact is sampled across all four wheels. The implementation distinguishes meaningful mixed/rough-surface contact from ordinary road so curb/shoulder texture can remain perceptible without turning normal driving into constant vibration.

Snow stages use a lower base road-texture scale, so the compatibility layer compensates tactile curb/shoulder contact conservatively while avoiding a continuous snow-road buzz.

Gear-change and collision feedback are transient effects with priority over optional low-level texture when necessary.

### Engine vibration

Estimated-RPM **Engine Vibration** is optional and disabled by default. When enabled, RPM is estimated from speed, current gear and throttle. Amplitude and frequency are smoothed and internally scaled to remain a texture rather than a dominant steering force.

### Device selection and safety

- Exact selected DirectInput FFB identity is persisted.
- Focus loss, state transitions and device loss clear active effects.
- Device reconnect schedules normal DirectInput reinitialization.
- Manual left/right direction tests are capped at 20%.
- Structural steering output is zeroed on invalid ownership/device states.
- A single FFB output owner prevents duplicate force paths from fighting the wheel.

### Hardware notes

- **MOZA R3** — primary development and regression hardware; ConstantForce, Spring and Damper paths are regularly checked.
- **Simucube 3** — community testing confirmed in-game disconnect/reconnect recovery with FFB resuming correctly.
- **Fanatec / multi-interface layouts** — v0.1.1 includes broader interface-selection, actuator probing and failure-recovery logic informed by tester reports. Additional model-specific results are welcome.

Different wheelbase torque, firmware, wheel diameter and driver-side damping/inertia/friction settings can change physical feel even when the game-side force model is identical.

### Diagnostics

`OutRun2006Tweaks.log` can record:

- selected DirectInput FFB identity;
- candidate-interface probing and recovery decisions;
- force-actuator discovery;
- ConstantForce/Spring/Damper creation status;
- transient update failures and reinitialization;
- SAT and final-output diagnostics;
- profile save destination and filesystem errors.

For a useful hardware report, include the full launch → race → exit log plus wheel-base model, driver and firmware version.

### Build and release validation

CI runs:

- `tools/verify_wheel_ffb_current.py` against the consolidated production source;
- production wheel FFB math tests;
- Win32 Release compilation;
- PE32 payload checks and compiled marker verification;
- final artifact upload from the exact release commit.

The v0.1.1 release workflow waits for the matching successful Build workflow before publishing the release ZIP.

### Credits / license

The implementation is based on `emoose/OutRun2006Tweaks` and incorporates design lessons from public OutRun wheel work including `hyp36rmax/multi-device-input` and `d-b-c-e/OutRun2006Tweaks-FFB`.

Repository license details are in `LICENSE.md` and `THIRD_PARTY_NOTICES.md`. The public binary ZIP receives one consolidated `LICENSES.txt` generated from the dependency source trees used for that build.

---

<a id="한국어"></a>
## 한국어

이 문서는 **OutRun2006Tweaks Wheel FFB v0.1.1**의 휠 입력 및 포스피드백 구조를 설명합니다.

### 범위

현재 릴리즈의 기본 경로는 다음과 같습니다.

- 입력: SDL3 Raw 멀티 디바이스 입력
- 포스피드백: Windows DirectInput COM
- 빌드: Win32 x86
- 게임 업데이트 주기: OutRun 기본 60 Hz 게임플레이 루프

개발과 회귀 테스트는 주로 **MOZA R3**로 진행합니다. v0.1.1에는 하나의 휠베이스 드라이버가 여러 DirectInput 인터페이스를 노출하는 환경을 위한 호환성 개선도 포함되며, 커뮤니티 테스트에는 **Simucube 3** 및 Fanatec 계열 멀티 인터페이스 구성도 반영되고 있습니다.

### 입력 처리 구조

`UseNewInput=true`일 때 **Input Bindings가 스티어링, 페달, 시프터, 버튼, 메뉴 조작의 주 바인딩 경로**입니다. 휠, 별도 페달, 시프터, 버튼박스, 게임패드가 동시에 한 플레이어의 입력에 참여할 수 있습니다.

기존 레거시 DirectInput 입력 경로는 호환성 폴백 용도로 남아 있습니다. 바인딩은 편집 중 실시간 적용되지만 수동 변경 사항은 **Save & Return to game**으로 저장해야 합니다. 완전한 멀티 디바이스 구성을 위한 이름 지정 입력 프로필도 사용할 수 있습니다.

### FFB 출력 소유권

휠 FFB 백엔드는 하나의 DirectInput COM 출력 소유자로 동작합니다. 비슷한 이름의 Windows 인터페이스 중 먼저 열거된 장치가 아니라 사용자가 선택한 실제 FFB 장치 식별 정보에 출력을 고정합니다.

실제 FFB 출력 장치 선택과 이름별 FFB 감각 프로필은 별도로 관리합니다. 따라서 감각 프로필을 불러와도 다른 물리 휠 인터페이스로 출력 대상이 임의 변경되지 않습니다.

### 조향력 모델

주 조향 모델은 다음 요소로 구성됩니다.

1. **Physics SAT** — 차량 움직임, 조향, yaw에서 전륜 슬립을 추정하고 횡력 응답과 총 trail을 이용해 self-aligning torque를 계산합니다.
2. **Natural SAT fallback** — 물리 샘플을 사용할 수 없거나 Physics SAT를 끈 경우 조향각 기반의 점진적인 중앙 복원 토크를 생성합니다.
3. **Mechanical / caster trail** — 별도의 강한 인공 센터 스프링이 아니라 전륜 횡하중과 함께 작동하는 기계적/캐스터 트레일 성분입니다.
4. **Pneumatic trail** — 전륜 슬립에 따라 변하며 언더스티어가 깊어질수록 조향 하중이 줄어드는 데 사용됩니다.
5. **Low-speed spring** — 저속 안정화용으로만 사용하며 코너링 복원력의 중심은 SAT가 담당합니다.
6. **Dynamic damping** — 조향 속도에 대한 저항이며 전륜이 밀리거나 차량이 슬라이드할 때 완화됩니다.
7. **Grip-loss unloading** — 사용 가능한 전륜 그립이 줄어들수록 조향 하중을 낮춥니다.
8. **Road / tire / gear / collision effects** — 기본 조향 신호 위에 일시적인 촉각 효과를 추가합니다.

Physics SAT 샘플은 구조적인 조향 출력에 사용되기 전에 유효성을 확인합니다. 물리 경로를 신뢰할 수 없는 경우 오래된 토크를 유지하지 않고 Natural SAT로 폴백합니다.

### DirectInput 장치 탐색

일부 휠베이스는 하나의 물리 장치가 여러 Windows/DirectInput 인터페이스로 보입니다. v0.1.1은 이름이 먼저 일치하는 첫 번째 인터페이스를 무조건 FFB 출력으로 사용하지 않습니다.

호환성 경로에서는 다음 처리를 수행할 수 있습니다.

- 저장된 DirectInput GUID를 우선 식별자로 사용
- DirectInput product identity와 VID/PID 정보 비교
- 가능한 경우 FFB driver/vendor 정보 활용
- 동일 물리 장치에 해당하는 호환 인터페이스 탐색
- 드라이버가 보고하는 force-actuator axis 열거
- 후보 actuator axis에서 ConstantForce 생성 시도
- 실제 0-force 실시간 업데이트를 검증한 뒤 사용 가능한 후보로 인정
- 사용할 수 없는 후보 인터페이스는 격리하고 다음 후보를 계속 탐색
- 일시적인 장치/업데이트 실패 후 안전한 재초기화 예약

이 구조는 장치 이름의 열거 순서가 아니라 실제 드라이버 동작을 기준으로 올바른 FFB 경로를 선택하기 위한 것입니다.

### 핫 리커넥트와 런타임 소유권

FFB 출력 장치는 실제 게임플레이에서 acquire되고 메뉴/상태 전환 시 필요에 따라 release됩니다. 따라서 메뉴에서 `waiting / released / inactive`가 보이는 것은 정상적인 대기 상태일 수 있으며 그 자체가 하드웨어 실패를 의미하지 않습니다.

주행 중 정상 동작하던 장치가 분리되면 활성 효과를 정리하고 DirectInput 재초기화를 예약합니다. 드라이버가 장치를 다시 정상적으로 노출하면 게임을 재시작하지 않고도 출력을 다시 acquire할 수 있습니다.

**Simucube 3** 커뮤니티 테스트에서는 게임 중 의도적인 분리/재연결 후 FFB가 정상 복구되는 것을 확인했습니다.

### Force Feedback UI

F11의 **Force Feedback** 화면에서 출력 장치 선택과 게임 내 FFB 튜닝을 담당합니다.

v0.1.1의 주요 상태 표시는 다음과 같습니다.

- `[..] FFB device (starts in gameplay)` — 선택한 장치가 게임플레이 acquire를 기다리는 상태이며 그 자체로 오류가 아닙니다.
- `[..] Direction test (not run)` — 안전 방향 테스트를 아직 실행하지 않은 상태입니다.
- 실제 초기화/출력 실패는 위의 정상 대기 상태와 별도로 표시됩니다.

수동 좌/우 방향 테스트는 최대 20%로 제한되며 휠베이스 토크를 올리기 전에 힘 방향을 확인하기 위한 용도입니다.

**Advanced FFB tuning**에는 Spring Saturation, Weight Transfer, Force Build Slew Rate, Countersteer Release Rate, Pneumatic Trail Response Lead, 출력 headroom/clipping, 선택형 wheel response correction 등의 세부 조정 값이 노출됩니다.

### 이름별 FFB 프로필

이름별 감각 프로필은 다음 위치에 저장됩니다.

`<게임 폴더>\OutRun2006Tweaks.profiles\FFB\<프로필 이름>.ini`

프로필에는 게임 측 FFB 감각/튜닝 값이 저장됩니다. 프로필을 불러와도 선택된 실제 DirectInput FFB 출력 장치를 임의로 바꾸지 않습니다.

v0.1.1의 프로필 저장 과정은 다음과 같습니다.

1. 임시 파일에 staged write
2. 기존 프로필이 있으면 백업 생성
3. Windows에서 허용되는 경우 정상 rename/replace
4. 파일시스템/필터/드라이버 예외 상황에서는 `copy_file` fallback
5. 최종 대상 파일 존재 확인
6. 실패 시 실제 대상 경로와 파일시스템 오류 표시/로그 기록

Windows 최초 저장 경로도 수정했습니다. 아직 목적지 `.ini` 또는 `.bak` 파일이 없는 상태는 정상적인 새 프로필 생성 상태로 처리하며 저장 실패로 보지 않습니다.

### 노면 및 촉각 효과

노면 접촉은 네 바퀴 전체를 샘플링합니다. 일반 도로와 의미 있는 mixed/rough surface 접촉을 구분해 연석/숄더 질감은 느껴지게 하면서 평상시 주행이 계속 진동하지 않도록 처리합니다.

눈 맵은 기본 노면 텍스처 스케일이 낮기 때문에 실제 연석/숄더 접촉이 있을 때만 보수적으로 보정하고 일반 눈길 자체가 지속적으로 떨리지 않도록 합니다.

기어 변속과 충돌 피드백은 일시적인 이벤트이며 필요한 경우 낮은 우선순위의 텍스처보다 우선합니다.

### 엔진 진동

추정 RPM 기반 **Engine Vibration**은 선택 기능이며 기본 OFF입니다. 켜면 속도, 현재 기어, 스로틀을 이용해 RPM을 추정합니다. 진폭과 주파수는 부드럽게 필터링하고 구조적인 조향력을 덮지 않는 촉각 텍스처 수준으로 내부 스케일링합니다.

### 장치 선택 및 안전 처리

- 선택한 DirectInput FFB 장치의 정확한 식별 정보를 저장합니다.
- 포커스 손실, 게임 상태 전환, 장치 손실 시 활성 FFB 효과를 정리합니다.
- 장치 재연결 시 정상적인 DirectInput 재초기화를 예약합니다.
- 수동 좌/우 방향 테스트는 최대 20%로 제한합니다.
- 출력 소유권이나 장치 상태가 유효하지 않으면 구조적인 조향 출력을 0으로 만듭니다.
- 하나의 FFB 출력 소유자만 사용해 서로 다른 force 경로가 휠을 동시에 제어하지 않도록 합니다.

### 하드웨어 참고

- **MOZA R3** — 주 개발 및 회귀 테스트 장비이며 ConstantForce, Spring, Damper 경로를 정기적으로 확인합니다.
- **Simucube 3** — 커뮤니티 테스트에서 게임 중 분리/재연결 후 FFB 정상 복구를 확인했습니다.
- **Fanatec / 멀티 인터페이스 구성** — 사용자 보고를 바탕으로 인터페이스 선택, actuator 탐색, 실패 복구 로직을 v0.1.1에 강화했습니다. 모델별 추가 결과를 환영합니다.

같은 게임 측 힘 계산을 사용하더라도 휠베이스 토크, 펌웨어, 휠 직경, 드라이버 측 damping/inertia/friction 설정에 따라 실제 체감은 달라질 수 있습니다.

### 진단 로그

`OutRun2006Tweaks.log`에는 다음 정보를 기록할 수 있습니다.

- 선택된 DirectInput FFB 장치 식별 정보
- 후보 인터페이스 탐색 및 복구 결정
- force-actuator 탐색
- ConstantForce/Spring/Damper 생성 상태
- 일시적인 업데이트 실패와 재초기화
- SAT 및 최종 출력 진단
- 프로필 저장 대상 경로와 파일시스템 오류

유용한 하드웨어 테스트 보고를 위해서는 게임 실행 → 레이스 → 종료까지의 전체 로그와 휠베이스 모델, 드라이버, 펌웨어 버전을 함께 제공하는 것을 권장합니다.

### 빌드 및 릴리즈 검증

CI에서는 다음을 수행합니다.

- 통합된 현재 소스에 대해 `tools/verify_wheel_ffb_current.py` 실행
- 실제 production wheel FFB math 테스트
- Win32 Release 컴파일
- PE32 payload 및 컴파일 마커 검증
- 해당 릴리즈 커밋에서 생성된 최종 artifact 업로드

v0.1.1 릴리즈 workflow는 동일 커밋의 Build workflow가 성공한 것을 확인한 뒤 배포 ZIP을 게시합니다.

### 크레딧 / 라이선스

구현은 `emoose/OutRun2006Tweaks`를 기반으로 하며 `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB` 등 공개 OutRun 휠 프로젝트의 설계와 참고 작업을 활용했습니다.

저장소 라이선스 세부 사항은 `LICENSE.md`와 `THIRD_PARTY_NOTICES.md`에 있으며 공개 바이너리 ZIP에는 실제 빌드에 사용한 의존성 소스 트리에서 생성한 통합 `LICENSES.txt`가 포함됩니다.
