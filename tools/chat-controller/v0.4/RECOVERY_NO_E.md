# Localization recovery baseline

This recovery branch is based on commit `42e3410d9582b85d74a51435188905c5bbd27feb`, the direct parent of commit `e34492f6024c3ef20c65dcfa2a14bcdee73776db` ("chat-controller: add elastic localization producer E").

## Contract

- Producers: A and B only.
- A owns `asset_queue_v2.index % 2 == 0`.
- B owns `asset_queue_v2.index % 2 == 1`.
- C is the mandatory QA barrier for the current A/B wave.
- A/B completion requires a real DDS change under `localization/graphics/hd_candidates/` and the exact `[AUTO:TASK_ID]` marker.
- C completion requires a durable shared-state/QA reconciliation commit with the exact marker.
- No E lane is scheduled or accepted.
- Localization and VR use separate Portainer stacks, volumes, ports and network.
- `localization/graphics/asset_queue.csv` is migration/history only; the operational queue is `asset_queue_v2.csv`.
