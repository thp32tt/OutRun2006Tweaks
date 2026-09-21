# Scheduled Work Durable Records

The four external Work schedules coordinate through GitHub, not chat memory.

- A writes per-run records on `vr-d3d9ex-review`.
- B writes per-run records on `vr-d3d9ex-candidate/<finding-id>-<run-id>`.
- C writes per-run records on `vr-d3d9ex-support`.
- D consumes those records and alone updates the integration queue/state/history on `vr-d3d9ex-focus`.

Run record path:
`docs/automation/runs/<A|B|C|D>/<run-id>.json`

Run IDs must be unique and stable. D records consumed run IDs idempotently and must not import the same run twice.

Central queue state is not edited by A/B/C. They publish a queue proposal in their own run record.
