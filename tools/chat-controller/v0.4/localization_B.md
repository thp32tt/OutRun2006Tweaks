OutRun 2006 한글화 B 생산. TARGET_BRANCH=korean-localization-clean.
GitHub 플러그인으로 최신 HEAD/controller_roles/canonical contract/TASK 기록을 확인하고 현재 checkpoint부터 실행해.
CONTROLLER_SELECTED_MATERIAL_TARGETS가 있으면 T1부터 즉시 실행. Skill은 도움될 때만 사용하며 미노출/부적합은 blocker가 아니다.
PIPELINE_BATCH: material commit 1개는 중간 checkpoint일 수 있다. controller release 전까지 같은 TASK_ID로 계속하고, 정상 목표는 실제 신규/재작업 DDS candidate 2개다.
한 asset이 render-ready가 되면 같은 TASK에서 KOREAN_RENDER→MEASURE_REFIT→EXACT_DDS_ENCODE→DECODED_FINAL_SELF_QA→PERSIST_CANDIDATE까지 끝내.
T1이 최신 Git상 유효하지 않을 때만 T2/다음 own-shard runnable 대상으로 즉시 전환. C qa_pending은 producer 종료 조건이 아니다.
상태확인/계획/RESULT_SHA=NOT_CREATED로 종료 금지. 실제 material 작업과 [AUTO:TASK_ID] commit을 계속해. runtime 미실행=UNTESTED.
