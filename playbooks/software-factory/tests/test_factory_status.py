"""Black-box document sequence, approval, and read-only factory status contracts."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "scripts" / "factory-status.py"
CHOOSE = "Choose the next feature or proof-of-concept scope with the developer, offering the roadmap's Now and Next items, then create its PRD at docs/features/<feature>/prd.md."
RUNNING = "Implementation, review, or developer validation in progress."
FALLBACK = " Slice order could not be fully parsed from the system design; using lexical order of slice directories for unlisted slices."
BASE = "docs/features/example"


class FactoryStatusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook factory status ")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.manifest = self.repo / "docs" / "user-approvals.json"
        self.manifest.parent.mkdir()
        self.approvals = {}
        self.agent_approvals = {}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.approvals))
        (self.manifest.parent / "agent-approvals.json").write_text(json.dumps(self.agent_approvals))

    def document(self, name, state="draft", approved=False, body="# Document\n"):
        kind = Path(name).name
        revision = {"product-vision.md": "vision-r1", "architecture.md": "arch-r1",
                    "prd.md": "prd-r1", "system-design.md": "sd-r1",
                    "tdd.md": "tdd-r1", "implementation-plan.md": "plan-r1"}.get(kind)
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = "---\nstate: " + state + "\n"
        if revision:
            frontmatter += "revision: " + revision + "\n"
        path.write_text(frontmatter + "---\n" + body)
        if approved:
            digest = hashlib.sha256(body.encode()).hexdigest()
            if kind in ("tdd.md", "implementation-plan.md"):
                self.agent_approvals[name] = {"hash": digest, "evidence": "Reviews and checks passed."}
            else:
                self.approvals[name] = digest
            self.save()
        return path

    def globals(self):
        self.document("docs/product-vision.md", "active", True)
        self.document("docs/architecture.md", "active", True)

    def run_cli(self, repo=None, program=PROGRAM):
        return subprocess.run([sys.executable, str(program), "--repo", str(repo or self.repo)],
                              capture_output=True, text=True, timeout=10, check=False)

    def status(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def assert_next(self, sentence):
        status = self.status()
        self.assertEqual(status["nextStep"], sentence)
        return status

    def test_opt_in_requires_user_file_not_agent_file(self):
        self.manifest.unlink()
        self.assertTrue((self.repo / "docs/agent-approvals.json").exists())
        self.assertEqual(self.status(), {"optedIn": False})
        self.manifest.write_text("{}")
        self.assertTrue(self.status()["optedIn"])

    def test_empty_project_vision_architecture_then_prd_selection(self):
        status = self.assert_next("Create docs/product-vision.md.")
        self.assertEqual(status, {"optedIn": True, "feature": None, "currentSlice": None,
                                  "documents": [], "openGates": ["docs/product-vision.md"],
                                  "nextStep": "Create docs/product-vision.md.", "ambiguity": None})
        self.document("docs/product-vision.md")
        self.assert_next("Review docs/product-vision.md and obtain developer approval.")
        self.document("docs/product-vision.md", "active", True)
        self.assert_next("Create docs/architecture.md.")
        self.document("docs/architecture.md")
        self.assert_next("Review docs/architecture.md and obtain developer approval.")
        self.document("docs/architecture.md", "active", True)
        self.assert_next(CHOOSE)

    def test_every_single_slice_document_step(self):
        self.globals()
        self.document(BASE + "/prd.md")
        status = self.assert_next("Review " + BASE + "/prd.md and obtain developer approval.")
        self.assertEqual(status["feature"], "example")
        self.assertEqual(status["currentSlice"], BASE)
        self.document(BASE + "/prd.md", "active", True)
        self.assert_next("Create " + BASE + "/tdd.md.")
        self.document(BASE + "/tdd.md")
        self.assert_next("Review " + BASE + "/tdd.md and obtain agent acceptance.")
        self.document(BASE + "/tdd.md", "active", True)
        self.assert_next("Create " + BASE + "/implementation-plan.md.")
        self.document(BASE + "/implementation-plan.md")
        self.assert_next("Review " + BASE + "/implementation-plan.md and obtain agent acceptance.")
        self.document(BASE + "/implementation-plan.md", "active", True)
        self.assert_next(RUNNING)
        self.document(BASE + "/implementation-plan.md", "done", True)
        self.assert_next(RUNNING)  # Both documents must be done, after validation.
        self.document(BASE + "/tdd.md", "done", True)
        status = self.assert_next("Mark " + BASE + "/prd.md and its system design, if present, done after all slices have developer validation.")
        self.assertIsNone(status["currentSlice"])
        self.document(BASE + "/prd.md", "done", True)
        status = self.assert_next(CHOOSE)
        self.assertIsNone(status["feature"])

    def design(self, state="active", approved=True):
        return self.document(BASE + "/system-design.md", state, approved,
                             "# Design\n\nIntro mentions slices/01-first/tdd.md.\n\n## Slice order\n"
                             "1. [Second](slices/02-second/tdd.md)\n2. [First](slices/01-first/tdd.md)\n")

    def test_every_multi_slice_step_and_system_design_order(self):
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        for name in ("01-first", "02-second"):
            (self.repo / BASE / "slices" / name).mkdir(parents=True)
        status = self.assert_next("Create " + BASE + "/system-design.md." + FALLBACK)
        self.assertIn(BASE + "/system-design.md", status["openGates"])
        self.design("draft", False)
        first = BASE + "/slices/02-second"
        second = BASE + "/slices/01-first"
        status = self.assert_next("Review " + BASE + "/system-design.md and obtain developer approval.")
        self.assertEqual(status["currentSlice"], first)
        self.design()
        self.assert_next("Create " + first + "/tdd.md.")
        self.document(first + "/tdd.md")
        self.assert_next("Review " + first + "/tdd.md and obtain agent acceptance.")
        self.document(first + "/tdd.md", "active", True)
        self.assert_next("Create " + first + "/implementation-plan.md.")
        self.document(first + "/implementation-plan.md")
        self.assert_next("Review " + first + "/implementation-plan.md and obtain agent acceptance.")
        self.document(first + "/implementation-plan.md", "active", True)
        self.assert_next(RUNNING)
        self.document(first + "/tdd.md", "done", True)
        self.document(first + "/implementation-plan.md", "done", True)
        status = self.assert_next("Create " + second + "/tdd.md.")
        self.assertEqual(status["currentSlice"], second)
        self.document(second + "/tdd.md", "done", True)
        self.document(second + "/implementation-plan.md", "done", True)
        self.assert_next("Mark " + BASE + "/prd.md and its system design, if present, done after all slices have developer validation.")
        self.document(BASE + "/prd.md", "done", True)
        self.design("done")
        self.assert_next(CHOOSE)

    def test_single_slice_fix_beneath_done_prd_is_current(self):
        self.globals()
        self.document(BASE + "/prd.md", "done", True)
        self.document(BASE + "/tdd.md", "active", True)
        self.document(BASE + "/implementation-plan.md", "active", True)
        status = self.assert_next(RUNNING)
        self.assertEqual(status["feature"], "example")
        self.assertEqual(status["currentSlice"], BASE)

    def test_fix_only_slice_without_system_design_beneath_done_prd(self):
        self.globals()
        for filename in ("prd.md", "tdd.md", "implementation-plan.md"):
            self.document(BASE + "/" + filename, "done", True)
        fix = BASE + "/slices/fix"
        self.document(fix + "/tdd.md", "draft")
        status = self.assert_next("Review " + fix + "/tdd.md and obtain agent acceptance.")
        self.assertEqual(status["currentSlice"], fix)
        self.assertNotIn(BASE + "/system-design.md", status["openGates"])

    def test_multi_slice_fix_beneath_done_prd_is_current(self):
        self.globals()
        self.document(BASE + "/prd.md", "done", True)
        self.design()
        delivered = BASE + "/slices/02-second"
        for filename in ("tdd.md", "implementation-plan.md"):
            self.document(delivered + "/" + filename, "done", True)
        fix = BASE + "/slices/01-first"
        self.document(fix + "/tdd.md", "active", True)
        self.document(fix + "/implementation-plan.md", "active", True)
        status = self.assert_next(RUNNING)
        self.assertEqual(status["currentSlice"], fix)

    def test_unfinished_system_design_under_done_prd_is_work(self):
        self.globals()
        self.document(BASE + "/prd.md", "done", True)
        self.design("draft", False)
        status = self.assert_next("Review " + BASE + "/system-design.md and obtain developer approval.")
        self.assertEqual(status["feature"], "example")
        self.assertEqual(status["currentSlice"], BASE + "/slices/02-second")

    def test_fallback_is_lexical_and_reported_in_next_step(self):
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        self.document(BASE + "/system-design.md", "active", True, "# Design\nNo parsable order.\n")
        for name in ("z-last", "a-first"):
            (self.repo / BASE / "slices" / name).mkdir(parents=True)
        status = self.assert_next("Create " + BASE + "/slices/a-first/tdd.md." + FALLBACK)
        self.assertEqual(status["currentSlice"], BASE + "/slices/a-first")

    def test_slice_table_order_uses_existing_names_not_lexical_order(self):
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        for name in ("a-first", "z-last"):
            (self.repo / BASE / "slices" / name).mkdir(parents=True)
        self.document(BASE + "/system-design.md", "active", True,
                      "# Design\n## Slices\n| Slice | Handoff |\n| --- | --- |\n"
                      "| `z-last` | Stored state |\n| `a-first` | Consumes state |\n")
        status = self.assert_next("Create " + BASE + "/slices/z-last/tdd.md.")
        self.assertEqual(status["currentSlice"], BASE + "/slices/z-last")

    def test_documented_slice_order_format_selects_first_slice_before_directories_exist(self):
        # The Feature system design contract's `## Slice order` format, ahead of an earlier slice mention.
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        self.document(BASE + "/system-design.md", "active", True,
                      "# Design\n## Slices\n- `01-shells` uses the store.\n\n## Slice order\n\n"
                      "1. `02-store` — persisted projects.\n2. `01-shells` — project shells.\n")
        status = self.assert_next("Create " + BASE + "/slices/02-store/tdd.md.")
        self.assertEqual(status["currentSlice"], BASE + "/slices/02-store")

    def test_design_without_slice_list_or_directories_reports_no_lexical_fallback(self):
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        self.document(BASE + "/system-design.md", "draft", False)
        self.assert_next("Review " + BASE + "/system-design.md and obtain developer approval.")
        self.document(BASE + "/system-design.md", "active", True)
        status = self.assert_next("Define the slice list in " + BASE + "/system-design.md before creating a technical design.")
        self.assertIsNone(status["currentSlice"])

    def test_create_step_names_feature_notes_section_only_for_its_target(self):
        self.globals()
        self.document(BASE + "/prd.md", "active", True)
        self.design()
        current = BASE + "/slices/02-second"
        notes = self.repo / BASE / "notes.md"
        notes.write_text("# Notes\n\n## slices/01-first/tdd.md\n\nLater slice.\n\n"
                         "### slices/02-second/tdd.md\n\nWrong level.\n")
        self.assert_next("Create " + current + "/tdd.md.")
        notes.write_text(notes.read_text() + "\n## `slices/02-second/tdd.md`\n\nShell holder finding.\n")
        self.assert_next("Create " + current + "/tdd.md. Source material: the slices/02-second/tdd.md section of "
                         + BASE + "/notes.md.")
        self.document(current + "/tdd.md")
        self.assert_next("Review " + current + "/tdd.md and obtain agent acceptance.")

    def test_open_gates_and_exact_document_row(self):
        self.globals()
        path = self.document(BASE + "/prd.md", "active", True)
        path.write_bytes(path.read_bytes() + b"Changed requirements.\n")
        status = self.status()
        self.assertIn(BASE + "/prd.md", status["openGates"])
        self.assertEqual(next(row for row in status["documents"] if row["path"] == BASE + "/prd.md"),
                         {"path": BASE + "/prd.md", "type": "prd", "state": "active",
                          "approved": False, "gate": "developer"})
        self.assertEqual(status["nextStep"], "Review " + BASE + "/prd.md and obtain developer approval.")

    def test_missing_upstream_documents_are_open_gates(self):
        self.document(BASE + "/implementation-plan.md")
        status = self.assert_next("Create docs/product-vision.md.")
        self.assertEqual(status["openGates"], sorted(["docs/product-vision.md", "docs/architecture.md",
                         BASE + "/prd.md", BASE + "/tdd.md", BASE + "/implementation-plan.md"]))

    def test_two_unfinished_features_are_ambiguous_not_arbitrarily_selected(self):
        self.globals()
        for feature in ("beta", "alpha"):
            self.document("docs/features/" + feature + "/prd.md")
        status = self.assert_next("Choose the feature to continue with the developer: alpha, beta.")
        self.assertEqual(status["ambiguity"], "Multiple features have unfinished work: alpha, beta.")
        self.assertIsNone(status["feature"])
        self.assertIsNone(status["currentSlice"])

    def test_ungated_roadmap_does_not_block_or_select_work(self):
        self.globals()
        self.document("docs/roadmap.md", "active")
        status = self.assert_next(CHOOSE)
        self.assertEqual(status["openGates"], [])
        row = next(row for row in status["documents"] if row["type"] == "roadmap")
        self.assertEqual(row["gate"], "none")

    def test_superseded_work_does_not_select_feature(self):
        self.globals()
        self.document(BASE + "/prd.md", "superseded")
        self.document(BASE + "/tdd.md", "superseded")
        self.assertIsNone(self.assert_next(CHOOSE)["feature"])

    def test_opt_out_emits_only_opted_in_false_and_does_not_inspect_documents(self):
        self.manifest.unlink()
        self.document("docs/product-vision.md").write_text("malformed document")
        self.assertEqual(self.status(), {"optedIn": False})
        self.assertFalse(self.manifest.exists())

    def test_malformed_approvals_fail_closed_without_json_output(self):
        self.manifest.write_text("{not-json}")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("malformed approvals JSON", result.stderr)

    def test_invalid_document_fails_with_stderr_only(self):
        self.document("docs/product-vision.md", state="unknown")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid document state", result.stderr)

    def test_status_has_no_writes_even_in_a_copied_install(self):
        install = self.repo / "readonly install"
        install.mkdir()
        copied = install / "factory-status.py"
        copied.write_bytes(PROGRAM.read_bytes())
        (install / "doc_approvals.py").write_bytes((ROOT / "scripts" / "doc_approvals.py").read_bytes())
        self.globals()
        self.document(BASE + "/prd.md")

        def snapshot():
            return {path.relative_to(self.repo).as_posix():
                    (path.read_bytes() if path.is_file() else None, path.stat().st_mtime_ns)
                    for path in [self.repo, *self.repo.rglob("*")]}

        before = snapshot()
        result = self.run_cli(program=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(), before)
        self.assertFalse((install / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
