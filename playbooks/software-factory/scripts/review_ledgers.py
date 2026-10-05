"""Per-document review ledgers: harness-recorded rounds, review modes, finding decisions, and receipts."""

import difflib
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from doc_approvals import ApprovalError, body_bytes, body_sha256, document_type, relative_path

LEDGER_ROOT = ".playbook/reviews"
DECISIONS = ("accepted", "rejected", "nit", "duplicate")
BLOCKING = ("Blocker", "Major")
CYCLE_RETURNS = 2
# From this many full rounds on, a full round with no accepted Blocker settles the document even with Majors.
FULL_ROUND_LIMIT = 7
DETAIL_LIMIT = 4000
SPECIALIST_TYPES = {
    "review-doc-product-vision-agent": "vision",
    "review-doc-system-architecture-agent": "architecture",
    "review-doc-prd-agent": "prd",
    "review-doc-system-design-agent": "system-design",
    "review-doc-technical-design-agent": "tdd",
    "review-doc-implementation-plan-agent": "implementation-plan",
}
COHERENCE = "review-doc-coherence-agent"
DOCUMENT_PATH = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*docs/[\w./-]+?\.md)\b")
FINDING_HEADING = re.compile(r"^###\s+(\S+)\s+[\u2014\u2013-]\s+(.+?)\s*$")
SEVERITY = re.compile(r"Severity\W{0,6}(Blocker|Major|Minor)\b")
CYCLE_REFUSAL = ("{subject}: {issue} has come back {returns} times after being fixed. Stop and summarize for the "
                 "developer what keeps returning, why the fixes are not holding, the options, and a recommendation. "
                 "Stopping here is the correct way to finish this turn, not a failure.")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ledger_path(repo: Path, subject: str) -> Path:
    """Map a document or `docs/features/<f>` coherence subject to its ledger file."""
    if subject.endswith(".md"):
        return Path(repo) / LEDGER_ROOT / (subject[len("docs/"):-len(".md")] + ".json")
    return Path(repo) / LEDGER_ROOT / subject[len("docs/"):] / "coherence.json"


def coherence_documents(repo: Path, feature: str) -> list:
    root = Path(repo)
    names = [name for name in ("docs/product-vision.md", "docs/architecture.md") if (root / name).is_file()]
    names += sorted(path.relative_to(root).as_posix() for path in (root / feature).rglob("*.md")
                    if document_type(path.relative_to(root)) is not None)
    return names


def body_text(repo: Path, name: str) -> str:
    return body_bytes((Path(repo) / name).read_bytes(), document_type(Path(name))).decode("utf-8")


def snapshot(repo: Path, subject: str):
    """Reviewed text: a document body, or every coherence-set document body by path."""
    if subject.endswith(".md"):
        return body_text(repo, subject)
    return {name: body_text(repo, name) for name in coherence_documents(repo, subject)}


def content_identity(repo: Path, subject: str) -> tuple:
    """Body hash and line count for a document, or for a feature's whole coherence set."""
    root = Path(repo)
    if subject.endswith(".md"):
        content = (root / subject).read_bytes()
        kind = document_type(Path(subject))
        return body_sha256(content, kind), body_bytes(content, kind).count(b"\n")
    digest, lines = hashlib.sha256(), 0
    for name in coherence_documents(repo, subject):
        content = (root / name).read_bytes()
        kind = document_type(Path(name))
        digest.update(f"{name}\0{body_sha256(content, kind)}\n".encode())
        lines += body_bytes(content, kind).count(b"\n")
    return digest.hexdigest(), lines


def validate_subject(repo: Path, subject: str) -> str:
    if subject.endswith(".md"):
        name = relative_path(repo, Path(repo) / subject)
        if document_type(Path(name)) not in SPECIALIST_TYPES.values():
            raise ApprovalError("not a reviewable product document: " + subject)
        return name
    if not re.fullmatch(r"docs/features/[^/]+", subject) or not (Path(repo) / subject).is_dir():
        raise ApprovalError("coherence subject must be an existing docs/features/<feature> directory: " + subject)
    return subject


def load(repo: Path, subject: str) -> dict:
    path = ledger_path(repo, subject)
    if not path.exists():
        return {"version": 1, "subject": subject, "kind": "document" if subject.endswith(".md") else "coherence",
                "rounds": [], "closed": None, "baseline": None, "fullRequested": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ApprovalError(f"{path.relative_to(repo).as_posix()}: unreadable review ledger") from error
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("subject") != subject \
            or not isinstance(data.get("rounds"), list):
        raise ApprovalError(f"{path.relative_to(repo).as_posix()}: malformed review ledger")
    return data


def save(repo: Path, data: dict) -> None:
    path = ledger_path(repo, data["subject"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".ledger-", delete=False) as stream:
            temporary = stream.name
            stream.write(json.dumps(data, indent=2, ensure_ascii=True) + "\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def parse_report(text: str) -> list:
    """Findings from a reviewer's fixed Markdown report; raise when its Findings section is unusable."""
    try:
        decoded = json.loads(text)
        if isinstance(decoded, str):
            text = decoded
    except json.JSONDecodeError:
        pass
    match = re.search(r"^## Findings[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        raise ApprovalError("report has no '## Findings' section")
    section = match.group(1).strip()
    if not section or re.match(r"None\b", section):
        return []
    findings, seen = [], set()
    for block in re.split(r"^(?=###\s)", section, flags=re.M):
        if not block.startswith("###"):
            continue
        heading = FINDING_HEADING.match(block.splitlines()[0])
        severity = SEVERITY.search(block)
        if not heading or not severity:
            raise ApprovalError("cannot read finding: " + block.splitlines()[0][:120])
        if heading[1] in seen:
            raise ApprovalError("duplicate finding ID in one report: " + heading[1])
        seen.add(heading[1])
        findings.append({"id": heading[1], "severity": severity[1], "title": heading[2],
                         "detail": block.split("\n", 1)[1].strip()[:DETAIL_LIMIT] if "\n" in block else "",
                         "decision": None, "reason": None, "duplicateOf": None, "evidence": None})
    if not findings:
        raise ApprovalError("Findings section has neither findings nor 'None'")
    return findings


def ingest(data: dict) -> bool:
    """Record pending rounds whose reviewer report now exists; return whether anything changed."""
    changed = False
    for entry in data["rounds"]:
        if entry["status"] != "pending" or not entry.get("reportPath"):
            continue
        report = Path(entry["reportPath"])
        if not report.is_file():
            continue
        try:
            findings = parse_report(report.read_text(encoding="utf-8"))
        except (ApprovalError, OSError, UnicodeError) as error:
            if entry.get("parseError") != str(error):
                entry["parseError"] = str(error)
                changed = True
            continue
        entry.update(status="recorded", findings=findings)
        entry.pop("reportPath", None)
        entry.pop("parseError", None)
        changed = True
    return changed


def recorded(data: dict) -> list:
    return [entry for entry in data["rounds"] if entry["status"] == "recorded"]


def locate(data: dict, reference: str) -> tuple:
    """(round entry, finding) for a `<round>:<id>` reference."""
    match = re.fullmatch(r"(\d+):(\S+)", reference or "")
    if match:
        for entry in data["rounds"]:
            if entry["round"] == int(match[1]):
                for item in entry.get("findings", []):
                    if item["id"] == match[2]:
                        return entry, item
    raise ApprovalError("unknown finding reference (use <round>:<id>): " + str(reference))


def root(data: dict, entry: dict, item: dict) -> tuple:
    """Follow duplicate links to the original finding."""
    seen = set()
    while item["decision"] == "duplicate" and item.get("duplicateOf") and id(item) not in seen:
        seen.add(id(item))
        entry, item = locate(data, item["duplicateOf"])
    return entry, item


def is_blocking_accepted(item: dict) -> bool:
    return item["decision"] == "accepted" and item["severity"] in BLOCKING


def returns(data: dict) -> dict:
    """Accepted blocking findings that came back after their fix: original reference -> returning rounds."""
    result = {}
    for entry in recorded(data):
        for item in entry["findings"]:
            if item["decision"] != "duplicate":
                continue
            origin, original = root(data, entry, item)
            if is_blocking_accepted(original) and origin["round"] < entry["round"]:
                result.setdefault((origin["round"], original["id"], original["title"]), []).append(entry)
    return result


def open_blocking(data: dict) -> list:
    """Blocking findings of the latest recorded round that still need a fix: accepted, or a returned fixed issue."""
    rounds = recorded(data)
    if not rounds:
        return []
    latest, items = rounds[-1], []
    for item in latest["findings"]:
        if is_blocking_accepted(item):
            items.append((latest, item))
        elif item["decision"] == "duplicate":
            origin, original = root(data, latest, item)
            if is_blocking_accepted(original) and origin["round"] < latest["round"]:
                items.append((latest, item))
    return items


def undecided(data: dict) -> list:
    return [f"{entry['round']}:{item['id']}" for entry in recorded(data)
            for item in entry["findings"] if item["decision"] is None]


def settled(data: dict) -> bool:
    """The initial review phase is over: a decided full round had no accepted Blocker/Major, or, from the
    FULL_ROUND_LIMIT-th full round on, no accepted Blocker."""
    full_rounds = 0
    for entry in recorded(data):
        if entry.get("mode", "full") != "full":
            continue
        full_rounds += 1
        if any(item["decision"] is None for item in entry["findings"]):
            continue
        accepted = [item for item in entry["findings"] if is_blocking_accepted(item)] + [
            original for original in (root(data, entry, item)[1] for item in entry["findings"]
                                      if item["decision"] == "duplicate") if is_blocking_accepted(original)]
        if not accepted or (full_rounds >= FULL_ROUND_LIMIT
                            and all(item["severity"] != "Blocker" for item in accepted)):
            return True
    return False


def next_mode(repo: Path, data: dict) -> str:
    if data.get("fullRequested") or not any(entry["status"] != "void" for entry in data["rounds"]) \
            or not data.get("baseline"):
        return "full"
    if data["kind"] == "coherence":
        added = set(coherence_documents(repo, data["subject"])) - set(data["baseline"])
        return "full" if added else "check"
    return "check" if settled(data) else "full"


def fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def change_packet(repo: Path, data: dict, subject: str) -> str:
    """The harness-written change-check brief: the fixes to verify and the diff since the last reviewed text."""
    baseline, current = data["baseline"], snapshot(repo, subject)
    pairs = [(subject, baseline, current)] if isinstance(current, str) else \
        [(name, baseline.get(name, ""), current.get(name, "")) for name in sorted(set(baseline) | set(current))
         if baseline.get(name, "") != current.get(name, "")]
    diff = "".join("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                                f"{name} (last reviewed)", f"{name} (current)"))
                   + ("" if after.endswith("\n") else "\n") for name, before, after in pairs)
    rounds = recorded(data)
    fixes = []
    if rounds:
        for item in rounds[-1]["findings"]:
            original = root(data, rounds[-1], item)[1] if item["decision"] == "duplicate" else item
            if original["decision"] == "accepted":
                fixes.append(f"#### {original['id']} ({original['severity']}) \u2014 {original['title']}\n\n"
                             f"{original.get('detail', '')}".rstrip())
    scope = ("whether these edits keep the document set coherent" if data["kind"] == "coherence"
             else f"whether these changes introduce a Blocker or Major defect in `{subject}` or break documents "
                  "that depend on it")
    marker = fence(diff)
    return "\n".join([
        "", "## Change check (written by the Playbook harness)", "",
        f"This round is a change check, not a full review. Report only (1) a listed fix that does not hold and "
        f"(2) {scope}. Do not report issues in unchanged text unless these changes make them wrong. "
        "Use your normal report format; write `None` when there are no findings.", "",
        "### Fixes to verify", "", "\n\n".join(fixes) if fixes else "None listed; check the changes only.", "",
        "### Changes since the last reviewed version", "", marker + "diff", diff.rstrip("\n"), marker, ""])


def resolve_subject(repo: Path, reviewer: str, text: str, context: str) -> str:
    """The single document (specialist) or feature (coherence) a reviewer task names."""
    def candidates(source: str) -> set:
        found = set()
        for raw in DOCUMENT_PATH.findall(source or ""):
            index = raw.find("docs/")
            path = Path(raw) if Path(raw).is_absolute() else Path(repo) / raw[index:]
            try:
                name = relative_path(repo, path)
            except ApprovalError:
                continue
            if document_type(Path(name)) is not None:
                found.add(name)
        return found

    for source in (text, context):
        names = candidates(source)
        if reviewer == COHERENCE:
            subjects = {"/".join(name.split("/")[:3]) for name in names if name.startswith("docs/features/")}
        else:
            subjects = {name for name in names if document_type(Path(name)) == SPECIALIST_TYPES[reviewer]}
        if len(subjects) == 1:
            return subjects.pop()
        if len(subjects) > 1:
            raise ApprovalError(f"{reviewer} task names several review subjects ({', '.join(sorted(subjects))}); "
                                "dispatch one reviewer per subject")
    want = "a feature document path (docs/features/<feature>/…)" if reviewer == COHERENCE \
        else f"exactly one repository-relative {SPECIALIST_TYPES[reviewer]} document path"
    raise ApprovalError(f"{reviewer} task must name {want} so the review round can be recorded")


def cycling(data: dict, since: Optional[str]) -> Optional[str]:
    """The first fixed issue that has come back too often since the developer's last answer, as a refusal."""
    for (number, fid, title), entries in returns(data).items():
        if len(entries) >= CYCLE_RETURNS and (since is None or entries[-1]["dispatchedAt"] >= since):
            return CYCLE_REFUSAL.format(subject=data["subject"], issue=f"{number}:{fid} ({title})", returns=len(entries))
    return None


def check_ready(repo: Path, data: dict, subject: str, since: Optional[str]) -> None:
    """Refuse another round until the previous one is recorded and decided, and while an issue is cycling."""
    ingest(data)
    pending = [entry for entry in data["rounds"] if entry["status"] == "pending"]
    if pending:
        entry = pending[0]
        raise ApprovalError(f"{subject}: round {entry['round']} has no recorded report"
                            + (f" ({entry['parseError']})" if entry.get("parseError") else "")
                            + "; wait for it, or void it with review_ledger and a reason")
    if undecided(data):
        raise ApprovalError(f"{subject}: decide every finding of earlier rounds with review_ledger before "
                            "another round: " + ", ".join(undecided(data)))
    stop = cycling(data, since)
    if stop:
        raise ApprovalError(stop)


def check_coherence_ready(repo: Path, feature: str) -> None:
    root_dir = ledger_path(repo, feature).parent
    ledgers = [load(repo, "docs/" + path.relative_to(Path(repo) / LEDGER_ROOT).with_suffix(".md").as_posix())
               for path in sorted(root_dir.rglob("*.json")) if path.name != "coherence.json"] if root_dir.is_dir() else []
    if not any(recorded(data) and data["subject"].endswith(("/system-design.md", "/tdd.md")) for data in ledgers):
        raise ApprovalError(f"{feature}: coherence runs when a system design or TDD is close to done; "
                            "no system design or TDD in this feature has a recorded review round yet")
    for data in ledgers:
        ingest(data)
        blocking = [f"{entry['round']}:{item['id']}" for entry, item in open_blocking(data)]
        if any(entry["status"] == "pending" for entry in data["rounds"]) or undecided(data) or blocking:
            raise ApprovalError(f"{feature}: coherence waits until {data['subject']} has no pending round, undecided "
                                "finding, or open blocking finding" + (f" ({', '.join(blocking)})" if blocking else ""))


def dispatch(repo: Path, reviewers: list, since: Optional[str], session_dir: Optional[str]) -> list:
    """Gate and record one round per reviewer task, choosing its mode; all or nothing."""
    plans, subjects = [], set()
    for task in reviewers:
        if task["reviewer"] != COHERENCE and task["reviewer"] not in SPECIALIST_TYPES:
            continue
        subject = resolve_subject(repo, task["reviewer"], task.get("text", ""), task.get("context", ""))
        if subject in subjects:
            raise ApprovalError(f"two reviewers dispatched for {subject} in one call")
        subjects.add(subject)
        data = load(repo, subject)
        check_ready(repo, data, subject, since)
        if task["reviewer"] == COHERENCE:
            check_coherence_ready(repo, subject)
        mode = next_mode(repo, data)
        if mode == "check" and data["baseline"] == snapshot(repo, subject):
            raise ApprovalError(f"{subject} has not changed since its last review, so there is nothing to check; "
                                "request a full review with review_ledger and a reason if one is needed")
        plans.append((task, subject, data, mode))
    results = []
    for task, subject, data, mode in plans:
        digest, lines = content_identity(repo, subject)
        packet = change_packet(repo, data, subject) if mode == "check" else None
        number = len(data["rounds"]) + 1
        agent = task.get("agentId")
        entry = {"round": number, "reviewer": task["reviewer"], "mode": mode, "agentId": agent,
                 "dispatchedAt": now(), "contentHash": digest, "lines": lines, "status": "pending",
                 "reportPath": str(Path(session_dir) / f"{agent}.md") if session_dir and agent else None,
                 "findings": []}
        if mode == "full" and data.get("fullRequested"):
            entry["fullReason"] = data["fullRequested"]["reason"]
        data["rounds"].append(entry)
        data.update(baseline=snapshot(repo, subject), fullRequested=None, closed=None)
        save(repo, data)
        results.append({"index": task.get("index"), "subject": subject, "round": number, "mode": mode,
                        "packet": packet})
    return results


def reconcile(repo: Path, rounds: list, session_dir: Optional[str]) -> None:
    """Bind recorded rounds to the reviewer ids OMP assigned, or drop rounds whose dispatch failed."""
    for item in rounds:
        data = load(repo, item["subject"])
        entry = next((entry for entry in data["rounds"] if entry["round"] == item["round"]), None)
        if entry is None or entry["status"] != "pending":
            continue
        if item.get("agentId") is None:
            data["rounds"].remove(entry)
        else:
            entry["agentId"] = item["agentId"]
            entry["reportPath"] = str(Path(session_dir) / f"{item['agentId']}.md") if session_dir else None
        save(repo, data)


def decide(repo: Path, subject: str, decisions: list) -> dict:
    data = load(repo, subject)
    ingest(data)
    if not decisions:
        raise ApprovalError("decide requires at least one decision")
    for change in decisions:
        entry, item = locate(data, change.get("finding"))
        decision, reason = change.get("decision"), (change.get("reason") or "").strip()
        evidence = (change.get("evidence") or "").strip() or None
        if decision not in DECISIONS:
            raise ApprovalError(f"{change.get('finding')}: decision must be one of {', '.join(DECISIONS)}")
        if not reason:
            raise ApprovalError(f"{change['finding']}: every decision needs a reason")
        if decision == "nit" and item["severity"] != "Minor":
            raise ApprovalError(f"{change['finding']}: only Minor findings can be passed as nits; "
                                f"a {item['severity']} finding is accepted, rejected, or a duplicate")
        duplicate_of = change.get("duplicateOf") if decision == "duplicate" else None
        if decision == "duplicate" and locate(data, duplicate_of)[1] is item:
            raise ApprovalError(f"{change['finding']}: a finding cannot duplicate itself")
        if decision == "accepted" and item["decision"] is not None \
                and root(data, entry, item)[1]["decision"] == "rejected" and not evidence:
            raise ApprovalError(f"{change['finding']}: was rejected; accepting it needs new evidence")
        item.update(decision=decision, reason=reason, duplicateOf=duplicate_of, evidence=evidence)
    data["closed"] = None
    save(repo, data)
    return data


def void(repo: Path, subject: str, number: int, reason: str) -> dict:
    data = load(repo, subject)
    ingest(data)
    entry = next((entry for entry in data["rounds"] if entry["round"] == number), None)
    if entry is None or entry["status"] != "pending":
        raise ApprovalError(f"{subject}: round {number} is not pending")
    if not (reason or "").strip():
        raise ApprovalError("void requires a reason")
    entry.update(status="void", voidReason=reason.strip())
    entry.pop("reportPath", None)
    entry.pop("parseError", None)
    save(repo, data)
    return data


def request_full(repo: Path, subject: str, reason: str) -> dict:
    data = load(repo, subject)
    if not (reason or "").strip():
        raise ApprovalError("a full review request needs a reason (the developer asked, or a strong reason such as "
                            "a sweeping change that could cascade)")
    data["fullRequested"] = {"reason": reason.strip(), "at": now()}
    save(repo, data)
    return data


def close(repo: Path, subject: str) -> dict:
    data = load(repo, subject)
    ingest(data)
    if not recorded(data):
        raise ApprovalError(f"{subject}: no recorded review round to close")
    if any(entry["status"] == "pending" for entry in data["rounds"]):
        raise ApprovalError(f"{subject}: a review round is still pending")
    if undecided(data):
        raise ApprovalError(f"{subject}: undecided findings: " + ", ".join(undecided(data)))
    blocking = open_blocking(data)
    if blocking:
        raise ApprovalError(f"{subject}: blocking findings need a fix and a change check: " + "; ".join(
            f"{entry['round']}:{item['id']} ({item['severity']}: {item['title']})" for entry, item in blocking))
    data["closed"] = {"hash": content_identity(repo, subject)[0], "round": recorded(data)[-1]["round"], "at": now()}
    save(repo, data)
    return data


def summary(repo: Path, data: dict, since: Optional[str]) -> dict:
    subject = data["subject"]
    exists = (Path(repo) / subject).exists()
    current_hash = content_identity(repo, subject)[0] if exists else None
    pending = [entry for entry in data["rounds"] if entry["status"] == "pending"]
    blocking = [f"{entry['round']}:{item['id']} ({item['severity']}: {item['title']})" for entry, item in open_blocking(data)]
    receipt = bool(data.get("closed")) and data["closed"]["hash"] == current_hash
    sizes = [entry["lines"] for entry in data["rounds"]]
    stopped = cycling(data, since)
    if pending:
        entry = pending[0]
        step = (f"void round {entry['round']} with a reason (report unusable: {entry['parseError']})"
                if entry.get("parseError") else f"wait for round {entry['round']}'s report ({entry.get('agentId')})")
    elif undecided(data):
        step = "decide findings: " + ", ".join(undecided(data))
    elif stopped:
        step = "stop and summarize for the developer: " + stopped.split(". Stop", 1)[0]
    elif not recorded(data):
        step = "dispatch a review"
    elif receipt:
        step = "closed on the current content"
    elif blocking:
        step = f"revise for the blocking findings, then dispatch a {next_mode(repo, data) if exists else 'full'} review"
    else:
        step = "apply accepted Minor findings, then close"
    return {
        "subject": subject, "kind": data["kind"], "ledger": ledger_path(repo, subject).relative_to(repo).as_posix(),
        "rounds": [{"round": entry["round"], "mode": entry.get("mode", "full"), "reviewer": entry["reviewer"],
                    "agentId": entry.get("agentId"), "status": entry["status"], "lines": entry["lines"],
                    "findings": len(entry.get("findings", [])),
                    **({"fullReason": entry["fullReason"]} if entry.get("fullReason") else {}),
                    **({"voidReason": entry["voidReason"]} if entry.get("voidReason") else {})}
                   for entry in data["rounds"]],
        "nextMode": next_mode(repo, data) if exists else None,
        "fullRequested": data.get("fullRequested"),
        "undecided": undecided(data),
        "openBlocking": blocking,
        "recurring": [f"{number}:{fid} {title} \u2014 returned {len(entries)} time(s)"
                      for (number, fid, title), entries in returns(data).items()],
        "rejected": [f"{entry['round']}:{item['id']} {item['title']} \u2014 {item['reason']}"
                     for entry in recorded(data) for item in entry["findings"] if item["decision"] == "rejected"],
        "growth": f"{sizes[0]} -> {sizes[-1]} lines over {len(sizes)} rounds" if sizes else None,
        "receiptCurrent": receipt,
        "next": step,
    }


def receipt(repo: Path, subject: str) -> tuple:
    """(True, evidence) when the ledger is closed on the current content, else (False, next step)."""
    data = load(repo, subject)
    state = summary(repo, data, None)
    if not state["receiptCurrent"]:
        if data.get("closed"):
            return False, "the document changed after its review ledger was closed; review or close it again"
        return False, "review ledger not closed: " + state["next"]
    counts = {decision: 0 for decision in DECISIONS}
    for entry in recorded(data):
        for item in entry["findings"]:
            counts[item["decision"]] += 1
    total = sum(counts.values())
    return True, (f"Review ledger closed at round {data['closed']['round']}: {total} findings decided ("
                  + ", ".join(f"{count} {name}" for name, count in counts.items()) + ").")
