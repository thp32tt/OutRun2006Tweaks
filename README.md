# OutRun2006Tweaks Wheel FFB v0.1.1

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

Unofficial wheel / force-feedback fork for **OutRun 2006: Coast 2 Coast**, based on [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks).

v0.1.1 adds modern multi-device wheel input, native Windows DirectInput force feedback, improved DirectInput device compatibility, named FFB profiles, and more robust reconnect/recovery behavior. Hardware development and regression testing were performed primarily with **MOZA R3**, with additional community testing on other DirectInput wheelbases.

### Highlights

- SDL3 raw multi-device input for wheel, pedals, shifter, button box and gamepad.
- One **Input Bindings** path for steering, pedals, shifter and buttons.
- Native DirectInput COM FFB; no vJoy or external FFB mapper required.
- Physics SAT with Natural SAT fallback, pneumatic/mechanical trail and fast counter-steer response.
- Light low-speed centering spring plus dynamic damping.
- Universal ConstantForce tactile path for road/slip detail where hardware periodic effects are not useful.
- Snow-stage curb/shoulder compensation and four-wheel mixed/full-rough surface handling.
- Gear-shift and collision feedback.
- Multi-interface DirectInput probing for wheelbases that expose several Windows interfaces.
- Force-actuator axis probing with live ConstantForce validation.
- Exact DirectInput FFB-device identity persistence, safer retry/reinitialization and hot reconnect recovery.
- Named FFB feel profiles stored under `OutRun2006Tweaks.profiles\FFB\<name>.ini`.
- Safer profile saving with staged writes, backup-on-overwrite, rename/copy fallback and final-file verification.
- Clearer F11 runtime status for menu-time pending states and the 20% direction test.
- Optional estimated-RPM **Engine Vibration**. It is **OFF by default**; the default stored strength is **0.20** and is internally scaled so it remains a subtle texture rather than 20% wheel torque.

### Setup

1. Extract **OutRun2006Tweaks-Wheel-FFB-v0.1.1.zip** into the OutRun 2006: Coast 2 Coast game directory and replace files when prompted.
2. Connect the wheel and pedals before starting the game.
3. Open the overlay with **F11**.
4. Configure steering, pedals, shifter and buttons in **Input Bindings**, then use **Save & Return to game**.
5. Open **Force Feedback** and select the intended DirectInput FFB output if it is not already selected.
6. Enter gameplay so the DirectInput FFB device is acquired.
7. Use the safe 20% left/right direction tests before increasing wheel-base torque.
8. Use **Load Universal Physics SAT** as the recommended starting feel. FFB tuning applies live; use **Save Force Feedback** to persist the current settings.

### Force-feedback notes

The main cornering return force comes from SAT rather than a strong artificial centre spring. Wheel/driver-side centering, damping, inertia and friction are additional forces, so keep them conservative while evaluating game-side FFB.

Physics SAT estimates front slip from vehicle motion, steering and yaw, then combines lateral-force response with pneumatic/mechanical trail. If the physics sample is unavailable, the implementation safely falls back to Natural SAT rather than holding stale torque.

Road and snow/curb tactile effects remain enabled in the default universal preset. The snow-stage compensation is retained because it gives useful curb/shoulder feedback, though exact strength can vary with the surface and wheel hardware.

**Engine Vibration** is intentionally optional. When enabled, RPM is estimated from speed, current gear and throttle. Its amplitude and frequency are smoothed and kept in a lighter haptic range. Collision and gear events retain priority.

### FFB device compatibility

v0.1.1 improves compatibility with wheelbases whose drivers expose more than one DirectInput interface. The runtime can probe compatible interfaces and reported force-actuator axes, validate ConstantForce creation/update, and move on from unusable candidates instead of assuming the first interface is correct.

The selected physical FFB device is persisted separately from named FFB feel profiles. Loading a feel profile therefore does not silently reroute output to a different wheel interface.

A working device that is temporarily disconnected can be reinitialized when the driver exposes it again. Community testing confirmed successful in-game disconnect/reconnect recovery on **Simucube 3**. The primary regression device remains **MOZA R3**; reports from Fanatec and other DirectInput wheelbases are welcome.

### FFB profiles

Named FFB profiles are stored in:

`<game folder>\OutRun2006Tweaks.profiles\FFB\<profile name>.ini`

Profile saving uses a staged temporary file, backup-on-overwrite, rename/copy fallback and a final existence check. v0.1.1 also fixes first-time profile creation on Windows when the destination file does not exist yet.

### Package contents

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `RELEASE_NOTES_v0.1.1.md`
- `LICENSES.txt`

### Credits

Based on `emoose/OutRun2006Tweaks`, with public design/reference work from `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB`, and OutRun community hardware reports and testing.

This is an unofficial community fork and is not affiliated with SEGA, MOZA, Fanatec or Simucube.

---

<a id="한국어"></a>
## 한국어

**OutRun 2006: Coast 2 Coast**에서 현대식 레이싱 휠과 네이티브 포스피드백을 사용할 수 있도록 만든 비공식 포크입니다. [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks)를 기반으로 합니다.

v0.1.1은 멀티 디바이스 입력과 Windows DirectInput 기반 휠 FFB에 더해, DirectInput 장치 호환성 강화, 이름별 FFB 프로필, 장치 재연결/복구 안정화를 포함합니다. 개발과 회귀 테스트는 주로 **MOZA R3**로 진행했으며 다른 DirectInput 휠베이스에 대한 커뮤니티 테스트도 반영하고 있습니다.

### 주요 기능

- 휠, 별도 페달, 시프터, 버튼박스, 게임패드를 함께 사용하는 SDL3 Raw 멀티 디바이스 입력
- 조향, 페달, 시프터, 버튼을 설정하는 단일 **Input Bindings** 경로
- vJoy나 외부 매퍼가 필요 없는 Windows DirectInput COM 네이티브 FFB
- Physics SAT + Natural SAT 폴백, Pneumatic/Mechanical Trail, 빠른 카운터스티어 반응
- SAT를 가리지 않는 약한 저속 센터링 스프링과 Dynamic Damping
- 하드웨어 periodic effect가 실질적으로 유용하지 않은 경우에도 동작하는 범용 ConstantForce 노면/슬립 촉각 경로
- 눈 맵 연석/숄더 보정과 네 바퀴 mixed/full-rough 표면 처리
- 기어 변속 및 충돌 피드백
- 여러 Windows 인터페이스를 노출하는 휠베이스를 위한 DirectInput 인터페이스 탐색
- force-actuator axis 탐색 및 실시간 ConstantForce 검증
- 정확한 DirectInput FFB 장치 식별 정보 저장, 안전한 재시도/재초기화, 핫 리커넥트 복구
- `OutRun2006Tweaks.profiles\FFB\<이름>.ini`에 저장되는 이름별 FFB 감각 프로필
- staged write, 기존 파일 백업, rename/copy fallback, 최종 파일 확인을 사용하는 안전한 프로필 저장
- 메뉴 대기 상태와 20% 방향 테스트 상태를 구분하는 F11 런타임 상태 표시
- 추정 RPM 기반 **Engine Vibration** 옵션. 기본값은 **OFF**, 저장 강도 기본값은 **0.20**이며 실제 휠 토크 20%가 바로 들어가는 방식이 아니라 내부에서 약하게 스케일됩니다.

### 설정 방법

1. **OutRun2006Tweaks-Wheel-FFB-v0.1.1.zip**을 게임 폴더에 압축 해제하고 파일을 덮어씁니다.
2. 게임 실행 전에 휠과 페달을 연결합니다.
3. **F11**로 오버레이를 엽니다.
4. **Input Bindings**에서 스티어링, 페달, 시프터, 버튼을 설정하고 **Save & Return to game**으로 저장합니다.
5. **Force Feedback**에서 사용할 DirectInput FFB 출력 장치를 확인합니다.
6. 실제 주행에 들어가 DirectInput FFB 장치가 acquire되도록 합니다.
7. 휠베이스 토크를 올리기 전에 안전한 20% 좌/우 방향 테스트를 사용합니다.
8. 기본 시작점은 **Load Universal Physics SAT**를 권장합니다. FFB 변경은 실시간 적용되며 **Save Force Feedback**으로 저장합니다.

### FFB 참고 사항

코너링에서 중앙으로 돌아가려는 주된 힘은 강한 인위적 센터 스프링이 아니라 SAT가 담당합니다. 휠베이스/드라이버 자체의 센터링, 댐핑, 관성, 마찰은 게임 FFB에 추가되는 힘이므로 과도하게 높이지 않는 것을 권장합니다.

Physics SAT는 차량 움직임, 조향, yaw를 바탕으로 전륜 슬립을 추정하고 횡력 응답과 Pneumatic/Mechanical Trail을 조합해 조향 토크를 만듭니다. 물리 샘플을 사용할 수 없는 경우에는 오래된 토크를 유지하지 않고 Natural SAT로 안전하게 폴백합니다.

노면과 눈길 연석 진동은 기본 범용 프리셋에서 유지합니다. 눈 맵 보정은 실제 테스트에서 연석/숄더 감각을 살리는 데 도움이 되지만 표면과 휠 하드웨어에 따라 체감 강도 차이는 있을 수 있습니다.

**Engine Vibration**은 취향에 따라 켜는 선택 옵션으로 기본 OFF입니다. 켜면 속도, 현재 기어, 스로틀로 RPM을 추정하고 진폭/주파수를 부드럽게 필터링합니다. 충돌/기어 이벤트가 우선합니다.

### FFB 장치 호환성

v0.1.1은 하나의 휠베이스 드라이버가 여러 DirectInput 인터페이스를 노출하는 환경에서의 호환성을 강화했습니다. 호환 가능한 인터페이스와 드라이버가 보고하는 force-actuator axis를 탐색하고 ConstantForce 생성/갱신을 실제로 검증한 뒤, 사용할 수 없는 후보는 건너뛸 수 있습니다.

실제 FFB 출력 장치 선택 정보와 이름별 FFB 감각 프로필은 별도로 관리합니다. 따라서 감각 프로필을 불러와도 출력 대상이 다른 휠 인터페이스로 임의 변경되지 않습니다.

정상 동작하던 장치가 일시적으로 분리된 경우 드라이버가 장치를 다시 노출하면 재초기화할 수 있습니다. **Simucube 3** 커뮤니티 테스트에서는 게임 중 분리/재연결 후 FFB가 정상 복구되는 것을 확인했습니다. 주 회귀 테스트 장비는 **MOZA R3**이며 Fanatec 및 다른 DirectInput 휠베이스 테스트 결과도 환영합니다.

### FFB 프로필

이름별 FFB 프로필은 다음 위치에 저장됩니다.

`<게임 폴더>\OutRun2006Tweaks.profiles\FFB\<프로필 이름>.ini`

프로필 저장은 임시 파일 작성 → 기존 파일 백업 → rename/copy fallback → 최종 파일 존재 확인 순서로 처리됩니다. v0.1.1에서는 Windows에서 최초 저장 대상 파일이 아직 존재하지 않을 때 저장 실패로 잘못 처리하던 문제도 수정했습니다.

### 배포 파일 구성

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `RELEASE_NOTES_v0.1.1.md`
- `LICENSES.txt`

### 크레딧

`emoose/OutRun2006Tweaks`를 기반으로 하며 `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB`의 공개 설계/참고 작업과 OutRun 커뮤니티의 하드웨어 보고 및 테스트를 참고했습니다.

이 프로젝트는 비공식 커뮤니티 포크이며 SEGA, MOZA, Fanatec 또는 Simucube와 제휴하거나 공식 지원받는 프로젝트가 아닙니다.
