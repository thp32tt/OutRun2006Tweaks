# 1·2차 리뷰 소스 적용 정합성: DX9Ex R84
작성: 2026-10-16, branch vr-d3d9ex-focus, parent 507fa0c7a15cfad0fe3bf0c2d02e00aa0ddd48fd
근거: [1차 리뷰](https://github.com/thp32tt/OutRun2006Tweaks/issues/129), [2차 리뷰](https://github.com/thp32tt/OutRun2006Tweaks/issues/130).

**검토 한계:** 1,000+3,000건은 자동 파일×관점 정적 검사이지 실기에서 확정한 결함 4,000건이 아니다. 임의로 전체 수정하면 이미 정상화된 GPU/HUD/렌즈/SkyGlow를 회귀시킬 수 있으므로 적용·기구현·실증 필요로 구분한다.

## 이 커밋의 실제 C++ 변경
- R29 독립 DirectGPU owner의 SetActive, MarkPending, PollProducer, RetirePublication에서 invalid ring index 접근을 차단한다.
- MarkPending frameId=0 무효 등록 방지, PollProducer invalid slot은 D3DERR_INVALIDCALL로 fail-closed.
- 유효한 slot 및 nonzero frameId 처리에는 변경이 없으므로 R32 four-slot scan/host ACK/fence/quarantine, 두 눈 StretchRect 및 fallback은 원래대로 유지.
- 기존 exact-SHA R29 owner seam 검증에 guard 순서 검사와 각 guard 제거 mutation 4건을 추가.
- 효과는 exported owner 안정성 개선에 한정. 프레임 향상이나 사용자가 본 화면 문제 해결을 주장하지 않는다.

## 1·2차 리뷰 findings 적용 분류
| 검토 분류 | 적용 상태 | 안전한 후속 |
|---|---|---|
| +TIME/GOAL source→D3DX deferred batch | ALREADY_CHANGED (CONVERSION-DX9EX-00924) | 신규 redundant hook/Flush 금지. 실제 per-eye submit HMD 증거로 검증 |
| GPU water profiler Reset epoch | ALREADY_CHANGED (CONVERSION-DX9EX-00924) | 장면별 GPU/CPU/p99 실측 필요 |
| DirectGPU free-slot/ACK-first 및 pre-Present 2ms 제거 | ALREADY_IMPLEMENTED | 이번 변경은 하위 R29 ring 범위 안전만 추가 |
| CPU shadow lookup + registry lock | ALREADY_OPTIMIZED (4-slot TLS cache) | 실제 mutex miss / copy 비율 측정 전 락 제거 금지 |
| Eye GPU StretchRect, water/glass/particle | NEED_PRODUCER_PROOF / NEED_PERF_MEASUREMENT | 양안/투명 품질 유지, blind draw suppression 금지 |
| HUD/F11/main menu/lens/GOAL/rank/vehicle shadow | NEED_EXACT_QUEST3_VDXR | source/batch/eye 출처 확인 뒤 기존 FEATURE_ID 소유자 아래 수정 |
| game Present + XR cadence | NEED_TIMESTAMP_CORRELATION | 60/72/90Hz token mismatch 원인 확정 전 limiter 변경 금지 |

## 검증 계약
정적 verifier pass ≠ C++ Win32 CI PASS ≠ Quest3 시각 PASS. 현재 HMD 실행하지 않았다면 RUNTIME_VALIDATION=UNTESTED; Windows x86 R84 game, x64 host, R26_SAFE rollback, package, Domain Isolation 및 영향 전체 소스검증 정확 SHA의 CI를 별도 확인한다. 성과 점수는 기존 TASK 재보고·문서 추가에 중복 반영하지 않는다.
