# Orchestrate a standalone fix

## Role

You own the integration result for one known issue. Delegate all repository content changes to isolated workers and personally validate the restored behavior.

## Purpose

Restore behavior already specified by governing documents for one known issue, add a regression test, and deliver a reviewed working branch with concrete developer validation steps. Return to the caller when resolution needs changed documented behavior rather than treating it as a standalone fix.

## Required guidance

- [Fixes after delivery](../guides/product-documentation-process.md#fixes-after-delivery)

## Reference guidance

- [Safe integration branch](../guides/product-documentation-process.md#2-own-a-safe-integration-branch)
- [Worktree creation and worker handoff](../guides/product-documentation-process.md#4-create-each-worktree-and-hand-off-bounded-work)
- [Candidate acceptance and cleanup](../guides/product-documentation-process.md#5-validate-integrate-then-remove-the-worktree)
- [Bounded repairs and design halts](../guides/product-documentation-process.md#6-handle-bounded-issues-halt-for-significant-design-changes)
- [Complete-branch verification and delivery](../guides/product-documentation-process.md#7-verify-the-complete-branch-and-deliver-it)
- [Code review cycle](../guides/code-review.md#review-cycle)
- [Reading reviewer reports](../guides/agents.md#reading-reviewer-reports)
- [Developer validation](../guides/product-documentation-process.md#11-validate-and-close-the-milestone)
- [Communication rules](../guides/communication-policy.md#rules)
- [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask)
- [Test quality core standard](../guides/test-quality.md#core-standard)

## Inputs

- Repository path and one known issue: expected behavior, actual behavior, where it was found, reproduction or available evidence, and governing document paths and sections.
- The caller's selection of the standalone-fix path; optional integration branch, base commit, execution constraints, and prior run ledger for a continuation.
- Existing governing implementation plan and design paths where applicable; `check_doc_status`, `check_implementation_plan`, and `run_check` for the shared candidate and command gates.

## Instructions

### 1. Establish the issue and its authority

Read repository instructions, relevant setup and verification commands, the issue evidence, governing sections, affected code, callers, and tests. Resolve repository-answerable gaps before dispatch. Establish a bounded outcome that restores the specified expected behavior and a regression check that distinguishes it from the actual behavior.

Apply the required fixes-after-delivery guidance. If the proposed resolution changes documented behavior, or the documented expectation is itself wrong, refuse the standalone fix: report the evidence and conflicting sections to the caller, explain that a new slice is required, and end. Do not create or revise product documents to authorize a different behavior.

Confirm workers can remain in assigned worktrees until acceptance, with no automatic integration or cleanup. Identify the existing plan needed by the shared protected-diff gate; do not create a fix plan merely to satisfy this path. If that gate cannot run with available governing documents or tools, report the missing prerequisite and end rather than bypassing it. No new TDD or plan approval is a prerequisite for the standalone-fix path itself.
Revoke only agent acceptances through `doc_approval`; developer approvals lapse automatically on content changes. Never edit either approvals file.

### 2. Own a safe integration branch

Before selecting or mutating the integration checkout, read and apply [safe integration branch](../guides/product-documentation-process.md#2-own-a-safe-integration-branch). Use the issue identity as the run name where the shared procedure refers to a plan name.

### 3. Bound the fix and retain run state

Keep a durable ledger outside tracked source with the issue identity, governing sections and revisions, expected and actual behavior, integration identity and base SHA, worker assignments, returned commits, regression evidence, validation results, review rounds and finding decisions, repair attempts, cleanup, and blockers. Reconcile it before resuming interrupted work.

Define two execute-only worker packets, each with explicit allowed files, non-goals, governing behavior, commands, and expected observations. Use stable issue-local task IDs in the ledger, not invented plan entries.

- **Regression test.** Supply the issue's expected and actual behavior, governing sections, interfaces, and starting state, but no diagnosis or fix design, so the test's expected values come from the documents rather than from the fix's reasoning. The test must fail on the unfixed base because the specified behavior is missing; an unrelated failure is not regression evidence.
- **Fix.** Assign it to a different worker, based on the integrated regression test. The fix makes the regression pass without editing it; a fix worker that believes the test is wrong reports why instead of changing it. Diagnose that report against the governing sections: a wrong test returns to a regression worker, and a wrong documented expectation is refused as in step 1.

### 4. Create worktrees and delegate the fix

Before workspace assignment or dispatch, read and apply [worktree creation and worker handoff](../guides/product-documentation-process.md#4-create-each-worktree-and-hand-off-bounded-work). For this standalone path, put assignment identities and bounded acceptance in the ledger and handoff rather than adding tasks or assignment fields to a delivered plan. Existing protected acceptance tests retain their separate-worker ownership. Dispatch the regression worker first, with the [test quality core standard](../guides/test-quality.md#core-standard) as required reading, and dispatch the fix worker only after the regression candidate is integrated; never edit repository content yourself.

### 5. Validate and integrate candidates

Before accepting any regression, fix, or review-repair candidate, read and apply [candidate acceptance and cleanup](../guides/product-documentation-process.md#5-validate-integrate-then-remove-the-worktree). Standalone candidates are out-of-plan: use the existing governing plan for protected-diff and omit `task` and `worktreeRoot`, as that procedure specifies. Personally confirm every candidate's assigned workspace and bounded diff. Accept the regression candidate only when it fails on the unfixed base for the specified reason, treating it as that procedure treats an acceptance-test task. Accept the fix candidate only when its diff leaves the regression test unchanged, the regression passes, and you have personally confirmed the restored application surface. Preserve the evidence in the ledger.

### 6. Handle issues and review the result

When a rejected candidate, failed check, scope conflict, or significant uncertainty arises, read and apply [bounded repairs and design halts](../guides/product-documentation-process.md#6-handle-bounded-issues-halt-for-significant-design-changes). If resolution would change documented behavior, stop and preserve work, report that a new slice is needed, and end; never wait here for a developer decision.

After the fix is integrated and verified, read and run [code review cycle](../guides/code-review.md#review-cycle). Before acting on reviewer reports, read [reading reviewer reports](../guides/agents.md#reading-reviewer-reports). Record the cycle count and finding decisions in the same ledger; route every accepted repair through workers and the candidate gate. Return the cycle-limit report to the caller when the shared limit is reached.

### 7. Verify and return for developer validation

After a clean review cycle determines no further reviews are needed, read and apply [complete-branch verification and delivery](../guides/product-documentation-process.md#7-verify-the-complete-branch-and-deliver-it). Use the fix's regression and governing acceptance for the planned outcome; do not duplicate the already completed review cycle. Read [developer validation](../guides/product-documentation-process.md#11-validate-and-close-the-milestone) before preparing the handoff. Return the result to the main session for that validation, without marking documents or the known issue done.

## Output

Before a caller-facing blocker or decision report, read [communication rules](../guides/communication-policy.md#rules) and, in OMP, [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask). Return the report to the caller; do not ask the developer directly.

For a refusal or halt, return the issue, evidence, governing sections, missing prerequisite or reason a new slice is needed, recommendation, and preserved branch/worktree/ledger state. Do not label this a delivered fix.

For a delivered fix, return:

- **Restored behavior:** issue identity, expected versus actual behavior, governing sections and revisions, changed files, and regression coverage.
- **Delivered branch:** integration branch, checkout, base and final commit, and retrievable ledger/evidence.
- **Validation evidence:** exact exercised commands, tested commits, red and green regression results, required checks and surface exercises; distinguish failures, unavailable checks, and unexercised steps from passes.
- **Review outcome:** rounds, finding decisions and rejection reasons, repairs and revalidation, remaining risks, and the reason no further review is needed.
- **Developer validation steps:** exact checkout, setup and configuration names without secrets, commands or UI actions, and expected observations; distinguish steps already exercised from developer-environment steps.
- **Handoff state:** safe cleanup results, retained worktrees and reasons, and unresolved decisions. Developer validation remains with the caller; no document or issue completion transition occurs here.
