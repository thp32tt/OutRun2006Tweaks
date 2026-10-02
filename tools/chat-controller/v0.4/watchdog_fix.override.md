중단된 N100-D Candidate Worker 작업을 즉시 이어서 진행해.

먼저 Issue #6의 기존 CLAIM/HANDOFF, 최신 vr-d3d9ex-focus HEAD, candidate branch/SHA, 예약 D의 통합 상태를 확인해 동일 stable_key의 중복 수정이나 stale base 작업을 하지 않는다.

유효한 N100-D claim이 있으면 exact branch에서 source fix/verifier/build/CI/handoff를 이어서 완료한다. claim이 stale/통합완료/다른 worker 소유면 그 작업을 건드리지 말고 다음 미소유 READY finding을 claim한다.

vr-d3d9ex-focus 직접 수정/merge/integration은 금지한다. 실제 source candidate 생성과 검증 증거를 우선하고, 종료 시 Issue #6에 현재 상태와 exact nextAction을 append-only로 남긴다.
