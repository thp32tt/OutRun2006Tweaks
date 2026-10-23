# Scheduled Work Durable Records

The four external Work schedules coordinate through GitHub, not chat memory.

- A performs architecture/state/lifetime review only and writes per-run records on `vr-d3d9ex-review-a`.
- B performs rendering/stereo/visual-correctness review only and writes per-run records on `vr-d3d9ex-review-b`.
- C performs performance/OpenXR/synchronization/testability review only and writes per-run records on `vr-d3d9ex-review-c`.
- D is the sole production worker: it creates candidate branches, fixes, builds, validates, integrates, and updates the central queue/state/history on `vr-d3d9ex-focus`.

Run record path:
`docs/automation/runs/<A|B|C|D>/<run-id>.json`

Run IDs must be unique and stable. D records consumed run IDs idempotently and must not import the same run twice.

Central queue state and production candidates are not edited by A/B/C. They publish findings/evidence in their own review records; D consumes them idempotently.
