# OutRun 2006 VR v0.01 Beta

v0.01 Beta 공개 베타입니다. 2026-11-02 Quest 3 + Virtual Desktop/VDXR에서 기존 DX9Ex Focus 렌더링 경로는 정상 동작이 확인됐고, 사용자 요청에 따라 2D/VR 선택 실행 구조를 포함해 게시합니다. 새 **직접 EXE 2D / CMD VR 진입점은 CI/정적 검증을 통과했으며 사용자 PC 실기 확인은 후속 검증 항목**입니다.

## 중요 조작: F12 리센터

- **VR 화면의 정면이 어긋나거나 메뉴/게임 화면 방향이 현재 착석 방향과 맞지 않으면, 원하는 정면을 바라본 상태에서 `F12`를 누르세요.**
- `F12`는 현재 HMD의 위치와 방향을 새 VR 기준 원점으로 다시 설정하여 메뉴/시어터와 게임플레이 공간을 다시 정렬합니다.
- 게임 시작 직후, HMD를 다시 착용했을 때, 또는 플레이 중 정면 기준이 어긋났을 때 언제든 사용할 수 있습니다.
- 기본 키: **F12 = VR Recenter** (`F10`은 HUD Toggle)

## English Summary

OutRun 2006 VR v0.01 Beta for Quest 3 / OpenXR (VDXR). This build includes the stabilized DX9Ex Focus VR path, fixed front-end/menu alignment, lens-flare and HUD-related fixes, and a quiet release profile with telemetry/file logging disabled by default.

- One shared `dinput8.dll` includes Tweaks, wheel FFB, and VR.
- Run `OR2006C2C.exe` directly for **2D + FFB**.
- Run `Start-OutRun-VR.cmd` for **VR + FFB**.
- `Start-OutRun.cmd` lets you choose 2D or VR.
- No PowerShell script is required in the release package.
- Extract the ZIP into the game folder containing `OR2006C2C.exe`.

## Important Control: F12 Recenter

- **If the VR view is not centered, or the menu/game is facing the wrong direction, look straight ahead in your desired forward direction and press `F12`.**
- `F12` resets the current HMD position and orientation as the new VR application origin, re-anchoring the menu/theater and gameplay space.
- Use it after launching the game, after putting the headset back on, or anytime the forward direction feels misaligned.
- Default key: **F12 = VR Recenter** (`F10` is HUD Toggle)

## 주요 수정

- 메인 메뉴/로딩/차량 선택 화면의 VR 좌표계 안정화
- 메뉴 깜빡임 제거 및 16:9 mirror geometry 고정
- 차량 선택 2D UI와 3D 차량의 whole-composite 정렬
- 메뉴에 남던 검은 직사각형(letterbox rail) 물리 좌표 수정
- 라이벌 표시, 차량 위 순위, +TIME, GOAL 관련 기존 수정 유지
- 렌즈플레어 안정화 상태 유지
- DirectGPU mono-elision 및 exact 0x418CF0 모래/자갈 파티클 fastpath 유지
- VR 렌더 해상도는 OpenXR/VDXR eye extent 기준, PC mirror와 분리

## v0.01 Beta 기본 성능 프로파일

- `VR.DirectGpuOnly=true`
- `Graphics.ReflectionUpdateRate=0.25`
- `Graphics.TransparencySupersampling=false`
- `VR.TransparencySupersampling=false`
- R23 pixel probe OFF
- `VR.Telemetry=false`
- `VR.FileLogging=false`

릴리즈 기본 실행에서는 `OutRun2006Tweaks.log`, host full-trace, eye-extent, pipeline, frame-pacing 파일을 만들지 않습니다. 개발/진단용 런처는 환경변수로 로그를 다시 켤 수 있습니다.

## 설치

ZIP 내용을 `OR2006C2C.EXE`가 있는 게임 폴더에 덮어씁니다.

- **선택 실행:** `Start-OutRun.cmd`에서 **1 = 2D + FFB**, **2 = VR + FFB**를 선택할 수 있습니다.
- **일반 2D 실행:** `OR2006C2C.EXE`를 직접 실행해도 됩니다. 동일한 `dinput8.dll`의 Tweaks/휠 FFB는 유지되고 VR 훅/OpenXR host만 비활성화됩니다.
- **VR 바로 실행:** `Start-OutRun-VR.cmd`를 실행합니다. 내부적으로 선택 런처의 VR 모드를 호출합니다.
- 릴리즈에는 별도 VR DLL을 두지 않습니다. **하나의 `dinput8.dll`에 FFB와 VR 코드가 함께 포함**되고 실행 모드만 분리합니다.
- 테스트 ZIP에서 사용하던 PS1은 릴리즈에 필요하지 않습니다. 정상 테스트 PS1이 넣던 DX9Ex/OpenXR/DirectGPU/cadence/HUD/menu 실행 프로파일을 `Start-OutRun.cmd`의 VR 경로에 직접 고정했습니다.
- 기존 `OutRun2006Tweaks.user.ini`에 `VR.Enabled=true`가 남아 있어도 릴리즈판의 EXE 직접 실행은 2D로 강제됩니다.

## 검증

- 기존 Quest 3 / Virtual Desktop / VDXR Focus 렌더링 상태: 메뉴/로딩/차량선택/게임플레이 정상 확인
- **신규 진입점 CI/정적 검증 PASS:** `OR2006C2C.EXE` 직접 실행 = 2D + FFB, `Start-OutRun-VR.cmd` = VR + FFB
- 사용자 PC에서는 위 두 실행 경로를 각각 한 번 확인하면 됩니다. 이 신규 진입점의 실제 PC 런타임 확인은 아직 별도 기록되지 않았습니다.
- 공개 베타 패키지는 테스트 로그 수집 PS1을 포함하지 않습니다.
