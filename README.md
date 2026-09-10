# OutRun2006Tweaks Wheel FFB v0.1

Unofficial experimental wheel / force-feedback build for **OutRun 2006: Coast 2 Coast**, based on [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks).

> **Hardware status:** I made this mainly for my own **MOZA R3** setup and have personally tested v0.1 only on a MOZA R3. Other DirectInput wheels may work, but I have not personally verified them. I am sharing it in case it is useful to someone else.
>
> This is not an official SEGA, MOZA, or upstream OutRun2006Tweaks release.

- [한국어](#한국어)
- [English](#english)
- [Credits / Licenses](#credits--licenses)

---

## 한국어

### 무엇이 다른가요?

이 빌드는 최신 OutRun2006Tweaks 기반에 현대 레이싱 휠용 입력과 네이티브 FFB를 추가한 개인용 포크입니다.

- **SDL3 raw joystick 멀티 디바이스 입력**: 휠, 페달, 쉬프터, 버튼박스, 게임패드를 각각 인식하고 한 플레이어에 함께 바인딩할 수 있습니다.
- **F11 Quick Setup / 입력 보정**: 조향, 엑셀, 브레이크, 패들, 메뉴 버튼을 게임 안에서 설정하고 축의 Min / Rest / Max를 보정할 수 있습니다.
- **DirectInput COM 네이티브 FFB**: 별도 vJoy나 외부 FFB 매퍼 없이 선택한 휠에 직접 효과를 출력합니다.
- **FFB 효과**: 속도 기반 센터링, 동적 댐핑, 코너링 하중, 그립 손실 시 하중 감소, 노면, 타이어 슬립, 기어 변속, 충돌 피드백을 제공합니다.
- **안전 처리**: 포커스 상실/Alt-Tab, 게임 상태 전환, 장치 손실 시 힘을 정리하고 재연결을 처리합니다. 테스트 힘은 게임 플레이 중에만 짧게 동작합니다.

### v0.1 기본 프로파일 — MOZA R3

v0.1은 전체 진동을 무작정 키우기보다 **핸들이 조금 더 묵직하게 돌아가는 저항감**을 우선하도록 조정했습니다. 충돌 피드백은 강하게 튀지 않도록 낮게 잡았습니다.

| 항목 | 기본값 |
| --- | ---: |
| Overall Strength | 0.70 |
| Aligning / Spring | 0.60 |
| Dynamic Damping | **0.42** |
| Cornering Load | 0.38 |
| Grip-loss Unload | 0.65 |
| Collision | **0.38** |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Low-speed Aligning | 0.08 |
| Corner-load Boost | 0.35 |

F11의 Force Feedback 화면에서 **`MOZA R3 v0.1 (default)`** 버튼으로 언제든 이 값을 다시 불러올 수 있습니다. 기존 설정 파일을 사용하던 경우에는 예전 사용자 설정이 기본값보다 우선할 수 있으므로, v0.1 값을 사용하려면 이 프리셋을 한 번 불러오는 것을 권장합니다.

### 설치 방법

1. **OutRun 2006: Coast 2 Coast**가 설치된 폴더와 세이브를 먼저 백업합니다.
2. Microsoft **Visual C++ 2015-2022 Redistributable x86** 최신 버전을 설치합니다.
3. v0.1 Release ZIP의 파일을 `OR2006C2C.EXE`가 있는 게임 폴더에 압축 해제하고, 요청 시 덮어씁니다.
4. 휠/페달을 연결하고 전원을 켠 뒤 게임을 실행합니다. 가능하면 게임 실행 전에 장치를 연결하세요.
5. 게임에서 **F11** 또는 Controller 설정 화면을 열고 **Quick Setup**으로 Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back 순서로 바인딩합니다.
6. 축 움직임을 확인하고 **Save bindings**를 눌러 저장합니다.
7. **Force Feedback** 탭에서 실제 FFB 휠을 선택합니다. MOZA R3에서는 기본 프리셋을 먼저 사용해 보세요.
8. 방향이 반대로 느껴질 때만 `Reverse ConstantForce` 또는 `Reverse Spring`을 조정합니다. MOZA R3에서 제가 테스트한 기본값은 Reverse Spring **OFF**입니다.

> **주의:** Direct Drive 휠은 큰 토크를 낼 수 있습니다. 처음 사용할 때는 휠 베이스 자체의 최대 힘을 보수적으로 설정하고, 손을 놓은 상태에서 강한 테스트를 반복하지 마세요.

### 현재 확인된 환경

- **개인 실기 테스트:** MOZA R3
- 조향 범위: 개인 환경에서는 270°로 사용
- 입력: SDL3 raw joystick multi-device
- FFB 출력: Windows DirectInput COM
- Windows / Win32 x86 빌드

다른 MOZA / Fanatec / Logitech / Thrustmaster / Simagic 등의 장치는 구조상 동작할 가능성이 있지만 **v0.1에서 제가 직접 확인한 것은 MOZA R3뿐입니다.** 문제가 있다면 `OutRun2006Tweaks.log`와 장치 모델/드라이버 정보를 함께 남겨 주세요.

### 문제 해결

- 장치가 안 보이면 F11의 Controllers에서 입력이 움직이는지 먼저 확인합니다.
- FFB가 없으면 Force Feedback 탭에서 휠을 다시 선택하고 **Refresh connected wheels**를 사용합니다.
- 휠이 코너 바깥쪽으로 계속 밀어내면 방향 반전 옵션을 확인합니다.
- 페달 방향이 반대라면 해당 축의 Invert/보정을 다시 설정합니다.
- 기존 설정과 충돌하는 것 같으면 사용자 설정 파일을 백업한 뒤 새 기본값으로 다시 테스트합니다.
- 진단 시 `OutRun2006Tweaks.log`의 `WheelFFB:` / multi-device 관련 로그가 가장 유용합니다.

---

## English

### What is this?

This is an unofficial personal fork of the current OutRun2006Tweaks codebase that adds modern wheel input and native force feedback.

- **SDL3 raw-joystick multi-device input**: bind a wheel, separate pedals, shifter, button box and gamepad to the same player.
- **F11 Quick Setup and calibration**: configure steering, pedals, paddles and menu buttons in-game, including Min / Rest / Max axis calibration.
- **Native DirectInput COM FFB**: no vJoy or external FFB mapper is required.
- **FFB model**: speed-based centering, dynamic damping, cornering load, grip-loss unloading, road texture, tyre slip, gear-shift and collision feedback.
- **Lifecycle safety**: torque is cleared on focus loss / Alt-Tab, game-state transitions and device loss; reconnect handling is included. Direction tests are short and gameplay-gated.

### v0.1 default profile — MOZA R3

The v0.1 tune is intentionally aimed at **more steering resistance/weight without making collision vibration excessive**.

| Setting | Default |
| --- | ---: |
| Overall Strength | 0.70 |
| Aligning / Spring | 0.60 |
| Dynamic Damping | **0.42** |
| Cornering Load | 0.38 |
| Grip-loss Unload | 0.65 |
| Collision | **0.38** |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Low-speed Aligning | 0.08 |
| Corner-load Boost | 0.35 |

You can restore these values at any time from the F11 Force Feedback page with **`MOZA R3 v0.1 (default)`**. If you are upgrading from an older test build, your existing user settings can override new defaults, so load the v0.1 preset once if you want the exact release tune.

### Installation

1. Back up your **OutRun 2006: Coast 2 Coast** game folder and save data.
2. Install the latest Microsoft **Visual C++ 2015-2022 Redistributable x86**.
3. Extract the v0.1 Release ZIP into the game directory containing `OR2006C2C.EXE`, replacing files when prompted.
4. Connect and power on the wheel/pedals before launching the game when possible.
5. Open **F11** or the Controller setup screen and run **Quick Setup**: Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back.
6. Verify live axis movement, then select **Save bindings**.
7. Open **Force Feedback**, select the actual FFB wheel interface and start with the MOZA R3 v0.1 profile.
8. Only change `Reverse ConstantForce` or `Reverse Spring` if the force direction is wrong. On my MOZA R3 test setup, Reverse Spring is **OFF**.

> **Caution:** Direct-drive wheels can generate substantial torque. Start with a conservative wheel-base torque limit and avoid repeated force tests with your hands in an unsafe position.

### Tested hardware

- **Personally hardware-tested:** MOZA R3 only
- Steering range used in my setup: 270°
- Input: SDL3 raw-joystick multi-device path
- FFB output: Windows DirectInput COM
- Windows / Win32 x86 build

Other MOZA, Fanatec, Logitech, Thrustmaster, Simagic and DirectInput wheels may work, but **I have not personally verified them in v0.1**. Compatibility reports are welcome; please include `OutRun2006Tweaks.log`, wheel model and driver/firmware information.

### Troubleshooting

- If input is missing, first check live movement under F11 **Controllers**.
- If FFB is missing, reselect the wheel under **Force Feedback** and try **Refresh connected wheels**.
- If force pushes farther away from center, check the direction options.
- If a pedal works backwards, recalibrate/invert that axis.
- If old settings appear to conflict with v0.1, back up the user config and retest from clean defaults.
- `WheelFFB:` and multi-device lines in `OutRun2006Tweaks.log` are the most useful diagnostics.

---

## Credits / Licenses

This fork exists because of the work already done by other OutRun community developers. Thank you especially to:

- **[emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks)** — the upstream project this fork is based on.
- **[hyp36rmax/multi-device-input](https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input)** — major reference for modern SDL3 multi-device wheel input, guided setup, device identity and community hardware-testing lessons.
- **[d-b-c-e/OutRun2006Tweaks-FFB](https://github.com/d-b-c-e/OutRun2006Tweaks-FFB)** — major reference for DirectInput wheel FFB architecture and force-model/signal-conditioning ideas.
- The OutRun2006Tweaks Discord/community testers who documented hardware behavior and shared troubleshooting results.

The referenced OutRun2006Tweaks repositories above publish their code under the **MIT License** and retain the upstream `Copyright (c) 2023 emoose` notice. This repository keeps that license and notice in [LICENSE.md](LICENSE.md). Additional attribution and scope notes are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

No `WheelFfb.dll` or vendored dbce wheel-toolkit binary is included or required by this fork; the FFB backend here is implemented directly through Windows DirectInput COM.

OutRun, OutRun 2006: Coast 2 Coast and related assets belong to their respective rights holders. MOZA and other hardware/vendor names are used only to describe compatibility. This project is not affiliated with or endorsed by those companies.

## Upstream project

For the original project's complete feature list, releases and community links, see **[emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks)**.

## Building

The project targets **Win32 Release** and uses Visual Studio 2022, CMake and Git. The `wheel-ffb` branch applies the wheel/input hardening passes during CI before compiling `dinput8.dll`.

See [WHEEL_FFB.md](WHEEL_FFB.md) for architecture and tuning details.
