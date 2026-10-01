OutRun 2006 한글화 B 실행.

GitHub 관련 작업은 공개 웹이 아니라 연결된 GitHub 플러그인을 실제 호출해 수행하고, 도구/schema/리소스 결과가 바로 보이지 않는다는 이유로 작업을 중단하지 마.

반드시 korean-localization-clean 최신 HEAD의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 localization/controller_roles.json을 먼저 읽고 현재 schema/정책을 그대로 적용해. GitHub가 상태·진행·QA SSOT다.

역할은 producer B이며 asset_queue.index % 3 == 1 shard만 담당한다. 다른 producer shard를 work-steal하지 말고, lane-local 산출물/증거/task record만 수정한다. 공용 상태 병합은 C가 담당한다. 세부 생산량·candidate-completion-first·source transport·QA·예외·완료 규칙은 현재 Git 계약이 유일한 권위다.
