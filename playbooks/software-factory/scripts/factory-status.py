#!/usr/bin/env python3
"""Report the document-derived software factory state without changing the repository."""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_approvals import (ApprovalError, approval_status, document_type,
                           load_approval_files, split_frontmatter)

VISION = "docs/product-vision.md"
ARCHITECTURE = "docs/architecture.md"
RUNNING = "Implementation, review, or developer validation in progress."
CHOOSE = "Choose the next feature or proof-of-concept scope with the developer, offering the roadmap's Now and Next items, then create its PRD at docs/features/<feature>/prd.md."


def slice_order(repo: Path, feature: str, documents: dict) -> tuple:
    """Read the system design's slice list, not incidental earlier slice references."""
    base = "docs/features/" + feature
    directory = repo / base / "slices"
    names = sorted(path.name for path in directory.iterdir() if path.is_dir()) if directory.is_dir() else []
    design = base + "/system-design.md"
    if design not in documents:
        return [base + "/slices/" + name for name in names], len(names) > 1
    body = split_frontmatter((repo / design).read_bytes())[1].decode("utf-8")
    sections = []
    lines = body.splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if not heading or not re.search(r"\bslices?\b|\b(?:build|implementation|delivery) order\b", heading[2], re.I):
            continue
        depth = len(heading[1])
        end = index + 1
        while end < len(lines):
            closing = re.match(r"^(#{1,6})\s", lines[end])
            if closing and len(closing[1]) <= depth:
                break
            end += 1
        priority = 0 if "order" in heading[2].lower() else 1
        sections.append((priority, index, lines[index + 1:end]))
    for _, _, section in sorted(sections):
        ordered = []
        for line in section:
            # Ordered/bulleted lists, slice tables, and per-slice subheadings.
            if not re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||#{1,6}\s)", line):
                continue
            references = re.findall(r"\bslices/([A-Za-z0-9][A-Za-z0-9_-]*)(?=/|\b)", line)
            if not references:
                references = [name for name in names
                              if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(name) + r"(?![A-Za-z0-9_-])", line)]
            if not references:
                identifier = re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s|\|\s*(?:\d+\s*\|\s*)?|#{1,6}\s)(?:\*\*|`)?(\d+[A-Za-z0-9_-]*-[A-Za-z0-9_-]+)", line)
                if identifier:
                    references = [identifier[1]]
            for name in references:
                if name not in ordered:
                    ordered.append(name)
        if ordered:
            extras = [name for name in names if name not in ordered]
            return [base + "/slices/" + name for name in ordered + extras], bool(extras)
    return [base + "/slices/" + name for name in names], bool(names)


def notes_hint(repo: Path, name: str) -> str:
    """Name the feature notes section for a document that does not exist yet."""
    parts = name.split("/")
    if len(parts) < 4 or parts[:2] != ["docs", "features"]:
        return ""
    base = "/".join(parts[:3])
    target = "/".join(parts[3:])
    notes = repo / base / "notes.md"
    if not notes.is_file():
        return ""
    heading = re.compile(r"##[ \t]+(`?)" + re.escape(target) + r"\1[ \t]*")
    # Notes are ungated source material; undecodable bytes must not fail status.
    if not any(heading.fullmatch(line) for line in notes.read_bytes().decode("utf-8", "replace").splitlines()):
        return ""
    return " Source material: the " + target + " section of " + base + "/notes.md."


def factory_status(repo: Path) -> dict:
    if not (repo / "docs" / "user-approvals.json").exists():
        return {"optedIn": False}
    approvals = load_approval_files(repo)
    documents = {}
    for path in sorted((repo / "docs").rglob("*.md")):
        name = path.relative_to(repo).as_posix()
        if document_type(Path(name)) is None:
            continue
        fields, _ = split_frontmatter(path.read_bytes())
        state = fields.get("state")
        if state not in ("draft", "active", "done", "superseded"):
            raise ApprovalError("invalid document state: " + name)
        approval = approval_status(repo, Path(name), approvals)
        documents[name] = {"path": name, "type": approval["type"], "state": state,
                           "approved": approval["approved"], "gate": approval["gate"]}

    def present(name):
        return name in documents and documents[name]["state"] != "superseded"

    def done(name):
        return present(name) and documents[name]["state"] == "done"

    features = sorted({Path(name).parts[2] for name in documents
                       if name.startswith("docs/features/")})
    work = []
    orders = {}
    needs_design = set()
    for feature in features:
        base = "docs/features/" + feature
        slices, fallback = slice_order(repo, feature, documents)
        if present(base + "/system-design.md") or len(slices) > 1:
            needs_design.add(feature)
        # A feature-level TDD/plan is the single slice. A later fix can live in slices/.
        if (present(base + "/tdd.md") or present(base + "/implementation-plan.md")
                or (not slices and not present(base + "/system-design.md"))):
            slices.insert(0, base)
        orders[feature] = (slices, fallback)
        descendants = [row for name, row in documents.items()
                       if name.startswith(base + "/") and row["type"] in ("system-design", "tdd", "implementation-plan")]
        if ((present(base + "/prd.md") and not done(base + "/prd.md"))
                or any(row["state"] not in ("done", "superseded") for row in descendants)):
            work.append(feature)

    feature = work[0] if len(work) == 1 else None
    current = None
    fallback = False
    if feature:
        slices, fallback = orders[feature]
        current = next((path for path in slices
                        if not (done(path + "/tdd.md") and done(path + "/implementation-plan.md"))), None)
    gates = {name for name, row in documents.items() if row["gate"] != "none" and not row["approved"]}

    # Existing downstream documents imply missing prerequisites even if the first
    # missing gate is earlier than the currently selected feature or slice.
    for name, row in documents.items():
        if row["gate"] == "none" or row["state"] == "superseded":
            continue
        ancestors = []
        if name != VISION:
            ancestors.append(VISION)
        if name.startswith("docs/features/"):
            base = "/".join(name.split("/")[:3])
            ancestors.append(ARCHITECTURE)
            if row["type"] != "prd":
                ancestors.append(base + "/prd.md")
            if "/slices/" in name and Path(base).name in needs_design:
                ancestors.append(base + "/system-design.md")
            if row["type"] == "implementation-plan":
                ancestors.append(str(Path(name).with_name("tdd.md")))
        gates.update(path for path in ancestors if not present(path))

    def step(name):
        if not present(name):
            gates.add(name)
            return "Create " + name + "." + notes_hint(repo, name)
        if not documents[name]["approved"]:
            gate = documents[name]["gate"]
            action = "developer approval" if gate == "developer" else "agent acceptance"
            return "Review " + name + " and obtain " + action + "."
        return None

    ambiguity = None
    next_step = step(VISION) or step(ARCHITECTURE)
    if len(work) > 1:
        ambiguity = "Multiple features have unfinished work: " + ", ".join(work) + "."
        if next_step is None:
            next_step = "Choose the feature to continue with the developer: " + ", ".join(work) + "."
    elif next_step is None and feature:
        base = "docs/features/" + feature
        next_step = step(base + "/prd.md")
        if next_step is None and feature in needs_design:
            next_step = step(base + "/system-design.md")
            if next_step is None and not orders[feature][0]:
                next_step = "Define the slice list in " + base + "/system-design.md before creating a technical design."
        if next_step is None and current:
            next_step = step(current + "/tdd.md") or step(current + "/implementation-plan.md") or RUNNING
        if next_step is None:
            next_step = "Mark " + base + "/prd.md and its system design, if present, done after all slices have developer validation."
    if next_step is None:
        next_step = CHOOSE
    if fallback and feature:
        next_step += " Slice order could not be fully parsed from the system design; using lexical order of slice directories for unlisted slices."
    return {"optedIn": True, "feature": feature, "currentSlice": current,
            "documents": list(documents.values()), "openGates": sorted(gates),
            "nextStep": next_step, "ambiguity": ambiguity}


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args(arguments)
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ApprovalError("--repo must name an existing directory")
        result = factory_status(repo)
    except (ApprovalError, OSError, UnicodeError) as error:
        print("factory-status: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
