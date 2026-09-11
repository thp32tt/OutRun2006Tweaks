# OutRun2006Tweaks Wheel FFB v0.1

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

First public release of the `wheel-ffb` branch.

### What this release adds

- SDL3 raw multi-device input for modern wheel setups.
- One Input Bindings path for steering, pedals, shifter and buttons.
- Native Windows DirectInput COM wheel FFB.
- Physics SAT with Natural SAT fallback and mechanical/caster trail.
- Dynamic damping and grip-loss unloading.
- Low-speed centering spring kept light so it does not dominate SAT.
- Road, curb, tire, gear and collision tactile effects.
- MOZA R3 DirectInput auto-match and exact GUID persistence.
- MOZA R3 ConstantForce road-texture fallback.
- Snow-stage curb compensation and four-wheel mixed/full-rough surface detection.
- Focus/device-loss cleanup, reconnect handling and 20% safe direction tests.

### Tested hardware

Primary hardware validation for v0.1 was performed with **MOZA R3**. Other DirectInput wheels may work but are not considered verified by this release unless separately reported.

### Setup

Use **F11 → Input Bindings** for steering, pedals, shifter and button configuration. After manual binding changes, use **Save & Return to game** to persist them.

For MOZA R3, **F11 → Force Feedback** provides `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT` as starting profiles. R3 road detail is then routed through the release compatibility layer's ConstantForce fallback.

FFB edits apply live. Use **Save Force Feedback** to persist changes; an unsaved live change can otherwise be lost after restart.

### Install

Extract `OutRun2006Tweaks-Wheel-FFB-v0.1.zip` into the OutRun 2006: Coast 2 Coast game directory and replace files when prompted.

The ZIP intentionally contains only the runtime files, the upstream replacement `OR2006C2C.exe`, one README and one consolidated open-source notice file.

### Package contents

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt` is generated from the actual dependency source trees used by CI so required notices are preserved without filling the release ZIP with separate license/readme files.

### Known issue

On snow stages, curb vibration may fade or disappear when all four wheels are fully on the same rough curb/shoulder surface. Partial curb contact is detected correctly. This affects tactile feedback only and does not affect steering or SAT. See [Issue #1](https://github.com/thp32tt/OutRun2006Tweaks/issues/1).

### Notes

- `DISCORD_SHARE_v0.1.md` is not part of the repository or release package anymore.
- Input setup is owned by Input Bindings; the release documentation does not require the old guided Quick Setup path.
- On MOZA R3, road/slip texture uses the ConstantForce fallback because the hardware sine path was not physically useful in testing.
- Mixed curb contact and fully crossing onto a rough curb use the same strong tactile profile, including snow-stage compensation.
- The release is built only after the consolidated source verifier and production FFB math tests pass.

### Credits

Based on `emoose/OutRun2006Tweaks`, with public design/reference work from `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB`, and OutRun community hardware reports.

This is an unofficial community fork and is not affiliated with SEGA or MOZA.

---

<a id="한국어"></a>
## 한국어

`wheel-ffb` 브랜치의 첫 공개 릴리즈입니다.

### 이번 릴리즈에 추가된 기능

- 현대식 휠 구성을 위한 SDL3 Raw 멀티 디바이스 입력
- 스티어링, 페달, 시프터, 버튼을 설정하는 단일 Input Bindings 경로
- Windows DirectInput COM 기반 네이티브 휠 FFB
- Physics SAT + Natural SAT 폴백 및 Mechanical/Caster Trail
- Dynamic Damping과 그립 손실 시 조향 하중 감소
- SAT를 가리지 않도록 약하게 설정한 저속 센터링 스프링
- 노면, 연석, 타이어, 기어, 충돌 촉각 효과
- MOZA R3 DirectInput 자동 매칭 및 정확한 GUID 저장
- MOZA R3 ConstantForce 노면 텍스처 폴백
- 눈 맵 연석 보정 및 네 바퀴 mixed/full-rough 표면 감지
- 포커스/장치 손실 시 효과 정리, 재연결 처리, 20% 안전 방향 테스트

### 테스트한 하드웨어

v0.1의 주 하드웨어 검증은 **MOZA R3**로 진행했습니다. 다른 DirectInput 휠도 동작할 수 있지만 별도 사용자 보고가 없는 장비는 이 릴리즈에서 검증된 것으로 보지 않습니다.

### 설정 방법

스티어링, 페달, 시프터, 버튼 설정은 **F11 → Input Bindings**를 사용합니다. 수동으로 바인딩을 변경한 뒤에는 **Save & Return to game**으로 저장합니다.

MOZA R3는 **F11 → Force Feedback**에서 시작용 프리셋인 `Load MOZA R3 Physics SAT`와 `Load MOZA R3 Natural SAT`를 사용할 수 있습니다. R3의 노면 디테일은 이후 릴리즈 호환 레이어의 ConstantForce 폴백을 통해 출력됩니다.

FFB 변경 사항은 즉시 적용됩니다. 재시작 후 유지하려면 **Save Force Feedback**으로 저장해야 합니다.

### 설치

`OutRun2006Tweaks-Wheel-FFB-v0.1.zip`을 OutRun 2006: Coast 2 Coast 게임 폴더에 압축 해제하고 파일 교체 안내가 나오면 덮어씁니다.

ZIP에는 실행에 필요한 파일, 원본 프로젝트에서 제공하는 교체용 `OR2006C2C.exe`, README 하나, 통합 오픈소스 고지 파일 하나만 포함하도록 구성했습니다.

### 배포 파일 구성

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt`는 CI가 실제로 사용한 의존성 소스 트리에서 생성합니다. 필요한 오픈소스 고지는 유지하면서 릴리즈 ZIP에 여러 라이선스/README 파일이 흩어지지 않도록 하나로 통합했습니다.

### 알려진 문제

눈 맵에서 네 바퀴가 모두 동일한 거친 연석/숄더 표면에 완전히 올라가면 연석 진동이 약해지거나 사라질 수 있습니다. 차량 일부만 연석에 걸친 상태는 정상적으로 감지됩니다. 촉각 피드백에만 영향을 주며 조향력이나 SAT에는 영향이 없습니다. 자세한 내용은 [Issue #1](https://github.com/thp32tt/OutRun2006Tweaks/issues/1)을 참고하세요.

### 참고 사항

- `DISCORD_SHARE_v0.1.md`는 더 이상 저장소나 릴리즈 패키지에 포함하지 않습니다.
- 입력 설정은 Input Bindings가 담당하며, v0.1 문서에서는 예전 Guided Quick Setup 경로를 필수로 안내하지 않습니다.
- MOZA R3에서는 테스트 시 하드웨어 sine 경로의 노면 질감이 실질적으로 유용하지 않아 노면/슬립 텍스처에 ConstantForce 폴백을 사용합니다.
- 부분 연석 접촉과 차량 전체가 거친 연석 위로 넘어간 상태에 같은 강한 촉각 프로필을 적용하며 눈 맵 보정도 포함됩니다.
- 통합 소스 검증기와 실제 FFB 수학 테스트가 성공한 뒤에만 릴리즈 빌드를 생성합니다.

### 크레딧

`emoose/OutRun2006Tweaks`를 기반으로 하며 `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB`의 공개 설계/참고 작업과 OutRun 커뮤니티의 하드웨어 보고를 참고했습니다.

이 프로젝트는 비공식 커뮤니티 포크이며 SEGA 또는 MOZA와 제휴하거나 공식적으로 지원받는 프로젝트가 아닙니다.
