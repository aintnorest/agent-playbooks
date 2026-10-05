"""Behavioral contracts for the implementation-plan DAG validator."""
import git_test_environment  # Scrub inherited Git hook state before fixture creation.

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "check-implementation-plans.py"


def task(identifier, dependency="none", reason="", tests="", protects="",
         target="`src/mod.py`::run (edit)"):
    return (
        f"### {identifier} — Deliver {identifier}\n"
        f"- Depends on: {dependency}\n"
        f"{reason}"
        f"- Targets: {target}\n"
        f"{protects}"
        "- Change: Implement TDD §3.\n"
        f"{tests}"
        "- Done when: The user sees the saved result.\n"
        "- Verify: Run the service; expect a saved result.\n"
    )


class CheckImplementationPlansTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook plans ")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "implementation-plan.md"

    def run_paths(self, mode, *paths, env=None):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), mode, *(str(path) for path in paths)],
            capture_output=True, text=True, check=False, env=env,
        )

    def run_validator(self, body, mode="--check"):
        self.path.write_text(body, encoding="utf-8")
        return self.run_paths(mode, self.path)

    def assert_error_at(self, result, path, line, subject):
        prefix = f"{path}:{line}:"
        self.assertTrue(
            any(text.startswith(prefix) and subject in text for text in result.stderr.splitlines()),
            result.stderr,
        )

    def test_no_file_target_is_sole_none(self):
        self.assertEqual(self.run_validator(task("T01", target="none")).returncode, 0)
        mixed = self.run_validator(task("T01", target="none; `src/mod.py` (edit)"))
        self.assertNotEqual(mixed.returncode, 0)
        self.assertIn("sole none", mixed.stderr)

    def test_valid_plan_with_direct_reasons_and_optional_tests(self):
        content = (
            "# Approved plan\n\n"
            + task("T01", tests="- Tests: Cover the observable saved result.\n")
            + "\n" + task("T02", "T01", "  - T01 — supplies the saved record.\n")
        )
        checked = self.run_validator(content)
        self.assertEqual((checked.returncode, checked.stdout, checked.stderr), (0, "", ""))

    def test_multiline_field_is_preserved_as_one_field(self):
        content = task("T01").replace(
            "- Targets: `src/mod.py`::run (edit)",
            "- Targets: `src/mod.py`::run (edit)\n  `tests/test_mod.py` (edit)",
        ).replace(
            "- Done when: The user sees the saved result.",
            "- Done when:\n  The user sees the saved result.\n  The next request retrieves it.",
        )
        result = self.run_validator(content, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        tasks = json.loads(result.stdout)
        self.assertEqual(tasks[0]["fields"]["Targets"],
                         "`src/mod.py`::run (edit)\n`tests/test_mod.py` (edit)")
        self.assertEqual(tasks[0]["fields"]["Done when"],
                         "The user sees the saved result.\nThe next request retrieves it.")

    def test_json_is_a_reusable_graph_without_fenced_fake_tasks(self):
        body = (
            "```markdown\n" + task("T99") + "```\n"
            + task("T01", tests="- Tests: Cover the observable saved result.\n") + "\n"
            + task("T02", "T01", "  - T01 — supplies the saved record.\n")
            + "\n## Epilogue\nUnrelated prose.\n"
        )
        result = self.run_validator(body, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        tasks = json.loads(result.stdout)
        self.assertEqual(tasks[0], {
            "id": "T01", "title": "Deliver T01", "depends_on": [],
            "fields": {
                "Depends on": "none",
                "Targets": "`src/mod.py`::run (edit)",
                "Change": "Implement TDD §3.",
                "Tests": "Cover the observable saved result.",
                "Done when": "The user sees the saved result.",
                "Verify": "Run the service; expect a saved result.",
            },
            "path": str(self.path), "line": 9,
        })
        self.assertEqual([row["id"] for row in tasks], ["T01", "T02"])
        self.assertEqual(tasks[1]["depends_on"], ["T01"])
        self.assertEqual(tasks[1]["title"], "Deliver T02")
        self.assertEqual(tasks[1]["fields"]["Depends on"], "T01")
        self.assertEqual(tasks[1]["path"], str(self.path))

    def test_non_task_prose_heading_is_ignored_but_malformed_task_is_not(self):
        result = self.run_validator("## 0. Foundation\nNotes outside blocks.\n"
                                    "### TDD context\nNotes outside blocks.\n\n" + task("T01"))
        self.assertEqual(result.returncode, 0, result.stderr)
        malformed = self.run_validator("### TAA2 — Bad ID\n" + task("T01"))
        self.assertNotEqual(malformed.returncode, 0)
        self.assert_error_at(malformed, self.path, 1, "heading")

    def test_task_shaped_headings_are_not_silently_dropped(self):
        for heading in ("## T02 — Wrong level", "### TPLAN02 — Wrong prefix",
                        "#### P03 — Wrong ID namespace", "### 02 — Missing prefix"):
            with self.subTest(heading=heading):
                later_fields = task("T02").split("\n", 1)[1]
                result = self.run_validator(task("T01") + "\n" + heading + "\n"
                                            + later_fields)
                self.assertNotEqual(result.returncode, 0)
                self.assert_error_at(result, self.path, 8, "heading")

    def test_tab_indented_backticks_do_not_hide_later_tasks(self):
        result = self.run_validator(task("T01") + "\t```not-a-fence\n\n"
                                    + task("T02", "T01", "  - T01 — supplies output.\n"), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([task["id"] for task in json.loads(result.stdout)], ["T01", "T02"])

    def test_tab_indented_fence_marker_does_not_close_a_fence(self):
        body = ("```markdown\n" + task("T99") + "\t```\n"
                + task("T98") + "```\n" + task("T01"))
        result = self.run_validator(body, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["id"] for row in json.loads(result.stdout)], ["T01"])

    def test_json_is_ascii_safe(self):
        body = task("T01").replace("Deliver T01", "Café output")
        self.path.write_text(body, encoding="utf-8")
        result = self.run_paths("--json", self.path,
                                env={**os.environ, "PYTHONIOENCODING": "ascii"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        self.assertEqual(json.loads(result.stdout)[0]["title"], "Café output")

    def test_long_dependency_chain_is_checked_without_recursion_failure(self):
        body = task("T1")
        for number in range(2, 1052):
            previous = f"T{number - 1}"
            body += task(f"T{number}", previous, f"  - {previous} — supplies output.\n")
        result = self.run_validator(body)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dependency_line_cannot_contain_prose(self):
        result = self.run_validator(task("T01") + "\n" + task(
            "T02", "T01 — needed first", "  - T01 — supplies the saved record.\n"
        ))
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 9, "Depends on")
        self.assertEqual(result.stdout, "")

    def test_reasons_match_direct_ids_in_order(self):
        result = self.run_validator(
            task("T01") + "\n" + task("T02") + "\n"
            + task("T03", "T01, T02", "  - T02 — supplies the wrong output.\n"
                   "  - T01 — supplies the other output.\n")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 16, "reasons")

    def test_duplicate_and_dangling_ids_are_rejected(self):
        result = self.run_validator(task("T01") + "\n" + task("T01") + "\n"
                                    + task("T03", "T99", "  - T99 — supplies an output.\n"))
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 8, "T01")
        self.assert_error_at(result, self.path, 15, "T99")

    def test_forward_and_cyclic_ids_are_rejected(self):
        result = self.run_validator(
            task("T01", "T02", "  - T02 — supplies output.\n") + "\n"
            + task("T02", "T01", "  - T01 — supplies output.\n")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 1, "T02")
        self.assert_error_at(result, self.path, 9, "cycle")

    def test_self_dependency_is_rejected(self):
        result = self.run_validator(task("T01", "T01", "  - T01 — supplies itself.\n"))
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 1, "T01")

    def test_task_shape_and_empty_fields_are_rejected(self):
        content = task("T01").replace("### T01 — Deliver T01", "### T01 - Deliver T01")
        content += "\n" + task("T02").replace(
            "- Targets: `src/mod.py`::run (edit)\n- Change: Implement TDD §3.\n",
            "- Change: Implement TDD §3.\n- Targets:\n- Change: Duplicate.\n",
        ).replace("- Verify: Run the service; expect a saved result.\n", "")
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 1, "heading")
        self.assert_error_at(result, self.path, 8, "Verify")
        self.assert_error_at(result, self.path, 11, "Targets")
        self.assert_error_at(result, self.path, 12, "Change")

    def test_json_does_not_publish_invalid_graph(self):
        result = self.run_validator(task("T01", "T02", "  - T02 — supplies output.\n"), "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assert_error_at(result, self.path, 1, "T02")

    def test_status_and_misplaced_tests_are_rejected(self):
        status = self.run_validator(
            task("T01").replace("- Targets:", "- Status: pending\n- Targets:"))
        self.assertNotEqual(status.returncode, 0)
        self.assert_error_at(status, self.path, 3, "Status")
        misplaced = self.run_validator(task(
            "T01", tests="- Tests: Cover the saved result.\n",
        ).replace("- Tests: Cover the saved result.\n", "").replace(
            "- Verify:", "- Tests: Cover the saved result.\n- Verify:",
        ))
        self.assertNotEqual(misplaced.returncode, 0)
        self.assert_error_at(misplaced, self.path, 6, "Tests")

    def test_none_dependency_rejects_reason_subbullet(self):
        result = self.run_validator(task("T01", reason="  - T02 — not a direct edge.\n"))
        self.assertNotEqual(result.returncode, 0)
        self.assert_error_at(result, self.path, 2, "reasons")

    def test_json_does_not_emit_partial_graph_across_files(self):
        invalid = self.path.with_name("invalid.md")
        self.path.write_text(task("T01"), encoding="utf-8")
        invalid.write_text(task("T02", "T99", "  - T99 — not present.\n"), encoding="utf-8")
        result = self.run_paths("--json", self.path, invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assert_error_at(result, invalid, 1, "T99")


    def test_protects_are_optional_ordered_and_retained_in_json(self):
        body = task("T01", protects="- Protects: tests/test_accept.py; tests/test_error.py\n",
                    target="`tests/test_accept.py` (create); `tests/test_error.py` (create)")
        result = self.run_validator(body, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["fields"]["Protects"],
                         "tests/test_accept.py; tests/test_error.py")
        misplaced = self.run_validator(body.replace(
            "- Protects: tests/test_accept.py; tests/test_error.py\n", "").replace(
            "- Done when:", "- Protects: tests/test_accept.py; tests/test_error.py\n- Done when:"))
        self.assertNotEqual(misplaced.returncode, 0)
        self.assertIn("task label out of order: Protects", misplaced.stderr)

    def test_protects_rejects_malformed_and_duplicate_paths(self):
        for value in ("", "/tests/test_accept.py", "../tests/test_accept.py",
                      "tests/./test_accept.py", "tests\\test_accept.py",
                      "`tests/test_accept.py`", "tests/test_accept.py;tests/other.py",
                      "tests/test_accept.py; tests/test_accept.py"):
            with self.subTest(value=value):
                result = self.run_validator(task("T01", protects=f"- Protects: {value}\n"))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Protects", result.stderr)

    def test_later_targets_cannot_name_protected_file(self):
        body = (task("T01", protects="- Protects: tests/test_accept.py\n",
                     target="`tests/test_accept.py` (create)") + "\n"
                + task("T02", "T01", "  - T01 — supplies acceptance test.\n",
                       target="`tests/test_accept.py`::case (edit)"))
        result = self.run_validator(body)
        self.assertNotEqual(result.returncode, 0)
        for evidence in ("protected", "T01", "tests/test_accept.py"):
            self.assertIn(evidence, result.stderr)
        unquoted = self.run_validator(body.replace(
            "`tests/test_accept.py`::case", "tests/test_accept.py::case"))
        self.assertNotEqual(unquoted.returncode, 0)
        self.assertIn("protected", unquoted.stderr)
        alias = self.run_validator(body.replace(
            "`tests/test_accept.py`::case", "`tests/./test_accept.py`::case"))
        self.assertNotEqual(alias.returncode, 0)
        self.assertIn("protected", alias.stderr)
        fully_quoted_symbol = self.run_validator(body.replace(
            "`tests/test_accept.py`::case", "`tests/test_accept.py::case`"))
        self.assertNotEqual(fully_quoted_symbol.returncode, 0)
        self.assertIn("malformed Targets", fully_quoted_symbol.stderr)
        malformed = self.run_validator(body.replace(
            "`tests/test_accept.py`::case (edit)", "rewrite tests/test_accept.py"))
        self.assertNotEqual(malformed.returncode, 0)
        self.assertIn("malformed Targets", malformed.stderr)

    def test_assignment_pair_is_optional_but_atomic_unique_and_ordered(self):
        location = str(self.path.parent / "tasks" / "T01")
        assigned = task("T01") + f"- Assigned worktree: {location}\n- Assigned branch: impl/T01\n"
        parsed = self.run_validator(assigned, "--json")
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(json.loads(parsed.stdout)[0]["fields"]["Assigned worktree"], location)
        for body, error in (
            (assigned.replace("- Assigned branch: impl/T01\n", ""), "must appear together"),
            (assigned.replace(location, "tasks/T01"), "absolute normalized"),
            (assigned.replace("impl/T01", "impl/../T01"), "malformed Assigned branch"),
            (assigned.replace("- Assigned branch: impl/T01\n", "- Assigned branch: impl/T01\n"
                              "- Assigned branch: impl/T02\n"), "duplicate task label"),
            (assigned.replace("- Assigned worktree:", "- Assigned branch: impl/T01\n- Assigned worktree:"),
             "task label out of order"),
            (assigned + "\n" + task("T02") +
             f"- Assigned worktree: {location}\n- Assigned branch: impl/T02\n", "multiple tasks"),
            (assigned + "\n" + task("T02") +
             f"- Assigned worktree: {self.path.parent / 'tasks' / 'T02'}\n"
             "- Assigned branch: impl/T01\n", "multiple tasks"),
        ):
            with self.subTest(error=error, body=body):
                result = self.run_validator(body)
                self.assertEqual(result.returncode, 1)
                self.assertIn(error, result.stderr)

    def test_assigned_candidate_must_match_registered_clean_worktree_and_tip(self):
        repository = self.path.with_name("assigned-repo")
        repository.mkdir()
        def git(*args, cwd=repository):
            return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        (repository / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
        git("add", ".gitignore")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "ignore worktrees")
        base = git("rev-parse", "HEAD")
        worktrees = repository / ".worktrees"
        worktrees.mkdir()
        location = worktrees / "T01"
        git("worktree", "add", "-q", "-b", "impl/T01", str(location), base)
        self.addCleanup(lambda: git("worktree", "remove", "--force", str(location))
                        if location.exists() else None)
        (location / "output.txt").write_text("first\n", encoding="utf-8")
        git("add", "output.txt", cwd=location)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "worker output", cwd=location)
        head = git("rev-parse", "HEAD", cwd=location)
        self.path.write_text(task("T01") +
                             f"- Assigned worktree: {location}\n- Assigned branch: impl/T01\n",
                             encoding="utf-8")
        def check(candidate=head, root=worktrees, plan=self.path, start=base):
            return subprocess.run([sys.executable, str(VALIDATOR), "--protected-diff", str(plan),
                                   "--repo", str(repository), "--base", start, "--head", candidate,
                                   "--task", "T01", "--worktree-root", str(root)],
                                  capture_output=True, text=True, check=False)
        index = Path(git("rev-parse", "--path-format=absolute", "--git-path", "index", cwd=location))
        # Identical content with stale cached stat info makes ordinary status refresh the index.
        tracked = location / "output.txt"
        stat = tracked.stat()
        os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        before_content = index.read_bytes()
        before_mtime = index.stat().st_mtime_ns
        checked = check()
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(index.read_bytes(), before_content)
        self.assertEqual(index.stat().st_mtime_ns, before_mtime)
        self.assertEqual(check().returncode, 0, check().stderr)
        self.assertIn("must be <repo-root>/.worktrees",
                      check(root=self.path.parent / "other").stderr)
        self.path.write_text(task("T01") +
                             f"- Assigned worktree: {self.path.parent / 'elsewhere'}\n"
                             "- Assigned branch: impl/T01\n", encoding="utf-8")
        self.assertIn("outside --worktree-root", check().stderr)
        self.path.write_text(task("T01") +
                             f"- Assigned worktree: {location}\n- Assigned branch: impl/T01\n",
                             encoding="utf-8")
        (repository / ".gitignore").unlink()
        self.assertIn("not ignored by Git", check().stderr)
        (repository / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
        self.assertIn("candidate is not assigned worktree branch tip", check(candidate=base).stderr)
        self.assertIn("requires --worktree-root", subprocess.run(
            [sys.executable, str(VALIDATOR), "--protected-diff", str(self.path), "--repo",
             str(repository), "--base", base, "--head", head, "--task", "T01"],
            capture_output=True, text=True).stderr)
        (location / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        self.assertIn("uncommitted changes", check().stderr)
        (location / "untracked.txt").unlink()
        source = self.path.with_name("submodule-source")
        source.mkdir()
        git("init", "-q", cwd=source)
        (source / "tracked.txt").write_text("original\n", encoding="utf-8")
        git("add", "tracked.txt", cwd=source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "submodule base", cwd=source)
        git("-c", "protocol.file.allow=always", "submodule", "add", "-q",
            str(source), "nested", cwd=location)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-am", "add submodule", cwd=location)
        submodule_head = git("rev-parse", "HEAD", cwd=location)
        git("config", "submodule.nested.ignore", "all", cwd=location)
        (location / "nested" / "tracked.txt").write_text("modified\n", encoding="utf-8")
        self.assertEqual(git("status", "--porcelain", "--untracked-files=all", cwd=location), "")
        self.assertIn("uncommitted changes", check(candidate=submodule_head).stderr)
        (location / "nested" / "tracked.txt").write_text("original\n", encoding="utf-8")
        git("branch", "-m", "impl/renamed", cwd=location)
        self.assertIn("branch differs", check(candidate=submodule_head).stderr)

    def test_registered_worktree_paths_preserve_embedded_newlines(self):
        repository = self.path.with_name("newline-repo")
        repository.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(repository), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "--allow-empty", "-m", "base")
        location = self.path.parent / "with\nnewline"
        git("worktree", "add", "-q", "-b", "impl/newline", str(location))
        self.addCleanup(lambda: git("worktree", "remove", "--force", str(location))
                        if location.exists() else None)
        spec = importlib.util.spec_from_file_location("plan_validator", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIn(location.resolve(), module.registered_worktrees(repository))

    def test_protected_diff_checks_git_changes_and_own_task_exception(self):
        repository = self.path.with_name("candidate")
        repository.mkdir()
        def git(*arguments):
            return subprocess.run(["git", "-C", str(repository), *arguments],
                                  check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "--allow-empty", "-m", "base")
        base = git("rev-parse", "HEAD")
        (repository / "src").mkdir()
        (repository / "src" / "mod.py").write_text("pass\n", encoding="utf-8")
        git("add", "src/mod.py")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "implementation")
        ordinary_head = git("rev-parse", "HEAD")
        (repository / "tests").mkdir()
        (repository / "tests" / "test_accept.py").write_text("assert True\n", encoding="utf-8")
        git("add", "tests/test_accept.py")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "acceptance")
        protected_head = git("rev-parse", "HEAD")
        self.path.write_text(
            task("T01", protects="- Protects: tests/test_accept.py\n",
                 target="`tests/test_accept.py` (create)") + "\n"
            + task("T02", "T01", "  - T01 — supplies acceptance test.\n"), encoding="utf-8")

        def diff(head, identifier=None, start=base, repo_root=repository):
            arguments = [sys.executable, str(VALIDATOR), "--protected-diff", str(self.path),
                         "--repo", str(repo_root), "--base", start, "--head", head]
            if identifier is not None:
                arguments.extend(("--task", identifier))
            return subprocess.run(arguments, capture_output=True, text=True, check=False)
        valid = diff(ordinary_head, "T02")
        self.assertEqual((valid.returncode, valid.stdout, valid.stderr), (0, "", ""))
        violation = diff(protected_head, "T02")
        self.assertEqual(violation.returncode, 1)
        for evidence in ("protected", "T02", "T01", "tests/test_accept.py"):
            self.assertIn(evidence, violation.stderr)
        allowed = diff(protected_head, "T01")
        self.assertEqual((allowed.returncode, allowed.stdout, allowed.stderr), (0, "", ""))
        no_task_valid = diff(ordinary_head)
        self.assertEqual((no_task_valid.returncode, no_task_valid.stdout,
                          no_task_valid.stderr), (0, "", ""))
        no_task_violation = diff(protected_head)
        self.assertEqual(no_task_violation.returncode, 1)
        for evidence in ("protected", "T01", "tests/test_accept.py"):
            self.assertIn(evidence, no_task_violation.stderr)
        missing = diff(protected_head, "T99")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("unknown task ID: T99", missing.stderr)
        invalid_base = diff(protected_head, "T02", "not-a-commit")
        self.assertEqual(invalid_base.returncode, 1)
        self.assertIn("cannot inspect protected diff", invalid_base.stderr)
        non_root = diff(protected_head, "T01", repo_root=repository / "src")
        self.assertEqual(non_root.returncode, 1)
        self.assertIn("repository root", non_root.stderr)
        (repository / "tests" / "test_accept.py").write_text("assert False\n", encoding="utf-8")
        git("add", "tests/test_accept.py")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "edit protected oracle")
        modified_head = git("rev-parse", "HEAD")
        modification = diff(modified_head, "T02", protected_head)
        self.assertEqual(modification.returncode, 1)
        for evidence in ("protected", "T02", "T01", "tests/test_accept.py"):
            self.assertIn(evidence, modification.stderr)
        git("mv", "tests/test_accept.py", "tests/renamed.py")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "rename protected file")
        rename = diff(git("rev-parse", "HEAD"), "T02", modified_head)
        self.assertEqual(rename.returncode, 1)
        for evidence in ("protected", "T02", "T01", "tests/test_accept.py"):
            self.assertIn(evidence, rename.stderr)

if __name__ == "__main__":
    unittest.main()
