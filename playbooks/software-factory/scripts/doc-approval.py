#!/usr/bin/env python3
"""Inspect hashes and record or revoke agent document acceptances."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_approvals import (ApprovalError, approval_status, body_sha256,
                           document_type, gate_for_type, load_approval_files, relative_path,
                           save_agent_approvals, split_frontmatter)
from review_ledgers import receipt


def emit(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))


def hash_entry(repo: Path, name: str) -> dict:
    digest = body_sha256((repo / name).read_bytes(), document_type(Path(name)))
    return {"path": name, "hash": digest, "line": json.dumps(name) + ": " + json.dumps(digest) + ","}


def developer_hashes(repo: Path) -> list:
    """Current entry lines for every developer-gated, non-superseded document."""
    data = load_approval_files(repo)
    entries = []
    for name in document_paths(repo):
        if gate_for_type(document_type(Path(name))) != "developer":
            continue
        if split_frontmatter((repo / name).read_bytes())[0].get("state") == "superseded":
            continue
        row = approval_status(repo, Path(name), data)
        entries.append({**hash_entry(repo, name), "approved": row["approved"], "reason": row["reason"]})
    return entries


def document_paths(repo: Path):
    candidates = list((repo / "docs").rglob("*.md"))
    candidates.extend((repo / "guides").glob("*.md"))
    roadmap = repo / "templates" / "roadmap.md"
    if roadmap.is_file():
        candidates.append(roadmap)
    return sorted(path.relative_to(repo).as_posix() for path in candidates
                  if document_type(path) is not None)


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ("status", "revoke", "accept", "hash"):
        mode.add_argument("--" + name, action="store_true")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--reason")
    parser.add_argument("--migrated-from", metavar="DATE",
                        help="Accept with evidence 'migrated from approved: DATE' (0.1.0 migration only; no review ledger).")
    args = parser.parse_args(arguments)
    if not args.status and not args.hash and args.path is None:
        parser.error("this mode requires --path")
    if args.revoke != (args.reason is not None) or (args.revoke and not args.reason.strip()):
        parser.error("--revoke requires a non-empty --reason, which no other mode accepts")
    if args.migrated_from is not None and (not args.accept or not args.migrated_from.strip()):
        parser.error("--migrated-from requires --accept and a non-empty date")
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ApprovalError("--repo must name an existing directory")
        name = relative_path(repo, args.path) if args.path is not None else None
        kind = document_type(Path(name)) if name is not None else None
        if args.hash:
            if name is None:
                emit({"status": "hashes", "entries": developer_hashes(repo)})
            else:
                emit({"status": "hash", **hash_entry(repo, name)})
            return 0
        if name is not None and kind is None:
            raise ApprovalError("unknown document path/type: " + name)
        if (args.accept or args.revoke) and gate_for_type(kind) != "agent":
            emit({"status": "refused", "reason": "developer-gated" if gate_for_type(kind) == "developer" else "ungated"})
            return 3
        data = load_approval_files(repo)
        if args.status:
            paths = [name] if name is not None else document_paths(repo)
            emit([approval_status(repo, Path(path), data) for path in paths])
        elif args.revoke:
            changed = name in data["agent"]
            if changed:
                del data["agent"][name]
                save_agent_approvals(repo, data["agent"])
            emit({"status": "revoked" if changed else "unchanged", "path": name})
        else:
            if args.migrated_from is not None:
                evidence = "migrated from approved: " + args.migrated_from.strip()
            else:
                closed, evidence = receipt(repo, name)
                if not closed:
                    emit({"status": "refused", "reason": "review-not-closed", "message": evidence})
                    return 3
            data["agent"][name] = {"hash": body_sha256((repo / name).read_bytes(), kind), "evidence": evidence}
            save_agent_approvals(repo, data["agent"])
            emit({"status": "accepted", "path": name})
    except (ApprovalError, OSError, UnicodeError) as error:
        print("doc-approval: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
