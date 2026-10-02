OutRun 2006 DX11 전환. TARGET_BRANCH=vr-dx11-native-r71.
GitHub 플러그인으로 HEAD, AGENTS.md, docs/CONVERSION_LANE_STATE.json, TASK_ID 기록을 읽고 현재 checkpoint부터 즉시 실행해.
Skill은 도움이 될 때만 사용. 로컬 PC/RenderDoc/OpenXR runtime 부재는 source/static/disassembly/GitHub Actions blocker가 아니다.
한 cycle은 C0_RECOVER→C1_REVIEW→C2_IMPLEMENT→C3_VALIDATE→C4_COMMIT→C5_PACKAGE(필요 없으면 이유+NOT_REQUIRED)→C6_STATE 전체를 완료해야 한다.
C1 review/state 기록 하나로 끝내지 말고 C2에서 실제 DX11 source/tool/test/workflow evidence를 변경하고 C3 검증까지 수행해.
C0-C6 [AUTO:TASK_ID]+Gate PASS도 lane state가 static/development complete가 아니면 checkpoint다. 같은 TASK_ID로 다음 static work의 C0-C6를 반복해. 계획/검토 하나로 종료 금지.
docs/automation/runs/<TASK_ID>.json에 pipeline_schema_version=2, pipeline C0-C6, changed_paths/work_product, validation, state_persisted=true, next_action, runtime_validation을 현재 cycle 기준으로 갱신해.
다른 backend 수정 금지. 실기 미실행=UNTESTED.
