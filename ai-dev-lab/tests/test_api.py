from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOARD_DB", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_task_lifecycle(client: TestClient):
    created = client.post(
        "/api/tasks",
        json={"title": "Write tests", "description": "Cover the API", "priority": 1},
    )
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Write tests"
    assert task["status"] == "todo"

    task_id = task["id"]
    updated = client.patch(
        f"/api/tasks/{task_id}",
        json={"status": "doing", "priority": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "doing"
    assert updated.json()["priority"] == 2

    listed = client.get("/api/tasks", params={"status": "doing"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [task_id]

    deleted = client.delete(f"/api/tasks/{task_id}")
    assert deleted.status_code == 204
    assert client.get("/api/tasks").json() == []


def test_missing_task_returns_404(client: TestClient):
    assert client.patch("/api/tasks/999", json={"status": "done"}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404


def test_validation_rejects_invalid_priority_and_status(client: TestClient):
    invalid_priority = client.post("/api/tasks", json={"title": "Bad", "priority": 9})
    assert invalid_priority.status_code == 422

    created = client.post("/api/tasks", json={"title": "Valid"}).json()
    invalid_status = client.patch(
        f"/api/tasks/{created['id']}", json={"status": "blocked"}
    )
    assert invalid_status.status_code == 422
