# Role D run records

Role D is the only role that may update the integration production source and consolidated queue/state/history.

Persist each consumed/integration run as `docs/automation/runs/D/<run-id>.json`.
Do not duplicate-import an A/B/C run ID already recorded as consumed.
