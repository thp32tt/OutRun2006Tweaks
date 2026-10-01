OutRun 2006 한글화 E 실행.

GitHub는 연결 플러그인이 보이면 우선 사용하고, 보이지 않으면 CONTROLLER_GITHUB_BROKER로 같은 TASK_ID를 계속해. GitHub 도구 부재를 이유로 중단/BLOCKED 처리하지 마.

반드시 korean-localization-clean 최신 HEAD의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 localization/controller_roles.json을 먼저 읽고 현재 schema/정책을 그대로 적용해. GitHub가 상태·진행·QA SSOT다.

역할은 elastic producer E이며 asset_queue.index % 3 == 2 shard만 담당한다. 다른 producer shard를 work-steal하지 말고, lane-local 산출물/증거/task record만 수정한다. E dispatch throttle과 공용 상태 병합 정책은 현재 Git 계약을 따른다. 세부 생산량·candidate-completion-first·source transport·QA·예외·완료 규칙은 현재 Git 계약이 유일한 권위다.
