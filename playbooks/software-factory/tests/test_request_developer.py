"""Consumer-visible developer request validation and rendering contracts."""
import re
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "request-developer.py"


def request(kind="decision"):
    record = {
        "version": 1, "kind": kind, "title": "Search ranking", "context": "Search in docs/search/prd.md needs ranking before release; alphabetical ordering was tried.",
        "question": "Which ranking should search use?", "blocking": kind == "blocked",
        "intentBasis": [{"source": "docs/search/prd.md", "reference": "US-1", "relevance": "Relevance serves fast discovery; alphabetical harms discovery but serves known-title lookup."}],
    }
    if kind == "decision":
        record.update(options=[
            {"label": "Relevance", "strengths": ["Serves US-1 discovery"], "weaknesses": ["Less predictable order"], "downstream": "Implement relevance ranking."},
            {"label": "Alphabetical", "strengths": ["Predictable known-title lookup"], "weaknesses": ["Harms US-1 discovery"], "downstream": "Keep title ordering."},
        ], recommendation={"option": "Relevance", "rationale": "US-1 prioritizes discovery."}, maintainability="Alphabetical is simpler, secondary to US-1.")
    elif kind == "approval":
        record["acceptance"] = "docs/search/prd.md revision prd-r2"
    elif kind == "input":
        record["needed"] = "The private catalog export"
    else:
        record["requiredAction"] = "Grant access to the private catalog"
    return record


class RequestDeveloperTests(unittest.TestCase):
    def run_request(self, value):
        return subprocess.run([sys.executable, str(SCRIPT), "--request", json.dumps(value)], capture_output=True, text=True)

    def assert_invalid(self, value, message):
        result = self.run_request(value)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)

    def test_all_kinds_render_the_requested_action(self):
        for kind, detail in (("decision", "US-1 prioritizes discovery."), ("approval", "prd-r2"), ("input", "private catalog export"), ("blocked", "Grant access")):
            with self.subTest(kind=kind):
                result = self.run_request(request(kind))
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                self.assertIn(detail, result.stdout)
                self.assertIn("docs/search/prd.md — US-1", result.stdout)
        rendered = self.run_request(request()).stdout
        self.assertLess(rendered.index("Intent basis"), rendered.index("Maintainability"))
        self.assertIn("Weaknesses: Less predictable order", rendered)
        self.assertIn("Downstream: Implement relevance ranking.", rendered)

    def test_each_kind_requires_its_fields(self):
        for kind, fields in (("decision", ("options", "recommendation", "maintainability")), ("approval", ("acceptance",)), ("input", ("needed",)), ("blocked", ("requiredAction",))):
            for field in fields:
                with self.subTest(kind=kind, field=field):
                    value = request(kind)
                    del value[field]
                    self.assert_invalid(value, field + ": required")

    def test_common_required_fields_and_version(self):
        for field in ("version", "kind", "title", "context", "question", "blocking"):
            value = request()
            del value[field]
            self.assert_invalid(value, field + ": required")
        for version in (0, 2, "1", True, 1.0, None):
            value = request()
            value["version"] = version
            self.assert_invalid(value, "version")

    def test_decision_option_boundaries_and_recommendation(self):
        for count in (0, 1, 6):
            value = request()
            value["options"] = [dict(value["options"][0], label=str(i)) for i in range(count)]
            self.assert_invalid(value, "options")
        value = request()
        value["recommendation"]["option"] = "Other"
        self.assert_invalid(value, "must name an option label exactly")
        value = request()
        value["options"][1]["label"] = "Relevance"
        self.assert_invalid(value, "labels must be unique")

    def test_intent_grounding_or_explicit_reason_not_both(self):
        value = request()
        value["intentBasis"] = []
        self.assert_invalid(value, "exactly one of intentBasis")
        value["intentBasisUnavailableReason"] = "No vision or PRD applies to this repository maintenance decision."
        self.assertEqual(self.run_request(value).returncode, 0)
        value["intentBasis"] = request()["intentBasis"]
        self.assert_invalid(value, "exactly one of intentBasis")
        value = request()
        value["intentBasis"][0]["reference"] = "  "
        self.assert_invalid(value, "reference: must be non-empty text")

    def test_unknown_fields_rejected_even_when_empty(self):
        for extra in (None, "", [], {}):
            value = request()
            value["typo"] = extra
            self.assert_invalid(value, "typo: unknown field")
        value = request()
        value["options"][0]["extra"] = 1
        self.assert_invalid(value, "extra: unknown field")

    def test_optional_empty_values_but_required_empty_values_rejected(self):
        for empty in (None, "", [], {}):
            value = request()
            value.update(acceptance=empty, needed=empty, requiredAction=empty, intentBasisUnavailableReason=empty)
            self.assertEqual(self.run_request(value).returncode, 0)
            value["recommendation"] = empty
            self.assert_invalid(value, "recommendation")
        value = request("blocked")
        value["blocking"] = False
        self.assert_invalid(value, "blocking: must equal true")

    def test_nested_shapes_and_non_object_requests_fail_cleanly(self):
        for value in (None, [], "request"):
            self.assert_invalid(value, "expected object")
        value = request()
        value["options"][0]["strengths"] = []
        self.assert_invalid(value, "strengths: needs at least 1 items")
        value = request()
        value["kind"] = {"malformed": True}
        self.assert_invalid(value, "kind: expected string")

    def test_kind_specific_fields_rejected_after_normalization(self):
        fields = {"options": request()["options"], "recommendation": request()["recommendation"],
                  "maintainability": "Lower coupling", "acceptance": "docs/search/prd.md prd-r2",
                  "needed": "Private export", "requiredAction": "Grant access"}
        allowed = {"decision": {"options", "recommendation", "maintainability"},
                   "approval": {"acceptance", "options", "recommendation"},
                   "input": {"needed"}, "blocked": {"requiredAction"}}
        for kind, permitted in allowed.items():
            for field, content in fields.items():
                if field in permitted:
                    continue
                with self.subTest(kind=kind, field=field):
                    value = request(kind)
                    value[field] = content
                    self.assert_invalid(value, field + ": field is not allowed")
                    value[field] = None
                    self.assertEqual(self.run_request(value).returncode, 0)
        value = request("approval")
        value.update(options=fields["options"], recommendation=fields["recommendation"])
        self.assertEqual(self.run_request(value).returncode, 0)

    def test_supplied_markdown_is_literal_and_newlines_survive(self):
        attack = "First\n```markdown\n# Forged heading\n> quote\n1. item\n- bullet\n+ bullet\n    indented\n<script>alert('x')</script>\n[link](https://example.test)\n~~~\n```"
        value = request()
        value.update(title="Title " + attack, question="Question " + attack,
                     context="Context " + attack, maintainability="Maintenance " + attack)
        for index, option in enumerate(value["options"]):
            option.update(label="Choice " + str(index) + " " + attack,
                          strengths=["Strength " + str(index) + " " + attack],
                          weaknesses=["Weakness " + str(index) + " " + attack],
                          downstream="Downstream " + str(index) + " " + attack)
        value["recommendation"] = {"option": value["options"][0]["label"], "rationale": "Rationale " + attack}
        value["intentBasis"] = [{"source": "Source " + attack, "reference": "Reference " + attack, "relevance": "Relevance " + attack}]
        result = self.run_request(value)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        for structural in ("```", "~~~", "\n# Forged", "\n> quote", "\n1. item", "\n- bullet", "\n+ bullet", "\n    indented", "<script>", "[link]("):
            self.assertNotIn(structural, result.stdout)
        decoded = re.sub(r"\\([\\`*_\[\]<>|~#\-+. \t])", r"\1", result.stdout).replace("  \n", "\n")
        for supplied in (value["title"], value["question"], value["context"], value["maintainability"],
                         value["recommendation"]["rationale"], *value["intentBasis"][0].values()):
            self.assertIn(supplied, decoded)
        for option in value["options"]:
            for supplied in (option["label"], option["downstream"], *option["strengths"], *option["weaknesses"]):
                self.assertIn(supplied, decoded)

    def test_stdin_preserves_large_json_request_and_cli_fallback(self):
        value = request("input")
        value["context"] = "Catalog record detail " * 20000
        result = subprocess.run([sys.executable, str(SCRIPT), "--stdin"], input=json.dumps(value), capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertIn(value["context"], result.stdout)
        ordinary = request("input")
        piped = subprocess.run([sys.executable, str(SCRIPT), "--stdin"], input=json.dumps(ordinary), capture_output=True, text=True)
        self.assertEqual(piped.stdout, self.run_request(ordinary).stdout)

    def test_plain_sentence_and_path_are_byte_identical(self):
        sentence = "Don't change skill-sources/a-b.md (it's the current path). Is that clear?"
        value = request("input")
        value.update(question=sentence, context=sentence, needed=sentence)
        result = self.run_request(value)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertIn("\n" + sentence + "\n", result.stdout)
        self.assertIn("**Context:** " + sentence + "\n", result.stdout)
        self.assertIn("**Needed:** " + sentence + "\n", result.stdout)
        self.assertNotIn("&#", result.stdout)


if __name__ == "__main__":
    unittest.main()
