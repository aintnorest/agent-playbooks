"""CLI contracts for Playbook document status frontmatter."""
import git_test_environment  # Scrub inherited Git hook state before fixture creation.

import json
import os
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check-doc-status.py"


class CheckDocStatusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook status ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/user-approvals.json").write_text("{}")
    def path(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def approve(self, path, repo=None):
        repo = repo or self.root
        agent = path.name in ("tdd.md", "implementation-plan.md")
        manifest = repo / ("docs/agent-approvals.json" if agent else "docs/user-approvals.json")
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        body = path.read_bytes().split(b"---\n", 2)[2]
        digest = hashlib.sha256(body).hexdigest()
        entry = {"hash": digest, "evidence": "Review loop concluded and checks passed."} if agent else digest
        data[path.relative_to(repo).as_posix()] = entry
        manifest.write_text(json.dumps(data))


    def run_checker(self, mode, *paths):
        return subprocess.run([sys.executable, str(CHECKER), mode, *(str(path) for path in paths)],
                              capture_output=True, text=True, check=False)

    def assert_error(self, path, body, message):
        result = self.run_checker("--check", self.path(path, body))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(message, result.stderr)

    def test_valid_document_types_and_json_rows(self):
        samples = [
            ("docs/product-vision.md", "vision", "vision", "active"),
            ("docs/architecture.md", "architecture", "arch", "active"),
            ("docs/features/search/prd.md", "prd", "prd", "draft"),
            ("docs/features/search/system-design.md", "system-design", "sd", "done"),
            ("docs/features/search/tdd.md", "tdd", "tdd", "draft"),
            ("docs/features/search/implementation-plan.md", "implementation-plan", "plan", "done"),
            ("docs/features/search/slices/browse/tdd.md", "tdd", "tdd", "done"),
            ("docs/features/search/slices/browse/implementation-plan.md", "implementation-plan", "plan", "active"),
        ]
        paths = []
        for relative, kind, prefix, state in samples:
            path = self.path(relative, f"---\nstate: {state}\nrevision: {prefix}-r12\n---\n"
                             "# Document\n\n## Status\n\nDetails about the document.\n")
            paths.append(path)
            if state in ("active", "done"):
                self.approve(path)
        paths.extend([
            self.path("docs/roadmap.md", "---\nstate: draft\n---\n# Roadmap\n"),
            self.path("templates/roadmap.md", "---\nstate: draft\n---\n# Roadmap\n"),
            self.path("guides/example.md", "---\nstate: active\napproved: 2025-01-01\n---\n"
                      "## Status\nUsage notes.\n"),
        ])
        checked = self.run_checker("--check", *paths)
        self.assertEqual((checked.returncode, checked.stdout, checked.stderr), (0, "", ""))
        result = self.run_checker("--json", *paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual([row["type"] for row in rows],
                         [s[1] for s in samples] + ["roadmap", "roadmap", "guide"])
        self.assertEqual(rows[5], {"path": str(paths[5]), "type": "implementation-plan",
                                   "state": "done", "revision": "plan-r12",
                                   "approval": {"gate": "agent", "valid": True}})
        self.assertIsNone(rows[-1]["revision"])
        self.assertEqual(rows[-1]["approval"],
                         {"gate": "none", "valid": False})

    def test_missing_state_unknown_state_and_missing_revision(self):
        self.assert_error("docs/product-vision.md", "---\nrevision: vision-r1\n---\n", "missing state")
        self.assert_error("docs/features/a/prd.md", "---\nstate: approved\nrevision: prd-r1\n---\n",
                          "invalid state for prd")
        self.assert_error("docs/architecture.md", "---\nstate: draft\n---\n", "missing revision")

    def test_approval_date_state_rules_and_calendar(self):
        self.assert_error("docs/features/a/tdd.md", "---\nstate: draft\nrevision: tdd-r1\n"
                          "approved: 2024-01-01\n---\n", "guides/migrations/0.1.0-to-1.0.0.md")
        self.assert_error("docs/features/a/implementation-plan.md", "---\nstate: done\n"
                          "revision: plan-r1\n---\n", "valid approval required")
        self.assert_error("docs/product-vision.md", "---\nstate: approved\n"
                          "revision: vision-r1\n---\n", "invalid state for vision")
        self.assert_error("guides/help.md", "---\nstate: active\napproved: 2023-02-29\n---\n"
                          "## Status\nDetails.\n", "real calendar date")
        roadmap = self.path("docs/roadmap.md", "---\nstate: active\n---\n")
        self.assertEqual(self.run_checker("--check", roadmap).returncode, 0)
        guide = self.path("guides/process.md", "---\nstate: active\napproved: 2025-01-01\n---\n"
                          "## Status\nProcess details.\n")
        self.assertEqual(self.run_checker("--check", guide).returncode, 0)

    def test_migrated_active_prd_requires_current_body_approval(self):
        path = self.path("docs/features/a/prd.md", "---\nstate: active\nrevision: prd-r1\n---\n"
                         "# PRD\nApproved content.\n")
        self.approve(path)
        self.assertEqual(self.run_checker("--check", path).returncode, 0)
        path.write_bytes(path.read_bytes() + b"Editorial change.\n")
        result = self.run_checker("--check", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("hash mismatch", result.stderr)
        path.write_text(path.read_text().replace("prd-r1", "prd-r2"))
        result = self.run_checker("--check", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("hash mismatch", result.stderr)

    def test_malformed_approval_manifest_is_a_json_diagnostic(self):
        path = self.path("docs/features/a/prd.md", "---\nstate: active\nrevision: prd-r1\n---\nBody.\n")
        (self.root / "docs/user-approvals.json").write_text('{')
        result = self.run_checker("--json", path)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["rows"][0]["approval"]["valid"])
        self.assertIn("malformed approvals JSON", payload["errors"][0]["message"])

    def test_revision_and_path_boundaries(self):
        self.assert_error("docs/features/a/slices/b/prd.md", "---\nstate: draft\nrevision: prd-r1\n---\n",
                          "unknown document path/type")
        self.assert_error("docs/features/a/tdd.md", "---\nstate: draft\nrevision: plan-r1\n---\n",
                          "expected tdd-r<N>")
        self.assert_error("docs/features/a/tdd.md", "---\nstate: draft\nrevision: tdd-r0\n---\n",
                          "expected tdd-r<N>")
        self.assert_error("docs/roadmap.md", "---\nstate: draft\nrevision: roadmap-r1\n---\n",
                          "revision is forbidden")
        self.assert_error("guides/help.md", "---\nstate: draft\n---\n## Status\nDetails.\n",
                          "invalid state for guide")

    def test_legacy_status_is_actionable_and_fenced_fake_headings_are_skipped(self):
        body = "# Title\n\n```markdown\n## Status\n- State: Approved\n```\n"
        path = self.path("guides/no-status.md", body)
        self.assertEqual(self.run_checker("--check", path).returncode, 0)
        self.assertEqual(json.loads(self.run_checker("--json", path).stdout), [])
        self.assert_error("guides/old.md", body + "## Status\n- State: Active\n",
                          "legacy Status key line")
        self.assert_error("docs/features/a/prd.md", "# PRD\n## Status\nApproved.\n",
                          "missing status frontmatter")
        self.assert_error("guides/restated.md", "---\nstate: active\napproved: 2025-01-01\n"
                          "---\n## Status\nActive.\n", "Status prose restates state")
        self.assertEqual(self.run_checker("--check", self.path("guides/fenced.md", "---\n"
                          "state: active\napproved: 2025-01-01\n---\n## Status\n"
                          "```md\n- State: Active\n```\nPurpose and history.\n")).returncode, 0)

    def test_unclosed_guide_frontmatter_without_status_is_reported(self):
        self.assert_error("guides/process.md", "---\nstate: active\napproved: 2025-01-01\n",
                          "frontmatter is not closed")
        self.assertEqual(self.run_checker("--check", self.path(
            "guides/thematic-break.md", "---\n# Unrelated guide\n\nSome prose.\n"
        )).returncode, 0)

    def test_malformed_frontmatter_duplicate_unknown_nested_and_order(self):
        for body, expected in [
            ("---\nstate: draft\nstate: draft\nrevision: tdd-r1\n---\n", "duplicate frontmatter key"),
            ("---\nstate: draft\nrevision: tdd-r1\nowner: team\n---\n", "unknown frontmatter key"),
            ("---\nstate: draft\nrevision:\n  value: tdd-r1\n---\n", "invalid frontmatter"),
            ("---\nrevision: tdd-r1\nstate: draft\n---\n", "out of order"),
            ("---\nstate: draft\nrevision: tdd-r1\n", "frontmatter is not closed"),
        ]:
            with self.subTest(expected=expected):
                self.assert_error("docs/features/a/tdd.md", body, expected)

    def test_multiple_paths_read_error_and_json_error_shape(self):
        valid = self.path("docs/roadmap.md", "---\nstate: draft\n---\n")
        invalid = self.path("docs/architecture.md", "---\nstate: active\nrevision: arch-r2\n---\n")
        missing = self.root / "docs" / "product-vision.md"
        result = self.run_checker("--json", valid, invalid, missing)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read document", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([row["path"] for row in payload["rows"]], [str(valid), str(invalid)])
        self.assertEqual([error["path"] for error in payload["errors"]], [str(invalid), str(missing)])
        self.assertIn("cannot read document", payload["errors"][-1]["message"])

    def git(self, repo, *args):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def repository(self, label):
        repo = self.root / label
        repo.mkdir()
        self.git(repo, "init", "-q")
        return repo

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.org",
                 "commit", "-qm", "snapshot", "--allow-empty")
        return self.git(repo, "rev-parse", "HEAD")

    def snapshot(self, repo, relative, state, revision, body="Original body.\n"):
        file = repo / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f"---\nstate: {state}\nrevision: {revision}\n---\n{body}", encoding="utf-8")
        if state in ("active", "done"):
            self.approve(file, repo)
        return file

    def frozen(self, repo, base, head, *extra):
        return subprocess.run([sys.executable, str(CHECKER), "--frozen-diff",
                               "--repo", str(repo), "--base", base, "--head", head,
                               *extra], capture_output=True, text=True, check=False)

    def test_frozen_done_documents_reject_mutation_deletion_and_rename(self):
        documents = [("prd.md", "prd-r1"), ("tdd.md", "tdd-r1"),
                     ("implementation-plan.md", "plan-r1"),
                     ("slices/design work/tdd.md", "tdd-r1"),
                     ("slices/design work/implementation-plan.md", "plan-r1")]
        for index, (name, revision) in enumerate(documents):
            for operation in ("modify", "delete", "rename"):
                with self.subTest(name=name, operation=operation):
                    repo = self.repository(f"repo-{index}-{operation}")
                    relative = "docs/features/feature name/" + name
                    file = self.snapshot(repo, relative, "done", revision)
                    base = self.commit(repo)
                    if operation == "modify":
                        file.write_bytes(file.read_bytes() + b"Extra line.\n")
                    elif operation == "delete":
                        file.unlink()
                    else:
                        file.rename(file.with_name("old-" + file.name))
                    head = self.commit(repo)
                    result = self.frozen(repo, base, head)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(relative, result.stderr)
                    self.assertIn("frozen", result.stderr)

    def test_transition_to_done_preserves_active_document_contract(self):
        for name, revision in (("prd.md", "prd-r2"), ("tdd.md", "tdd-r2"),
                               ("implementation-plan.md", "plan-r2")):
            with self.subTest(document=name):
                repo = self.repository("transition-" + name)
                relative = "docs/features/search/" + name
                self.snapshot(repo, relative, "active", revision)
                base = self.commit(repo)
                self.snapshot(repo, relative, "done", revision, "Altered on delivery.\n")
                invalid = self.frozen(repo, base, self.commit(repo))
                self.assertEqual(invalid.returncode, 1, invalid.stderr)
                self.assertIn(relative, invalid.stderr)
                self.assertIn("unchanged body and revision", invalid.stderr)
                self.snapshot(repo, relative, "done", revision)
                self.assertEqual(self.frozen(repo, base, self.commit(repo)).returncode, 0)

    def test_frozen_rejects_malformed_head_even_when_state_would_bypass_freeze(self):
        repo = self.repository("malformed")
        file = self.snapshot(repo, "docs/features/x/prd.md", "done", "prd-r2")
        base = self.commit(repo)
        file.write_text("---\nstate: made-up\nrevision: prd-r2\n---\nChanged.\n")
        result = self.frozen(repo, base, self.commit(repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid state for prd", result.stderr)

    def test_system_design_body_changes_need_higher_revision_and_reopening(self):
        repo = self.repository("system-revisions")
        relative = "docs/features/design space/system-design.md"
        self.snapshot(repo, relative, "active", "sd-r2")
        base = self.commit(repo)
        self.snapshot(repo, relative, "active", "sd-r2", "Changed body.\n")
        unchanged_revision = self.commit(repo)
        result = self.frozen(repo, base, unchanged_revision)
        self.assertEqual(result.returncode, 1)
        self.assertIn("revision greater than sd-r2", result.stderr)
        self.snapshot(repo, relative, "active", "sd-r3", "Changed body.\n")
        stale_acceptance = self.commit(repo)
        result = self.frozen(repo, base, stale_acceptance)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be draft", result.stderr)
        self.snapshot(repo, relative, "draft", "sd-r3", "Changed body.\n")
        revised = self.commit(repo)
        self.assertEqual(self.frozen(repo, base, revised).returncode, 0)
        self.snapshot(repo, relative, "active", "sd-r3", "Changed body.\n")
        accepted = self.commit(repo)
        self.assertEqual(self.frozen(repo, revised, accepted).returncode, 0)
        self.snapshot(repo, relative, "done", "sd-r3", "Changed body.\n")
        done = self.commit(repo)
        self.assertEqual(self.frozen(repo, accepted, done).returncode, 0)
        self.snapshot(repo, relative, "draft", "sd-r4", "New slice design.\n")
        reopened = self.commit(repo)
        self.assertEqual(self.frozen(repo, done, reopened).returncode, 0)
        self.snapshot(repo, relative, "draft", "sd-r3", "New slice design.\n")
        failed_reopen = self.commit(repo)
        self.assertIn("revision greater than sd-r3",
                      self.frozen(repo, done, failed_reopen).stderr)

    def test_system_design_done_transition_requires_only_metadata_change(self):
        repo = self.repository("system-metadata")
        relative = "docs/features/x/system-design.md"
        self.snapshot(repo, relative, "active", "sd-r7")
        base = self.commit(repo)
        self.snapshot(repo, relative, "done", "sd-r7")
        head = self.commit(repo)
        self.assertEqual(self.frozen(repo, base, head).returncode, 0)
        self.snapshot(repo, relative, "done", "sd-r7", "Modified content.\n")
        changed = self.commit(repo)
        result = self.frozen(repo, base, changed)
        self.assertEqual(result.returncode, 1)
        self.assertIn("revision greater than sd-r7", result.stderr)

    def test_system_design_deletion_and_rename_fail_closed(self):
        for operation in ("delete", "rename"):
            with self.subTest(operation=operation):
                repo = self.repository("design-" + operation)
                relative = "docs/features/x/system-design.md"
                file = self.snapshot(repo, relative, "done", "sd-r2")
                base = self.commit(repo)
                if operation == "delete":
                    file.unlink()
                else:
                    file.rename(file.with_name("renamed-system-design.md"))
                result = self.frozen(repo, base, self.commit(repo))
                self.assertEqual(result.returncode, 1)
                self.assertIn("system-design deletion or rename", result.stderr)

    def test_new_feature_document_must_have_valid_status(self):
        repo = self.repository("new-document")
        base = self.commit(repo)
        file = repo / "docs/features/x/slices/y/tdd.md"
        file.parent.mkdir(parents=True)
        file.write_text("No frontmatter.\n", encoding="utf-8")
        result = self.frozen(repo, base, self.commit(repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing status frontmatter", result.stderr)

    def test_frozen_unchanged_documents_and_non_feature_changes_are_allowed(self):
        repo = self.repository("unchanged")
        self.snapshot(repo, "docs/features/x/prd.md", "done", "prd-r1")
        self.snapshot(repo, "docs/features/x/slices/y/tdd.md", "done", "tdd-r2")
        base = self.commit(repo)
        (repo / "notes.txt").write_text("Unrelated change.\n", encoding="utf-8")
        head = self.commit(repo)
        self.assertEqual(self.frozen(repo, base, head).returncode, 0)
        self.assertEqual(self.frozen(repo, head, head).returncode, 0)
        self.assertNotEqual(self.frozen(repo, base, "nonexistent-revision").returncode, 0)
        self.assertNotEqual(self.frozen(repo, base, head, "docs/features/x/prd.md").returncode, 0)

    def test_frozen_approvals_only_changes_and_removed_done_entry(self):
        repo = self.repository("approvals-only")
        path = self.snapshot(repo, "docs/features/x/prd.md", "done", "prd-r1")
        base = self.commit(repo)
        manifest = repo / "docs/user-approvals.json"
        data = json.loads(manifest.read_text())
        data["docs/product-vision.md"] = hashlib.sha256(b"Vision body.\n").hexdigest()
        manifest.write_text(json.dumps(data))
        head = self.commit(repo)
        self.assertEqual(self.frozen(repo, base, head).returncode, 0)
        manifest = repo / "docs/user-approvals.json"
        manifest.write_text("{}")
        removed = self.frozen(repo, head, self.commit(repo))
        self.assertEqual(removed.returncode, 1)
        self.assertIn("approval entry must remain", removed.stderr)

    def test_frozen_agent_approvals_only_changes_and_removed_done_entry(self):
        repo = self.repository("agent-approvals-only")
        path = self.snapshot(repo, "docs/features/x/tdd.md", "done", "tdd-r1")
        base = self.commit(repo)
        manifest = repo / "docs/agent-approvals.json"
        data = json.loads(manifest.read_text())
        data[path.relative_to(repo).as_posix()]["evidence"] = "A renewed review passed."
        manifest.write_text(json.dumps(data))
        head = self.commit(repo)
        self.assertEqual(self.frozen(repo, base, head).returncode, 0)
        manifest.write_text("{}")
        result = self.frozen(repo, head, self.commit(repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/agent-approvals.json", result.stderr)

    def test_bare_relative_paths_and_explicit_repository(self):
        repo = self.repository("root-discovery")
        path = self.snapshot(repo, "docs/features/x/prd.md", "active", "prd-r1")
        relative = path.relative_to(repo)
        for args in ([], ["--repo", str(repo)]):
            result = subprocess.run([sys.executable, str(CHECKER), "--json", *args, str(relative)],
                                    cwd=repo, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)[0]["approval"]["valid"])

    def test_repository_discovery_ignores_inherited_git_state(self):
        repo = self.repository("clean-discovery")
        victim = self.repository("unrelated-victim")
        path = self.snapshot(repo, "docs/features/x/prd.md", "active", "prd-r1")
        poisoned = {**os.environ, "GIT_DIR": str(victim / ".git"),
                    "GIT_WORK_TREE": str(victim), "GIT_INDEX_FILE": str(victim / ".git/index")}
        result = subprocess.run([sys.executable, str(CHECKER), "--check", str(path)],
                                env=poisoned, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


    def test_frozen_rejects_binary_changed_document(self):
        repo = self.repository("binary")
        file = self.snapshot(repo, "docs/features/x/tdd.md", "active", "tdd-r1")
        base = self.commit(repo)
        file.write_bytes(file.read_bytes() + b"\0")
        result = self.frozen(repo, base, self.commit(repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary document", result.stderr)


if __name__ == "__main__":
    unittest.main()
