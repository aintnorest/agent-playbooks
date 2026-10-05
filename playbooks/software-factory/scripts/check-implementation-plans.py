#!/usr/bin/env python3
"""Check implementation-plan grammar and protected files, or emit the task DAG."""

import argparse
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from git_environment import clean_git_environment


HEADING = re.compile(r"^### (T[0-9]+) — (\S(?:.*\S)?)$")
TASK_LIKE = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9_-]*[0-9]+|[0-9]+(?=\s+[-—–])|Task\b|T(?:[A-Z]+(?=\s+[-—–])|(?=\s*[-—–:]|$)))"
)
SECTION = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+(.+?)\s*$")
LABEL = re.compile(r"^- ([A-Za-z][A-Za-z ]*):(.*)$")
DEPENDENCIES = re.compile(r"^(?:none|T[0-9]+(?:, T[0-9]+)*)$")
REASON = re.compile(r"^[ \t]+- (T[0-9]+) — (\S(?:.*\S)?)$")
SUB_BULLET = re.compile(r"^[ \t]+- ")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(?:.*)$")
MANDATORY = ("Depends on", "Targets", "Change", "Done when", "Verify")
ORDER = ("Depends on", "Targets", "Protects", "Change", "Tests", "Done when", "Verify", "Assigned worktree", "Assigned branch")
PROTECTED_PATH = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")
TARGET_ITEM = re.compile(
    r"^(?:`([^`:\n]+)`|([^\s`;():]+))(?:\s*::[^\n;]+)?\s+\((?:edit|create)\)$"
)
BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]*$")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True,
                          check=True, text=True, env=clean_git_environment()).stdout.strip()

def registered_worktrees(repo: Path) -> List[Path]:
    """Parse Git's NUL-delimited worktree records without splitting path newlines."""
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "worktree", "list", "--porcelain", "-z"],
                            capture_output=True, check=True, env=clean_git_environment()).stdout
    return [Path(os.fsdecode(field[len(b"worktree "):])).resolve()
            for field in result.split(b"\0") if field.startswith(b"worktree ")]


def visible_lines(text: str) -> List[Optional[str]]:
    """Keep source line positions while hiding complete Markdown code fences."""
    result: List[Optional[str]] = []
    marker = ""
    length = 0
    for line in text.splitlines():
        opening = FENCE_OPEN.fullmatch(line)
        if marker:
            result.append(None)
            if re.fullmatch(r" {0,3}" + re.escape(marker) +
                            "{" + str(length) + r",}[ \t]*", line):
                marker = ""
            continue
        if opening:
            marker = opening[1][0]
            length = len(opening[1])
            result.append(None)
        else:
            result.append(line)
    return result


def parse_plan(path: Path, text: str) -> Tuple[List[dict], List[Tuple[int, str]]]:
    """Return parsed tasks and (source line, diagnostic) pairs for one plan."""
    lines = visible_lines(text)
    tasks: List[dict] = []
    errors: List[Tuple[int, str]] = []
    blocks: List[Tuple[int, int, re.Match]] = []
    active: Optional[Tuple[int, re.Match]] = None
    for index, line in enumerate(lines):
        if line is None:
            continue
        section = SECTION.fullmatch(line)
        if section is None:
            continue
        if active is not None:
            blocks.append((active[0], index, active[1]))
            active = None
        heading = HEADING.fullmatch(line)
        if heading:
            active = (index, heading)
        elif TASK_LIKE.match(section[1]):
            errors.append((index + 1, "invalid task heading; expected ### T<digits> — <title>"))
    if active is not None:
        blocks.append((active[0], len(lines), active[1]))
    if not blocks and not errors:
        errors.append((1, "no implementation-plan task blocks found"))

    for start, end, heading in blocks:
        task = {
            "id": heading[1], "title": heading[2], "depends_on": [],
            "fields": {}, "path": str(path), "line": start + 1,
        }
        tasks.append(task)
        seen: Dict[str, int] = {}
        last_position = -1
        index = start + 1
        while index < end:
            line = lines[index]
            if line is None or not line.strip():
                index += 1
                continue
            match = LABEL.fullmatch(line)
            if match:
                name, value = match[1], match[2]
                if name not in ORDER:
                    errors.append((index + 1, "unknown task label: " + name))
                    index += 1
                    continue
                if name in seen:
                    errors.append((index + 1, "duplicate task label: " + name))
                else:
                    seen[name] = index + 1
                    position = ORDER.index(name)
                    if position < last_position:
                        errors.append((index + 1, "task label out of order: " + name))
                    last_position = max(last_position, position)
                content = value.strip()
                if name == "Depends on":
                    if not DEPENDENCIES.fullmatch(value.lstrip(" ")) or value != " " + content:
                        errors.append((index + 1, "malformed Depends on; use one line of direct IDs separated by ', ', or none"))
                    elif content != "none":
                        task["depends_on"] = content.split(", ")
                    expected = task["depends_on"]
                    dependency_line = index + 1
                    index += 1
                    reasons: List[Tuple[int, str]] = []
                    while index < end and (lines[index] is not None and SUB_BULLET.match(lines[index])):
                        reason = REASON.fullmatch(lines[index])
                        if reason is None:
                            errors.append((index + 1, "malformed dependency reason; expected indented '- T<digits> — <reason>'"))
                        else:
                            reasons.append((index + 1, reason[1]))
                        index += 1
                    if [identifier for _, identifier in reasons] != expected:
                        errors.append((dependency_line, "dependency reasons must match direct IDs exactly, in order"))
                    if index < end and lines[index] is not None and lines[index][:1] in (" ", "\t") and lines[index].strip():
                        errors.append((index + 1, "Depends on accepts only immediate reason sub-bullets"))
                    if name not in task["fields"]:
                        task["fields"][name] = content
                    continue
                if name not in task["fields"]:
                    task["fields"][name] = content
                index += 1
                continuations: List[str] = []
                while index < end and (lines[index] is None or not lines[index] or lines[index][:1] in (" ", "\t")):
                    if lines[index] is not None and lines[index].strip():
                        continuations.append(lines[index].strip())
                    index += 1
                if continuations and task["fields"].get(name) == content:
                    task["fields"][name] = "\n".join(filter(None, [content, *continuations]))
                continue
            if not line[:1] in (" ", "\t"):
                errors.append((index + 1, "unexpected unindented content in task block"))
            else:
                errors.append((index + 1, "continuation without a task label"))
            index += 1
        for name in MANDATORY:
            if name not in seen:
                errors.append((start + 1, "missing task label: " + name))
        for name in ORDER:
            if name in seen and not task["fields"].get(name, "").strip():
                errors.append((seen[name], "empty task field: " + name))

    assignments: Dict[str, str] = {}
    branches: Dict[str, str] = {}
    for task in tasks:
        path = task["fields"].get("Assigned worktree")
        branch = task["fields"].get("Assigned branch")
        if (path is None) != (branch is None):
            errors.append((task["line"], "Assigned worktree and Assigned branch must appear together"))
            continue
        if path is None:
            continue
        if not Path(path).is_absolute() or posixpath.normpath(path) != path or any(c in path for c in "\r\n\0"):
            errors.append((task["line"], "Assigned worktree must be an absolute normalized path"))
        elif str(Path(path).resolve()) in assignments:
            errors.append((task["line"], "worktree assigned to multiple tasks: " + path))
        else:
            assignments[str(Path(path).resolve())] = task["id"]
        if not BRANCH.fullmatch(branch) or subprocess.run(
            ["git", "--no-optional-locks", "check-ref-format", "--branch", branch], capture_output=True,
            env=clean_git_environment()
        ).returncode:
            errors.append((task["line"], "malformed Assigned branch"))
        elif branch in branches:
            errors.append((task["line"], "branch assigned to multiple tasks: " + branch))
        else:
            branches[branch] = task["id"]

    by_id: Dict[str, int] = {}
    for position, task in enumerate(tasks):
        identifier = task["id"]
        if identifier in by_id:
            errors.append((task["line"], "duplicate task ID: " + identifier))
        else:
            by_id[identifier] = position
    for position, task in enumerate(tasks):
        found = set()
        for prerequisite in task["depends_on"]:
            if prerequisite in found:
                errors.append((task["line"], "duplicate prerequisite ID: " + prerequisite))
            found.add(prerequisite)
            if prerequisite == task["id"]:
                errors.append((task["line"], "self dependency: " + prerequisite))
            elif prerequisite not in by_id:
                errors.append((task["line"], "dangling prerequisite ID: " + prerequisite))
            elif by_id[prerequisite] >= position:
                errors.append((task["line"], "forward prerequisite ID: " + prerequisite))
    protected: Dict[str, Tuple[str, int]] = {}
    for position, task in enumerate(tasks):
        value = task["fields"].get("Protects")
        if value is None:
            continue
        paths = value.split("; ")
        if "; ".join(paths) != value or not paths or any(
            not PROTECTED_PATH.fullmatch(item) or
            any(part in (".", "..") for part in item.split("/"))
            for item in paths
        ):
            errors.append((task["line"], "malformed Protects; use semicolon-and-space-separated repository-relative file paths"))
            continue
        if len(paths) != len(set(paths)):
            errors.append((task["line"], "duplicate protected file in Protects"))
        for item in paths:
            if item in protected:
                errors.append((task["line"], "protected file declared by multiple tasks: " + item))
            else:
                protected[item] = (task["id"], position)
    for position, task in enumerate(tasks):
        if task["fields"].get("Targets", "").strip() == "none":
            continue
        for item in re.split(r";\s*|\n", task["fields"].get("Targets", "")):
            match = TARGET_ITEM.fullmatch(item.strip())
            if match is None:
                errors.append((task["line"], "cannot check protected files in malformed Targets item: " + item.strip() + "; use path[::symbol] (edit|create), separated by semicolons/newlines, or sole none"))
                continue
            target = match[1] or match[2]
            owner = protected.get(posixpath.normpath(target))
            if owner is not None and owner[1] < position:
                errors.append((task["line"], "Targets names protected file from " + owner[0] + ": " + target))


    # Traverse iteratively even when the earlier-task rule is violated; long plans
    # should report their errors rather than hitting Python's recursion limit.
    colors: Dict[str, int] = {}
    for identifier in by_id:
        if colors.get(identifier, 0):
            continue
        colors[identifier] = 1
        stack = [(identifier, iter(tasks[by_id[identifier]]["depends_on"]))]
        while stack:
            current, edges = stack[-1]
            prerequisite = next(edges, None)
            if prerequisite is None:
                colors[current] = 2
                stack.pop()
            elif prerequisite in by_id:
                if colors.get(prerequisite) == 1:
                    errors.append((tasks[by_id[current]]["line"],
                                   "dependency cycle: " + current + " -> " + prerequisite))
                elif colors.get(prerequisite, 0) == 0:
                    colors[prerequisite] = 1
                    stack.append((prerequisite, iter(tasks[by_id[prerequisite]]["depends_on"])))
    return tasks, sorted(errors)


def protected_diff(tasks: List[dict], repo: Path, base: str, head: str,
                   task_id: Optional[str], worktree_root: Optional[Path] = None) -> List[Tuple[int, str]]:
    """Check protected paths and, for assigned tasks, live worktree/branch identity."""
    selected = next((task for task in tasks if task["id"] == task_id), None)
    if task_id is not None and selected is None:
        return [(1, "unknown task ID: " + task_id)]
    try:
        root = git(repo, "rev-parse", "--show-toplevel")
        if Path(root).resolve() != repo.resolve():
            return [(1, "--repo must name the Git repository root")]
        revisions = [git(repo, "rev-parse", "--verify", "--end-of-options", name + "^{commit}")
                     for name in (base, head)]
        changed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), "diff", "--name-only", "--no-ext-diff",
             "--no-renames", "-z", *revisions, "--"],
            capture_output=True, check=True, env=clean_git_environment(),
        ).stdout
    except OSError as error:
        return [(1, f"cannot inspect protected diff: {error}")]
    except subprocess.CalledProcessError as error:
        detail = error.stderr
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        return [(1, "cannot inspect protected diff: " + (detail or str(error)).strip())]
    if selected is not None and "Assigned worktree" in selected["fields"]:
        assignment = selected["fields"]
        location = Path(assignment["Assigned worktree"])
        if worktree_root is None:
            return [(selected["line"], "assigned task requires --worktree-root")]
        permitted = worktree_root.resolve()
        expected_root = repo.resolve() / ".worktrees"
        actual = location.resolve()
        if not worktree_root.is_absolute() or permitted != expected_root:
            return [(selected["line"], "--worktree-root must be <repo-root>/.worktrees")]
        if actual == permitted or permitted not in actual.parents:
            return [(selected["line"], "assigned worktree is outside --worktree-root")]
        try:
            if subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "check-ignore", "-q", "--",
                               str(repo / ".worktrees")], capture_output=True, env=clean_git_environment()).returncode:
                return [(selected["line"], "<repo-root>/.worktrees/ is not ignored by Git")]
            if actual not in registered_worktrees(repo):
                return [(selected["line"], "assigned worktree is not registered")]
            if git(location, "symbolic-ref", "--quiet", "--short", "HEAD") != assignment["Assigned branch"]:
                return [(selected["line"], "assigned worktree branch differs from plan")]
            if git(location, "rev-parse", "HEAD") != revisions[1]:
                return [(selected["line"], "candidate is not assigned worktree branch tip")]
            if subprocess.run(["git", "--no-optional-locks", "-C", str(location), "status", "--porcelain",
                               "--untracked-files=all", "--ignore-submodules=none"],
                              capture_output=True, check=True, env=clean_git_environment()).stdout:
                return [(selected["line"], "assigned worktree has uncommitted changes")]
            subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "merge-base", "--is-ancestor",
                            revisions[0], revisions[1]], capture_output=True, check=True, env=clean_git_environment())
        except (OSError, subprocess.CalledProcessError) as error:
            return [(selected["line"], "cannot verify assigned worktree or candidate ancestry: " + str(error))]
    elif worktree_root is not None and selected is None:
        return [(1, "--worktree-root requires --task")]

    changed_paths = set(changed.decode("utf-8", errors="surrogateescape").split("\0"))
    return [
        (task["line"], f"candidate {task_id or '(no task)'} changes {item} protected by {task['id']}")
        for task in tasks if task_id is None or task["id"] != task_id
        for item in task["fields"].get("Protects", "").split("; ")
        if item and item in changed_paths
    ]


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check tasks and report errors")
    mode.add_argument("--json", action="store_true", help="emit parsed tasks as JSON when valid")
    mode.add_argument("--protected-diff", metavar="PLAN", type=Path,
                      help="check a candidate Git diff against protected files")
    parser.add_argument("--repo", type=Path, help="Git repository root")
    parser.add_argument("--base", help="base commit")
    parser.add_argument("--head", help="candidate commit")
    parser.add_argument("--task", help="plan task ID whose own protected files may change (omit for non-task candidates)")
    parser.add_argument("--worktree-root", type=Path, help="required <repo-root>/.worktrees for assigned candidates")
    parser.add_argument("paths", nargs="*", type=Path, help="implementation-plan Markdown files")
    args = parser.parse_args(arguments)
    diff_flags = (args.repo, args.base, args.head)
    if args.protected_diff:
        if args.paths or any(value is None for value in diff_flags):
            parser.error("--protected-diff requires --repo, --base, --head and no other plan paths")
        args.paths = [args.protected_diff]
    elif not args.paths or args.task is not None or args.worktree_root is not None or any(value is not None for value in diff_flags):
        parser.error("--check/--json require plan paths and cannot use diff flags")
    if args.protected_diff and args.worktree_root is not None and not args.worktree_root.is_absolute():
        parser.error("--worktree-root must be absolute")
    all_tasks: List[dict] = []
    failures = False
    for path in args.paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            print(f"{path}:1: cannot read plan: {error}", file=sys.stderr)
            failures = True
            continue
        tasks, errors = parse_plan(path, text)
        all_tasks.extend(tasks)
        for line, message in errors:
            print(f"{path}:{line}: {message}", file=sys.stderr)
        failures |= bool(errors)
    if failures:
        return 1
    if args.protected_diff:
        path = args.protected_diff
        errors = protected_diff(all_tasks, args.repo, args.base, args.head, args.task, args.worktree_root)
        for line, message in errors:
            print(f"{path}:{line}: {message}", file=sys.stderr)
        if errors:
            return 1
    if args.json:
        print(json.dumps(all_tasks, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
