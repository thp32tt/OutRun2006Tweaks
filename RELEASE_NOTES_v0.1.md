# OutRun2006Tweaks Wheel FFB v0.1

## 한국어

이 빌드는 **OutRun 2006: Coast 2 Coast를 현대 레이싱 휠로 플레이하기 위한 실험적 wheel-ffb 포크**입니다. 현재 제가 직접 실기 확인한 장비는 **MOZA R3**이며, 다른 DirectInput 휠은 구조상 동작할 수 있지만 미검증입니다.

### 주요 기능

- SDL3 raw joystick 기반 멀티 디바이스 입력: 휠 / 별도 페달 / 쉬프터 / 버튼박스 / 게임패드 동시 바인딩
- 게임 내 **Input Bindings Quick Setup**과 Steering / Accelerator / Brake Min-Rest-Max 보정
- Quick Setup의 Start / Confirm / Back / Menu Up-Right-Down-Left 설정, 필요 없는 단계 Skip, 완료 후 `Keep & Fine-tune`
- Windows DirectInput COM 네이티브 FFB
- Physics SAT + Natural SAT fallback, 저속 센터링 Spring, Dynamic Damping, 그립 손실 언로드, 노면/타이어/기어/충돌 효과
- 정확한 FFB GUID 선택, 포커스 상실/장치 손실/watchdog 안전 처리
- 게임 플레이 중에만 동작하는 고정 20% 좌/우 방향 테스트

### MOZA R3 권장 시작점

F11 **Force Feedback**에는 두 프리셋이 있습니다.

| Setting | Physics SAT | Natural SAT |
| --- | ---: | ---: |
| Overall Strength | 0.70 | 0.70 |
| Centering Spring | 0.65 | 0.65 |
| Spring Saturation | 0.95 | 0.95 |
| Dynamic Damping | 0.28 | 0.30 |
| Self-aligning Torque | 1.45 | 1.75 |
| Grip-loss Response | 0.65 | 0.65 |
| Weight Transfer | 0.15 | 0.20 |
| Force Slew Rate | 0.040 | 0.045 |
| Road Detail | 0.30 | 0.30 |
| Tire Slip | 0.20 | 0.20 |
| Collision | 0.38 | 0.38 |
| Hardware Spring / Damper / sine | ON | ON |
| Reverse SAT / ConstantForce | ON | ON |
| Reverse Spring | OFF | OFF |

`Load MOZA R3 Physics SAT`는 차량 이동/방향으로 front slip을 추정하고, 유효한 Physics 샘플이 없을 때는 Natural SAT로 폴백합니다. `Load MOZA R3 Natural SAT`는 조향각 기반의 보다 단순한 비교 경로입니다. 방향은 드라이버/장치에 따라 달라질 수 있으므로 20% 방향 테스트 결과를 우선하세요.

### 초기 설정

1. 휠/페달을 연결하고 게임을 실행합니다.
2. 게임의 Controller Configuration 또는 **F11 → Force Feedback → Open Input Bindings**를 엽니다.
3. Quick Setup으로 Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left를 설정합니다. 없는 기능은 `Skip this step`을 사용합니다.
4. 완료 화면에서 조향/페달 값을 확인합니다. 범위가 맞지 않으면 `Keep & Fine-tune` 후 해당 JoyAxis의 **Calibrate**에서 Min / Rest / Max를 잡습니다.
5. `Save bindings` 또는 `Save & Return to game`으로 입력을 저장합니다.
6. Force Feedback에서 실제 FFB 출력 장치를 선택하고 Physics SAT 또는 Natural SAT 프리셋을 시작점으로 사용합니다.
7. FFB 수동 변경은 즉시 적용되며 `Save Force Feedback`으로 저장합니다. 별표(*)가 있으면 아직 저장되지 않은 변경이 있다는 뜻입니다.

> Direct Drive 휠은 큰 토크를 낼 수 있습니다. 처음에는 휠 베이스의 최대 토크를 보수적으로 설정하고 안전 방향 테스트부터 확인하세요.

### 테스트 범위

- 직접 테스트: MOZA R3
- 개인 테스트 조향 범위: 270°
- 입력: SDL3 raw joystick multi-device
- FFB: Windows DirectInput COM
- Windows Win32 x86

문제 제보 시 `OutRun2006Tweaks.log`, 휠/페달/쉬프터 모델과 드라이버/펌웨어 정보를 함께 남겨 주세요.

---

## English

This is an experimental **wheel-ffb fork for modern driving hardware in OutRun 2006: Coast 2 Coast**. My personally hardware-tested setup is a **MOZA R3**; other DirectInput wheels may work but remain unverified by me.

### Highlights

- SDL3 raw-joystick multi-device input for wheel / separate pedals / shifter / button box / gamepad
- In-game **Input Bindings Quick Setup** plus Steering / Accelerator / Brake Min-Rest-Max calibration
- Start / Confirm / Back / Menu Up-Right-Down-Left steps, optional-step Skip, and `Keep & Fine-tune`
- Native Windows DirectInput COM force feedback
- Physics SAT with full Natural SAT fallback, low-speed centering spring, Dynamic Damping, grip-loss unloading, road/tyre/gear/collision effects
- Exact FFB GUID selection plus focus-loss, device-loss and watchdog safety
- Fixed 20% left/right direction tests gated to active gameplay

### Recommended MOZA R3 starting points

The F11 **Force Feedback** page provides two presets:

| Setting | Physics SAT | Natural SAT |
| --- | ---: | ---: |
| Overall Strength | 0.70 | 0.70 |
| Centering Spring | 0.65 | 0.65 |
| Spring Saturation | 0.95 | 0.95 |
| Dynamic Damping | 0.28 | 0.30 |
| Self-aligning Torque | 1.45 | 1.75 |
| Grip-loss Response | 0.65 | 0.65 |
| Weight Transfer | 0.15 | 0.20 |
| Force Slew Rate | 0.040 | 0.045 |
| Road Detail | 0.30 | 0.30 |
| Tire Slip | 0.20 | 0.20 |
| Collision | 0.38 | 0.38 |
| Hardware Spring / Damper / sine | ON | ON |
| Reverse SAT / ConstantForce | ON | ON |
| Reverse Spring | OFF | OFF |

`Load MOZA R3 Physics SAT` estimates front slip from current vehicle motion/heading and falls back to Natural SAT whenever a valid physics sample is unavailable. `Load MOZA R3 Natural SAT` is the simpler steering-angle-based comparison path. Driver direction can vary, so the safe 20% direction test takes precedence over preset assumptions.

### Initial setup

1. Connect/power the wheel and pedals, then launch the game.
2. Open the game's Controller Configuration or **F11 → Force Feedback → Open Input Bindings**.
3. Run Quick Setup: Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left. Use `Skip this step` for controls the wheel does not have.
4. Verify the live steering/pedal bars. If a range is wrong, choose `Keep & Fine-tune` and use **Calibrate** on the JoyAxis to set Min / Rest / Max.
5. Persist input with `Save bindings` or `Save & Return to game`.
6. Under Force Feedback, select the actual FFB output and start from the Physics SAT or Natural SAT preset.
7. Manual FFB changes apply live; use `Save Force Feedback` to persist them. An asterisk (*) means changes are still unsaved.

> Direct-drive wheels can generate substantial torque. Start with a conservative wheel-base torque limit and verify the safe direction tests first.

### Tested scope

- Personally tested: MOZA R3
- Steering range used in my setup: 270°
- Input: SDL3 raw-joystick multi-device
- FFB: Windows DirectInput COM
- Windows Win32 x86

For compatibility reports, include `OutRun2006Tweaks.log`, wheel/pedal/shifter models, and driver/firmware versions.

### Credits / license

This work builds on public source, design and testing from **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB**, and community hardware reports. The upstream MIT license and notices are retained; see `LICENSE.md` and `THIRD_PARTY_NOTICES.md`.
