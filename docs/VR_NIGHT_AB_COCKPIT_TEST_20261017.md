# 2026-10-17 Quest 3/VDXR DX9Ex 한 번에 A/B/C 실기 비교

이 패키지는 원본 게임의 EXE/PMT/DDS를 수정하지 않습니다. `OR2006C2C.EXE`가 있는 폴더에 ZIP 전체를 풀고 `OutRunVR-Slot-Selector.cmd`를 실행합니다. 먼저 Virtual Desktop에서 VDXR을 선택합니다. 게임이 켜져 있으면 변경할 수 없으므로 반드시 게임과 `outrun-vr-host.exe`를 모두 종료한 뒤 다른 옵션을 누릅니다.

## 운전석 A/B/C (같은 R84 최신 렌더러)

| 선택 | 실제 동작 | 확인할 항목 |
| --- | --- | --- |
| **A 운전석 기본 100%** | DriverSeatView=true, DriverSeatVehicleScale=1.00 | 운전석 기준 위치, 차체 크기 |
| **B 운전석 115%** | DriverSeatView=true, DriverSeatVehicleScale=1.15 | A 대비 차체 비율/시야 |
| **C 운전석 130%** | DriverSeatView=true, DriverSeatVehicleScale=1.30 | 과대 비율/차체 절단 |
| **CURRENT_FOCUS** | DriverSeatView=false | 원본형 전방 시야 대조군 |
| **G_COCKPIT** | 운전석 기본 INI(현재 1.15) | 입자 효과 결합 비교 |

- F11 VR 메뉴에서 운전석 전후/좌우/높이/차량 배율을 추가 조정할 수 있습니다. 수치 기록 후 다시 실행하여 비교하면 됩니다.
- 유리 불투명도 콤보 0.20/0.30/0.50/0.80은 **진단용**입니다. 설정값과 유리 재질 후보 추적 로그만 기록하며 유리 렌더링의 알파값을 바꾸지 않습니다. 원본 PMT를 손대지 않으며, 현재 확보되지 않은 머티리얼 소유권을 추측하지 않습니다.
- 각 A/B/C 실행 시 `RUN_OVERRIDES.txt`에 실제 전달한 게임 인수와 스케일/불투명도 진단값을 기록합니다. 게임 종료 후 `OutRun2_VR_ANALYZE_*.zip`을 수집합니다.
- 나머지 B_HUD / C_FLARE / D_PERF / R26_SAFE 슬롯은 기존 기능 문제 분리용입니다. 선택 전에 실행 중인 게임/호스트를 종료합니다.
- `START_DX9EX_TEST.cmd`는 안전한 R84 일반 기본 실행(운전석 OFF)입니다. 운전석 테스트는 GUI의 A/B/C를 선택해야 합니다.
- GitHub Actions Windows 컴파일/패키지 검증과 Quest 3 실제 VR 검증은 다릅니다. `RUNTIME_VALIDATION=UNTESTED` until HMD test.
