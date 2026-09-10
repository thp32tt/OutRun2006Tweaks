# OutRun2006Tweaks Wheel FFB v0.1

## 한국어

이 빌드는 제가 **OutRun 2006: Coast 2 Coast를 MOZA R3로 플레이하려고 개인적으로 만들기 시작한 버전**입니다. 현재 실제 하드웨어 테스트는 **제 MOZA R3에서만** 했습니다. 다른 휠에서도 동작할 수 있도록 구조는 범용 DirectInput/SDL3 방식으로 만들었지만, 제가 직접 확인한 것은 R3뿐입니다.

같은 환경에서 필요한 분이 있을까 해서 **v0.1로 한번 공유해 봅니다.** 아직 초기 버전이므로 다른 휠의 호환성 피드백이나 로그를 환영합니다.

### v0.1 주요 기능

- SDL3 raw joystick 기반 **멀티 디바이스 입력**: 휠/페달/쉬프터/버튼박스/게임패드 개별 인식
- F11 **Quick Setup**, 입력 바인딩 및 Min/Rest/Max 축 보정
- Windows **DirectInput COM 네이티브 FFB**
- 속도 기반 센터링, Dynamic Damping, Cornering Load, Grip-loss Unload
- 노면/타이어 슬립, 기어 변속, 충돌 피드백
- 정확한 DirectInput GUID 선택, 장치 재연결/포커스 상실 안전 처리
- 안전한 20% 좌/우 FFB 방향 테스트

### MOZA R3 v0.1 기본 FFB

이번 기본값은 **전체 진동을 세게 만드는 대신 핸들 저항감을 조금 더 높이고, 충돌 진동은 과하지 않게** 맞췄습니다.

| Setting | Value |
| --- | ---: |
| Overall Strength | 0.70 |
| Aligning / Spring | 0.60 |
| **Dynamic Damping** | **0.42** |
| Cornering Load | 0.38 |
| Grip-loss Unload | 0.65 |
| **Collision** | **0.38** |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Low-speed Aligning | 0.08 |
| Corner-load Boost | 0.35 |

F11 → Force Feedback에서 **`MOZA R3 v0.1 (default)`**로 다시 불러올 수 있습니다. 이전 테스트 버전의 사용자 설정이 남아 있다면 프리셋을 한 번 눌러 주세요.

### 설치

1. 게임 폴더/세이브를 백업합니다.
2. 최신 **Microsoft Visual C++ 2015-2022 Redistributable x86**를 설치합니다.
3. ZIP 내용을 `OR2006C2C.EXE`가 있는 폴더에 풀고 덮어씁니다.
4. 휠/페달 전원을 켠 뒤 게임을 실행합니다.
5. F11 또는 Controller 설정 → **Quick Setup**으로 조향/엑셀/브레이크/패들/메뉴 버튼을 설정합니다.
6. **Save bindings**로 저장합니다.
7. Force Feedback 탭에서 실제 FFB 휠을 선택하고 `MOZA R3 v0.1 (default)`를 사용합니다.

> Direct Drive 휠은 강한 힘을 낼 수 있습니다. 처음에는 휠 베이스의 최대 토크를 낮게 잡고 테스트해 주세요.

### 테스트 범위 / Known limitation

- **직접 테스트 완료: MOZA R3만**
- 개인 설정에서는 270° 사용
- 다른 MOZA/Fanatec/Logitech/Thrustmaster/Simagic 등은 미검증
- 문제 제보 시 `OutRun2006Tweaks.log`, 휠/페달 모델, 드라이버/펌웨어 버전을 같이 알려주시면 좋습니다.

### 감사 및 라이선스

이 작업은 다음 프로젝트의 공개 소스와 아이디어/테스트 경험을 기반으로 했습니다.

- [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks) — 원본 프로젝트
- [hyp36rmax/multi-device-input](https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input) — SDL3 멀티 디바이스 입력/설정 구조의 주요 참고
- [d-b-c-e/OutRun2006Tweaks-FFB](https://github.com/d-b-c-e/OutRun2006Tweaks-FFB) — DirectInput FFB/포스 모델의 주요 참고

세 저장소의 루트 라이선스는 MIT이며, 원본 `Copyright (c) 2023 emoose` 고지와 MIT 전문은 이 저장소의 `LICENSE.md`에 유지했습니다. 자세한 내용은 `THIRD_PARTY_NOTICES.md`를 참고해 주세요.

**공개해 준 개발자와 테스트 결과를 공유해 준 커뮤니티 분들께 감사합니다.**

---

## English

I originally started this build **for my own MOZA R3 setup in OutRun 2006: Coast 2 Coast**. The only wheel I have personally hardware-tested for v0.1 is **my MOZA R3**. The input/FFB architecture is intended to be generic enough for other DirectInput wheels, but I cannot claim that I have personally verified them.

I am sharing **v0.1 in case somebody else finds it useful**. It is still an early experimental release, so compatibility reports and logs from other hardware are very welcome.

### Highlights

- SDL3 raw-joystick **multi-device input** for wheel / pedals / shifter / button box / gamepad
- F11 **Quick Setup**, binding editor and Min/Rest/Max axis calibration
- Native Windows **DirectInput COM force feedback**
- Speed-based centering, dynamic damping, cornering load and grip-loss unloading
- Road/tyre detail, gear-shift and collision feedback
- Exact DirectInput GUID selection, reconnect handling and focus-loss safety
- Safe fixed-20% left/right FFB direction tests

### MOZA R3 v0.1 default FFB

The release tune is designed for **a little more steering resistance/weight without making collision vibration excessive**.

| Setting | Value |
| --- | ---: |
| Overall Strength | 0.70 |
| Aligning / Spring | 0.60 |
| **Dynamic Damping** | **0.42** |
| Cornering Load | 0.38 |
| Grip-loss Unload | 0.65 |
| **Collision** | **0.38** |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Low-speed Aligning | 0.08 |
| Corner-load Boost | 0.35 |

Restore it from F11 → Force Feedback with **`MOZA R3 v0.1 (default)`**. If you are upgrading from an older test build, existing user settings may override new defaults, so load the preset once.

### Installation

1. Back up the game folder/save data.
2. Install the latest **Microsoft Visual C++ 2015-2022 Redistributable x86**.
3. Extract the ZIP into the folder containing `OR2006C2C.EXE` and replace files when prompted.
4. Power on/connect the wheel and pedals before launching the game.
5. Open F11 or Controller setup and run **Quick Setup** for steering, throttle, brake, paddles and menu buttons.
6. Select **Save bindings**.
7. Under Force Feedback, select the actual FFB wheel interface and use `MOZA R3 v0.1 (default)`.

> Direct-drive wheels can generate substantial torque. Begin with a conservative wheel-base torque limit while testing.

### Tested scope / known limitation

- **Personally tested: MOZA R3 only**
- 270° steering range used in my personal setup
- Other MOZA/Fanatec/Logitech/Thrustmaster/Simagic hardware is currently unverified by me
- For compatibility reports, please include `OutRun2006Tweaks.log`, wheel/pedal model and driver/firmware version.

### Thanks and license

This work builds on public source/design/testing from:

- [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks) — original/upstream project
- [hyp36rmax/multi-device-input](https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input) — major multi-device SDL3 input/setup reference
- [d-b-c-e/OutRun2006Tweaks-FFB](https://github.com/d-b-c-e/OutRun2006Tweaks-FFB) — major DirectInput FFB / force-model reference

The root licenses reviewed for these repositories are MIT and retain the upstream `Copyright (c) 2023 emoose` notice. This repository keeps the full upstream MIT license in `LICENSE.md`; see `THIRD_PARTY_NOTICES.md` for details.

**Many thanks to the developers who published their work and to the community members who shared hardware tests and troubleshooting results.**
