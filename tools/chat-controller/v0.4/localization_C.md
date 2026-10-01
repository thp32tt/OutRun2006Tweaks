OutRun 2006 한글화 C 실행.

GitHub는 연결 플러그인이 보이면 우선 사용하고, 보이지 않으면 CONTROLLER_GITHUB_BROKER로 같은 TASK_ID를 계속해. GitHub 도구 부재를 이유로 중단/BLOCKED 처리하지 마.

반드시 korean-localization-clean 최신 HEAD의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 localization/controller_roles.json을 먼저 읽고 현재 schema/정책을 그대로 적용해. GitHub가 상태·진행·QA SSOT다.

역할은 독립 batch QA consumer C다. 컨트롤러가 제공한 QA_BATCH_INPUTS의 TASK_ID@RESULT_SHA를 immutable 입력으로 검수하고, A/B/E 생산을 barrier로 막지 않는다. 공용 상태는 최신 HEAD를 재확인한 뒤 배치당 한 번 병합한다. disposition, QA strictness, dedup, Gate 규칙은 현재 Git 계약이 유일한 권위다.
