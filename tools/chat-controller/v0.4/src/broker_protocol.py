from __future__ import annotations

import json
import re
from typing import Any

MAX_READ_REQUESTS = 8
MAX_CHANGESET_EDITS = 24
MAX_PATH_LENGTH = 320


class BrokerProtocolError(ValueError):
    pass


def safe_repo_path(path: str) -> str:
    value = str(path or "").strip().replace("\\", "/")
    if not value or len(value) > MAX_PATH_LENGTH:
        raise BrokerProtocolError("invalid repository path")
    if value.startswith("/") or value.startswith(".git/") or value == ".git":
        raise BrokerProtocolError(f"unsafe repository path: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise BrokerProtocolError(f"unsafe repository path: {value}")
    return value


def _extract_tag_json(text: str, tag: str) -> Any | None:
    pattern = rf"\[{re.escape(tag)}\]\s*(.*?)\s*\[/{re.escape(tag)}\]"
    match = re.search(pattern, text or "", flags=re.I | re.S)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith("'''") and raw.endswith("'''"):
        raw = raw[3:-3].strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2 and lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
            raw = "\n".join(lines).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrokerProtocolError(f"{tag} payload is not valid JSON: {exc}") from exc


def parse_broker_read(text: str) -> list[dict]:
    payload = _extract_tag_json(text, "BROKER_READ")
    if payload is None:
        return []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("files") or payload.get("requests") or payload.get("paths") or []
    else:
        raise BrokerProtocolError("BROKER_READ must contain an object or list")

    result: list[dict] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for item in items:
        if isinstance(item, str):
            spec = {"path": safe_repo_path(item), "start": None, "end": None}
        elif isinstance(item, dict):
            path = safe_repo_path(item.get("path"))
            start = item.get("start")
            end = item.get("end")
            if start is not None:
                start = max(1, int(start))
            if end is not None:
                end = max(1, int(end))
            if start is not None and end is not None and end < start:
                raise BrokerProtocolError(f"invalid line range for {path}")
            spec = {"path": path, "start": start, "end": end}
        else:
            raise BrokerProtocolError("BROKER_READ item must be a path or object")
        key = (spec["path"], spec["start"], spec["end"])
        if key not in seen:
            result.append(spec)
            seen.add(key)
        if len(result) > MAX_READ_REQUESTS:
            raise BrokerProtocolError(f"BROKER_READ supports at most {MAX_READ_REQUESTS} files per turn")
    return result


def parse_broker_changeset(text: str) -> dict | None:
    payload = _extract_tag_json(text, "BROKER_CHANGESET")
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise BrokerProtocolError("BROKER_CHANGESET must contain an object")

    base_sha = str(payload.get("base_sha") or "").strip()
    message = str(payload.get("commit_message") or "").strip()
    edits = payload.get("edits")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base_sha):
        raise BrokerProtocolError("BROKER_CHANGESET base_sha must be a 40-character commit SHA")
    if not message:
        raise BrokerProtocolError("BROKER_CHANGESET commit_message is required")
    if not isinstance(edits, list) or not edits:
        raise BrokerProtocolError("BROKER_CHANGESET edits must be a non-empty list")
    if len(edits) > MAX_CHANGESET_EDITS:
        raise BrokerProtocolError(f"BROKER_CHANGESET supports at most {MAX_CHANGESET_EDITS} edits")

    normalized = []
    for raw in edits:
        if not isinstance(raw, dict):
            raise BrokerProtocolError("changeset edit must be an object")
        op = str(raw.get("op") or "").strip().lower()
        path = safe_repo_path(raw.get("path"))
        expected_sha = str(raw.get("expected_sha") or "").strip() or None
        if expected_sha and not re.fullmatch(r"[0-9a-fA-F]{40}", expected_sha):
            raise BrokerProtocolError(f"invalid expected_sha for {path}")
        item = {"op": op, "path": path, "expected_sha": expected_sha}
        if op == "replace":
            old = raw.get("old")
            new = raw.get("new")
            if not isinstance(old, str) or not old:
                raise BrokerProtocolError(f"replace old text is required for {path}")
            if not isinstance(new, str):
                raise BrokerProtocolError(f"replace new text must be a string for {path}")
            count = int(raw.get("count", 1))
            if count < 1 or count > 100:
                raise BrokerProtocolError(f"invalid replacement count for {path}")
            item.update(old=old, new=new, count=count)
        elif op in {"create", "write", "append"}:
            value = raw.get("content")
            if not isinstance(value, str):
                raise BrokerProtocolError(f"{op} content must be a string for {path}")
            item["content"] = value
        elif op == "delete":
            pass
        else:
            raise BrokerProtocolError(f"unsupported edit operation {op!r} for {path}")
        normalized.append(item)

    return {
        "base_sha": base_sha.lower(),
        "commit_message": message,
        "edits": normalized,
    }


def apply_text_edit(current: str | None, edit: dict) -> str | None:
    op = edit["op"]
    path = edit["path"]
    if op == "create":
        if current is not None:
            raise BrokerProtocolError(f"create target already exists: {path}")
        return edit["content"]
    if op == "delete":
        if current is None:
            raise BrokerProtocolError(f"delete target does not exist: {path}")
        return None
    if current is None:
        raise BrokerProtocolError(f"{op} target does not exist: {path}")
    if op == "write":
        return edit["content"]
    if op == "append":
        return current + edit["content"]
    if op == "replace":
        expected = int(edit["count"])
        actual = current.count(edit["old"])
        if actual != expected:
            raise BrokerProtocolError(
                f"replace occurrence mismatch for {path}: expected {expected}, found {actual}"
            )
        return current.replace(edit["old"], edit["new"], expected)
    raise BrokerProtocolError(f"unsupported edit operation: {op}")
