OutRun 2006 한글화 A 실행.

GitHub는 CONTROLLER_GITHUB_BROKER가 기본 경로다. Broker는 ChatGPT에 노출되는 tool/schema/interface가 아니라 컨트롤러가 처리하는 채팅 텍스트 프로토콜이다. 제공된 BROKER_READ_RESULT로 즉시 작업하고, 추가 파일은 BROKER_READ, 수정은 BROKER_CHANGESET 태그로 요청해. 연결 플러그인은 선택사항이며 tool/interface 부재를 이유로 중단/BLOCKED 처리하지 마.

반드시 korean-localization-clean 최신 HEAD의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 localization/controller_roles.json을 먼저 읽고 현재 schema/정책을 그대로 적용해. GitHub가 상태·진행·QA SSOT다.

역할은 producer A이며 asset_queue.index % 3 == 0 shard만 담당한다. 다른 producer shard를 work-steal하지 말고, lane-local 산출물/증거/task record만 수정한다. 공용 상태 병합은 C가 담당한다. 세부 생산량·candidate-completion-first·source transport·QA·예외·완료 규칙은 현재 Git 계약이 유일한 권위다.
