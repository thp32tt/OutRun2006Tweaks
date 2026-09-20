# Role C — Validation / Support Store

This branch is the durable store for scheduled Role C validation/support work.

Source of truth for integration state is `vr-d3d9ex-focus`:
- `docs/VR_AUTODEV_PROTOCOL.md`
- `docs/VR_WORK_QUEUE.json`
- `docs/VR_AUTODEV_STATE.json`
- `docs/VR_RUNTIME_FEEDBACK.json`

Role C does not modify production runtime source and does not merge to integration.

Persist every run as:
`docs/automation/runs/C/<run-id>.json`

Validate immutable candidate SHA plus exact config/toolchain/profile identity. Reuse unchanged successful checks. Actual result states should distinguish:
- STATICALLY VERIFIED
- BUILD VERIFIED
- NEED_HMD_TEST
- FAIL_BUILD
- FAIL_REGRESSION
- CAPABILITY_BLOCKED

If no candidate is ready or CI is running, improve deterministic non-production verifiers/support tooling, inspect cancellation/cache/package identity, or identify missing regression coverage.
