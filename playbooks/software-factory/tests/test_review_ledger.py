"""Black-box contracts for harness-recorded review rounds, finding decisions, and receipts."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "scripts" / "review-ledger.py"
TDD = "docs/features/example/slices/01-first/tdd.md"
TDD_REVIEWER = "review-doc-technical-design-agent"


def report(*findings):
    body = "\n\n".join(f"### {fid} \u2014 {title}\n\n**Severity:** {severity}\n\n**Evidence:** quoted."
                       for fid, severity, title in findings) or "None"
    return json.dumps(f"Outcome sentence.\n\n## Coverage\n\nx\n\n## Findings\n\n{body}\n\n## Questions\n\nNone\n")


class ReviewLedgerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="playbook ledger ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.reports = self.root / "session"
        self.reports.mkdir()
        self.write(TDD, "# Design\n")
        self.write("docs/features/example/prd.md", "# PRD\n")

    def write(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nstate: draft\n---\n" + body)

    def run_cli(self, *args, payload=None):
        command = [sys.executable, str(PROGRAM), *args[:1], "--repo", str(self.root), *args[1:]]
        if payload is not None:
            command.append("--stdin")
        return subprocess.run(command, input=None if payload is None else json.dumps(payload),
                              capture_output=True, text=True, check=False, timeout=20)

    def ok(self, *args, payload=None):
        result = self.run_cli(*args, payload=payload)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def refused(self, *args, payload=None):
        result = self.run_cli(*args, payload=payload)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        return json.loads(result.stdout)["message"]

    def dispatch(self, agent_id, text=f"Review `{TDD}` (tdd-r2) per your skill.", reviewer=TDD_REVIEWER,
                 since="2000-01-01T00:00:00.000Z", context=""):
        return self.run_cli("--dispatch", "--since", since, "--session-dir", str(self.reports),
                            payload=[{"index": 0, "reviewer": reviewer, "agentId": agent_id,
                                      "text": text, "context": context}])

    def review(self, agent_id, *findings, **kwargs):
        result = self.dispatch(agent_id, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.reports / f"{agent_id}.md").write_text(report(*findings))
        return json.loads(result.stdout)["rounds"][0]["round"]

    def status(self, subject=TDD, since="2000-01-01T00:00:00.000Z"):
        flag = "--path" if subject.endswith(".md") else "--feature"
        return self.ok("--status", flag, subject, "--since", since)["ledgers"][0]

    def decide(self, *decisions, subject=TDD):
        return self.run_cli("--decide", "--path", subject, payload=list(decisions))

    def test_rounds_are_recorded_out_of_docs_and_reports_ingested(self):
        self.review("R1", ("R1-F1", "Major", "Gap"), ("R1-F2", "Minor", "Wording"))
        ledger = self.root / ".playbook/reviews/features/example/slices/01-first/tdd.json"
        self.assertTrue(ledger.is_file())
        state = self.status()
        self.assertEqual(state["undecided"], ["1:R1-F1", "1:R1-F2"])
        self.assertEqual(state["nextMode"], "full")
        self.assertEqual(json.loads(ledger.read_text())["rounds"][0]["findings"][0]["severity"], "Major")
        self.ok("--decide", "--path", TDD, payload=[
            {"finding": "1:R1-F1", "decision": "rejected", "reason": "Parent assigns it."},
            {"finding": "1:R1-F2", "decision": "nit", "reason": "Cosmetic."}])
        self.write(TDD, "# Design, revised\n")
        self.review("R2")
        self.assertEqual([round_["mode"] for round_ in self.status()["rounds"]], ["full", "check"])
        self.assertEqual(self.status()["next"], "apply accepted Minor findings, then close")

    def test_next_round_waits_for_report_and_decisions(self):
        self.assertEqual(self.dispatch("R1").returncode, 0)
        self.assertIn("no recorded report", self.refused("--dispatch", "--since", "2000-01-01T00:00:00.000Z",
                                                          "--session-dir", str(self.reports), payload=[
            {"index": 0, "reviewer": TDD_REVIEWER, "agentId": "R2", "text": TDD, "context": ""}]))
        (self.reports / "R1.md").write_text(report(("R1-F1", "Major", "Gap")))
        self.assertIn("1:R1-F1", json.loads(self.dispatch("R2").stdout)["message"])
        self.ok("--decide", "--path", TDD, payload=[{"finding": "1:R1-F1", "decision": "accepted", "reason": "Real gap."}])
        self.assertEqual(self.dispatch("R2").returncode, 0)

    def test_full_reviews_until_a_clean_one_then_harness_written_change_checks(self):
        self.review("R1", ("R1-F1", "Major", "Gap"))
        self.ok("--decide", "--path", TDD, payload=[{"finding": "1:R1-F1", "decision": "accepted", "reason": "Real."}])
        self.write(TDD, "# Design\nGap closed.\n")
        self.review("R2", ("R1-F1", "Minor", "Name the queue"))
        self.assertEqual(self.status()["rounds"][1]["mode"], "full")
        self.ok("--decide", "--path", TDD, payload=[{"finding": "2:R1-F1", "decision": "accepted", "reason": "Clearer."}])
        self.assertEqual(self.status()["nextMode"], "check")
        self.write(TDD, "# Design\nGap closed.\nThe sign-in queue is named.\n")
        packet = json.loads(self.dispatch("R3").stdout)["rounds"][0]["packet"]
        self.assertIn("change check, not a full review", packet)
        self.assertIn("R1-F1 (Minor) \u2014 Name the queue", packet)
        self.assertIn("+The sign-in queue is named.", packet)
        (self.reports / "R3.md").write_text(report())
        self.assertIn("has not changed since its last review", json.loads(self.dispatch("R4").stdout)["message"])
        self.assertEqual(self.run_cli("--request-full", "--path", TDD, "--reason", " ").returncode, 2)
        self.ok("--request-full", "--path", TDD, "--reason", "Developer asked for a full pass.")
        result = json.loads(self.dispatch("R4").stdout)["rounds"][0]
        self.assertEqual((result["mode"], result["packet"]), ("full", None))
        self.assertEqual(self.status()["rounds"][-1]["fullReason"], "Developer asked for a full pass.")

    def test_new_blockers_keep_going_but_a_fix_that_keeps_failing_stops_until_the_developer_answers(self):
        for number in range(1, 7):
            self.write(TDD, f"# Design v{number}\n")
            self.review(f"R{number}", ("R1-F1", "Major", f"New gap {number}"))
            self.ok("--decide", "--path", TDD, payload=[{"finding": f"{number}:R1-F1", "decision": "accepted", "reason": "Real."}])
        for number in (7, 8):
            self.write(TDD, f"# Design v{number}\n")
            self.review(f"R{number}", ("R1-F1", "Major", "Gap 1 again"))
            self.ok("--decide", "--path", TDD, payload=[{"finding": f"{number}:R1-F1", "decision": "duplicate",
                                                         "reason": "Fix did not hold.", "duplicateOf": "1:R1-F1"}])
        self.assertIn("8:R1-F1", self.status()["openBlocking"][0])
        self.assertIn("blocking findings need a fix", self.refused("--close", "--path", TDD))
        self.write(TDD, "# Design v9\n")
        message = json.loads(self.dispatch("R9").stdout)["message"]
        self.assertIn("1:R1-F1 (New gap 1) has come back 2 times", message)
        self.assertEqual(self.dispatch("R9", since="2999-01-01T00:00:00.000Z").returncode, 0)

    def test_dispatch_needs_one_identifiable_subject(self):
        for text in ("Review the slice design.", f"Review `{TDD}` and `docs/features/example/slices/02-x/tdd.md`."):
            self.assertEqual(self.dispatch("R1", text=text).returncode, 3)
        self.assertEqual(self.dispatch("R1", text="Review the design.", context=f"Target: {TDD}").returncode, 0)

    def test_coherence_waits_for_a_ready_design_then_checks_only_the_edits(self):
        def coherence(agent_id):
            return self.dispatch(agent_id, reviewer="review-doc-coherence-agent", text="Whole-set coherence.",
                                 context="Documents: docs/features/example/prd.md, " + TDD)
        self.assertIn("no system design or TDD", json.loads(coherence("C1").stdout)["message"])
        self.review("R1", ("R1-F1", "Major", "Gap"))
        self.ok("--decide", "--path", TDD, payload=[{"finding": "1:R1-F1", "decision": "accepted", "reason": "Real."}])
        self.assertIn("1:R1-F1", json.loads(coherence("C1").stdout)["message"])
        self.write(TDD, "# Design, fixed\n")
        self.review("R2")
        result = json.loads(coherence("C1").stdout)["rounds"][0]
        self.assertEqual((result["subject"], result["mode"]), ("docs/features/example", "full"))
        (self.reports / "C1.md").write_text(report())
        self.write("docs/features/example/prd.md", "# PRD\nClarified.\n")
        result = json.loads(coherence("C2").stdout)["rounds"][0]
        self.assertEqual(result["mode"], "check")
        self.assertIn("+Clarified.", result["packet"])
        self.assertNotIn("tdd.md (current)", result["packet"])
        (self.reports / "C2.md").write_text(report())
        self.write("docs/features/example/slices/02-second/tdd.md", "# Second\n")
        self.assertEqual(json.loads(coherence("C3").stdout)["rounds"][0]["mode"], "full")

    def test_decision_rules(self):
        self.review("R1", ("R1-F1", "Major", "Gap"), ("R1-F2", "Minor", "Wording"))
        for decision in ({"finding": "1:R1-F1", "decision": "accepted", "reason": " "},
                         {"finding": "1:R1-F1", "decision": "nit", "reason": "Small."},
                         {"finding": "1:R1-F1", "decision": "duplicate", "reason": "Same.", "duplicateOf": "1:R9-F9"},
                         {"finding": "R1-F1", "decision": "rejected", "reason": "No round."}):
            self.assertEqual(self.decide(decision).returncode, 3, decision)
        self.assertEqual(self.decide({"finding": "1:R1-F1", "decision": "rejected", "reason": "Parent owns it."},
                                     {"finding": "1:R1-F2", "decision": "nit", "reason": "Cosmetic."}).returncode, 0)
        self.write(TDD, "# Design v2\n")
        self.review("R2", ("R1-F1", "Major", "Gap again"))
        self.assertEqual(self.decide({"finding": "2:R1-F1", "decision": "duplicate", "reason": "Re-raised.",
                                      "duplicateOf": "1:R1-F1"}).returncode, 0)
        for reference in ("1:R1-F1", "2:R1-F1"):
            self.assertIn("needs new evidence", json.loads(self.decide(
                {"finding": reference, "decision": "accepted", "reason": "Changed mind."}).stdout)["message"])
        self.assertEqual(self.decide({"finding": "2:R1-F1", "decision": "accepted", "reason": "Reopened.",
                                      "evidence": "Spike showed the parent rule cannot hold."}).returncode, 0)

    def test_close_needs_verified_blocking_fixes_and_binds_the_current_content(self):
        self.review("R1", ("R1-F1", "Blocker", "Unsafe"))
        self.ok("--decide", "--path", TDD, payload=[{"finding": "1:R1-F1", "decision": "accepted", "reason": "Real."}])
        self.assertIn("need a fix and a change check", self.refused("--close", "--path", TDD))
        self.write(TDD, "# Design, fixed\n")
        self.review("R2")
        self.assertTrue(self.ok("--close", "--path", TDD)["ledger"]["receiptCurrent"])
        self.write(TDD, "# Design, edited after close\n")
        self.assertFalse(self.status()["receiptCurrent"])
        self.ok("--close", "--path", TDD)
        self.review("R3")
        self.assertFalse(self.status()["receiptCurrent"])

    def test_void_and_failed_dispatch(self):
        self.assertEqual(self.dispatch("Lost").returncode, 0)
        self.assertEqual(self.run_cli("--void", "--path", TDD, "--round", "1", "--reason", " ").returncode, 2)
        self.ok("--void", "--path", TDD, "--round", "1", "--reason", "Reviewer was cancelled.")
        self.assertEqual(self.status()["rounds"][0]["status"], "void")
        self.assertEqual(self.dispatch("Failed").returncode, 0)
        self.ok("--reconcile", "--session-dir", str(self.reports), payload=[{"subject": TDD, "round": 2, "agentId": None}])
        self.assertEqual(len(self.status()["rounds"]), 1)
        self.assertEqual(self.dispatch("Guess").returncode, 0)
        self.ok("--reconcile", "--session-dir", str(self.reports), payload=[{"subject": TDD, "round": 2, "agentId": "Actual"}])
        (self.reports / "Actual.md").write_text(report())
        self.assertEqual(self.status()["rounds"][1]["status"], "recorded")

    def test_unreadable_report_stays_pending_with_its_error(self):
        self.assertEqual(self.dispatch("R1").returncode, 0)
        (self.reports / "R1.md").write_text(json.dumps("No sections at all."))
        self.assertIn("void round 1", self.status()["next"])


if __name__ == "__main__":
    unittest.main()
