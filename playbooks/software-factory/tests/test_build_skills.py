"""Consumer-visible safety and inclusion contracts for the optional publisher."""

import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PUBLISHER = Path(__file__).resolve().parents[1] / "scripts" / "build-skills.py"
PUBLISHER_VALUES = runpy.run_path(str(PUBLISHER))
SKILL_POINTER = PUBLISHER_VALUES["SKILL_POINTER"]
COMPLETION_LINE = PUBLISHER_VALUES["COMPLETION_LINE"]
FALLBACK_LINE = PUBLISHER_VALUES["FALLBACK_LINE"]


class BuildSkillsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook publisher ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for directory in ("agents", "scripts", "guides", "skill-sources"):
            (self.root / directory).mkdir()
        shutil.copy2(PUBLISHER, self.root / "scripts" / PUBLISHER.name)
        self.rules = self.root / "guides" / "rules.md"
        self.rules.write_text(
            "# Guide\n\n## Parent\nPreserve the parent obligation.\n\n"
            "### Child\nPreserve the child obligation.\n\n"
            "### Sibling\nPreserve the sibling obligation.\n",
            encoding="utf-8",
        )
        (self.root / "skill-sources" / "task.md").write_text(
            "# Task\n\n## Purpose\nProduces the requested task result from supplied obligations.\n\n"
            "## Required guidance\n\n"
            "- [Child](../guides/rules.md#child)\n"
            "- [Parent](../guides/rules.md#parent)\n"
            "- [Child again](../guides/rules.md#child)\n\n"
            "## Instructions\nApply the supplied obligations.\n",
            encoding="utf-8",
        )
        self.output = self.root / "skills" / "task" / "SKILL.md"
        self.agent = self.root / "agents" / "task-agent.md"
        self.write_agent()
        self.write_routing_cases()
        self.write_checks()

    def write_agent(
        self,
        *,
        path=None,
        name="task-agent",
        skill="task",
        tools="read",
        omit_standard=None,
        extra_body="",
        description='"Produces a test result. Use when checking the task. Not for unrelated work."',
    ):
        path = path or self.agent
        standard = [
            SKILL_POINTER.format(skill=skill),
            COMPLETION_LINE,
            FALLBACK_LINE.format(skill=skill),
        ]
        body = [
            "You handle exactly one test task.",
            *[line for line in standard if line != omit_standard],
        ]
        if extra_body:
            body.append(extra_body)
        path.write_text(
            "---\n"
            + "name: "
            + name
            + "\n"
            + "description: " + description + "\n"
            + "model: test/model\n"
            + "tools: "
            + tools
            + "\n"
            + "read-summarize: false\n"
            + "autoloadSkills:\n"
            + "  - "
            + skill
            + "\n"
            + "---\n\n"
            + "\n\n".join(body)
            + "\n",
            encoding="utf-8",
        )

    def write_checks(self, *, skills_without_agents=None, exemptions=None):
        configuration = {
            "skillsWithoutAgents": skills_without_agents or {},
            "exemptions": exemptions or {},
        }
        (self.root / "agents" / "checks.json").write_text(
            json.dumps(configuration), encoding="utf-8"
        )
    def write_routing_cases(self, cases=None):
        if cases is None:
            cases = {
                "task-agent": {
                    "positive": ["Handle a sample task", "Apply sample obligations", "Produce task result"],
                    "negative": [
                        {"request": "Review a sample PRD", "expected": None},
                        {"request": "Write sample code", "expected": None},
                    ],
                }
            }
        (self.root / "agents" / "routing-cases.json").write_text(
            json.dumps(cases), encoding="utf-8"
        )

    def write_source(self, text, name="task"):
        (self.root / "skill-sources" / (name + ".md")).write_text(text, encoding="utf-8")

    def reference_source(self, read_section="Instructions"):
        body = {
            "Inputs": ("[Read](../guides/rules.md#sibling)\n", "Work.\n", "Report.\n"),
            "Instructions": ("None.\n", "[Read](../guides/rules.md#sibling)\n", "Report.\n"),
            "Output": ("None.\n", "Work.\n", "[Read](../guides/rules.md#sibling)\n"),
        }[read_section]
        self.write_source(
            "# Task\n\n## Purpose\nProduces one task result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Reference guidance\n- [Sibling](../guides/rules.md#sibling)\n\n"
            "## Inputs\n" + body[0] + "\n## Instructions\n" + body[1]
            + "\n## Output\n" + body[2]
        )

    def publish_current(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def publish(self, *arguments):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / PUBLISHER.name), *arguments],
            cwd=self.root.parent,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_publishes_self_contained_skill_with_frontmatter(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self.output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "---")
        self.assertEqual(lines[1], "name: task")
        self.assertTrue(lines[2].startswith("description: "))
        self.assertNotEqual(lines[2], 'description: ""')
        self.assertEqual(lines[3], "hide: true")
        self.assertEqual(lines[4], "---")
        self.assertEqual(
            lines[5], "<!-- GENERATED BY scripts/build-skills.py; DO NOT EDIT. -->"
        )
        content = "\n".join(lines[6:])
        self.assertIn("## Included guidance", content)
        self.assertIn("Preserve the parent obligation.", content)
        self.assertIn("## Task", content)
        self.assertIn("# Task", content)
        self.assertIn("Apply the supplied obligations.", content)
        self.assertIn("## Supply inputs", content)

    def test_parent_after_child_preserves_all_rules_once(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.output.read_text(encoding="utf-8")
        for obligation in ("parent", "child", "sibling"):
            self.assertEqual(content.count("Preserve the " + obligation + " obligation."), 1)

    def test_freshness_check_detects_changed_guidance_without_writing(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        previous = self.output.read_bytes()
        self.rules.write_text(self.rules.read_text(encoding="utf-8") + "\nA new obligation.\n", encoding="utf-8")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.output.read_bytes(), previous)
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A new obligation.", self.output.read_text(encoding="utf-8"))
        self.assertEqual(self.publish("--check").returncode, 0)

    def test_unrecognized_output_is_not_overwritten(self):
        self.output.parent.mkdir(parents=True)
        user_content = "These are independently maintained user instructions.\n"
        self.output.write_text(user_content, encoding="utf-8")
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.output.read_text(encoding="utf-8"), user_content)

    def test_agent_check_accepts_a_passing_agent(self):
        self.publish_current()
        result = self.publish("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_skill_has_agent_rule_fails(self):
        self.publish_current()
        self.agent.unlink()
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("skill task: skill-has-agent:", result.stderr)

    def test_agent_has_skill_rule_fails(self):
        self.publish_current()
        self.write_agent(skill="missing")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent task-agent.md: agent-has-skill:", result.stderr)

    def test_name_matches_file_rule_fails(self):
        self.publish_current()
        self.write_agent(name="different-agent")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent task-agent.md: name-matches-file:", result.stderr)

    def test_standard_lines_rule_fails(self):
        self.publish_current()
        self.write_agent(omit_standard=COMPLETION_LINE)
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent task-agent.md: standard-lines:", result.stderr)

    def test_no_done_when_rule_fails(self):
        self.publish_current()
        self.write_agent(extra_body="You are done when the work is complete.")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent task-agent.md: no-done-when:", result.stderr)

    def test_reviewer_read_only_rule_fails(self):
        self.publish_current()
        self.agent.unlink()
        self.agent = self.root / "agents" / "review-task-agent.md"
        self.write_agent(name="review-task-agent", tools="read, write")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent review-task-agent.md: reviewer-read-only:", result.stderr)

    def test_valid_exception_suppresses_agent_rule(self):
        self.publish_current()
        self.agent.unlink()
        self.agent = self.root / "agents" / "review-task-agent.md"
        self.write_agent(name="review-task-agent", tools="read, write")
        self.write_routing_cases({
            "review-task-agent": {
                "positive": ["Review example task", "Check sample work", "Assess sample result"],
                "negative": [
                    {"request": "Draft a plan", "expected": None},
                    {"request": "Fix a bug", "expected": None},
                ],
            }
        })
        self.write_checks(
            exemptions={
                "review-task-agent": {
                    "reviewer-read-only": "This fixture exercises the exception."
                }
            }
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_skills_without_agents_suppresses_skill_rule(self):
        self.publish_current()
        self.agent.unlink()
        self.write_routing_cases({})
        self.write_checks(
            skills_without_agents={
                "task": "This fixture exercises a directly loaded skill."
            }
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exception_with_empty_reason_fails(self):
        self.publish_current()
        self.write_checks(
            exemptions={"task-agent": {"standard-lines": ""}}
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("reason must be a non-empty string", result.stderr)

    def test_exception_naming_missing_agent_skill_or_rule_fails(self):
        self.publish_current()
        cases = (
            (
                {},
                {"missing-agent": {"standard-lines": "A reason."}},
                "unknown agent",
            ),
            ({"missing-skill": "A reason."}, {}, "unknown skill"),
            (
                {},
                {"task-agent": {"missing-rule": "A reason."}},
                "unknown rule",
            ),
        )
        for skills_without_agents, exemptions, expected in cases:
            with self.subTest(expected=expected):
                self.write_checks(
                    skills_without_agents=skills_without_agents,
                    exemptions=exemptions,
                )
                result = self.publish("--check")
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stderr)

    def test_heading_reference_and_task_link(self):
        self.reference_source()
        result = self.publish_current()
        reference = self.output.parent / "references" / "rules--sibling.md"
        self.assertEqual(
            reference.read_text(encoding="utf-8"),
            "<!-- GENERATED BY scripts/build-skills.py; DO NOT EDIT. -->\n"
            "Source: guides/rules.md#sibling\n\n"
            "### Sibling\nPreserve the sibling obligation.\n",
        )
        content = self.output.read_text(encoding="utf-8")
        self.assertIn("[Read](skill://task/references/rules--sibling.md)", content)
        self.assertNotIn("## Reference guidance", content)
        self.assertIn("name lines words references", result.stdout)

    def test_whole_file_reference_and_internal_link(self):
        other = self.root / "guides" / "other.md"
        other.write_text("# Other\n\n## Rules\nApply another obligation.\n", encoding="utf-8")
        self.write_source(
            "# Task\n\n## Purpose\nProduces one result.\n\n"
            "## Required guidance\n- [Rules](../guides/other.md#rules)\n\n"
            "## Reference guidance\n- [Guide](../guides/rules.md)\n\n"
            "## Instructions\nRead [Guide](../guides/rules.md) when needed.\n"
        )
        self.rules.write_text(self.rules.read_text(encoding="utf-8") + "\n[Child](#child)\n", encoding="utf-8")
        self.publish_current()
        reference = self.output.parent / "references" / "rules.md"
        text = reference.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(
            "<!-- GENERATED BY scripts/build-skills.py; DO NOT EDIT. -->\nSource: guides/rules.md\n\n# Guide"
        ))
        self.assertIn("[Child](skill://task/references/rules.md)", text)
        self.assertIn("[Guide](skill://task/references/rules.md)", self.output.read_text(encoding="utf-8"))

    def test_reference_only_linked_from_inputs_fails(self):
        self.reference_source("Inputs")
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertIn("reference guidance not linked from Instructions or Output: rules--sibling.md", result.stderr)
        self.assertFalse(self.output.exists())

    def test_cross_list_selected_range_overlap_fails(self):
        self.reference_source()
        text = (self.root / "skill-sources" / "task.md").read_text(encoding="utf-8")
        self.write_source(text.replace(
            "## Reference guidance\n- [Sibling](../guides/rules.md#sibling)",
            "## Reference guidance\n- [Parent](../guides/rules.md#parent)",
        ))
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Required and Reference guidance overlap", result.stderr)

    def test_duplicate_derived_reference_filename_fails(self):
        directory = self.root / "guides" / "nested"
        directory.mkdir()
        (directory / "rules.md").write_text("# Different\n\n## Sibling\nDistinct.\n", encoding="utf-8")
        self.write_source(
            "# Task\n\n## Purpose\nProduces one result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Reference guidance\n- [One](../guides/rules.md#sibling)\n"
            "- [Two](../guides/nested/rules.md#sibling)\n\n"
            "## Instructions\nRead [One](../guides/rules.md#sibling) and "
            "[Two](../guides/nested/rules.md#sibling).\n"
        )
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate reference filename", result.stderr)

    def test_repeated_reference_entry_is_not_silently_deduplicated(self):
        self.reference_source()
        text = (self.root / "skill-sources" / "task.md").read_text(encoding="utf-8")
        self.write_source(text.replace(
            "- [Sibling](../guides/rules.md#sibling)",
            "- [Sibling](../guides/rules.md#sibling)\n- [Again](../guides/rules.md#sibling)",
        ))
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate reference filename", result.stderr)

    def test_reference_link_in_fence_does_not_satisfy_read_condition(self):
        self.reference_source()
        text = (self.root / "skill-sources" / "task.md").read_text(encoding="utf-8")
        self.write_source(text.replace(
            "## Instructions\n[Read](../guides/rules.md#sibling)",
            "## Instructions\n```\n[Read](../guides/rules.md#sibling)\n```",
        ))
        result = self.publish()
        self.assertEqual(result.returncode, 1)
        self.assertIn("reference guidance not linked from Instructions or Output", result.stderr)

    def test_reference_change_is_detected_without_writing(self):
        self.reference_source("Output")
        self.publish_current()
        reference = self.output.parent / "references" / "rules--sibling.md"
        previous = reference.read_bytes()
        self.rules.write_text(
            self.rules.read_text(encoding="utf-8").replace(
                "Preserve the sibling obligation.", "Preserve the revised sibling obligation."
            ),
            encoding="utf-8",
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("out of date: skills/task/references/rules--sibling.md", result.stderr)
        self.assertEqual(reference.read_bytes(), previous)

    def test_skill_description_uses_purpose_first_paragraph(self):
        self.write_source(
            "# Task\n\n## Purpose\nA precise description\nacross two physical lines.\n\n"
            "Second paragraph does not belong here.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Instructions\nWork.\n"
        )
        self.publish_current()
        self.assertIn(
            'description: "A precise description across two physical lines."',
            self.output.read_text(encoding="utf-8"),
        )

    def test_oversize_fails_check_and_publish_without_writing(self):
        self.write_source(
            "# Task\n\n## Purpose\nProduces one result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Instructions\n" + ("word " * 3801) + "\n"
        )
        for arguments in (("--check",), ()):
            result = self.publish(*arguments)
            self.assertEqual(result.returncode, 1)
            self.assertIn("oversize: skills/task/SKILL.md (", result.stderr)
            self.assertIn("limit 500/3800)", result.stderr)
            self.assertFalse(self.output.exists())

    def test_line_budget_counts_the_whole_skill(self):
        self.write_source(
            "# Task\n\n## Purpose\nProduces one result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Instructions\n" + ("one\n" * 501)
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("oversize: skills/task/SKILL.md (", result.stderr)
        self.assertIn("limit 500/3800)", result.stderr)

    def test_stale_reference_removed_on_publish(self):
        self.reference_source()
        self.publish_current()
        references = self.output.parent / "references"
        self.assertTrue(references.is_dir())
        self.write_source(
            "# Task\n\n## Purpose\nProduces one result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Instructions\nWork.\n"
        )
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale: skills/task/references/rules--sibling.md", result.stderr)
        self.publish_current()
        self.assertFalse(references.exists())

    def test_description_contract_and_exemption(self):
        self.publish_current()
        descriptions = (
            "Test agent",
            '"Use when tasked. Not for other work. MUST apply."',
            '"' + "x" * 401 + ' Use when X. Not for Y."',
        )
        for description in descriptions:
            with self.subTest(description=description[:30]):
                self.write_agent(description=description)
                result = self.publish("--check")
                self.assertIn("description-contract", result.stderr)
        self.write_checks(exemptions={"task-agent": {"description-contract": "Legacy fixture."}})
        self.assertEqual(self.publish("--check").returncode, 0)

    def test_routing_cases_contract_and_exemption(self):
        self.publish_current()
        invalid = {
            "task-agent": {
                "positive": ["Do the task", "Do the task", "Use task-agent to work"],
                "negative": [{"request": "Anything", "expected": "task-agent"}],
            }
        }
        self.write_routing_cases({**invalid, "missing-agent": {"positive": [], "negative": []}})
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("routing-cases", result.stderr)
        self.assertIn("unknown agent", result.stderr)
        self.write_routing_cases(invalid)
        self.write_checks(exemptions={"task-agent": {"routing-cases": "Fixture deliberately invalid."}})
        self.assertEqual(self.publish("--check").returncode, 0)

    def test_only_builds_selected_skill_without_stale_scan_or_agent_checks(self):
        self.write_source(
            "# Other\n\n## Purpose\nProduces another result.\n\n"
            "## Required guidance\n- [Child](../guides/rules.md#child)\n\n"
            "## Instructions\nWork.\n", name="other"
        )
        stale = self.root / "skills" / "orphan" / "SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text(
            "<!-- GENERATED BY scripts/build-skills.py; DO NOT EDIT. -->\n", encoding="utf-8"
        )
        self.write_agent(description='"Invalid."')
        result = self.publish("--check", "--only", "task")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "out of date: skills/task/SKILL.md\n")
        result = self.publish("--only", "task")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.output.exists())
        self.assertFalse((self.root / "skills" / "other" / "SKILL.md").exists())
        self.assertTrue(stale.exists())
        self.assertEqual(self.publish("--check", "--only", "task").returncode, 0)

    def test_verbatim_read_is_required_on_every_agent(self):
        self.publish_current()
        text = self.agent.read_text(encoding="utf-8").replace("read-summarize: false\n", "")
        self.agent.write_text(text, encoding="utf-8")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("verbatim-read: frontmatter must set read-summarize: false", result.stderr)
        self.write_checks(exemptions={"task-agent": {"verbatim-read": "summaries wanted"}})
        self.assertEqual(self.publish("--check").returncode, 0)

    def test_full_check_rejects_only_output_frontmatter_key(self):
        self.publish_current()
        text = self.agent.read_text(encoding="utf-8")
        self.agent.write_text(text.replace("tools: read\n", "tools: read\ncustom: allowed\n"), encoding="utf-8")
        self.assertEqual(self.publish("--check").returncode, 0)
        self.agent.write_text(text.replace("tools: read\n", "tools: read\noutput: {}\n"), encoding="utf-8")
        result = self.publish("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent task-agent.md: frontmatter must not contain output", result.stderr)

    def test_every_playbook_skill_delivers_shared_developer_request_guidance(self):
        repository = PUBLISHER.parent.parent
        shutil.copytree(repository / "guides", self.root / "guides", dirs_exist_ok=True)
        shutil.copytree(repository / "integrations", self.root / "integrations")
        shutil.copytree(
            repository / "skill-sources", self.root / "skill-sources", dirs_exist_ok=True
        )
        (self.root / "skill-sources" / "task.md").unlink()
        policy = self.root / "guides" / "communication-policy.md"
        lines = policy.read_text(encoding="utf-8").splitlines(keepends=True)
        headings = PUBLISHER_VALUES["parse_headings"](lines)
        requests = next(heading for heading in headings if heading.slug == "developer-requests")
        sentinel = "Developer-request adoption probe: preserve the complete decision context."
        lines.insert(requests.end, sentinel + "\n\n")
        policy.write_text("".join(lines), encoding="utf-8")

        names = sorted(path.stem for path in (repository / "skill-sources").glob("*.md"))
        for name in names:
            with self.subTest(skill=name):
                bundle, = PUBLISHER_VALUES["build_bundles"](self.root, only=[name])
                reference = bundle.output.parent / "references" / "communication-policy--rules.md"
                self.assertIn(reference, bundle.files)
                guidance = bundle.files[reference].decode("utf-8")
                self.assertIn(sentinel, guidance)
                self.assertNotIn("## Evidence", guidance)
                self.assertIn(
                    "skill://" + name + "/references/" + reference.name,
                    bundle.files[bundle.output].decode("utf-8"),
                )

    def test_blocking_decision_agents_deliver_omp_escalation_reference(self):
        repository = PUBLISHER.parent.parent
        for directory in ("guides", "integrations", "skill-sources"):
            shutil.copytree(repository / directory, self.root / directory, dirs_exist_ok=True)
        names = (
            "draft-implementation-plan",
            "draft-prd",
            "draft-product-vision",
            "draft-skill",
            "draft-system-architecture",
            "draft-system-design",
            "draft-technical-design",
            "orchestrate-implementation-plan",
            "orchestrate-fix",
        )
        integration = self.root / "integrations" / "omp.md"
        lines = integration.read_text(encoding="utf-8").splitlines(keepends=True)
        headings = PUBLISHER_VALUES["parse_headings"](lines)
        ask = next(
            heading for heading in headings
            if heading.slug == "developer-requests-and-omps-built-in-ask"
        )
        sentinel = "OMP escalation probe: return rendered requests to the interactive caller."
        lines.insert(ask.end, sentinel + "\n\n")
        integration.write_text("".join(lines), encoding="utf-8")

        for name in names:
            with self.subTest(skill=name):
                agent = PUBLISHER_VALUES["parse_agent"](
                    repository / "agents" / (name + "-agent.md")
                )
                tools = [tool.strip() for tool in agent.frontmatter["tools"].split(",")]
                self.assertIn("request_developer", tools)
                self.assertNotIn("ask", tools)
                if name.startswith("draft-"):
                    self.assertNotIn("bash", tools)

                bundle, = PUBLISHER_VALUES["build_bundles"](self.root, only=[name])
                reference = (
                    bundle.output.parent / "references"
                    / "omp--developer-requests-and-omps-built-in-ask.md"
                )
                self.assertIn(reference, bundle.files)
                guidance = bundle.files[reference].decode("utf-8")
                self.assertIn(sentinel, guidance)
                self.assertNotIn("## Templates", guidance)
                task = bundle.files[bundle.output].decode("utf-8")
                self.assertIn(
                    "(skill://" + name + "/references/" + reference.name + ")",
                    task,
                )
                self.assertNotIn(sentinel, task)


if __name__ == "__main__":
    unittest.main()
