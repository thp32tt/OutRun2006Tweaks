OutRun 2006 DX11 전환 자동 작업을 진행해줘.

[2026-10-10 최신 사용자 지시 — BATCH_COMPILE_POLICY=GROUPED / 작은 수정 묶음 검증]
같은 TASK_ID·work_key·소스 소유권 안에서 관련된 작은 수정 2~5건(또는 하나의 완결된 기능)을 한 배치로 모아 개발한다. 숫자를 채우려고 불필요한 변경을 만들지 말고, 약 20분 이내의 검토 가능한 범위로 한정한다. 변경마다 전체 컴파일/Win32-WARP/호스트·게임 패키징/GitHub Actions를 실행하지 마. 중간에는 문법 검사·관련 소스 정적 검사·작은 단위 테스트 등 가벼운 확인만 하고, 모든 소스/테스트 수정을 묶은 최종 material commit에 [AUTO:TASK_ID]를 붙여 대상 게임 브랜치에 한 번 반영해 exact-SHA 필수 Gate 및 필요한 전체 컴파일을 배치당 한 번 수행해. 실패가 확인되면 그 원인만 수정한 새 SHA로 필수 Gate를 다시 실행한다. ABI/훅/메모리 안전 관련 중대한 위험이 있으면 전체 빌드를 조기 수행할 수 있다.
5분 GitHub 진행 체크포인트는 컨트롤러 체크포인트 브랜치에 그대로 저장하되, 게임 브랜치에 미완성 소스를 수정 한 건마다 push해 무거운 CI를 재실행하지 마. 30분 롤오버 전에 아직 커밋하지 않은 실제 코드가 유실될 우려가 있으면 해당 TASK_ID만 소유하는 임시 작업 브랜치에 미완성 패치/소스를 보존하고, 재개 시 원격 HEAD/소유권을 확인해 최종 배치에 통합해. 임시 브랜치는 C6 완료·PASS 증명이 아니며 [AUTO:TASK_ID] 최종 표식을 붙이지 않는다. 검증된 최종 material SHA를 bookkeeping SHA로 덮어쓰지 마. 작업/CI가 이미 같은 SHA로 끝났다면 재실행하지 마.
최종 판정은 변경된 전체 배치 소스의 정확한 SHA에서 필수 GitHub CI가 PASS해야만 가능하다. RUNTIME_VALIDATION=UNTESTED 및 독립 lane 경계, C0→C6, 기존 회귀 안전 게이트를 유지한다.

TARGET_BRANCH는 vr-dx11-native-r71이다. 기존 검증된 VR 기준은 참조만 하고 vr-d3d9ex-focus를 직접 수정하지 마. 시작 즉시 현재 branch HEAD, docs/reviews/VR_BACKEND_100_REVIEW_INDEX.md, AGENTS.md, VR 자동화/상태 문서를 읽고 가장 우선순위가 높은 실행 가능한 DX11 전환 작업 하나만 선택해 끝까지 처리해.

[네이티브 구현 우선 / HMD 대기 비차단] 실기 테스트가 필요한 항목은 해당 런타임 검증·배포 승격만 NEED_HMD_TEST로 남기고 다음 독립 DX11 네이티브 C++ 구현으로 즉시 전환해. 현재 소스 기준 live D3D9/D3D11 device-object ownership → 리소스/VB/IB·셰이더 바인딩 → Draw/DrawIndexed 연결 → OpenXR 제출·프레임 페이싱 순으로 실질적인 구현 장애물을 제거해. 활성화 안전 게이트는 임의로 우회하지 마. 준비 상태 scalar/hash/receipt 재확인만 무한 반복하지 말고 실제 렌더 경로의 원인 코드 수정에 우선 배정해. 동일 HUD 소스 1000/5000회 반복 정적검사는 하지 말고 변경 관련 검사 1회와 GitHub CI만 수행해. 한 작업은 작게 유지하고, 소스 수정·정적 검증·자동 테스트·작업 기록을 같은 branch에 반영해. 실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.

[장시간 채팅 진행·중복 방지]
일반 ChatGPT 채팅에서 개발을 지속한다. 작업 시작과 실제 단계 전환/도구 결과가 나올 때 TASK_ID, C0~C6 단계, 마지막 확인된 GitHub SHA/CI, 다음 행동을 간단히 중간 보고하고, 그 보고만으로 작업을 끝내지 마. 인터페이스에서 가능하면 20~30초 이상 무표시를 피하되 시간 간격을 보장하거나 백그라운드 실행을 주장하지 마. 롤오버·retry·새 채팅은 기존 TASK_ID의 미완료 단계만 이어받는다. 실제 현재 GitHub 결과가 확인되면 이미 수행한 소스 수정/검증을 재실행하지 말고 근거를 재사용한다. 작업 소유권 또는 기존 채팅의 진행 여부가 불명확하면 새 TASK_ID를 독자 생성하거나 같은 변경을 병렬로 수행하지 않는다.

[2026-10-08 사용자 최신 우선순위] 자동개발은 기존처럼 A(DX11 네이티브 구현)와 C(DX9Ex VR 안정화)를 동시에 두 작업 실행한다. B(DXVK)는 동결한다. A는 다른 lane의 코드나 HMD 결과를 기다리지 않고 실제 네이티브 DX11 Draw/DrawIndexed와 D3D11 디바이스·버퍼·리소스·셰이더·OpenXR 연동 구현에 집중한다. HMD 실기를 못 해도 C0→C6, live device-object lifetime / native resource / shader / 실제 Draw 호출 / OpenXR 제출 경로의 독립 작업을 계속 개발한다. 단계가 막히면 결함 근거와 NEED_HMD_TEST를 남기되 DXVK나 동일 코드 1000·5000회 검사로 돌아가지 마. 실제 구현이 없는 bookkeeping-only 커밋은 진도에 포함하지 않는다. 기존 동시 소유권 충돌을 피하고 exact-SHA GitHub Actions 결과를 확인한 후 다음 구현 항목으로 넘어간다.


[VR 체크포인트 정책]
5분마다 컨트롤러 브랜치의 진행 체크포인트를 저장해. 미완성 소스는 필요시 해당 TASK_ID 전용 임시 브랜치에 보존하되, 대상 게임 브랜치에는 검증할 배치가 완성된 때 최종 material commit을 반영한다. 장시간 작업을 30분마다 같은 TASK_ID로 새 대화에서 이어간다. 먼저 chat-controller-downloads 브랜치 tools/chat-controller/checkpoints/vr/<TASK_ID>/ 최신 파일, 대상 브랜치 HEAD, run 기록을 확인하고 완료한 수정은 반복하지 마. 작업 결과로 확인된 material commit에만 [AUTO:TASK_ID] 최종 결과 표식을 붙여. 기록만 남긴 경우 구현 완료로 주장하지 마.
