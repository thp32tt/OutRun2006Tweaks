OutRun 2006 VR v0.03 Beta - Cockpit Passenger Update

ENGLISH

WHAT'S NEW
- Cockpit passenger handling is now stable in physical VR testing.
- F11 > Settings > VR provides two exclusive passenger choices:
  * Passenger: Follow Camera 0 (default): follows the game's native camera-0 passenger state.
  * Passenger: Remove: hides the passenger only in cockpit camera mode 1.
- High-speed vertical passenger jitter was corrected by matching the passenger transform to the stabilized cockpit vehicle transform.
- VR startup now prewarms the OpenXR host before the game and keeps the helper hidden, preventing the release launcher from falling into 2D Theater or stealing game focus.
- The menu/theater presentation keeps the game window fullscreen-marked so the Windows taskbar does not appear inside the HMD crop.
- Existing cockpit crash hardening, F0 Render Scope, glass-reflection suppression, original full-car rendering and seat persistence are retained.

PASSENGER CONTROLS
- Passenger: Follow Camera 0 keeps the native ROB02 passenger lifecycle and follows the original camera-0 state.
- Passenger: Remove affects cockpit camera mode 1 only.
- Camera 0 and goal/finish-scene passenger rendering are not removed.
- Passenger mode changes apply live and persist through OutRun2006Tweaks.user.ini.

DEFAULT COCKPIT POSITION
- SeatBack=-0.08
- SeatDown=+0.08
- SeatRight=0.0
- Press F12 while looking forward to recenter.

INSTALL / RUN
- Extract the ZIP into the folder containing OR2006C2C.EXE.
- Run Start-OutRun-VR.cmd for VR cockpit mode.
- Direct OR2006C2C.EXE launch remains normal 2D + FFB.

VERIFICATION
- Native passenger runtime verifier.
- 10 independent passenger-path static audits before release packaging.
- Original ROB02 passenger-hook ABI verification against the canonical replacement OR2006C2C.EXE.
- Win32 game DLL, x64 OpenXR host, launcher/package validation and canonical EXE SHA gate.
- Physical Quest 3 testing confirmed stable passenger options and general VR operation.

한국어

주요 변경사항
- 실제 VR 테스트에서 운전석 동승자 표시/제거 옵션이 안정화되었습니다.
- F11 > Settings > VR에 서로 배타적인 두 동승자 옵션을 제공합니다.
  * Passenger: Follow Camera 0 (기본값): 게임의 0번 3인칭 시점에 존재하는 원본 동승자 상태를 운전석에서도 따라갑니다.
  * Passenger: Remove: 동승자를 운전석 카메라(mode 1)에서만 숨깁니다.
- 고속 주행 시 동승자만 위아래로 떨리던 현상을 차량과 동일한 안정화 변환을 사용하도록 수정했습니다.
- VR 실행 시 OpenXR host를 게임보다 먼저 숨김 실행하도록 수정하여 릴리즈 버전이 2D Theater로 시작하거나 게임 포커스를 빼앗기는 문제를 수정했습니다.
- 메뉴/시어터 화면에서 Windows 작업표시줄이 HMD 4:3 화면에 함께 보이는 문제를 완화하도록 게임 창을 fullscreen 상태로 표시합니다.
- 기존 시작 크래시 방지, F0 Render Scope, 유리 반사 억제, 원본 전체 차량 유지, 좌석 위치 저장 기능은 그대로 유지합니다.

동승자 옵션
- Passenger: Follow Camera 0는 원본 ROB02 동승자 이벤트 생명주기를 유지하면서 0번 카메라 상태를 따라갑니다.
- Passenger: Remove는 운전석 카메라(mode 1)에만 적용됩니다.
- 0번 카메라 및 골/피니시 장면의 원본 동승자 렌더링은 제거하지 않습니다.
- 동승자 설정은 즉시 적용되며 OutRun2006Tweaks.user.ini에 저장됩니다.

기본 운전석 위치
- SeatBack=-0.08
- SeatDown=+0.08
- SeatRight=0.0
- 정면을 바라본 상태에서 F12를 누르면 VR 시점이 재정렬됩니다.

설치 / 실행
- ZIP을 OR2006C2C.EXE가 있는 게임 폴더에 압축 해제합니다.
- VR 운전석 모드는 Start-OutRun-VR.cmd를 실행합니다.
- OR2006C2C.EXE를 직접 실행하면 기존처럼 2D + FFB로 실행됩니다.

검증
- Native passenger runtime 검증.
- 릴리즈 패키징 전 10개 독립 동승자 경로 정적 검증.
- canonical OR2006C2C.EXE 대상 원본 ROB02 passenger-hook ABI 검증.
- Win32 게임 DLL, x64 OpenXR host, 런처/패키징 검증 및 원본 EXE SHA 고정 검증.
- Quest 3 실제 테스트에서 동승자 옵션과 전반적인 VR 동작 안정성을 확인했습니다.

This is a fan-made beta mod. Keep a backup of your game folder.
