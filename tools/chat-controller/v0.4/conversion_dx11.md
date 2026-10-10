OutRun 2006 DX11 전환 자동 작업을 진행해줘.

[2026-10-10 20:39 KST 사용자 최신 개발방향 — DX11_FIRST_PLAYABLE_GAME_FRAME / 00537 이후 신규 작업부터]
목표는 더 많은 Rxxx 테스트·독립 WARP 프로브를 만드는 것이 아니라, 실제 OutRun 2006 게임이 네이티브 DX11로 그린 화면을 보이고 이후 조작 가능한 상태로 만드는 것이다. 기능 단위로 개발하고 완성 시 한 번 통합 검증한다. 00536 이전 미완료 TASK는 기존 소유권을 존중하고 무리하게 새 작업으로 갈아타지 마.

0순위 R175 TEXCOORD6 VS/PS varying 색상 불일치를 실제 실패한 CI 단계와 소스/셰이더 연결에서 해결한다. 기존 작업자 CONVERSION-DX11-00477의 claim·lease·work_key를 원격으로 먼저 조회하고, 명시적 해제 또는 fencing된 소유권 이관 증거 없이는 그 파일을 중복 수정하지 마. 소유권 이관이 불가능하면 막힌 R175를 근거와 함께 유지하되, 충돌하지 않는 live game Draw 연결 작업으로 진행하고 임의로 R175 검사/게이트를 우회하지 마.

다음 최우선 기능은 'FIRST_GAME_DRAW_FRAME'이다. 게임에서 실제 발생한 D3D9 Draw/DrawIndexed 한 건을 캡처하고, 라이브 resource/vertex/index/shader/target 소유권을 D3D11 명령에 연결하여, fail-closed 진단 opt-in에서 눈으로 확인 가능한 게임 프레임 경로까지 완성한다. 미지원 draw는 DX9Ex로 폴백한다. 단순 테스트 도형의 WARP GPU 픽셀 PASS는 이 기능의 완료가 아니다. NativeDrawPathActive의 일반 사용자 기본값은 계속 false이며 실기/시각 동등성 증거 없이는 배포 모드 활성화·성공 선언하지 마.

FIRST_GAME_DRAW_FRAME 이후 메뉴/차량선택/실제 주행 화면 → 입력 → Quest3 양안·HUD·OpenXR 순서로 확장한다. R240, R241 등 새로운 독립 WARP 프로브, guard, counter, readiness만 만들고 별도 TASK를 완료하는 방식은 중단한다. 직접적인 live-game-frame 결함을 제거하고 실제 hook/renderer/submit 경로를 연결하는 최소 하위 테스트만 기능 내부에서 허용한다.

새 TASK_ID>=CONVERSION-DX11-00537부터 docs/automation/DX11_AUTODEV_EXECUTION_POLICY.json의 gameplay_delivery_target을 필수로 지정한다. R175 작업은 R175_CI_UNBLOCK+소유권 이관 증거, 게임 드로우 통합은 FIRST_GAME_DRAW_FRAME+실제 D3D9_CALLSITE→D3D11_NATIVE_DRAW→VISIBLE_FRAME_OUTPUT 단계·안전한 DX9Ex fallback·실기 검증 계획을 기록한다. 기능을 끝내기 전 신규 TASK나 전체 빌드 반복을 만들지 마. 실제 화면을 테스트 못 했다면 FRAME_PATH_CODE_COMPLETE와 RUNTIME_VALIDATION=UNTESTED를 구분해 기록한다.


[2026-10-10 최신 사용자 확정 — FEATURE_BASED_DEVELOPMENT]
20분/2~5개 사소한 수정 묶음 정책은 폐기한다. 작업 단위는 작은 패치가 아니라 하나의 완결된 기능이다. 기본 1~3시간 규모를 상정하되 시간·커밋 수로 완료 여부를 판단하거나 쪼개지 마. 기능 정의는 미완료인 최우선 실제 문제·구현 경로·완료 조건·변경 대상·부정 회귀로 명확히 한정한다. 조사만 하고 끝내거나 이미 해결된 패치를 재검토하는 신규 TASK_ID를 만들지 마.
컨트롤러가 준 FEATURE_ID와 FEATURE_BRANCH(보통 vr-feature/<lane>/<task-id>)를 확인해. 기능 미완료 중에는 컨트롤러 체크포인트 브랜치에 소스 패치를 저장하고 FEATURE_BRANCH 및 TARGET_BRANCH에는 중간 push하지 마. 기능 개발 중 변경은 5분마다 소스 패치로 보존하고 최종 기능 완성 시 FEATURE_BRANCH에 결합해. 5분 간격으로 실제 변경 패치와 남은 TODO를 GitHub 컨트롤러 체크포인트에 보존하고, 30분 채팅 롤오버에서는 같은 FEATURE_ID/TASK_ID와 브랜치를 계속 사용해. 점수·완료를 중간 커밋마다 증가시키지 마.
전체 컴파일/Win32-WARP/패키징/GitHub Actions를 중간 수정마다 하지 말고 문법·변경부 관련 경량 정적·필요한 targeted 테스트만 수행해. 단, 위험한 ABI/훅/메모리 문제가 발생하면 관련 빌드를 조기에 시행할 수 있다. 기능 통합 소스가 완성되고 targeted 테스트가 준비되면 FEATURE_BRANCH의 docs/automation/runs/<TASK_ID>.json에 task_id/target_branch/feature_id/feature_branch/work_key/feature_status=FEATURE_READY/feature_acceptance={implementation_complete:true,targeted_checks:[검증 명세],integration_contract:연결된 실질 기능·안전 회귀 계약}/runtime_validation=UNTESTED를 남겨. 그 최종 기능 커밋의 메시지에 [AUTO:TASK_ID]를 단 한 번 넣되 CI skip을 넣지 마. 컨트롤러가 최종 기능 브랜치와 target 최신 HEAD의 fast-forward·실제 소스 diff·명시적 기능 완료 증거를 검사하여 TARGET_BRANCH로 게시하고 해당 SHA에서 전체 CI를 한 번 실행한다.
TARGET_BRANCH의 Actions가 완료되기 전에는 FEATURE_READY가 PASS가 아니다. 실제 CI 실패 시 실패한 원인만 같은 FEATURE_BRANCH에서 수리하고 변경된 최종 SHA를 다시 제출해. 실패한 동일 SHA를 검증·재시도 반복하지 마. CI PASS 뒤 C6 결과만 별도 bookkeeping 커밋으로 기입하고 필수 검증을 재실행하지 마. HMD 실기 미수행은 언제나 RUNTIME_VALIDATION=UNTESTED.
DX11 A와 DX9Ex C는 서로 독립, DXVK B는 FROZEN. 기능별 원격 work_key/owner/경로 충돌을 먼저 확인하고 타 작업자 변경에 force-push·강제 reset·덮어쓰기 하지 마.

TARGET_BRANCH는 vr-dx11-native-r71이다. 기존 검증된 VR 기준은 참조만 하고 vr-d3d9ex-focus를 직접 수정하지 마. 시작 즉시 branch HEAD, 소유권/기존 작업, docs/reviews/VR_BACKEND_100_REVIEW_INDEX.md, AGENTS.md, 최신 정책을 확인한 뒤 R175 해제 또는 FIRST_GAME_DRAW_FRAME 완성 경로를 선택해. 이미 검증된 독립 프로브를 신규 작업으로 반복하지 마.

[네이티브 구현 우선 / HMD 대기 비차단] 실기 테스트가 필요한 항목은 런타임 결론만 NEED_HMD_TEST로 남겨. 다음 작은 독립 구현으로 도피하지 말고 동일 FIRST_GAME_DRAW_FRAME 기능에서 실제 코드/연결 작업을 계속해. 현재 소스 기준 live D3D9/D3D11 device-object ownership → 리소스/VB/IB·셰이더 바인딩 → Draw/DrawIndexed 연결 → OpenXR 제출·프레임 페이싱 순으로 실질적인 구현 장애물을 제거해. 활성화 안전 게이트는 임의로 우회하지 마. 준비 상태 scalar/hash/receipt 재확인만 무한 반복하지 말고 실제 렌더 경로의 원인 코드 수정에 우선 배정해. 동일 HUD 소스 1000/5000회 반복 정적검사는 하지 말고 변경 관련 검사 1회와 GitHub CI만 수행해. 작업은 작은 패치가 아니라 완결 가능한 큰 네이티브 기능 단위로 유지하며, 세부 소스/테스트는 FEATURE_BRANCH에 누적하고 기능 완료 후 TARGET_BRANCH에서 통합 검증해. 실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.

[장시간 채팅 진행·중복 방지]
일반 ChatGPT 채팅에서 개발을 지속한다. 작업 시작과 실제 단계 전환/도구 결과가 나올 때 TASK_ID, C0~C6 단계, 마지막 확인된 GitHub SHA/CI, 다음 행동을 간단히 중간 보고하고, 그 보고만으로 작업을 끝내지 마. 인터페이스에서 가능하면 20~30초 이상 무표시를 피하되 시간 간격을 보장하거나 백그라운드 실행을 주장하지 마. 롤오버·retry·새 채팅은 기존 TASK_ID의 미완료 단계만 이어받는다. 실제 현재 GitHub 결과가 확인되면 이미 수행한 소스 수정/검증을 재실행하지 말고 근거를 재사용한다. 작업 소유권 또는 기존 채팅의 진행 여부가 불명확하면 새 TASK_ID를 독자 생성하거나 같은 변경을 병렬로 수행하지 않는다.

[2026-10-08 사용자 최신 우선순위] 자동개발은 기존처럼 A(DX11 네이티브 구현)와 C(DX9Ex VR 안정화)를 동시에 두 작업 실행한다. B(DXVK)는 동결한다. A는 다른 lane의 코드나 HMD 결과를 기다리지 않고 실제 네이티브 DX11 Draw/DrawIndexed와 D3D11 디바이스·버퍼·리소스·셰이더·OpenXR 연동 구현에 집중한다. HMD 실기를 못 해도 C0→C6, live device-object lifetime / native resource / shader / 실제 Draw 호출 / OpenXR 제출 경로의 독립 작업을 계속 개발한다. 단계가 막히면 결함 근거와 NEED_HMD_TEST를 남기되 DXVK나 동일 코드 1000·5000회 검사로 돌아가지 마. 실제 구현이 없는 bookkeeping-only 커밋은 진도에 포함하지 않는다. 기존 동시 소유권 충돌을 피하고 같은 FEATURE_ID에서 기능 구현을 모두 완료한 뒤 대상 브랜치의 exact-SHA GitHub Actions 결과를 확인한다.


[VR 체크포인트 정책]
5분마다 컨트롤러 브랜치 체크포인트를 저장하고, 실제 중간 소스/테스트는 FEATURE_BRANCH에 보존한다. 대상 게임 브랜치는 기능 완료 시 컨트롤러만 갱신한다. 장시간 작업을 30분마다 같은 TASK_ID로 새 대화에서 이어간다. 먼저 chat-controller-downloads 브랜치 tools/chat-controller/checkpoints/vr/<TASK_ID>/ 최신 파일, 대상 브랜치 HEAD, run 기록을 확인하고 완료한 수정은 반복하지 마. 작업 결과로 확인된 material commit에만 [AUTO:TASK_ID] 최종 결과 표식을 붙여. 기록만 남긴 경우 구현 완료로 주장하지 마.