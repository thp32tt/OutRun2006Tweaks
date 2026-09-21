OutRun2006Tweaks N100 지속 심층 리뷰를 계속해.

먼저 GitHub 최신 vr-d3d9ex-focus HEAD, A/B/C 전용 review ledger/checkpoint, consolidated findings, D의 실행 상태, Issue #6 N100 Review Inbox를 다시 읽어 변경사항을 반영해.

N100은 리뷰 전용이다. production source/candidate/build/CI/merge/integration은 하지 않는다. 실제 실행은 예약작업 D가 담당한다.

이미 같은 target/dependency identity + file/function/path + lens + hypothesis가 충분히 검토됐고 새 증거가 없으면 건너뛴다. HEAD 변경은 영향받은 dependency만 stale 처리한다. 기존 finding의 추가 근거는 보강하고, 수정 후 재발 근거는 REOPEN_CANDIDATE로 연결한다.

A/B/C가 덜 다룬 미검토 영역, cross-subsystem 경계, historical regression, adversarial falsification을 계속 탐색한다. 새롭고 근거 있는 finding/evidence만 Issue #6에 append-only 댓글로 기록한다.

한 영역이 끝나도 유용한 미검토 범위가 남아 있으면 즉시 다음 영역으로 진행하고 마지막에 exact nextReview를 남겨.