#!/usr/bin/env python3
"""Record review rounds, decide findings, and close per-document review ledgers."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_approvals import ApprovalError
from review_ledgers import (LEDGER_ROOT, close, decide, dispatch, ingest, load, reconcile, request_full, save,
                            summary, validate_subject, void)


def emit(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))


def subjects(repo: Path) -> list:
    root = repo / LEDGER_ROOT
    names = []
    for path in sorted(root.rglob("*.json")) if root.is_dir() else []:
        relative = path.relative_to(root).with_suffix("").as_posix()
        names.append("docs/" + relative[:-len("/coherence")] if relative.endswith("/coherence")
                     else "docs/" + relative + ".md")
    return names


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ("status", "decide", "void", "close", "request-full", "dispatch", "reconcile"):
        mode.add_argument("--" + name, action="store_true")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--path", help="Reviewed document, repository-relative.")
    parser.add_argument("--feature", help="docs/features/<feature> for its coherence ledger.")
    parser.add_argument("--round", type=int)
    parser.add_argument("--reason")
    parser.add_argument("--since", help="ISO time of the developer's last answer; a cycling stop lifts after it.")
    parser.add_argument("--session-dir", help="Directory holding reviewer reports as <agent-id>.md.")
    parser.add_argument("--stdin", action="store_true", help="Read the JSON payload for decide/dispatch/reconcile.")
    args = parser.parse_args(arguments)
    if args.path and args.feature:
        parser.error("use --path or --feature, not both")
    needs_subject = args.decide or args.void or args.close or args.request_full
    if needs_subject and not (args.path or args.feature):
        parser.error("this mode requires --path or --feature")
    if (args.decide or args.dispatch or args.reconcile) != args.stdin:
        parser.error("decide, dispatch, and reconcile read their JSON payload with --stdin; other modes take none")
    if (args.void or args.request_full) and not (args.reason or "").strip():
        parser.error("void and request-full require a non-empty --reason")
    if args.void and args.round is None:
        parser.error("void requires --round")
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ApprovalError("--repo must name an existing directory")
        payload = json.loads(sys.stdin.read()) if args.stdin else None
        subject = validate_subject(repo, args.path or args.feature) if (args.path or args.feature) else None
        if args.dispatch:
            try:
                emit({"status": "recorded", "rounds": dispatch(repo, payload, args.since, args.session_dir)})
            except ApprovalError as refusal:
                emit({"status": "refused", "reason": "review-round", "message": str(refusal)})
                return 3
            return 0
        if args.reconcile:
            reconcile(repo, payload, args.session_dir)
            emit({"status": "reconciled"})
            return 0
        if args.status:
            rows = []
            for name in [subject] if subject else subjects(repo):
                data = load(repo, name)
                if ingest(data):
                    save(repo, data)
                rows.append(summary(repo, data, args.since))
            emit({"status": "ok", "ledgers": rows})
            return 0
        try:
            data = (decide(repo, subject, payload) if args.decide
                    else void(repo, subject, args.round, args.reason) if args.void
                    else request_full(repo, subject, args.reason) if args.request_full
                    else close(repo, subject))
        except ApprovalError as refusal:
            emit({"status": "refused", "reason": "review-ledger", "message": str(refusal)})
            return 3
        emit({"status": "ok", "ledger": summary(repo, data, args.since)})
    except (ApprovalError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        print("review-ledger: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
