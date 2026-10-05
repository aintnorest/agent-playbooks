"""Black-box contracts for content-bound document approvals."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "scripts" / "doc-approval.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from doc_approvals import body_sha256, document_type  # noqa: E402
SAMPLES = [
    ("docs/product-vision.md", "vision-r1", True),
    ("docs/architecture.md", "arch-r1", True),
    ("docs/features/example/prd.md", "prd-r1", True),
    ("docs/features/example/system-design.md", "sd-r1", True),
    ("docs/features/example/tdd.md", "tdd-r1", False),
    ("docs/features/example/implementation-plan.md", "plan-r1", False),
    ("docs/features/example/slices/first/tdd.md", "tdd-r1", False),
    ("docs/features/example/slices/first/implementation-plan.md", "plan-r1", False),
    ("guides/example.md", None, False),
    ("docs/roadmap.md", None, False),
]


class DocApprovalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook approvals ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / "docs" / "agent-approvals.json"

    def document(self, relative, revision=None, body="# Document\n", state="draft"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        revision_line = "revision: " + revision + "\n" if revision else ""
        path.write_bytes(("---\nstate: " + state + "\n" + revision_line + "---\n").encode() + body.encode())
        return path

    def run_cli(self, mode, *args, cwd=None, program=PROGRAM):
        return subprocess.run([sys.executable, str(program), mode, "--repo", str(self.root), *args],
                              cwd=cwd, capture_output=True, text=True, check=False, timeout=10)

    def successful(self, mode, *args):
        result = self.run_cli(mode, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def status(self, relative):
        return self.successful("--status", "--path", relative)[0]

    def close_review(self, relative):
        """A ledger closed on the document's current body, as review_ledger close would leave it."""
        digest = body_sha256((self.root / relative).read_bytes(), document_type(Path(relative)))
        ledger = self.root / ".playbook/reviews" / (relative[len("docs/"):-len(".md")] + ".json")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps({"version": 1, "subject": relative, "kind": "document", "closed": {
            "hash": digest, "round": 1, "at": "2026-10-05T00:00:00.000Z"}, "rounds": [{
            "round": 1, "reviewer": "review-doc-technical-design-agent", "agentId": "Review",
            "dispatchedAt": "2026-10-05T00:00:00.000Z", "contentHash": digest, "lines": 1, "status": "recorded",
            "findings": [{"id": "R1-F1", "severity": "Major", "title": "Gap", "decision": "rejected",
                          "reason": "Out of scope.", "duplicateOf": None, "evidence": None}]}]}))

    def accept(self, relative):
        self.close_review(relative)
        return self.successful("--accept", "--path", relative)

    def approve(self, relative):
        manifest = self.root / "docs/user-approvals.json"
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        data[relative] = hashlib.sha256((self.root / relative).read_bytes().split(b"---\n", 2)[2]).hexdigest()
        manifest.write_text(json.dumps(data))

    def test_accept_is_stably_formatted(self):
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        self.accept(relative)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(self.manifest.read_text(), json.dumps(data, indent=2, sort_keys=True) + "\n")

    def test_accept_refuses_every_developer_gate_without_writing(self):
        self.manifest.parent.mkdir()
        self.manifest.write_text("{}\n")
        for relative, revision, developer_gated in SAMPLES:
            if not developer_gated:
                continue
            with self.subTest(path=relative):
                document = self.document(relative, revision)
                before = (document.read_bytes(), self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns)
                result = self.run_cli("--accept", "--path", relative)
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"status": "refused", "reason": "developer-gated"})
                self.assertEqual(result.stderr, "")
                self.assertEqual((document.read_bytes(), self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns), before)

    def test_accept_refusal_does_not_initialize_repository(self):
        self.document("docs/product-vision.md", "vision-r1")
        result = self.run_cli("--accept", "--path", "docs/product-vision.md")
        self.assertEqual(result.returncode, 3)
        self.assertFalse(self.manifest.exists())

    def test_body_edit_invalidates_but_frontmatter_state_edit_does_not(self):
        relative = "docs/features/example/tdd.md"
        path = self.document(relative, "tdd-r1")
        original = path.read_bytes()
        self.accept(relative)
        entry = json.loads(self.manifest.read_text())[relative]
        self.assertEqual(entry, {"hash": hashlib.sha256(b"# Document\n").hexdigest(), "evidence":
                                 "Review ledger closed at round 1: 1 findings decided (0 accepted, 1 rejected, 0 nit, 0 duplicate)."})
        self.assertTrue(self.status(relative)["approved"])
        for state in (b"active", b"done", b"superseded"):
            path.write_bytes(original.replace(b"state: draft", b"state: " + state))
            self.assertTrue(self.status(relative)["approved"])
        path.write_bytes(path.read_bytes() + b"Changed body.\n")
        self.assertEqual(self.status(relative)["reason"], "hash mismatch")
        self.assertFalse(self.status(relative)["approved"])

    def test_exact_body_bytes_include_line_endings_and_trailing_whitespace(self):
        relative = "docs/features/example/tdd.md"
        path = self.document(relative, "tdd-r1")
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.accept(relative)
        entry = json.loads(self.manifest.read_text())[relative]
        self.assertEqual(entry["hash"], hashlib.sha256(b"# Document\r\n").hexdigest())
        path.write_bytes(path.read_bytes().replace(b"# Document\r\n", b"# Document \r\n"))
        self.assertEqual(self.status(relative)["reason"], "hash mismatch")

    def test_revision_bump_does_not_invalidate_body_approval(self):
        relative = "docs/features/example/tdd.md"
        path = self.document(relative, "tdd-r1")
        self.accept(relative)
        path.write_bytes(path.read_bytes().replace(b"tdd-r1", b"tdd-r2"))
        self.assertIsNone(self.status(relative)["reason"])
        self.assertTrue(self.status(relative)["approved"])

    def test_plan_assignment_lines_match_checker_plain_label_grammar(self):
        relative = "docs/features/example/implementation-plan.md"
        body = "### T1 — Implement\n- Depends on: none\n- Targets: none\n- Change: Implement.\n- Done when: Complete.\n- Verify: true\n"
        path = self.document(relative, "plan-r1", body)
        self.accept(relative)
        original = path.read_bytes()
        for ending in (b"\n", b"\r\n"):
            path.write_bytes(original + b"- Assigned worktree: /tmp/worktree" + ending
                             + b"- Assigned branch: impl/T1" + ending)
            self.assertTrue(self.status(relative)["approved"])
        path.write_bytes(path.read_bytes().replace(b"impl/T1", b"impl/changed"))
        self.assertTrue(self.status(relative)["approved"])
        path.write_bytes(original + b"- **Assigned branch:** impl/T1\n")
        self.assertEqual(self.status(relative)["reason"], "hash mismatch")
        path.write_bytes(original.replace(b"Implement.", b"Change behavior."))
        self.assertEqual(self.status(relative)["reason"], "hash mismatch")

    def test_developer_approval_records_and_documents_are_unchanged(self):
        for relative, revision, developer_gated in SAMPLES:
            if not developer_gated:
                continue
            with self.subTest(path=relative):
                path = self.document(relative, revision)
                before = path.read_bytes()
                self.approve(relative)
                entry = json.loads((self.root / "docs/user-approvals.json").read_text())[relative]
                self.assertEqual(entry, hashlib.sha256(b"# Document\n").hexdigest())
                self.assertEqual(path.read_bytes(), before)
                self.assertTrue(self.status(relative)["approved"])

    def test_agent_entry_extra_field_is_malformed(self):
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        self.accept(relative)
        data = json.loads(self.manifest.read_text())
        data[relative]["extra"] = "unexpected"
        self.manifest.write_text(json.dumps(data))
        before = self.manifest.read_bytes()
        result = self.run_cli("--status")
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/agent-approvals.json", result.stderr)
        self.assertIn(relative, result.stderr)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_user_file_tdd_key_is_malformed(self):
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        (self.root / "docs/user-approvals.json").write_text(json.dumps({relative: "a" * 64}))
        result = self.run_cli("--status")
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/user-approvals.json", result.stderr)
        self.assertIn(relative, result.stderr)

    def test_invalid_hashes_and_gate_types_fail_closed(self):
        self.document("docs/product-vision.md", "vision-r1")
        user = self.root / "docs/user-approvals.json"
        for data in ([], {"docs/product-vision.md": "a" * 63},
                     {"docs/product-vision.md": "A" * 64},
                     {"docs/roadmap.md": "a" * 64},
                     {"guides/example.md": "a" * 64}):
            user.write_text(json.dumps(data))
            result = self.run_cli("--status")
            self.assertEqual(result.returncode, 1)
            self.assertIn("docs/user-approvals.json", result.stderr)
            self.assertEqual(result.stdout, "")
        user.unlink()
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        for entry in ({"hash": "a" * 64}, {"hash": "a" * 64, "evidence": " "},
                      {"hash": "g" * 64, "evidence": "Checks passed."}):
            self.manifest.write_text(json.dumps({relative: entry}))
            result = self.run_cli("--status")
            self.assertEqual(result.returncode, 1)
            self.assertIn(relative, result.stderr)
            self.assertIn("docs/agent-approvals.json", result.stderr)

    def test_hash_is_paste_ready_and_read_only(self):
        relative = "docs/product-vision.md"
        path = self.document(relative, "vision-r1")
        before = path.read_bytes()
        digest = hashlib.sha256(b"# Document\n").hexdigest()
        self.assertEqual(self.successful("--hash", "--path", relative),
                         {"status": "hash", "path": relative, "hash": digest,
                          "line": f'"{relative}": "{digest}",'})
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(self.manifest.exists())
        self.assertFalse((self.root / "docs/user-approvals.json").exists())

    def test_hash_without_path_lists_current_developer_gated_entries(self):
        vision, architecture, prd, design = (path for path, _, gated in SAMPLES if gated)
        for relative, revision, _ in SAMPLES:
            self.document(relative, revision)
        self.approve(vision)
        self.approve(architecture)
        self.document(architecture, "arch-r1", "# Changed\n")
        self.document(design, "sd-r1", state="superseded")
        manifest = self.root / "docs/user-approvals.json"
        before = manifest.read_bytes()

        def entry(relative, approved, reason):
            digest = hashlib.sha256((self.root / relative).read_bytes().split(b"---\n", 2)[2]).hexdigest()
            return {"path": relative, "hash": digest, "line": f'"{relative}": "{digest}",',
                    "approved": approved, "reason": reason}

        self.assertEqual(self.successful("--hash"), {"status": "hashes", "entries": [
            entry(architecture, False, "hash mismatch"),
            entry(prd, False, "missing"),
            entry(vision, True, None),
        ]})
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse(self.manifest.exists())

    def test_hash_non_document_starting_with_frontmatter_marker_uses_raw_bytes(self):
        relative = "notes.txt"
        path = self.root / relative
        content = b"---\nnot document frontmatter\nraw bytes\n"
        path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(self.successful("--hash", "--path", relative),
                         {"status": "hash", "path": relative, "hash": digest,
                          "line": f'"{relative}": "{digest}",'})
        self.assertEqual(path.read_bytes(), content)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_guides_and_roadmap_are_ungated_without_revisions(self):
        for relative in ("guides/example.md", "docs/roadmap.md", "templates/roadmap.md"):
            with self.subTest(path=relative):
                path = self.document(relative, state="active")
                if relative.startswith("guides/"):
                    path.write_bytes(path.read_bytes().replace(b"state: active\n", b"state: active\napproved: 2026-10-02\n"))
                row = self.status(relative)
                self.assertEqual(row["gate"], "none")
                self.assertFalse(row["approved"])
                self.assertEqual(row["reason"], "missing")
                result = self.run_cli("--accept", "--path", relative)
                self.assertEqual(result.returncode, 3)
                self.assertEqual(json.loads(result.stdout), {"status": "refused", "reason": "ungated"})
                self.assertFalse(self.manifest.exists())

    def test_revoke_is_agent_only_and_idempotent(self):
        for relative, revision, developer_gated in SAMPLES:
            self.document(relative, revision)
            if developer_gated or not revision:
                result = self.run_cli("--revoke", "--path", relative, "--reason", "Review reopened.")
                self.assertEqual(result.returncode, 3)
                self.assertEqual(json.loads(result.stdout), {"status": "refused",
                    "reason": "developer-gated" if developer_gated else "ungated"})
                continue
            self.accept(relative)
            for status in ("revoked", "unchanged"):
                self.assertEqual(self.successful("--revoke", "--path", relative, "--reason", "Review reopened."),
                                 {"status": status, "path": relative})
            self.assertNotIn(relative, json.loads(self.manifest.read_text()))

    def test_malformed_approvals_fail_closed_and_preserve_bytes(self):
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        invalid = ['{', '[]', '{"unknown": {}}', '{"x": 1, "x": 2}',
                   '{"docs/features/example/tdd.md": {}}']
        for text in invalid:
            self.manifest.write_text(text, encoding="utf-8")
            for mode, extra in (("--status", []),
                                ("--accept", ["--path", relative]),
                                ("--revoke", ["--path", relative, "--reason", "Review reopened."])):
                with self.subTest(text=text, mode=mode):
                    result = self.run_cli(mode, *extra)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("approval", result.stderr)
                    self.assertEqual(self.manifest.read_text(), text)

    def test_status_lists_documents_and_uses_repo_not_caller_cwd(self):
        for relative, revision, _ in SAMPLES:
            self.document(relative, revision)
        result = self.run_cli("--status", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["path"] for row in json.loads(result.stdout)], sorted(s[0] for s in SAMPLES))
        self.close_review("docs/features/example/tdd.md")
        result = self.run_cli("--accept", "--path", "docs/features/example/tdd.md", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("--status", "--path", str(self.root / "docs/features/example/tdd.md"), cwd=ROOT)
        self.assertTrue(json.loads(result.stdout)[0]["approved"])

    def test_path_escape_and_free_text_evidence_are_rejected_without_writes(self):
        self.document("docs/features/example/tdd.md", "tdd-r1")
        for args in (("--path", "../docs/features/example/tdd.md"),
                     ("--path", "docs/features/example/tdd.md", "--evidence", "Checks passed."),
                     ("--path", "docs/features/example/tdd.md", "--migrated-from", " ")):
            result = self.run_cli("--accept", *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse(self.manifest.exists())

    def test_accept_requires_a_review_ledger_closed_on_the_current_body(self):
        relative = "docs/features/example/tdd.md"
        path = self.document(relative, "tdd-r1")
        refused = self.run_cli("--accept", "--path", relative)
        self.assertEqual(refused.returncode, 3, refused.stderr)
        self.assertEqual(json.loads(refused.stdout)["reason"], "review-not-closed")
        self.close_review(relative)
        path.write_bytes(path.read_bytes().replace(b"# Document", b"# Changed after review"))
        refused = self.run_cli("--accept", "--path", relative)
        self.assertEqual(refused.returncode, 3, refused.stderr)
        self.assertIn("changed after", json.loads(refused.stdout)["message"])
        self.assertFalse(self.manifest.exists())
        self.close_review(relative)
        self.assertEqual(self.successful("--accept", "--path", relative)["status"], "accepted")

    def test_migration_acceptance_records_its_date_without_a_ledger(self):
        relative = "docs/features/example/tdd.md"
        self.document(relative, "tdd-r1")
        self.successful("--accept", "--path", relative, "--migrated-from", "2026-08-01")
        self.assertEqual(json.loads(self.manifest.read_text())[relative]["evidence"], "migrated from approved: 2026-08-01")

    def test_status_creates_no_project_or_install_files_including_bytecode(self):
        install = self.root / "install" / "scripts"
        install.mkdir(parents=True)
        for name in ("doc-approval.py", "doc_approvals.py", "review_ledgers.py"):
            shutil.copyfile(ROOT / "scripts" / name, install / name)
        self.document("docs/features/example/tdd.md", "tdd-r1")

        def snapshot():
            return {str(path.relative_to(self.root)): (
                        path.read_bytes() if path.is_file() else None, path.stat().st_mtime_ns)
                    for path in [self.root, *self.root.rglob("*")]}

        before = snapshot()
        environment = os.environ.copy()
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        environment.pop("PYTHONPYCACHEPREFIX", None)
        for args in ([], ["--path", "docs/features/example/tdd.md"]):
            result = subprocess.run([sys.executable, str(install / "doc-approval.py"), "--status",
                                     "--repo", str(self.root), *args], capture_output=True,
                                    text=True, check=False, env=environment, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(snapshot(), before)
            self.assertFalse((install / "__pycache__").exists())
            self.assertFalse(self.manifest.exists())


if __name__ == "__main__":
    unittest.main()
