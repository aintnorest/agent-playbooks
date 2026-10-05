"""Content-bound approval records shared by Playbook contract programs."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

ASSIGNMENT = re.compile(rb"^- Assigned (?:worktree|branch):[^\r\n]*(?:\r?\n)?$")
DEVELOPER_GATED_TYPES = {"vision", "architecture", "prd", "system-design"}


class ApprovalError(ValueError):
    """A document or approval record cannot be inspected safely."""


def document_type(path: Path) -> Optional[str]:
    parts = path.parts
    if len(parts) >= 2 and parts[-2:] == ("templates", "roadmap.md"):
        return "roadmap"
    if len(parts) >= 2 and parts[-2] == "guides" and path.suffix == ".md":
        return "guide"
    if len(parts) >= 2 and parts[-2] == "docs":
        return {"product-vision.md": "vision", "architecture.md": "architecture",
                "roadmap.md": "roadmap"}.get(parts[-1])
    if len(parts) >= 4 and parts[-4] == "docs" and parts[-3] == "features" and parts[-2]:
        return {"prd.md": "prd", "system-design.md": "system-design",
                "tdd.md": "tdd", "implementation-plan.md": "implementation-plan"}.get(parts[-1])
    if (len(parts) >= 6 and parts[-6] == "docs" and parts[-5] == "features"
            and parts[-4] and parts[-3] == "slices" and parts[-2]):
        return {"tdd.md": "tdd", "implementation-plan.md": "implementation-plan"}.get(parts[-1])
    return None


def gate_for_type(kind: Optional[str]) -> str:
    if kind in DEVELOPER_GATED_TYPES:
        return "developer"
    if kind in ("tdd", "implementation-plan"):
        return "agent"
    return "none"


def split_frontmatter(content: bytes) -> tuple:
    """Split flat frontmatter from the exact stored body bytes."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip(b"\r\n") != b"---":
        raise ApprovalError("missing status frontmatter")
    fields = {}
    for index, line in enumerate(lines[1:], 1):
        if line.rstrip(b"\r\n") == b"---":
            return fields, b"".join(lines[index + 1:])
        try:
            match = re.fullmatch(r"([a-z][a-z-]*): ([^\s].*)", line.decode("utf-8").rstrip("\r\n"))
        except UnicodeError as error:
            raise ApprovalError("frontmatter is not UTF-8") from error
        if not match or match[1] in fields:
            raise ApprovalError("invalid or duplicate frontmatter field")
        fields[match[1]] = match[2]
    raise ApprovalError("frontmatter is not closed")


def normalize_plan_assignments(body: bytes) -> bytes:
    return b"".join(line for line in body.splitlines(keepends=True)
                    if not ASSIGNMENT.fullmatch(line))


def body_bytes(content: bytes, kind: Optional[str] = None) -> bytes:
    body = split_frontmatter(content)[1] if kind is not None else content
    return normalize_plan_assignments(body) if kind == "implementation-plan" else body


def body_sha256(content: bytes, kind: Optional[str] = None) -> str:
    return hashlib.sha256(body_bytes(content, kind)).hexdigest()


def relative_path(repo: Path, path: Path) -> str:
    root = Path(repo).resolve()
    candidate = Path(path)
    candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError as error:
        raise ApprovalError("document path must be inside --repo") from error


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ApprovalError("duplicate JSON key: " + key)
        result[key] = value
    return result


def validate_approval_file(data, filename: str, gate: str) -> None:
    def fail(key, message):
        raise ApprovalError(f"{filename}: {key}: {message}")
    if not isinstance(data, dict):
        fail("<root>", "expected JSON object")
    for name, entry in data.items():
        path = Path(name)
        if (path.is_absolute() or path.as_posix() != name or ".." in path.parts
                or "\\" in name or gate_for_type(document_type(path)) != gate):
            fail(name, "invalid path or wrong approval gate")
        digest = entry
        if gate == "agent":
            if not isinstance(entry, dict) or set(entry) != {"hash", "evidence"}:
                fail(name, "expected exactly hash and evidence fields")
            if not isinstance(entry["evidence"], str) or not entry["evidence"].strip():
                fail(name, "evidence must be non-empty text")
            digest = entry["hash"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(name, "hash must be 64 lowercase hexadecimal characters")


def parse_approval_file(text, filename: str, gate: str) -> dict:
    try:
        data = json.loads(text, object_pairs_hook=_unique_object)
    except (ValueError, TypeError, UnicodeError) as error:
        raise ApprovalError(f"{filename}: malformed approvals JSON: {error}") from error
    validate_approval_file(data, filename, gate)
    return data


def _load_file(repo: Path, filename: str, gate: str) -> dict:
    try:
        text = (Path(repo) / filename).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError) as error:
        raise ApprovalError(f"{filename}: cannot read approvals: {error}") from error
    return parse_approval_file(text, filename, gate)


def load_user_approvals(repo: Path) -> dict:
    return _load_file(repo, "docs/user-approvals.json", "developer")


def load_agent_approvals(repo: Path) -> dict:
    return _load_file(repo, "docs/agent-approvals.json", "agent")


def load_approval_files(repo: Path) -> dict:
    return {"developer": load_user_approvals(repo), "agent": load_agent_approvals(repo)}


def save_agent_approvals(repo: Path, data: dict) -> None:
    filename = "docs/agent-approvals.json"
    validate_approval_file(data, filename, "agent")
    path = Path(repo) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".agent-approvals-", delete=False) as stream:
            temporary = stream.name
            stream.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def approval_status(repo: Path, path: Path, approvals: Optional[dict] = None) -> dict:
    name = relative_path(repo, path)
    kind = document_type(Path(name))
    if kind is None:
        raise ApprovalError("unknown document path/type: " + name)
    data = load_approval_files(repo) if approvals is None else approvals
    gate = gate_for_type(kind)
    entry = data.get(gate, {}).get(name)
    row = {"path": name, "type": kind, "gate": gate, "approved": False, "reason": "missing"}
    if entry is not None:
        digest = entry if gate == "developer" else entry["hash"]
        if digest == body_sha256((Path(repo) / name).read_bytes(), kind):
            row.update(approved=True, reason=None)
        else:
            row["reason"] = "hash mismatch"
    return row
