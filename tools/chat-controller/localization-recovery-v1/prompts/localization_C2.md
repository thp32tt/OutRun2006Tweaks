OutRun 한글화 C2 독립 최종 QA 실행

저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 이 브랜치의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md를 읽는 것이다.
C2는 반드시 짝수 숫자 asset_queue.csv index만 담당한다. 홀수 index와 index 없는 특별 C 작업은 C1이 담당하므로 수정하거나 중복 검수하지 마.
현재 브랜치의 queue/증거를 재조회하고 C2 대상 미완료/REWORK/HOLD 자산을 1회 최대 3개까지 완전한 실제 검증·증거 기록으로 처리해. C3 추가 검증/사용자 실기 미검증 규칙은 계약대로 유지해.
실제 검수 증거와 변경사항은 같은 GitHub 브랜치에 commit/push하고 원격 HEAD를 재확인해. 작업 전후에 동일한 후보 SHA를 중복 완료 처리하지 마.
VR/FFB/DX11/DXVK 및 별도 컨트롤러 TASK_ID/큐 엔진을 사용하지 마. 요청받은 샤드의 실질 QA를 우선해.
