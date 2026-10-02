OutRun 2006 한글화 C 연속 QA. TARGET_BRANCH=korean-localization-clean.
GitHub 플러그인으로 최신 HEAD/controller_roles/canonical contract/TASK 기록을 확인하고 QA_BATCH_INPUTS의 모든 TASK_ID@RESULT_SHA를 검증해.
Skill은 도움될 때만 사용하며 미노출은 blocker가 아니다. 일부 입력만 검토하고 종료 금지.
current-v2 static PASS/REWORK를 reconcile하고 [AUTO:TASK_ID] Gate 대상 commit을 남겨. CI-skip 금지.
batch PASS는 backlog가 남아 있으면 중간 checkpoint다. controller가 주는 다음 QA batch를 같은 TASK_ID에서 계속 drain해. runtime 미실행=UNTESTED.
