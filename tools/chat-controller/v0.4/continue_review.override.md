OutRun2006Tweaks N100 지속 심층 리뷰를 계속해.

먼저 GitHub 최신 vr-d3d9ex-focus HEAD, A/B/C 전용 review ledger/checkpoint, consolidated findings, D의 실행 상태를 확인하고, Issue #6에서는 최신 N100_CHECKPOINT와 그 이후 신규 댓글만 우선 복구해. checkpoint가 완전하면 그 이전 Issue #6 이력을 매번 다시 요약하지 마.

현재 canonical 역할은 A(:00)=architecture/state/lifetime/OpenXR lifecycle/synchronization, N100(:10)=보조 리뷰, B(:20)=rendering/stereo/visual/performance/frame-pacing, C(:35)=post-fix/change-sanity/dedup/validation-prep/D_IMPLEMENT_NEXT, D(:45)=유일 production IMPLEMENT+BUILD+VALIDATE+INTEGRATE이다. 과거 문서의 예전 :15/:30 또는 B=FIX/C=Validation 역할은 무시한다.

이미 같은 target/dependency identity + file/function/path + lens + hypothesis가 충분히 검토됐고 새 증거가 없으면 건너뛴다. HEAD 변경은 영향받은 dependency만 stale 처리한다. 기존 finding의 추가 근거는 보강하고, 수정 후 재발 근거는 REOPEN_CANDIDATE로 연결한다.

A/B/C가 덜 다룬 미검토 영역, cross-subsystem 경계, historical regression, adversarial falsification을 계속 탐색한다. 새롭고 근거 있는 finding/evidence만 Issue #6에 append-only 댓글로 기록한다.

한 영역이 끝나도 유용한 미검토 범위가 남아 있으면 즉시 다음 영역으로 진행한다. 실행 마지막에는 Issue #6에 N100_CHECKPOINT(target_sha, processed_through, A/B/C ledger identity, stable_keys_seen 요약, new_or_augmented keys, exact nextReview)를 append-only로 남겨 다음 실행이 delta 복구할 수 있게 한다.