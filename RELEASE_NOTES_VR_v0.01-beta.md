# OutRun 2006 VR v0.01 Beta

첫 공개 베타 패키지입니다. 2026-11-02 Quest 3 + Virtual Desktop/VDXR 실기에서 현재 테스트 경로가 정상 동작하는 것을 확인한 DX9Ex Focus 빌드를 기준으로 합니다.

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

- Quest 3 / Virtual Desktop / VDXR 사용자 실기: 현재 메뉴/로딩/차량선택/게임플레이 화면 정상 확인
- 릴리즈 패키지는 테스트 로그 수집 스크립트를 포함하지 않습니다.
