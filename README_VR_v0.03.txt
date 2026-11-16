OutRun 2006 VR v0.03 Beta - Cockpit Passenger Update

ENGLISH
- Extract the ZIP into the folder containing OR2006C2C.EXE.
- Run Start-OutRun-VR.cmd for VR cockpit mode.
- Press F12 while looking forward to recenter.
- F11 > Settings > VR includes two exclusive passenger choices:
  * Passenger: Follow Camera 0 (default): cockpit follows the native camera-0 passenger state.
  * Passenger: Remove: hides the passenger only in cockpit camera mode 1.
- Camera 0 always keeps the game's original passenger rendering.
- The mod never creates a missing ROB02 passenger event or rewrites/closes the native passenger lifecycle.
- SeatBack=-0.08, SeatDown=+0.08, SeatRight=0.0 remain the default cockpit position.
- F0 Render Scope remains ON in the VR launcher.
- Driver hidden / original full car retained / cockpit glass reflection suppression remain unchanged.
- Seat and passenger settings persist through OutRun2006Tweaks.user.ini.
- Direct OR2006C2C.EXE launch remains normal 2D + FFB.

VERIFICATION
- Native passenger runtime verifier.
- 10 independent passenger-path static audits before release packaging.
- Original ROB02 passenger hook ABI validation against the replacement OR2006C2C.EXE in the normal build.
- Existing crash hardening and copy/run launcher validation remain enabled.

한국어 안내
- ZIP을 OR2006C2C.EXE가 있는 게임 폴더에 압축 해제합니다.
- VR 운전석 모드는 Start-OutRun-VR.cmd를 실행합니다.
- 정면을 바라본 상태에서 F12를 누르면 VR 시점이 재정렬됩니다.
- F11 > Settings > VR에서 동승자 옵션 두 개 중 하나를 선택합니다.
  * Passenger: Follow Camera 0 (기본값): 0번 3인칭 시점의 원본 동승자 상태를 운전석에서도 따라갑니다.
  * Passenger: Remove: 동승자를 운전석 카메라(mode 1)에서만 숨깁니다.
- Remove를 선택해도 0번 시점의 원본 동승자는 그대로 유지됩니다.
- 모드는 없는 ROB02 동승자 이벤트를 새로 만들지 않고 원본 이벤트 생명주기를 변경하지 않습니다.
- 기본 운전석 위치는 SeatBack=-0.08, SeatDown=+0.08, SeatRight=0.0입니다.
- 차량 떨림 완화용 F0 Render Scope는 VR 런처에서 기본 ON입니다.
- 운전자 숨김, 원본 전체 차량 유지, 유리 반사 억제 설정은 기존과 동일합니다.
- 좌석 및 동승자 설정은 OutRun2006Tweaks.user.ini 경로로 유지됩니다.
- OR2006C2C.EXE를 직접 실행하면 기존처럼 2D + FFB로 실행됩니다.

This is a fan-made beta mod. Keep a backup of your game folder.
