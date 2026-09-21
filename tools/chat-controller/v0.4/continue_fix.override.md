OutRun2006Tweaks N100-D Candidate Worker 작업을 계속해.

먼저 GitHub 최신 vr-d3d9ex-focus HEAD, 예약 D 상태, A/B/C post-review/ledger, Issue #6 CLAIM/HANDOFF 댓글, active candidate/CI를 다시 읽어 충돌과 중복을 제거한다.

N100-D는 실제 source fix + verifier + isolated candidate + build/CI까지 수행할 수 있지만 vr-d3d9ex-focus merge/integration은 절대 하지 않는다.

이전 claim이 아직 유효하고 candidate가 미완료면 그 exact base/branch에서 안전하게 이어서 완료한다. 이미 예약 D가 통합했거나 다른 worker가 같은 stable_key를 더 최신 base에서 처리했다면 stale claim을 종료하고 다음 READY 항목으로 이동한다.

실제 source fix가 가능한 READY 항목이 있으면 문서 정리나 verifier-only 작업으로 턴을 끝내지 말고 최소 하나의 실제 source candidate를 시도한다. 전체 source fetch -> isolated branch update -> exact diff verification -> verifier/build/CI -> Issue #6 HANDOFF 순서를 지킨다.

한 항목이 막혀도 WIP cap 내에서 다음 독립 READY 항목을 검토한다. 마지막에는 candidate SHA/CI/post-review/통합 대기 상태와 exact nextAction을 남긴다.
