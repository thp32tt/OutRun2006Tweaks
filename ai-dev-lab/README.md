# AgentBoard

A deliberately small full-stack project for testing AI coding agents.

AgentBoard is a local task board with a FastAPI backend, SQLite persistence, a tiny browser UI, automated tests, and CI. The initial version is intentionally simple so an AI agent can safely extend it through small, verifiable tasks.

## Why this project is useful for AI development tests

It exercises several common software-engineering skills at once:

- understand an unfamiliar codebase
- modify API behavior
- change a database schema
- preserve backward compatibility
- update a frontend
- write tests before/after changes
- satisfy CI
- document decisions

## Current features

- Create tasks
- List tasks
- Filter by status
- Update task title, description, priority, and status
- Delete tasks
- SQLite storage
- Simple single-page browser UI
- API tests with pytest

## Stack

- Python 3.12+
- FastAPI
- SQLite (`sqlite3`, no ORM)
- Vanilla HTML/CSS/JavaScript
- pytest

## Run locally

```bash
cd ai-dev-lab
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run tests

```bash
pytest
```

## AI-agent test workflow

1. Give the coding agent one item from `BACKLOG.md`.
2. Tell it to inspect `AGENTS.md` first.
3. Ask it to implement the change, add tests, and explain its choices.
4. Review the diff and CI result instead of giving it implementation hints.
5. Repeat with a harder backlog item.

A good first task is **B1: add due dates and an overdue filter**.
