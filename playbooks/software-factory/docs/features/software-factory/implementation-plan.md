---
state: draft
revision: plan-r2
---

# Implementation plan: Software factory

This plan lists what has to change in the Playbook to meet the [software factory PRD](prd.md). It does not follow the Playbook's own plan format: this is Playbook work, not a project built with the Playbook. Tasks name their target files, the change, what "done" looks like, their dependencies, and the PRD requirements they cover.

## Decisions this plan makes

Veto any of these before execution; each one changes several tasks.

1. **Two files and opt-in.** Approvals move out of frontmatter. The developer alone edits `docs/user-approvals.json`; its existence opts a consumer repository into enforcement. For a new project the orchestrator asks the developer to create `{}`. Agent acceptances live in `docs/agent-approvals.json`, written only through `doc_approval`. Frontmatter keeps `state` and `revision`; the `approved` key is removed.
2. **Content binding.** An approval is valid only while the document's body hashes to its recorded SHA-256; frontmatter revision is not part of approval validity.
   - The body is everything after the frontmatter, so a lifecycle edit such as `state: active` → `done` does not void an approval.
   - For implementation plans, the hash skips task `Assigned worktree:` and `Assigned branch:` lines, because the implementation orchestrator writes them at task pickup.
   - Any other content change voids the approval.
3. **Who approves what.**
   - **Developer:** the product vision, architecture, PRDs, and system designs.
   - **Agents:** technical designs and implementation plans, through `doc_approval`, requiring a current closed ledger and generated evidence.
   - **Nobody:** the roadmap is not gated, so recording an issue or trimming an item never reopens a gate. Playbook guides are Playbook internals, not product documents: they stay outside the approvals scheme and keep their current frontmatter rules.
   - **Revoking:** document-writing agents may revoke only agent acceptances through `doc_approval`; developer approvals lapse automatically on content changes. Review agents stay read-only. Agents never edit either approval file.
4. **One refusal text.** The hook blocks through OMP's native blocked-call result, with the shared message as its reason. `doc_approval` returns the same text as an ordinary result when it refuses. The text is defined once in `omp-extension.ts`.
5. **Inert unless opted in.** Every hook does nothing in a repository without `docs/user-approvals.json`, so the Playbook adds no friction to projects that do not use its documents.
6. **Review-round gate and ledger.**
   - **What counts:** main-session `task` dispatches of `review-doc-*` record rounds in tracked per-document ledgers under `.playbook/reviews/`; coherence has one ledger per feature. Subagent reviewer dispatches are unrecorded.
   - **Cycling stop:** an accepted Blocker/Major returning a second time after its fix, directly or through a duplicate chain, refuses the next dispatch; summarize recurrence, why fixes do not hold, options, and a recommendation. The developer's next answer lifts refusal; another return refuses again. Real Blocker/Major findings keep review going.
   - **Modes:** the harness chooses full reviews until a document has a decided full round with no accepted Blocker/Major, or, from the seventh full round on, no accepted Blocker, then change checks. Existing documents without ledgers get full first reviews. Coherence is full initially and when the set gains a document, otherwise a change check of edited documents. `request-full` records a reasoned request for the next dispatch; unchanged content refuses a change check. The ledger retains the last reviewed text as its baseline.
   - **Prerequisites:** previous report recorded or voided, every finding decided. Coherence additionally needs a recorded specialist system-design/TDD round and all feature document ledgers settled: no pending round, undecided finding, or open blocking finding. Reports are ingested automatically; callers read them in full.
   - **Decisions and scope:** `accepted`, `rejected`, Minor-only `nit`, or `duplicate` of an earlier finding, with reasons. Reopening rejection requires new evidence. Recurring accepted Blocker/Major duplicates reopen blocking work and require a fix and change check; rejected duplicates close quietly. Full reviews are blind. Change checks receive only the baseline diff and accepted fixes (including recurring ones), never rejected findings, dispositions, verdicts, or totals, and check fixes and diff-introduced Blocker/Major or broken dependents, not unchanged text unless the change makes it wrong.
   - **Receipt and status:** `close` requires a recorded round, no pending round, every finding decided, and no open blocking finding; apply accepted Minors first. Acceptance requires the current-body receipt and generates evidence. Only Playbook hooks and `review_ledger` write ledgers through `status`, `decide`, `void`, `close`, and `request-full`. Status shows per-round and next modes, recurrence, per-round line counts and overall growth, and `next`.
7. **Current work.** Factory status finds unfinished work in two places:
   - a PRD that is not `done`;
   - an unfinished system design, TDD, or plan beneath a `done` PRD, which covers fix slices.

   The current slice is the first unfinished slice in the system design's order, or the feature's single TDD. When more than one feature has unfinished work, the hooks do not block; the status line reports the ambiguity.
8. **Main-session skill.** The orchestrator is a skill, `orchestrate-factory`, loaded in the interactive session. It has no agent, because the session that talks to the developer must be the top session. It is listed in `agents/checks.json` `skillsWithoutAgents`.
9. **Run state has distinct owners.** Factory status reports documents and approvals. The orchestrator keeps execution phase; the harness ledger persists review rounds, finding decisions, and rejection reasons. Full status combines `factory_status`, `review_ledger status`, and execution phase.
10. **Version.** No `v1.0.0` tag has been released. `VERSION` stays `1.0.0`; rewrite the existing migration guide in place for the two-file design.

## Shared contracts

Every task uses these as written. A task that needs a different shape stops and reports instead of diverging.

### Two approval files

`docs/user-approvals.json` is developer-owned:

```json
{
  "docs/product-vision.md": "<64 lowercase hex>"
}
```

`docs/agent-approvals.json` contains agent acceptances:

```json
{
  "docs/features/example/tdd.md": {
    "hash": "<64 lowercase hex>",
    "evidence": "Review ledger closed at round 3: 7 findings decided (2 accepted, 3 rejected, 1 nit, 1 duplicate)."
  }
}
```

- **Keys:** repository-relative forward-slash document paths.
- **Ownership:** only the developer edits the user file, by hand. No script or tool writes it. Only `doc_approval` accept/revoke writes the agent file; missing agent file means no acceptances. `{}` is valid for either file.
- **Strict validation:** non-object top levels, wrong-gate keys, malformed hashes, and extra or missing agent-entry fields fail closed with a diagnostic naming the file and key. Hashes are exactly 64 lowercase hexadecimal characters; evidence is non-empty text. Roadmap and guide keys are forbidden.
- **Body bytes:** unchanged `body_sha256` rule: everything after frontmatter, exactly as stored; for implementation plans strip plain `- Assigned worktree:` and `- Assigned branch:` lines first.
- **Gates by type:** developer: product vision, architecture, PRD, system design; agent: technical design, implementation plan; none: roadmap, guide.
- **Validity:** the entry hash equals the current body hash. Gated `active`/`done` documents require valid approval; `draft`/`superseded` do not. Approval records contain no metadata beyond the shown values.

### `scripts/doc-approval.py`

A standard-library program in the style of the existing checkers: JSON on stdout, diagnostics on stderr, nonzero exit on failure. Helpers it shares with `check-doc-status.py` must not write `__pycache__` into a read-only install.

- `--status --repo <root> [--path <doc>]`: array of `{path, type, gate, approved, reason}`; reason is `"missing"`, `"hash mismatch"`, or null.
- `--accept --repo <root> --path <doc>`: agent-gated only; requires a current-body closed ledger and generates evidence; success `{status: "accepted", path}`, otherwise refusal `review-not-closed`. CLI-only `--migrated-from <date>` records inventoried legacy approval evidence without a ledger.
- `--revoke --repo <root> --path <doc> --reason <text>`: agent-gated only; removes entry; success `{status: "revoked"|"unchanged", path}`.
- Accept/revoke refuse developer-gated or ungated documents with exit 3 and `{status: "refused", reason: "developer-gated"|"ungated"}`, without writing.
- `--hash --repo <root> --path <file>`: any existing file inside the repo; read-only `{status: "hash", path, hash, line}`, where `line` is the paste-ready `"<path>": "<hash>",`.

Agent writes create the file if missing, with 2-space indentation, sorted keys, trailing newline, and atomic replacement. All writes target only the consumer repository's agent file, never the developer file or Playbook install. `doc_approval` modes are `status`, `accept`, and `revoke`.

### `scripts/factory-status.py`

`--repo <root>` prints:

```text
{feature, currentSlice, documents: [{path, type, state, approved, gate}], openGates: [path], nextStep: <sentence>, ambiguity: <sentence|null>}
```

- `nextStep` covers the document-derivable steps of the PRD's sequence (SF-001 to SF-009, SF-054). With an accepted TDD and plan that are not `done`, it says "implementation, review, or developer validation in progress".
- It prints `{feature: null, ...}` when there is no unfinished work.
- It prints `optedIn: false` and nothing else when `docs/user-approvals.json` is absent.

### Refusal message

Defined once in `omp-extension.ts`; hook and tool use identical text:

> Approval files are not edited directly. `docs/user-approvals.json` belongs to the developer: stop, render a developer request, and ask them to record approval; they can get the line to paste with `/playbook-hash <path>`. To accept or revoke a technical design or implementation plan, use `doc_approval`. Stopping here is the correct way to finish this turn, not a failure.

### Order-refusal message

Built from `factory-status.py`:

> `<document>` is waiting for `<developer|agent>` approval. Next expected step: `<nextStep>`. Discussion, research, and edits to existing documents are still open.

## Tasks

### Phase 1: governing documents and contract programs (parallel)

- **T1 — Product vision constraint.** Target: `docs/product-vision.md`.
  - Change: revise "Only the developer accepts" (L71) so it covers developer-gated documents. State that agents accept technical designs and implementation plans on evidence, never on a default or a timeout. Bump to `vision-r7`.
  - Done when the constraint no longer forbids agent acceptance of TDDs and plans, and no other vision text contradicts SF-024.
  - Covers SF-024, SF-028–SF-030. Gate: developer approval.
- **T2 — Architecture.** Target: `docs/architecture.md`.
  - Change:
    - a trust-boundary exception for `doc_approval` writing `docs/agent-approvals.json` in the consumer repository; the user file stays developer-only;
    - a "contract hooks" rule: hooks that enforce Playbook contracts live in `omp-extension.ts`, next to contract tools;
    - under tracked persistence, record per-document and feature-coherence ledgers under the consumer's `.playbook/reviews/`, written only by the Playbook;
    - consumer-contract entries for both approval files, `doc_approval`, `factory_status`, and the hooks, each naming its readers;
    - replace the `approved`-date wording at L65;
    - mark migrations `[EXISTS]` once T13a lands;
    - add the technology index rows.

    Bump to `arch-r9`.
  - Done when every new contract has one owner and named readers.
  - Covers SF-041. Gate: developer approval.
- **T3 — `scripts/doc-approval.py` and tests.** Targets: `scripts/doc-approval.py`, `tests/test_doc_approval.py`.
  - Change: implement the program contract above.
  - Tests:
    - developer-gated `--accept` is refused and leaves the file byte-identical;
    - a body edit invalidates an approval; a frontmatter-only edit does not;
    - writing a plan task's assignment lines does not invalidate the plan; any other plan edit does;
    - a revision bump alone does not invalidate approval;
    - roadmap and guide report `gate: "none"` and cannot have approval entries;
    - accept/revoke refuse developer and ungated types without writing;
    - malformed JSON, wrong-gate keys, invalid hashes, and extra/missing fields fail closed with precise file/key diagnostics;
    - hash mode is read-only; agent writes create missing files atomically in canonical format.
  - Done when the tests pass.
  - Covers SF-029–SF-032.
- **T4 — `check-doc-status.py` reads approvals.** Targets: `scripts/check-doc-status.py`, `tests/test_check_doc_status.py`, `tests/test_checker_no_write.py`, `tests/test_git_environment.py`. Depends on T3's hashing; share one helper module, or deliberately duplicate the few lines.
  - Change:
    - reject the `approved` frontmatter key, pointing to the migration guide;
    - for gated types, `active` and `done` require a valid approval; the roadmap needs none;
    - the `--json` row becomes `{path, type, state, revision, approval: {gate, valid}}`;
    - frozen-diff preserves delivered-document constraints and approval entries while allowing approval-file-only changes.
  - Done when the existing and updated tests pass, including a migrated active process-guide fixture.
  - Covers SF-024, SF-031, SF-056.
- **T5 — `scripts/factory-status.py` and tests.** Targets: `scripts/factory-status.py`, `tests/test_factory_status.py`. Depends on T3's helpers.
  - Change: implement the status contract above.
  - Tests:
    - an empty opted-in project yields the vision step, then architecture, then the PRD;
    - every document step for single-slice and multi-slice features yields the right `nextStep`;
    - a fix slice under a `done` PRD, single-slice and multi-slice, is found and becomes `currentSlice`;
    - an open developer gate appears in `openGates`;
    - two features with unfinished work produce `ambiguity`;
    - a repository without the user approval file yields `optedIn: false`.
  - Done when the tests pass.
  - Covers SF-002–SF-009, SF-034–SF-038.

### Phase 2: extension (one owner; depends on T3–T5)

- **T6 — Tools, hooks, and command.** Targets: `omp-extension.ts`, `tests/omp-extension.test.js`, `tests/optional-arguments.test.js`, `tests/run-check.test.js`, new `tests/hooks.test.js`.
  - **Tools:**
    - `doc_approval` (`status`, `revoke`, `accept`) wraps T3, and returns the shared refusal message as an ordinary result when it refuses;
    - `factory_status` wraps T5.
  - **Approvals-file guard** (`tool_call`, all sessions): block with the shared refusal message when
    - an `edit` or `write` path, or an `ast_edit` path or glob, resolves to either approval file, including directories and aliases; edit paths come from the edit input's file sections;
    - a `bash` or `eval` text names either approval filename together with a write pattern (redirection, `tee`, `sed -i`, `mv`, `cp`, `rm`, `truncate`, write-mode `open(`, `writeFile`, `Bun.write`).

    Reads such as `cat`, `jq` without in-place flags, and `git diff`, `log`, or `show` stay allowed.
  - **Creation guard** (`tool_call`, all sessions, including drafters): block a `write`, or an `edit` that creates a file, when it would create a document whose type is downstream of an open gate. Use the order-refusal message. Edits to existing documents always pass.
  - **Implementation gate** (`before_subagent_spawn`): block `orchestrate-implementation-plan-agent` unless the current slice's TDD and plan have valid approvals and every developer gate above them is approved. Worker, reviewer, and fix-agent spawns are not gated.
  - **Review-round gate** (`tool_call` on main-session `task` with `review-doc-*`): resolve one matching document or feature coherence subject, record through `scripts/review-ledger.py`, and gate later dispatches per decision 6 (SF-016). Subagent dispatches are unrecorded.
    - Lift cycling refusal on the developer's next answer; another return of that issue refuses again. Append the harness diff/accepted-fix packet for change checks and enforce coherence readiness.
    - **Ledger write guard:** refuse direct file, shell, and eval writes under `.playbook/reviews/`; only Playbook hooks and `review_ledger` write ledgers.
  - **Status line** (`before_agent_start`, main session only, `ctx.agent.kind === "main"`): append one status line from T5 and pointers to `review_ledger status` and `skill://orchestrate-factory`, keeping the base prompt intact.
  - **`/playbook-hash <path>`:** register with the positional command API, call T3 `--hash`, and show its paste-ready `line` including the path through `ctx.ui.notify` at info level. Write nothing.
  - **General:** every hook is inert per decision 5, and the test fakes gain `on` and `registerCommand`.
  - **Done when** Bun tests prove each case below, and `scripts/check-omp-load.py` passes with the new tool names.

    | Area | Must block | Must allow |
    | --- | --- | --- |
    | Approval files | Edit, AST-glob/directory/alias, and shell writes to either file | Shell reads |
    | Refusal text | — | Identical text from the hook and the tool |
    | Document order | Creating a downstream document while a gate is open | Revising an existing downstream document while a gate is open |
    | Implementation start | `orchestrate-implementation-plan-agent` without accepted TDD and plan | Nested worker and reviewer spawns |
    | Review-round gate | Fifth main-session round per document; pending report or undecided findings | Independent document counts; developer answer resets; timeout does not; subagent dispatches unrecorded |
    | Developer hash | — | Paste-ready entry through info notification; no write |
    | Opt-in | — | Every hook silent without the user approval file |

  - Covers SF-016, SF-017, SF-021, SF-022, SF-027–SF-032, SF-034–SF-038.

### Phase 3: guidance (parallel, disjoint files; depends on the shared contracts only)

- **T7 — Process guide.** Target: `guides/product-documentation-process.md`.
  - **Document state and revision** (L102–L123): the two approval files, content binding, developer, agent, and no gate by type, and `done` set only after the developer validates.
  - **Full-feature workflow** (L521–L571):
    - order: vision, then architecture once before the first PRD, then PRD, then a system design only for multi-slice features, then per slice TDD, plan, implementation, code review, and developer validation;
    - the review loop, harness-selected modes, and cycling stop, linking T8;
    - coherence readiness after specialist system-design/TDD review, with change checks of coherence edits and parents/dependents changed by cascade;
    - the gates by type;
    - failed validation: the developer chooses an in-slice correction, a document correction with replanning, or a new slice, then review and validation repeat;
    - after validation: deviations go to the main session, the TDD is revised, reviewed, and re-accepted, then the plan and TDD become `done`.
  - **Implementation execution** (L573–L652): every direct developer instruction becomes a report to the caller. That covers `.worktrees` (L365, L591), missing base prerequisites (L587), unavailable commands (L624), and the significant-issue procedure (L636–L646).
    - Small issues are fixed in-run through workers, with TDD deviations recorded in the ledger.
    - A large issue or repeated failure means stop, preserve work, report, and end.
    - Replan only the unfinished part, then resume from the ledger.
    - The post-integration review cycle links T10.
    - No `done` transitions.
  - **Lightweight path** (L82–L86) and **frozen-document rule** (L119–L121) become the post-delivery fix path:
    - known issues go to Beads when the repository has `.beads/`, otherwise to the roadmap's Known issues section;
    - a standalone fix restores documented behavior, adds a regression test, and goes through the review cycle and developer validation;
    - wrong documented behavior needs a new slice;
    - a fix-only slice adds a TDD and plan without a system design.
  - **Roadmap contract** (L210–L235): add Known issues, and state that the roadmap is not gated.
  - **PRD contract** (Feature Product Requirements Document): the altitude test keeps mechanisms out of requirements and acceptance intent, even visible ones, and a PRD never cites another document's revision or tracks the documents below it.
  - Done when no section requires developer acceptance of a TDD or plan, frontmatter approval, a direct developer ask from the implementation orchestrator, or `done` before developer validation.
  - Covers SF-002–SF-009, SF-018–SF-024, SF-042–SF-048, SF-053–SF-064.
- **T8 — Review rules.** Targets: `guides/document-review.md`, `guides/agents.md`.
  - Change:
    - the caller decides each finding, with a reason for every rejection;
    - the drafter applies only the findings it is given and does not triage;
    - the orchestrator may apply small, precise edits itself;
    - a rejected finding is not accepted later without new evidence; reasons and decisions persist in the harness ledger;
    - after each round, the caller states whether another is needed and why;
    - cycling refusal on the second return of an accepted Blocker/Major after its fix, developer escalation, and lifting refusal on the developer's next answer;
    - full versus change-check scope, reasoned full-review requests, unchanged-content refusal, coherence readiness and post-coherence change checks.
  - Done when the triage/apply split has one home and the drafters can link to it.
  - Covers SF-010–SF-020.
- **T9 — Developer gates in communication.** Target: `guides/communication-policy.md`.
  - Change:
    - approval requests name what the developer is asked to agree to: read in full and accept for the vision and PRD, understand well enough to explain and defend, and agree for architecture and system design;
    - an architecture or system design approval request briefs the developer to explain and defend the whole design on first approval, or each change and changed decision on re-approval, pointing to the sections that hold the detail;
    - stopping at a developer gate or a limit is a correct finish to the turn.
  - Done when the rules attach to Developer requests (L31–L40).
  - Covers SF-021–SF-023, SF-025–SF-027.
- **T10 — Code review cycle.** Target: `guides/code-review.md`.
  - Change: add a review cycle section.
    - Pick reviewers by the languages in the changed files (TypeScript, Python, Rust, Tauri), plus design, invariants, tests, and unused-code reviews every time.
    - The orchestrator triages findings, delegates fixes, and revalidates the application and the slice.
    - At most four cycles, then stop and report what happened, the open issues, and the proposed fix.
    - After a clean cycle, state whether another round is worthwhile and which reviews it needs.
  - Done when the implementation and fix orchestrators can both link one section.
  - Covers SF-049–SF-052, SF-060.
- **T11 — Roadmap template.** Target: `templates/roadmap.md`.
  - Change: add the Known issues section and remove the frontmatter approval instruction.
  - Covers SF-057.
- **T12 — Integration notes.** Targets: `integrations/omp.md`, `README.md`.
  - Change:
    - list every tool, including `check_doc_status` and `run_check`, which `integrations/omp.md` omits today;
    - list the hooks and `/playbook-hash`;
    - explain loading `/skill:orchestrate-factory` in the main session;
    - explain the opt-in file;
    - state the enforcement goal: forgotten steps, not deliberate circumvention.
  - Covers SF-039, SF-041.
- **T13a — Migration guide and version.** Targets: `guides/migrations/0.1.0-to-1.0.0.md`, `VERSION`.
  - Change: rewrite the existing migration guide in place:
    - developer-gated documents: the developer creates `docs/user-approvals.json`, obtains each entry through `/playbook-hash <path>`, and pastes it by hand;
    - TDDs and plans: migrate inventoried dates with CLI-only `--migrated-from <date>`; otherwise review and check, close the current ledger, then `doc_approval accept` without evidence;
    - remove legacy frontmatter approval keys and obsolete records; roadmap remains ungated.

    Keep `VERSION` at `1.0.0`; no `v1.0.0` tag has shipped.
  - Covers SF-024.

### Phase 4: skills and agents (parallel; depends on T7–T10 for link targets)

- **T14 — Main-session orchestrator skill.** Targets: `skill-sources/orchestrate-factory.md`, `agents/checks.json`.
  - **Starting:** ask the developer to create `docs/user-approvals.json` containing `{}` for a new project, then ask for the next feature, offering roadmap Now and Next items.
  - **Sequence:** vision, then architecture once, then PRD, then a system design only for multiple slices. Per slice: TDD, plan, implementation through the implementation orchestrator, the review cycle, and developer validation.
  - **Document loop:** decide every finding through `review_ledger`, have the drafter apply accepted findings, respect harness-selected full/change-check modes and cycling refusal, close, and run coherence readiness and cascade change checks.
  - **Approvals:** render developer gates with ledger status through `request_developer`, ask for `/playbook-hash <path>` and a hand-pasted entry, then end the turn; agent acceptance requires a current closed ledger through `doc_approval accept` without evidence. Never edit approval files or ledgers directly.
  - **Run state:** keep execution phase; read rounds and finding decisions from `review_ledger status` and combine with `factory_status` on request. Offer the next step itself.
  - **Implementation reports:** on a large-issue report, pick the wrong document, run its loop and gate, re-review below it, replan the unfinished part, and resume the implementation orchestrator.
  - **After validation:** collect deviations, then revise, review, and re-accept the TDD, then mark the plan and TDD `done`.
  - **Failed validation:** follow the branches from T7.
  - **Known issues:** record them, and offer the choice between a standalone fix and a new slice.
  - Every subagent report returns here; only this session asks the developer.
  - Add `skillsWithoutAgents.orchestrate-factory` with its reason.
  - Done when `scripts/build-skills.py --check` passes, the generated skill stays within 500 lines and 3,800 words, and each branch named above has a numbered step with its completion condition.
  - Covers SF-001–SF-027, SF-038–SF-040, SF-045, SF-047, SF-048, SF-053–SF-058.
- **T15 — Implementation orchestrator.** Targets: `skill-sources/orchestrate-implementation-plan.md`, `agents/orchestrate-implementation-plan-agent.md`.
  - **Gates** (L30, L47, L55): valid approvals for the plan and TDD replace execution authorization and `approved` dates.
  - **Escalation:** every developer ask (skill L37–L38, L89, L98; agent body L19, "return to the developer") becomes a report to the caller. Stop and end on a large issue.
  - **Small issues:** fixed in-run through workers. The delegate-only boundary (agent body L20, skill L51) stays.
  - **Workers** get execute-only handoffs.
  - **Deviations:** record TDD deviations and return them in the completion report.
  - **Review:** run the T10 review cycle after integration.
  - **Completion report:** keeps "Your validation steps" (L95) and drops the `done` transitions (L83).
  - **Agent:** add `doc_approval` to its tools, and update its description to say it reports to its caller.
  - Done when no step asks the developer directly.
  - Covers SF-040, SF-042–SF-046, SF-048–SF-054.
- **T16 — Fix orchestrator.** Targets: `skill-sources/orchestrate-fix.md`, `agents/orchestrate-fix-agent.md`, `agents/routing-cases.json`, `tests/test_build_skills.py` (the L585–L613 list of agents that must have `request_developer`).
  - Change:
    - it takes one known issue, with expected and actual behavior;
    - workers fix it and add a regression test;
    - then it runs the T10 cycle and returns a validation-steps report;
    - it refuses work that changes documented behavior and reports that a new slice is needed.

    Agent frontmatter mirrors the implementation orchestrator: `spawns: "*"`, `run_check`, `request_developer`, `doc_approval`. Routing cases: at least three positive and two negative.
  - Covers SF-059–SF-061.
- **T17 — Drafters.** Targets:
  - `skill-sources/draft-product-vision.md`
  - `skill-sources/draft-system-architecture.md`
  - `skill-sources/draft-prd.md`
  - `skill-sources/draft-system-design.md`
  - `skill-sources/draft-technical-design.md`
  - `skill-sources/draft-implementation-plan.md`
  - the matching six `agents/draft-*-agent.md`

  Change:
  - replace each reviewer-report hook with "apply the accepted findings and reasons you are given; do not decide which findings to accept" (vision L34, architecture L38, PRD L38, system design L40 and L51, TDD L42, plan L31);
  - the plan drafter requires an agent-accepted TDD instead of developer acceptance (L24, L34);
  - remove the system-design exception that allows a single-slice system design (draft-system-design L44);
  - add `doc_approval` to the six drafter agents' tools.
  - allow revocation only of agent acceptances through `doc_approval`; developer approvals lapse automatically on content changes; never edit either approvals file or accept one's own document.

  One task, because the edit is the same in each file. Covers SF-007, SF-012, SF-013, SF-024, SF-029.
- **T18 — Reviewers.** Targets: `skill-sources/review-doc-implementation-plan.md` (L39), `skill-sources/review-doc-coherence.md` (L50–L51, L65).
  - Change: approval state comes from the two files through `check_doc_status` as `{gate, valid}`. The plan reviewer confirms the TDD's agent acceptance, not developer acceptance. Reviewer tools stay read-only.
  - Covers SF-024.

### Phase 5: developer environment

This repository is not a factory project and is not migrated: its own documents keep their current frontmatter. The migration guide (T13a) is for consumer repositories only.

- **T19 — Beads rule.** Target: `~/.omp/agent/AGENTS.md`, outside the repository.
  - Change: remove the rule that limits Beads to explicit requests, keeping the `bd where` and `bd prime` discovery steps.
  - Done when the file no longer forbids agents from recording issues in Beads.
  - Covers SF-057.

### Phase 6: verification

- **T20 — Gates.** Run:

  ```sh
  python3 scripts/build-skills.py
  python3 scripts/build-skills.py --check
  python3 -m unittest discover -s tests
  bun test
  python3 scripts/check-omp-load.py
  mise run lint-markdown
  ```

- **T21 — Smoke run in a scratch repository.** Create a throwaway Git repository. Load the extension in a real interactive OMP session; the existing load check has no UI and cannot exercise approvals or `ask`. Observe:
  1. **Starting from nothing:** after the developer creates `docs/user-approvals.json` containing `{}`, the empty repository shows the vision step, and creating a PRD before vision and architecture approval is refused.
  2. **Protecting both approval files:**
     - editing either approval file with `edit` is blocked, and so is a write through `bash`;
     - reading either file is allowed;
     - `doc_approval accept` on the PRD returns the same message as the hook.
  3. **Developer approval:** `/playbook-hash <path>` displays the paste-ready entry without writing; the developer pastes it into the user file, and a later body edit voids approval.
  4. **Agent gates and document order:**
     - `doc_approval accept` on a TDD records an acceptance;
     - a drafter revising an existing TDD while the PRD gate is open is allowed;
     - creating a new TDD while that gate is open is refused.
  5. **Review-round gate:** a fifth main-session round for one document is refused; a developer response resets the count. Documents have separate counts, and subagent dispatches are unrecorded.
  6. **Status line:** it appears in the main session and not in subagents.
  7. **Opt-in:** hooks are silent in a repository without `docs/user-approvals.json`.

  Then delete the scratch repository.

## Out of scope

General improvements to the implementation orchestrator beyond what the PRD requires, and the feature record idea in the [roadmap](../../roadmap.md).
