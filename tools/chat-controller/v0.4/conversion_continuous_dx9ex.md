# DX9Ex 자동개발 — 30분 독립 실행 (2026-10-11 최신 우선)

목적: 미완료 VR 안정화/성능 최적화를 실제 소스에 지속 구현한다. TASK_ID는 GitHub 커밋 이력용으로만 유지한다. C6·과거 BLOCKED·한정된 FEATURE_CONTRACT/feature_backlog.json 소진은 신규 개발 발행을 막지 않는다.

1. GitHub 연결 도구로 thp32tt/OutRun2006Tweaks의 vr-d3d9ex-focus 최신 HEAD와 AGENTS.md, docs/DX9EX_AUTODEV_PRIORITY_20261010.md, docs/VR_PROBLEM_HISTORY.md 및 실제 소스 상태를 확인한다.
2. 이미 CI 통과한 FRAME_PACING_DIAGNOSTICS / XR_RECOMMENDED_EYE_EXTENT를 같은 SHA로 반복 점검하지 않는다. **성능·VR frame pacing 개선의 구현 가능한 병목**, Reset/ResetEx·device-loss 복구, OpenXR per-eye RT 통합, HUD 중복/헤드락/렌즈플레어 등 남아 있는 실제 결함을 우선 구현한다.
3. 이전 TASK가 아직 C6 대기라도 다른 미완료 코드 경로를 개발한다. 과거에 구현한 기능은 재작성하지 않는다. 소스/테스트 실질 변경 없는 리뷰·문서·검증 전용 커밋은 성과로 계산하지 않는다.
4. 동일 파일/기능을 다른 작업자가 수정 중이면 원격 GitHub claim과 최신 HEAD를 보고 다른 독립 문제를 선택한다. 강제 push/강제 reset/CI skip 금지. SkyGlow/정상 도로·차량 스테레오 및 기존 장치 복구 보호 기준을 유지한다.
5. C0~C6 가능한 단계까지 실제 C++/후킹/셰이더/IPC 코드를 작성하고 관련 소규모 회귀 후 material commit을 남긴다. 직접 Quest3·VDXR 테스트하지 않았다면 RUNTIME_VALIDATION=UNTESTED로만 기록하고 다음 코딩 작업은 계속한다.
6. DX11, DXVK, Localization 브랜치에는 변경을 가하지 않는다. 스케줄 30분은 재개/새 개발의 상한이며 작업 중단/승인 대기 근거가 아니다.

30분마다 받는 지시는 새 구현 작업이다. GitHub에 확정한 SHA를 인수인계로 사용하고 실제 미완료 소스 변경을 바로 진행한다.
