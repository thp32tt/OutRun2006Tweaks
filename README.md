# OutRun2006Tweaks Wheel FFB v0.1

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

Unofficial wheel / force-feedback fork for **OutRun 2006: Coast 2 Coast**, based on [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks).

This release is focused on modern multi-device driving setups and native wheel force feedback. It was developed and hardware-tested primarily with a **MOZA R3**. Other DirectInput wheels may work, but v0.1 should be treated as unverified on hardware that has not been reported by users.

This is not an official SEGA, MOZA, or upstream OutRun2006Tweaks release.

### v0.1 highlights

- SDL3 raw multi-device input for wheel, separate pedals, shifter, button box and gamepad.
- One canonical **Input Bindings** path for steering, pedals and buttons.
- Axis calibration for steering / accelerator / brake.
- Native Windows DirectInput COM force feedback; no vJoy or external FFB mapper required.
- Physics SAT with Natural SAT fallback, mechanical/caster trail, grip-loss unloading and dynamic damping.
- Low-speed centering spring kept intentionally light so it does not hide SAT.
- Road / curb tactile feedback, including MOZA R3 ConstantForce fallback and snow-stage curb handling.
- Gear-shift and collision feedback.
- Exact DirectInput FFB device identity, reconnect handling, focus-loss cleanup and 20% safe direction tests.
- MOZA R3 automatic DirectInput name matching on a clean setup.

### Install

1. Back up your game folder and save data.
2. Extract **OutRun2006Tweaks-Wheel-FFB-v0.1.zip** into the `OutRun 2006 Coast 2 Coast` game directory.
3. Replace files when prompted. The package includes the replacement `OR2006C2C.exe` distributed by the upstream OutRun2006Tweaks v0.1 release.
4. Connect and power on the wheel and pedals before starting the game.
5. Open the in-game overlay with **F11**.
6. Configure steering, pedals, shifter and buttons in **Input Bindings**. After manual edits, use **Save & Return to game** to persist the bindings before leaving the screen.
7. Open **Force Feedback**. On MOZA R3 the FFB interface should normally auto-match; otherwise use **Refresh Devices** and select the actual FFB device.
8. Use the 20% left/right direction tests before raising wheel-base torque. If the steering force is reversed, change `Reverse SAT / ConstantForce`. Change `Reverse Spring` only when the spring itself pushes away from center.

### MOZA R3 notes

The tested R3 path deliberately favors the game's SAT over artificial centering. The v0.1 R3 compatibility layer uses the ConstantForce fallback for road texture because the driver can report sine-effect support without producing useful physical road detail on the tested wheel.

The F11 Force Feedback page still provides `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT` as starting profiles. The live R3 compatibility layer then applies the R3-specific road-output handling used by this release.

For curb / shoulder contact, the code compares all four wheel-surface samples. A mixed surface is detected while only part of the car is on the curb, and a fully rough surface remains tactile after the car crosses completely onto it. Snow stages receive additional compensation so curb detail is not lost under the snow-road attenuation.

The exact feel still depends on wheel-base firmware and MOZA Pit House settings. Keep base-side centering, damping, inertia and friction conservative while evaluating game-side FFB.

### Known issue

On snow stages, curb vibration may fade when all four wheels are fully on the same rough curb/shoulder surface. Partial curb contact is detected correctly, and steering/SAT is not affected. This is tracked in [Issue #1](https://github.com/thp32tt/OutRun2006Tweaks/issues/1).

### Troubleshooting

- **No steering/pedal input:** check the live device values under F11 and rebind in **Input Bindings**.
- **No FFB:** open **Force Feedback**, Refresh Devices, then select the actual DirectInput FFB interface.
- **R3 not selected automatically:** select `R3 Racing Wheel and Pedals` manually once; the exact DirectInput GUID is saved afterward.
- **Pedal direction/range wrong:** recalibrate that axis in Input Bindings.
- **Force pushes away from center:** verify `Reverse SAT / ConstantForce` with the 20% direction test.
- **Need diagnostics:** attach `OutRun2006Tweaks.log` and include wheel model, driver and firmware version.

### Package contents

The public v0.1 ZIP is intentionally kept small:

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt` is the only additional legal-notice file in the ZIP. It is generated from the actual source/dependency trees used by the build so required open-source notices are not dropped while keeping the package uncluttered.

### Credits and license

This fork is based on **emoose/OutRun2006Tweaks** and also benefited from public work and design references from **hyp36rmax/multi-device-input** and **d-b-c-e/OutRun2006Tweaks-FFB**.

The upstream project is MIT licensed. The original notice is preserved in this repository's `LICENSE.md`, and the binary package contains the applicable bundled dependency notices in `LICENSES.txt`.

OutRun, OutRun 2006: Coast 2 Coast and related game assets belong to their respective rights holders. MOZA and other vendor names are used only to describe hardware compatibility.

### Building

The branch targets **Win32 Release** with Visual Studio 2022 and CMake. CI validates the consolidated wheel FFB source and production FFB math before building the release DLL.

See [WHEEL_FFB.md](WHEEL_FFB.md) for architecture and tuning details.

---

<a id="한국어"></a>
## 한국어

**OutRun 2006: Coast 2 Coast**에서 현대식 레이싱 휠과 포스피드백(FFB)을 사용할 수 있도록 만든 비공식 포크입니다. [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks)를 기반으로 합니다.

v0.1은 휠, 별도 페달, 시프터, 버튼박스, 게임패드처럼 여러 입력 장치를 함께 사용하는 환경과 네이티브 휠 FFB 지원에 초점을 맞췄습니다. 개발과 실제 하드웨어 검증은 주로 **MOZA R3**로 진행했습니다. 다른 DirectInput 휠도 동작할 가능성이 있지만, 사용자 검증이 보고되지 않은 장비는 v0.1에서 미검증 상태로 봐야 합니다.

이 프로젝트는 SEGA, MOZA 또는 원본 OutRun2006Tweaks의 공식 릴리즈가 아닙니다.

### v0.1 주요 기능

- 휠, 별도 페달, 시프터, 버튼박스, 게임패드를 동시에 사용할 수 있는 SDL3 Raw 멀티 디바이스 입력
- 조향, 페달, 버튼 설정을 위한 단일 **Input Bindings** 경로
- 스티어링 / 가속 / 브레이크 축 캘리브레이션
- Windows DirectInput COM 기반 네이티브 FFB. vJoy나 외부 FFB 매퍼가 필요 없음
- Physics SAT + Natural SAT 폴백, Mechanical/Caster Trail, 그립 손실 시 조향 하중 감소, Dynamic Damping
- SAT를 가리지 않도록 저속 센터링 스프링을 의도적으로 약하게 설정
- MOZA R3 ConstantForce 폴백과 눈 맵 보정을 포함한 노면 / 연석 촉각 피드백
- 기어 변속 및 충돌 피드백
- 정확한 DirectInput FFB 장치 식별, 재연결 처리, 포커스 손실 시 효과 정리, 20% 안전 방향 테스트
- 초기 설정에서 MOZA R3 DirectInput 장치명 자동 매칭

### 설치 방법

1. 게임 폴더와 세이브 데이터를 백업합니다.
2. **OutRun2006Tweaks-Wheel-FFB-v0.1.zip**의 내용을 `OutRun 2006 Coast 2 Coast` 게임 폴더에 압축 해제합니다.
3. 파일 교체 안내가 나오면 덮어씁니다. 패키지에는 원본 OutRun2006Tweaks v0.1 릴리즈에서 배포한 교체용 `OR2006C2C.exe`가 포함되어 있습니다.
4. 게임을 실행하기 전에 휠과 페달을 연결하고 전원을 켭니다.
5. 게임에서 **F11**을 눌러 오버레이를 엽니다.
6. **Input Bindings**에서 스티어링, 페달, 시프터, 버튼을 설정합니다. 수동으로 변경했다면 화면을 나가기 전에 **Save & Return to game**으로 저장합니다.
7. **Force Feedback**을 엽니다. MOZA R3는 일반적으로 FFB 장치가 자동 매칭됩니다. 자동으로 잡히지 않으면 **Refresh Devices**를 누르고 실제 FFB 장치를 선택합니다.
8. 휠베이스 토크를 높이기 전에 20% 좌/우 방향 테스트를 사용합니다. 조향 힘의 방향이 반대라면 `Reverse SAT / ConstantForce`를 변경합니다. 스프링 자체가 중앙 반대쪽으로 미는 경우에만 `Reverse Spring`을 변경합니다.

### MOZA R3 참고 사항

R3용 설정은 인위적인 센터 스프링보다 게임의 SAT가 주된 조향 하중으로 느껴지도록 구성했습니다. 테스트한 R3에서는 드라이버가 sine effect 지원을 보고하더라도 실제 노면 디테일이 유용하게 전달되지 않아, v0.1 호환 레이어에서 노면 진동에 **ConstantForce 폴백**을 사용합니다.

F11의 Force Feedback 화면에는 시작용 프리셋인 `Load MOZA R3 Physics SAT`와 `Load MOZA R3 Natural SAT`가 있습니다. 이후 실시간 R3 호환 레이어가 이 릴리즈의 R3 전용 노면 출력 처리를 적용합니다.

연석/숄더 접촉은 네 바퀴의 표면 샘플을 비교합니다. 차량 일부만 연석에 올라간 상태는 혼합 표면으로 감지하고, 차량 전체가 거친 표면으로 넘어간 상태도 촉각 피드백을 유지하도록 처리합니다. 눈 맵에서는 눈길 감쇠 때문에 연석 디테일이 사라지지 않도록 추가 보정을 적용합니다.

실제 느낌은 휠베이스 펌웨어와 MOZA Pit House 설정에도 영향을 받습니다. 게임 쪽 FFB를 평가할 때는 휠베이스 자체의 센터링, 댐핑, 관성, 마찰 설정을 과도하게 높이지 않는 것을 권장합니다.

### 알려진 문제

눈 맵에서 네 바퀴가 모두 동일한 거친 연석/숄더 표면에 완전히 올라가면 연석 진동이 약해지거나 사라질 수 있습니다. 차량 일부만 연석에 걸친 상태는 정상적으로 감지되며 조향력과 SAT에는 영향을 주지 않습니다. 자세한 내용은 [Issue #1](https://github.com/thp32tt/OutRun2006Tweaks/issues/1)을 참고하세요.

### 문제 해결

- **스티어링/페달 입력이 없음:** F11의 실시간 장치 값을 확인하고 **Input Bindings**에서 다시 바인딩합니다.
- **FFB가 없음:** **Force Feedback**에서 Refresh Devices를 누른 뒤 실제 DirectInput FFB 인터페이스를 선택합니다.
- **R3가 자동 선택되지 않음:** `R3 Racing Wheel and Pedals`를 한 번 수동 선택하면 이후 정확한 DirectInput GUID가 저장됩니다.
- **페달 방향/범위가 잘못됨:** Input Bindings에서 해당 축을 다시 캘리브레이션합니다.
- **핸들이 중앙 반대 방향으로 밀림:** 20% 방향 테스트로 `Reverse SAT / ConstantForce`를 확인합니다.
- **진단이 필요함:** `OutRun2006Tweaks.log`와 함께 휠 모델, 드라이버 버전, 펌웨어 버전을 첨부해 주세요.

### 배포 파일 구성

공개 v0.1 ZIP은 필요한 파일만 포함하도록 최소화했습니다.

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt`는 ZIP에 추가되는 유일한 법적 고지 파일입니다. 실제 빌드에 사용한 소스/의존성 트리에서 필요한 오픈소스 고지를 자동 수집해 하나의 파일로 만들며, 불필요한 문서가 배포 파일에 많이 들어가지 않도록 했습니다.

### 크레딧 및 라이선스

이 포크는 **emoose/OutRun2006Tweaks**를 기반으로 하며, **hyp36rmax/multi-device-input** 및 **d-b-c-e/OutRun2006Tweaks-FFB**의 공개 작업과 설계 아이디어도 참고했습니다.

원본 프로젝트는 MIT 라이선스입니다. 원본 고지는 이 저장소의 `LICENSE.md`에 유지되며, 바이너리 배포 패키지에는 해당 의존성 고지가 `LICENSES.txt`로 포함됩니다.

OutRun, OutRun 2006: Coast 2 Coast 및 관련 게임 자산의 권리는 각 권리자에게 있습니다. MOZA 및 기타 제조사 명칭은 하드웨어 호환성을 설명하기 위해서만 사용합니다.

### 빌드

`wheel-ffb` 브랜치는 Visual Studio 2022와 CMake를 사용한 **Win32 Release** 빌드를 대상으로 합니다. CI는 릴리즈 DLL을 빌드하기 전에 통합된 wheel FFB 소스와 실제 FFB 수학 로직을 검증합니다.

구조와 세부 튜닝 내용은 [WHEEL_FFB.md](WHEEL_FFB.md)를 참고하세요.
