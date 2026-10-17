[2026-10-17 — SOURCE_IMPLEMENTATION_70_PERCENT]
유효 작업시간의 최소 70%는 미완료 기능의 실제 C++/HLSL/후킹/host·입력 소스 개발과 실패 원인 수리에 우선 배분한다. 분석 ≤15%, 국소 검증·최종 CI 조정 ≤10%, 기록·C6 ≤5% 목표이며 필수 통합 게이트는 그대로 유지한다. CI 원격 대기는 별도 집계하고 확인되지 않은 작업 비율을 실제 측정값으로 주장하지 않는다.
30분 주기는 신규 TASK_ID 발급이 아니라 기존 미완료 TASK_ID를 보존한 체크포인트·안전한 대화 재개 주기다. C6·CI 대기·대화 전환으로 미완료 기능을 포기하거나 새 점수를 가산하지 않는다. 전체 CI는 마지막 통합 validation-bearing SHA에, 실패했으면 동일 TASK_ID의 바뀐 SHA에만 실행한다.

[2026-10-15 21:30 KST — DEVELOPMENT_FIRST_20261015 운영 정책 / 기존 필수 CI 유지]
- 새 작업은 실제 미완료 게임 C++/HLSL/후킹/host/입력 경로 또는 사용자 확인 시각 결함·측정된 성능 병목부터 선택한다. C0/C1은 최신 HEAD·claim·실패 지점만 짧게 확인하고 C2 기능 전체를 우선 개발한다.
- 기능 단위로 소스와 필요한 국소 회귀 테스트를 함께 구현한다. 검증 스크립트의 오래된 문자열/정규식·정책 기록 실패는 실제 컴파일·동작 실패와 구분하고, 필요 최소한으로 한 번 묶어 수리한다. 검증 항목을 삭제하거나 PASS를 허위 기입하지 않는다.
- 개발 중에는 변경 영역 정적/단위 검증을 사용하고, 기능 후보의 마지막 validation-bearing SHA에서 필수 GitHub Actions 전체 Gate를 수행한다. 실제 실패로 소스/검증 입력 SHA가 변경되면 동일 TASK_ID에서 원인 수리 후 해당 SHA로 재검증한다. 동일 SHA PASS 재실행·불필요한 중복 전체 빌드 금지.
- CI 수리·회귀 보정·C6 기록·checkpoint·rollover는 별도 새 기능이나 신규 점수 성과가 아니다. 기존 TASK_ID/FEATURE_ID와 material_result_sha를 유지하고, C6만 남으면 최소 결과 기록 후 다른 안전한 미완료 기능을 개발한다.
- DX11은 메뉴→차량→레이스 전 프레임과 게임패드·OpenXR 연결, DX9Ex는 R84 실게임 렌즈/HUD/+TIME/GOAL·측정 성능 결함을 우선한다. DXVK 동결·DX9Ex 폴백·원본 입력/FFB/SkyGlow·장치 복구 보호. HMD 미실행은 RUNTIME_VALIDATION=UNTESTED.
- 소스 구현·필요한 수리·최종 CI·C6를 하나의 기능 결과로 보고하고, 구현 커밋과 검증/기록 커밋을 별도로 구분한다. 컨트롤러 이미지 재빌드·재배포 증거 없이는 GitHub 정책 커밋을 실시간 적용으로 주장하지 않는다.

# DX9Ex 자동개발 — 30분 독립 실행 (2026-10-11 최신 우선)

목적: 미완료 VR 안정화/성능 최적화를 실제 소스에 지속 구현한다. TASK_ID는 GitHub 커밋 이력용으로만 유지한다. C6·과거 BLOCKED·한정된 FEATURE_CONTRACT/feature_backlog.json 소진은 신규 개발 발행을 막지 않는다.

1. GitHub 연결 도구로 thp32tt/OutRun2006Tweaks의 vr-d3d9ex-focus 최신 HEAD와 AGENTS.md, docs/DX9EX_AUTODEV_PRIORITY_20261010.md, docs/VR_PROBLEM_HISTORY.md 및 실제 소스 상태를 확인한다.
2. 이미 CI 통과한 FRAME_PACING_DIAGNOSTICS / XR_RECOMMENDED_EYE_EXTENT를 같은 SHA로 반복 점검하지 않는다. **성능·VR frame pacing 개선의 구현 가능한 병목**, Reset/ResetEx·device-loss 복구, OpenXR per-eye RT 통합, HUD 중복/헤드락/렌즈플레어 등 남아 있는 실제 결함을 우선 구현한다.
3. 이전 TASK가 C6 대기라면 동일 검증 SHA 기록만 최소 처리하고 새로운 ID를 발급해 덮어쓰지 않는다. 과거에 구현한 기능은 재작성하지 않는다. 소스/테스트 실질 변경 없는 리뷰·문서·검증 전용 커밋은 성과로 계산하지 않는다.
4. 동일 파일/기능을 다른 작업자가 수정 중이면 원격 GitHub claim과 최신 HEAD를 보고 다른 독립 문제를 선택한다. 강제 push/강제 reset/CI skip 금지. SkyGlow/정상 도로·차량 스테레오 및 기존 장치 복구 보호 기준을 유지한다.
5. C0~C6 가능한 단계까지 실제 C++/후킹/셰이더/IPC 코드를 작성하고 관련 소규모 회귀 후 material commit을 남긴다. 직접 Quest3·VDXR 테스트하지 않았다면 RUNTIME_VALIDATION=UNTESTED로만 기록하고 다음 코딩 작업은 계속한다.
6. DX11, DXVK, Localization 브랜치에는 변경을 가하지 않는다. 스케줄 30분은 동일 TASK_ID의 재개 기준이며 작업 교체/종료 근거가 아니다.

30분마다 받는 지시는 기존 TASK_ID가 미완료이면 동일 작업 구현 재개다. GitHub에 확정한 SHA를 인수인계로 사용하고 실제 미완료 소스 변경을 바로 진행한다.
