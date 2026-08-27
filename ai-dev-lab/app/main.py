from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import connect, init_db

TaskStatus = Literal["todo", "doing", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    priority: int = Field(default=2, ge=1, le=3)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    priority: int | None = Field(default=None, ge=1, le=3)
    status: TaskStatus | None = None


class Task(BaseModel):
    id: int
    title: str
    description: str
    priority: int
    status: TaskStatus
    created_at: str
    updated_at: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="AgentBoard", version="0.1.0", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tasks", response_model=list[Task])
def list_tasks(status: TaskStatus | None = Query(default=None)) -> list[dict]:
    sql = "SELECT * FROM tasks"
    params: tuple[str, ...] = ()
    if status:
        sql += " WHERE status = ?"
        params = (status,)
    sql += " ORDER BY status, priority ASC, id DESC"

    with connect() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate) -> dict:
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, description, priority) VALUES (?, ?, ?)",
            (payload.title.strip(), payload.description, payload.priority),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate) -> dict:
    values = payload.model_dump(exclude_unset=True)
    if "title" in values and values["title"] is not None:
        values["title"] = values["title"].strip()

    if not values:
        return _get_task(task_id)

    assignments = ", ".join(f"{field} = ?" for field in values)
    params = [*values.values(), task_id]

    with connect() as connection:
        existing = connection.execute(
            "SELECT id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        connection.execute(
            f"UPDATE tasks SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return dict(row)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> Response:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=204)


def _get_task(task_id: int) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)
