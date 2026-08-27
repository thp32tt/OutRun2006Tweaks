# AgentBoard backlog

Use these as progressively harder autonomous-development tests. Give the agent only one task at a time.

## B1 — Due dates and overdue filtering

Add an optional `due_date` (`YYYY-MM-DD`) to tasks.

Acceptance criteria:
- existing databases migrate without data loss,
- create/update APIs accept and validate the date,
- task responses expose `due_date`,
- `GET /api/tasks?overdue=true` returns unfinished tasks whose due date is before today,
- browser UI shows due dates,
- automated tests cover migration, validation, and filtering.

## B2 — Search and sorting

Add case-insensitive search across title and description plus explicit sorting.

Acceptance criteria:
- `q` query parameter performs partial matching,
- `sort` accepts `newest`, `oldest`, and `priority`,
- filters can be combined with status,
- invalid sort values return HTTP 422,
- tests cover combined filters.

## B3 — Optimistic concurrency

Prevent users from accidentally overwriting a task changed by another client.

Acceptance criteria:
- task responses include a monotonically increasing `version`,
- updates require the caller's expected version,
- stale updates return HTTP 409,
- UI reloads and explains the conflict,
- tests simulate two clients editing the same task.

## B4 — Audit trail

Record task lifecycle events.

Acceptance criteria:
- keep create/update/delete events,
- each event contains timestamp, task id, action, and changed fields,
- `GET /api/tasks/{id}/history` returns the event history,
- deleting a task does not delete its audit history,
- tests verify exact event ordering.

## B5 — Import/export

Implement JSON backup and restore.

Acceptance criteria:
- export all current tasks to a versioned JSON format,
- import validates the complete document before changing the database,
- duplicate IDs are handled deterministically,
- failed imports are atomic,
- tests cover round-trip and malformed input.

## B6 — Agent-selected improvement

Ask the coding agent to inspect the codebase and propose one improvement itself. It must explain the problem, define acceptance criteria, implement it, and prove correctness with tests. This is useful for testing planning quality rather than instruction following alone.
