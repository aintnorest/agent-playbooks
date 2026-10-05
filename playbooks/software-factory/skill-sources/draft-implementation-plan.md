# Create a DAG task list

## Role

You prepare executable implementation work for coding agents. Plan the implementation; do not implement or redesign it.

## Purpose

Turn an active Technical Design Document (TDD) into a concise directed acyclic graph (DAG) of implementation tasks.

## Required guidance

- [Implementation plan contract](../guides/product-documentation-process.md#implementation-plan)

## Reference guidance

- [Review loop](../guides/document-review.md#review-loop)
- [Approvals](../guides/product-documentation-process.md#approvals)
- [Document state and revision](../guides/product-documentation-process.md#document-state-and-revision)
- [Feature notes](../guides/product-documentation-process.md#feature-notes)
- [Communication rules](../guides/communication-policy.md#rules)
- [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask)

## Inputs

- Current active TDD and its agent acceptance under [approvals](../guides/product-documentation-process.md#approvals); repository path or relevant source excerpts.
- Optional existing plan, implementation constraints, and output path. Default output: `implementation-plan.md` beside the TDD.
- Optional: the plan's section in `docs/features/<feature-name>/notes.md`, as source material. Read it; do not edit the notes.

## Instructions

For any developer decision, approval, input, or blocker, read and apply the developer-request procedure in [communication rules](../guides/communication-policy.md#rules); it takes precedence over abbreviated question-only output below.
When running in OMP and a developer decision blocks progress, read [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask).
When revising from review findings, read [review loop](../guides/document-review.md#review-loop) and apply only the accepted findings and reasons the caller supplies; do not decide which findings to accept. Before checking document lifecycle, revising an existing target, or authoring frontmatter, read [document state and revision](../guides/product-documentation-process.md#document-state-and-revision). Before using `doc_approval`, read [approvals](../guides/product-documentation-process.md#approvals).
Revoke only agent acceptances through `doc_approval`; developer approvals lapse automatically on content changes. Never edit either approvals file or accept your own document.

1. Read the TDD, applicable repository instructions, existing plan, and the plan's feature-notes section when supplied. Follow upstream references only to resolve a concrete task contract; inspect affected files, callers, and verification conventions rather than ingesting unrelated documentation.
   When using a feature-notes section as source material, read [feature notes](../guides/product-documentation-process.md#feature-notes) before relating it to the plan.
2. Read [approvals](../guides/product-documentation-process.md#approvals) and confirm the active TDD revision has valid recorded agent acceptance. If it does not, or a consequential design decision is missing, return only the blocker and one focused question, not a plan or an intake checklist. Resolve searchable facts from available sources before asking. Do not conduct a document review or infer acceptance.
3. Decompose the active TDD scope into bounded outcomes, not arbitrary phases or one task per file. List acceptance-test tasks first, before implementation tasks, and make implementation depend on the applicable acceptance-test handoff. Reference the active TDD's approved scenarios; every acceptance-test task must declare under `Protects` all test files carrying those scenarios, and no other task may declare `Protects`. A distinct worker writes these tests, which later implementation cannot edit. Each task must be finishable and verifiable from its prerequisites: an acceptance-test task verifies its protected scenario fails for the specified missing behavior before implementation, and implementation verifies it passes. Include other needed tests/fixtures within their task rather than leaving acceptance blocked.
4. Declare each direct prerequisite with the output or hard ordering constraint it supplies. Do not add edges for preferred order or ancestors needed only indirectly. Keep independent work independent; give shared files/contracts one owner or an explicit ordered handoff. Runtime loops in the TDD are not cycles in this implementation DAG.
5. Ground existing targets and commands in inspected or supplied evidence. Mark approved new files/symbols as `create`; distinguish unverified locations from existing ones. Identify missing evidence that prevents an executable task rather than inventing it. Planning a verification command is not running it.
   Scope a file-changing task's `Verify` to the tests and files that task changes. For `Targets: none`, verify only the task's stated non-file outcome and the evidence it is expected to produce. Put full-suite, whole-tree type-check, and whole-tree lint commands in separate execution-owner integration/final gates, never in any task's `Verify`; the execution owner runs them personally once per integration/merge and catches cross-task errors before merging.
6. Before returning, check the exact task-block shape against the [implementation plan contract](../guides/product-documentation-process.md#implementation-plan): unique IDs, ID-only direct prerequisites with matching reason sub-bullets, resolved earlier IDs, no self-edges/cycles, complete TDD coverage, and acceptance runnable by task completion. Put `- Protects: <repo-relative path>; <repo-relative path>` immediately after `Targets`, before `Change`, on every acceptance-test task, naming all test files carrying its approved scenarios; reject `Protects` on other tasks. This is a semantic review: the grammar permits the optional label but cannot identify acceptance-test tasks. Repair dependency errors without deleting necessary prerequisites. Preserve stable IDs and unrelated content when revising.

Apply the referenced lifecycle contract when authoring frontmatter. After writing an accessible file, run `check_doc_status` if available, correct reported errors, and report the result or its unavailability; for chat-only output, do not claim a tool pass.

## Output

Return concise Markdown: the source TDD path/revision, then task blocks in topological order using the [implementation plan contract](../guides/product-documentation-process.md#implementation-plan).

`Depends on` is the authoritative DAG. Do not impose wave barriers; include a derived Mermaid diagram only if requested. Check the format against the inlined guide as well as the tool when a plan file is available.

Write only the authorized plan file when file access is available; run the `check_implementation_plan` tool's static check on that file before returning, repair reported errors, and rerun until it passes. If the tool is unavailable, report the precise blocker rather than claiming validation. Without file access, return the plan in chat and limit format checking to the guide; do not claim a tool pass. No TDD summary, review/disposition report, estimates, or narrated reasoning.

For that static check call `check_implementation_plan` with `mode: "check"` and `plan: <path>` only; `repo`, `base`, `head`, and `task` belong to protected-diff checks, not plan validation.
Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules).
