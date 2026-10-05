#!/usr/bin/env python3
"""Validate Playbook document status frontmatter and emit machine-readable metadata."""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_approvals import (ApprovalError, approval_status, body_bytes, document_type,
                           gate_for_type, load_approval_files, parse_approval_file)
from git_environment import clean_git_environment


STATES = {
    "vision": {"draft", "active", "superseded"},
    "architecture": {"draft", "active", "superseded"},
    "roadmap": {"draft", "active", "superseded"},
    "prd": {"draft", "active", "done", "superseded"},
    "system-design": {"draft", "active", "done", "superseded"},
    "tdd": {"draft", "active", "done", "superseded"},
    "implementation-plan": {"draft", "active", "done", "superseded"},
    "guide": {"active", "superseded"},
}
PREFIX = {"vision": "vision", "architecture": "arch", "prd": "prd",
          "system-design": "sd", "tdd": "tdd", "implementation-plan": "plan"}
FIELD = re.compile(r"^([a-z][a-z-]*): ([^\s].*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
RESTATEMENT = re.compile(
    r"^(?:[-*] )?(?:state\s*:\s*|(?:the |this document(?:'s)? )?state is\s+)?"
    r"(draft|approved|active|done|superseded)(?:\.|\s+status\.?|\s+state\.?)?$",
    re.IGNORECASE,
)




def visible_lines(lines: List[str], start: int) -> List[Tuple[int, str]]:
    """Hide fenced examples without losing original source line numbers."""
    visible = []
    marker = ""
    length = 0
    for index in range(start, len(lines)):
        line = lines[index]
        if marker:
            if re.fullmatch(r" {0,3}" + re.escape(marker) +
                            "{" + str(length) + r",}[ \t]*", line):
                marker = ""
            continue
        opening = FENCE.match(line)
        if opening:
            marker = opening[1][0]
            length = len(opening[1])
        else:
            visible.append((index + 1, line))
    return visible


def check_document(path: Path, kind: str, text: str) -> Tuple[Optional[dict], List[dict]]:
    lines = text.splitlines()
    errors: List[dict] = []

    def fail(line: int, message: str) -> None:
        errors.append({"path": str(path), "line": line, "message": message})

    frontmatter_end = 0
    fields: Dict[str, str] = {}
    positions: Dict[str, int] = {}
    if lines and lines[0] == "---":
        try:
            closing = lines.index("---", 1)
        except ValueError:
            fail(1, "frontmatter is not closed; add a closing --- line")
            closing = len(lines)
        frontmatter_end = min(closing + 1, len(lines))
        last_order = -1
        for index in range(1, closing):
            line = lines[index]
            match = FIELD.fullmatch(line)
            if not match:
                fail(index + 1, "invalid frontmatter; use flat 'state: value' scalar lines")
                continue
            key, value = match.groups()
            if key not in ("state", "revision", "approved"):
                fail(index + 1, "unknown frontmatter key: " + key)
                continue
            if key == "approved" and kind != "guide":
                fail(index + 1, "approved frontmatter is forbidden for product documents; "
                     "see guides/migrations/0.1.0-to-1.0.0.md")
            if key in fields:
                fail(index + 1, "duplicate frontmatter key: " + key)
                continue
            fields[key] = value
            positions[key] = index + 1
            order = ("state", "revision", "approved").index(key)
            if order < last_order:
                fail(index + 1, "frontmatter keys out of order; use state, revision, approved")
            last_order = max(last_order, order)
    else:
        fail(1, "missing status frontmatter; start with --- then state: <state> then ---")

    visible = visible_lines(lines, frontmatter_end)
    status = [(i, line_number) for i, (line_number, line) in enumerate(visible)
              if (heading := HEADING.fullmatch(line)) and len(heading[1]) == 2
              and heading[2] == "Status"]
    # A leading thematic break followed by a heading is not status frontmatter.
    thematic_break = (lines and lines[0] == "---" and
                      next((line for line in lines[1:] if line.strip()), "").startswith("#"))
    if kind == "guide" and not status and (not lines or lines[0] != "---" or thematic_break):
        return None, []
    for index, _ in status:
        for line, body in visible[index + 1:]:
            match = HEADING.fullmatch(body)
            if match and len(match[1]) <= 2:
                break
            if RESTATEMENT.fullmatch(body.strip()):
                fail(line, "Status prose restates state; keep state only in frontmatter")
            if re.match(r"^\s*-\s*(?:State|Revision|Approved):", body, re.IGNORECASE):
                fail(line, "legacy Status key line; move status metadata to frontmatter")

    state = fields.get("state")
    revision = fields.get("revision")
    approved = fields.get("approved")
    if state is None:
        fail(1, "missing state; add state: <allowed lowercase state> to frontmatter")
    elif state not in STATES[kind]:
        fail(positions["state"], "invalid state for " + kind + ": " + state +
             "; allowed: " + ", ".join(sorted(STATES[kind])))
    if kind in PREFIX:
        if revision is None:
            fail(1, "missing revision; add revision: " + PREFIX[kind] + "-r<N>")
        elif not re.fullmatch(re.escape(PREFIX[kind]) + r"-r[1-9][0-9]*", revision):
            fail(positions["revision"], "invalid revision; expected " + PREFIX[kind] + "-r<N>")
    elif revision is not None:
        fail(positions["revision"], "revision is forbidden for " + kind)
    if kind == "guide":
        if state in ("active", "done"):
            if approved is None:
                fail(1, "missing approved; add approved: YYYY-MM-DD for " + state)
        elif approved is not None:
            fail(positions["approved"], "approved is forbidden unless state is active or done")
        if approved is not None:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", approved):
                fail(positions["approved"], "invalid approved date; expected YYYY-MM-DD")
            else:
                try:
                    datetime.date.fromisoformat(approved)
                except ValueError:
                    fail(positions["approved"], "invalid approved date; expected a real calendar date")
    return {"path": str(path), "type": kind, "state": state,
            "revision": revision, "approval": {"gate": gate_for_type(kind),
                                               "valid": False}}, errors


class GitFailure(Exception):
    """A Git object or comparison could not be inspected safely."""


def git_bytes(repo: Path, *arguments: str) -> bytes:
    command = ["git", "--no-optional-locks", "-C", str(repo), *arguments]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, env=clean_git_environment())
    except OSError as error:
        raise GitFailure(f"cannot run git: {error}") from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitFailure(f"git {' '.join(arguments[:2])} failed: {detail or result.returncode}")
    return result.stdout


def commit_id(repo: Path, revision: str) -> str:
    object_id = git_bytes(repo, "rev-parse", "--verify", "--end-of-options",
                          revision + "^{commit}").strip()
    if not re.fullmatch(rb"[0-9a-fA-F]{40,64}", object_id):
        raise GitFailure(f"invalid commit object for {revision!r}")
    return object_id.decode("ascii")


def tree_paths(repo: Path, commit: str) -> set:
    listing = git_bytes(repo, "ls-tree", "-r", "-z", "--name-only", commit,
                        "--", "docs/features/")
    return {os.fsdecode(name) for name in listing.split(b"\0") if name}


def document_at(repo: Path, commit: str, name: str) -> bytes:
    return git_bytes(repo, "show", f"{commit}:{name}")


def checked_snapshot(name: str, kind: str, content: bytes, commit: str) -> Tuple[dict, bytes]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise GitFailure(f"{name}: {commit}: document is not UTF-8") from error
    if any((byte < 32 and byte not in (9, 10, 13)) or byte == 127
           for byte in content):
        raise GitFailure(f"{name}: {commit}: binary document contains control bytes")
    row, problems = check_document(Path(name), kind, text)
    if problems:
        raise GitFailure("; ".join(f"{commit}: {problem['path']}:{problem['line']}: "
                                   f"{problem['message']}" for problem in problems))
    if row is None:
        raise GitFailure(f"{name}: {commit}: missing document status")
    return row, body_bytes(content, kind)


def approvals_at(repo: Path, commit: str) -> dict:
    result = {}
    for gate, filename in (("developer", "docs/user-approvals.json"),
                           ("agent", "docs/agent-approvals.json")):
        paths = git_bytes(repo, "ls-tree", "--name-only", commit, "--", filename)
        try:
            result[gate] = parse_approval_file(document_at(repo, commit, filename),
                                               filename, gate) if paths.strip() else {}
        except ApprovalError as error:
            raise GitFailure(f"{commit}: {error}") from error
    return result


def repository_for(path: Path) -> Path:
    """Discover from the document, never from the checker's installation."""
    directory = path.resolve().parent
    for ancestor in (directory, *directory.parents):
        if (ancestor / ".git").exists() or (ancestor / "docs/user-approvals.json").exists():
            return ancestor
    raise ApprovalError("cannot find repository root; use --repo or an ancestor containing .git or docs/user-approvals.json")


def check_frozen_diff(repo: Path, base: str, head: str) -> int:
    try:
        base_id, head_id = commit_id(repo, base), commit_id(repo, head)
        base_paths, head_paths = tree_paths(repo, base_id), tree_paths(repo, head_id)
        head_approvals = approvals_at(repo, head_id)
        changes = git_bytes(repo, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                            "--name-only", "-z", base_id, head_id, "--", "docs/features/")
        names = {os.fsdecode(name) for name in changes.split(b"\0") if name}
        for name in sorted(names):
            kind = document_type(Path(name))
            if kind not in ("prd", "tdd", "implementation-plan", "system-design"):
                continue
            before = after = None
            if name in base_paths:
                before = document_at(repo, base_id, name)
                base_row, base_body = checked_snapshot(name, kind, before, base_id)
            if name in head_paths:
                after = document_at(repo, head_id, name)
                head_row, head_body = checked_snapshot(name, kind, after, head_id)
            if before is None and after is None:
                raise GitFailure(f"{name}: changed path missing from both commits")
            if kind != "system-design":
                if before is not None and base_row["state"] == "done" and after != before:
                    raise GitFailure(f"{name}: done {kind} is frozen; deletion, rename, "
                                     "or byte modification is forbidden")
                if after is not None and head_row["state"] == "done" and (
                        before is None or base_row["state"] != "active"
                        or base_body != head_body
                        or base_row["revision"] != head_row["revision"]
                        ):
                    raise GitFailure(f"{name}: transition to done requires an active {kind} "
                                     "with unchanged body and revision")
            if kind == "system-design" and before is not None and before != after:
                if after is None:
                    raise GitFailure(f"{name}: system-design deletion or rename requires "
                                     "a new revision at this path")
                old_revision = base_row["revision"][4:]
                new_revision = head_row["revision"][4:]
                same_revision = base_row["revision"] == head_row["revision"]
                same_body = base_body == head_body
                acceptance = base_row["state"] == "draft" and head_row["state"] == "active"
                completion = base_row["state"] == "active" and head_row["state"] == "done"
                if same_revision and same_body and (acceptance or completion):
                    continue
                if (len(new_revision), new_revision) <= (len(old_revision), old_revision):
                    raise GitFailure(f"{name}: system-design change requires revision "
                                     f"greater than sd-r{old_revision}; got sd-r{new_revision}")
                if head_row["state"] != "draft":
                    raise GitFailure(f"{name}: new system-design revision sd-r{new_revision} "
                                     "must be draft")
        # Inspect every delivered document, including approvals-only commits.
        for name in sorted(head_paths):
            kind = document_type(Path(name))
            if gate_for_type(kind) == "none":
                continue
            row, _ = checked_snapshot(name, kind, document_at(repo, head_id, name), head_id)
            gate = gate_for_type(kind)
            if row["state"] == "done" and name not in head_approvals[gate]:
                filename = "user-approvals.json" if gate == "developer" else "agent-approvals.json"
                raise GitFailure(f"{name}: done {kind} approval entry must remain in docs/{filename}")
    except GitFailure as error:
        print(f"frozen-diff: {error}", file=sys.stderr)
        return 1
    return 0


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report status errors")
    mode.add_argument("--json", action="store_true", help="emit JSON status records and errors")
    mode.add_argument("--frozen-diff", action="store_true",
                      help="check frozen documents and system-design revisions between commits")
    parser.add_argument("--repo", type=Path, help="repository root; required for --frozen-diff. "
                        "For --check/--json, defaults to the nearest ancestor containing "
                        ".git or docs/user-approvals.json")
    parser.add_argument("--base", help="base commit for --frozen-diff")
    parser.add_argument("--head", help="head commit for --frozen-diff")
    parser.add_argument("paths", nargs="*", type=Path, help="document paths")
    args = parser.parse_args(arguments)
    if args.frozen_diff:
        if args.paths or args.repo is None or args.base is None or args.head is None:
            parser.error("--frozen-diff requires --repo, --base, --head and no file paths")
        return check_frozen_diff(args.repo, args.base, args.head)
    if not args.paths or any(value is not None for value in (args.base, args.head)):
        parser.error("--check/--json require file paths and do not accept --base/--head")
    rows: List[dict] = []
    errors: List[dict] = []
    for path in args.paths:
        kind = document_type(path)
        if kind is None:
            errors.append({"path": str(path), "line": 1, "message": "unknown document path/type"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append({"path": str(path), "line": 1, "message": "cannot read document: " + str(error)})
            continue
        row, problems = check_document(path, kind, text)
        if row is not None and gate_for_type(kind) != "none" and not problems:
            try:
                repo = args.repo.resolve() if args.repo else repository_for(path)
                approvals = load_approval_files(repo)
                status = approval_status(repo, path.resolve(), approvals)
                row["approval"]["valid"] = status["approved"]
                if row["state"] in ("active", "done") and not status["approved"]:
                    problems.append({"path": str(path), "line": 1,
                                     "message": "valid approval required in docs/"
                                                + ("user-approvals.json" if status["gate"] == "developer"
                                                   else "agent-approvals.json") + ": " + str(status["reason"])})
            except (ApprovalError, OSError, ValueError) as error:
                problems.append({"path": str(path), "line": 1, "message": str(error)})
        if row is not None:
            rows.append(row)
        errors.extend(problems)
    if args.json:
        print(json.dumps({"rows": rows, "errors": errors} if errors else rows,
                         indent=2, ensure_ascii=True))
    for error in errors:
        print("{path}:{line}: {message}".format(**error), file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
