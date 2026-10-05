# Code review contract

## Scope and evidence

This contract governs language, integration, and focused code reviews. Assess the requested focus in its actual context, not idealized architecture or only executable bugs.

1. Establish the requested technology or review focus, paths/component, and candidate identity. An explicit diff/base-target request is a change review: report issues introduced or materially worsened by that change, including affected unchanged callers, not unrelated existing debt; otherwise review the supplied current snapshot without inventing a baseline.
2. If no paths are supplied, map the repository and review its first-party code relevant to the selected technology or focus, excluding unrelated languages for a language review, vendored dependencies, and generated output as independent review targets. State the actual files/components and revision or working-tree state covered; do not claim comprehensive coverage of unread code or turn a language review into a repository-wide audit.
3. Read applicable instructions, relevant configuration, enclosing code, direct callers, existing tests, and contracts before judging a candidate issue. For language or integration reviews, cross into another language only through an actual API, serialization, foreign-function, IPC, lifecycle, or build connection needed to assess the target; stop when that contract is understood, and report a connected mismatch as one boundary finding rather than unrelated findings about foreign internals.
4. Ground version-sensitive claims in the installed toolchain/dependencies and applicable documentation. With missing source or configuration, finish supported checks and name the precise coverage limit or question; absence of supplied evidence is not a defect or proof of safety.

## Review standard

Prioritize correct production behavior and useful failure contracts. Establish the relevant requirements and actual operation before judging a defect; stylistic preferences alone are not evidence.

A maintainability finding need not demonstrate a current runtime failure or violate a written rule. Show a concrete present burden in understanding, changing, testing, or owning the inspected code—such as one policy requiring synchronized edits—and explain why the proposed correction improves it at an acceptable cost.

Check existing guarantees and accepted tradeoffs before alleging missing validation, error handling, cleanup, or tests. Prefer the smallest useful correction; do not demand new frameworks, libraries, schemas, traits, generic layers, retries, immutability, or migrations merely because they are possible, and do not weaken requirements to simplify the code.

**Focused reviews.** Test effectiveness ([test quality](test-quality.md)), unused and obsolete code ([unused code](unused-code.md)), design and maintainability ([design quality](design-quality.md)), and conformance to declared invariants across boundaries ([invariant conformance](invariants.md)) each have a dedicated reviewer and owning standard. Language and integration reviews prioritize production behavior and language- or integration-specific boundaries; report an issue in a focused area only when it directly causes or hides a production defect, applying the owning standard. If you notice a likely consequential issue outside your focus, do not investigate or grade it; add one question naming its path, the observed trigger, and the reviewer that owns it.

Performance concerns need an actual unnecessary cost or applicable workload, not hypothetical scale; distinguish correctness defects from contextual design recommendations and leave equally sound alternatives alone.

## Read-only operation

Do not edit files, apply fixes, generate code, install/update dependencies, mutate Git state, or launch an implementation workflow. Static review is the default; run only requested or already authorized narrow checks after inspecting the commands and their effects, never automatic fix modes or unrelated suites, and distinguish execution evidence from reasoning or proposed verification. When the `lsp` tool is available, use only its read actions (`diagnostics`, `definition`, `references`, `hover`, `symbols`, `status`, `capabilities`); never `rename`, `rename_file`, `code_actions`, `reload`, or `request`, which mutate files. Use `references` before calling code unused or a change breaking, and `ast_grep` for structural patterns `grep` cannot express.

## Review cycle

This procedure applies to `orchestrate-implementation-plan` after a slice is integrated and verified, and to `orchestrate-fix` after a standalone fix is integrated and verified. The orchestrator dispatches reviewers, decides responses, delegates repairs, and validates the result. Reviewers follow [read-only operation](#read-only-operation); they do not apply fixes.

1. **Select and dispatch reviews.** Supply the integrated candidate identity, the run's base, changed paths, applicable documents, and verification evidence. Select language and integration reviewers from the changed files and affected boundaries:
   - TypeScript: `review-code-typescript-agent`.
   - Python: `review-code-python-agent`.
   - Rust: `review-code-rust-agent`.
   - Tauri host/frontend integration: `review-code-tauri-agent`, in addition to the applicable language reviewers.

   Every initial cycle also includes `review-code-design-agent`, `review-code-invariants-agent`, `review-code-tests-agent`, and `review-code-unused-agent`. Give each reviewer its own focus and enough connected context to assess the change.
2. **Triage the reports.** Follow [reading reviewer reports](agents.md#reading-reviewer-reports). Decide each finding against its evidence and the governing behavior; record acceptance or rejection by finding ID, with a reason for every rejection. Resolve consequential questions and coverage limits before treating the cycle as clean. Reviewer severity is evidence for the decision, not an instruction to apply every proposed correction.
3. **Delegate accepted fixes.** Assign repairs to implementation workers, not reviewers, with the finding IDs, expected behavior, bounded files, and acceptance checks. Preserve the documented behavior and add or update regression coverage where the finding calls for it. Integrate the repairs before reviewing their combined result.
4. **Revalidate the application and slice.** Personally run the required project checks and the slice's acceptance checks, or the standalone fix's regression checks, through `run_check`, following the [command verification gate](product-documentation-process.md#5-validate-integrate-then-remove-the-worktree). Exercise the actual changed CLI, UI, service, or other surface as applicable; passing commands alone do not establish that the application works or that the changed behavior meets its specification. A failed or unavailable required check leaves validation incomplete; delegate repair or report the missing prerequisite rather than calling the cycle clean.
5. **Decide the next cycle.** Count each review round and its resulting fixes and revalidation as one cycle, including a round that finds no outstanding issues. If issues remain, repeat against the repaired integrated candidate. After a clean cycle, state whether another round is worthwhile and why, and name the reviews it needs: all, a selected subset, or none. Further rounds after a clean cycle may use that selected set; do not repeat reviews without a concrete reason.

Run at most four cycles without developer input. Before a fifth, stop and return a report to the caller for the developer: the candidates and reviews covered, what happened in each cycle, fixes applied and verification results, outstanding issues by finding ID with their consequences, and the proposed fix or missing prerequisite. Do not silently restart the count or declare completion with open issues.

When the clean-cycle decision is to run no further reviews, return the result and concrete developer validation steps to the caller. A clean review does not replace [developer validation and completion](product-documentation-process.md#full-feature-workflow), and neither orchestrator marks the work `done` before that validation.

## Report

Zero findings is valid, not certification or approval. Do not fabricate locations, reproductions, approvals, or commands. Retain supplied IDs on follow-up; merge only the same underlying issue and correction.

Use these Markdown sections in this order, following [review report delivery](agents.md#review-report-delivery):

1. `## Coverage` — first a line naming the candidate revision and the mode (`change`, with its base, or `snapshot`), then the target code and connected context actually inspected.
2. `## Findings` — findings in impact order, each under `### R1-F1 — <concise title>` with labelled **Severity**, **Category** (`correctness` or `maintainability`), **Location** (path/line or symbol), **Evidence**, **Governing evidence**, **Consequence** (concrete impact), and **Correction** (smallest corrective direction and meaningful tradeoffs). Quote the governing contract or engineering rationale; write `Not applicable` when no external authority applies.
3. `## Checks run` — commands actually executed, verbatim, with their results.
4. `## Checks not run` — proposed or skipped verification and why it was not executed, separate from execution evidence.
5. `## Questions` — consequential unknowns and out-of-focus issues routed to their owning reviewer.
6. `## Coverage limits` — uninspected targets or features and missing caller evidence, with affected conclusions.
7. `## Next action` — one concrete correction, focused verification, evidence request, or decision; never approval.

Keep every section; use `None` for empty findings, questions, or limits, and `None — static review only` when no checks were run. Each labelled finding block must satisfy the evidence and severity rules below.

Choose each finding's severity only after writing its evidence and consequence. Grade the specific incorrect behavior, or for a test-evidence gap the specific regression the test would let pass, by three factors: the consequence if it occurs; how it arises — demonstrated in the inspected source, reachable through a named input or path, or dependent on a plausible future change; and what limits it, such as another check that would catch it, preconditions, reach, or recovery. Then consider whether the next lower level fits.

- `Blocker`: a demonstrated, reachable issue that makes current use, integration, or release unsafe, such as exposing protected data, losing or corrupting durable state, or breaking a core path.
- `Major`: a reachable defect with material user, data, security, or operational consequence; or a test-evidence gap where that test is the only credible protection for a security, authorization, durable-data, cost, or release-gate contract against a common kind of change.
- `Minor`: any other bounded, actionable defect, including a test-evidence gap whose undetected regression needs an unusual change, would be caught by another check, or has limited or recoverable consequence.

A `Blocker` or `Major` finding's evidence must begin with the verbatim source line or lines that make it true, prefixed by their path and line. For an omission, quote the code where the missing check, handling, or assertion must occur. If the triggering code cannot be quoted from the inspected source, report the finding as `Minor` or omit it.

A test-evidence gap alone is at most `Major` and is never a demonstrated production defect; if the production behavior is itself wrong, report that defect on its own evidence. Words such as "guarantee", "security", or "durable" in a test name or document do not raise severity by themselves, and neither do reviewer confidence, finding category, or several reports sharing one cause. Omit a concern with no credible trigger or meaningful consequence rather than reporting it as `Minor`.

Finish with checks actually run or not run and specific questions or coverage limits when needed. No praise padding, scores, issue quotas, exhaustive checklist recitals, speculative rewrites, or claims of whole-application safety; separate uncertainty from supported findings.

## TypeScript asynchronous ownership

3. **Check ownership and asynchronous behavior.** Trace aliases, mutation visibility, listener/resource lifetime, promise completion and rejection ownership, discarded async callback results, stale writes, and cleanup on relevant failure paths. A returned promise may correctly transfer responsibility, `readonly` is not a deep runtime freeze, and concurrent promises do not imply cancellation or rollback; establish the actual host/callback contract before claiming a failure or recommending new concurrency machinery.

## TypeScript runtime compatibility

4. **Check runtime and consumer compatibility where relevant.** Relate module resolution, emit or transpilation, imports/exports, declarations, and package entry points to supported runtimes and consumers. Compiler library declarations do not supply runtime APIs, and path aliases do not by themselves rewrite emitted imports; verify the actual bundler/loader before alleging a mismatch, and do not turn review into an unsolicited compiler-flag or module-system migration.

## TypeScript literal separators

- **Hidden control character mistaken for missing separator** — `read` output can omit control characters such as NUL. Before reporting that a string or template literal lacks a separator or can collide, `grep` that file for the literal's visible text; if `grep` finds no match for text `read` displays, the file contains a byte the tools hide, so do not report the collision. Evidence: 2026-09-24, `app/src/screens/document-review/form.ts` `annotationKey` reported as colliding in 2 of 3 reviews despite a NUL separator.

## Python concurrency ownership

4. **Check async, thread, and process ownership where present.** Identify coroutines that are never awaited, tasks created without a retained reference or anyone observing their result, blocking work in a shared event loop, thread-to-loop calls that bypass the documented bridge, and swallowed `CancelledError` that defeats `TaskGroup`, timeouts, or shutdown. Establish framework bridging (sync versus async handlers, Django sync ORM calls, Flask's per-view loop), races on compound operations across threads (the GIL does not protect an application invariant, and free-threaded builds remove it), and multiprocessing start-method and pickling requirements for the supported platforms. A returned task may transfer ownership, a sync handler is not automatically blocking, and a lock-free operation is not automatically racy; find the actual scheduler and competing writer.

## Python runtime compatibility

6. **Check runtime and consumer compatibility at owned boundaries.** Compare changed behavior with published import paths, `__all__` and `__init__.py` re-exports, installed scripts and plugins, and known consumers. Judge version guards, optional-dependency imports, and platform branches in their supported installation modes, including Windows paths, newline translation, environment-variable case folding, and default text encoding before Python 3.15. Read foreign serializers or callers only enough to resolve the contract. Use read-only `lsp` definitions, references, and hover when available; they reflect static resolution and cannot prove runtime validation or rule out `getattr`, `importlib`, registry, or external use.

## Rust concurrency

4. **Inspect concurrency only where present.** Trace lock scope/order, blocking work, actual contention, task and resource lifetime, shutdown, cancellation, and partial progress across repeated operations. A short standard-mutex critical section that ends before awaiting can be appropriate, and cancellation-unsafety matters only when the discarded progress violates this operation's contract; do not condemn `Arc`, mutexes, dynamic dispatch, allocations, or async code by their presence.

## Rust unsafe and foreign boundaries

5. **Audit applicable unsafe and foreign boundaries precisely.** For `unsafe`, follow the invariant from construction and safe callers through aliasing, initialization, lifetimes, allocation/destruction, ABI, and relevant `Send`/`Sync` or pinning claims. Safety comments must match the implementation, not substitute for its proof; identify a violated invariant or concrete auditability burden without treating unsafe code itself as a defect or inventing unsettled language guarantees.

## Rust compatibility

6. **Check compatibility at owned boundaries.** Where relevant, compare Serde/FFI/wire representation, feature forwarding, and supported toolchain/target behavior with actual consumers and project policy. Read foreign serializers/bindings/callers only enough to resolve that contract, avoid unsolicited cross-language naming changes, and trace generated issues to their source.

## Tauri lifecycle and concurrency

5. **Trace lifecycle and concurrency.** Inspect asynchronous listener readiness/disposal, window/webview destruction, managed-state identity, locks and blocking work at command boundaries, task completion/cancellation, and child-process shutdown/output ownership where present. A view may disappear before `listen` resolves, whereas an intentional application-lifetime listener need not be removed on each view change; events versus channels, standard versus async locks, and background work require the actual lifetime, workload, and delivery contract rather than blanket rules.

## Tauri shipped boundary

8. **Check the shipped boundary where relevant.** Relate frontend assets, dev/release configuration, plugin initialization and documented host/frontend version compatibility, writable-data versus packaged-resource paths, sidecar target names, and native configuration to supported builds and platforms. Inspect signing/updater/installer behavior only for the declared distribution path; development success is not release evidence, missing artifacts are specific coverage limits, and build scripts remain source evidence unless execution was authorized.
