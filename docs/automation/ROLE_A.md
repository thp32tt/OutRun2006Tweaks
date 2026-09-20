# Role A — Deep Review Store

This branch is the durable store for scheduled Role A review work.

Source of truth for integration state is `vr-d3d9ex-focus`:
- `docs/VR_AUTODEV_PROTOCOL.md`
- `docs/VR_WORK_QUEUE.json`
- `docs/VR_AUTODEV_STATE.json`
- `docs/VR_RUNTIME_FEEDBACK.json`

Role A does not modify production runtime behavior or the central integration queue/history.

Persist every run as:
`docs/automation/runs/A/<run-id>.json`

Required run record fields:
- exact integration/base SHA reviewed
- subsystem + review lens + relevant input/dependency hashes
- finding IDs
- evidence paths/functions
- contrary evidence checked
- severity/confidence
- verifier/test level
- queue transition proposal only
- nextAction

Avoid rereading unchanged completed input/lens combinations. When one review closes, move to a new subsystem/lens, regression history, deterministic verifier or upstream reference.
