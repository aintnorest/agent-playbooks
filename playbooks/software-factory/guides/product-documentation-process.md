---
state: active
approved: 2026-09-29
---

# Product documentation process

This process keeps product intent, system architecture, technical design, and implementation work separate while preserving a traceable path from vision to verified code.

It governs document roles, hierarchy, workflow, and [non-goals and boundaries](#non-goals-and-boundaries). General developer-facing output follows [the communication policy](communication-policy.md); confidence labels and the rules for expressing mechanisms, interfaces, failures, and tradeoffs follow [the technical-writing standards](technical-writing-standards.md). Those shared guides are authoritative for their subjects. Project-specific facts remain in the document that owns them; any deviation from shared guidance must name the affected rule, scope, reason, and replacement.

This is the full-feature workflow for material product work. Problems found after delivery follow [fixes after delivery](#fixes-after-delivery).

## Status

Working agreement for new or revised product documentation; independent document reviews follow the shared rules in [document review](document-review.md).

## Governing principles

1. **One fact has one authoritative home.** Other documents reference that fact instead of copying it.
2. **Use the smallest document hierarchy that keeps boundaries clear.** Do not create slices, diagrams, or templates merely because the process permits them.
3. **Split work at independently testable handoffs.** A slice ends with observable or persisted state that the next slice can consume.
4. **Design precedes task decomposition.** An implementation plan divides decided work; it does not silently make product or architecture decisions.

## Non-goals and boundaries

For every document type that has non-goals or boundaries, keep them inside the scope the document commits to. Name only what a reader could reasonably expect that scope to include but the document intentionally excludes. Listing things nobody would expect adds nothing.

In a design, state what will not be built, including scale targets, edge cases, generalizations, or optimizations intentionally omitted when they meet that expectation test.

## Documentation hierarchy

Product-level documents sit together at the root of `docs/` and apply to every feature. Each feature gets its own directory under `docs/features/`, shaped by whether it needs slices.

### Small feature

```text
docs/
├── product-vision.md
├── architecture.md
├── roadmap.md
└── features/
    └── <feature-name>/
        ├── prd.md
        ├── tdd.md
        └── implementation-plan.md
```

### Large feature

```text
docs/
├── product-vision.md
├── architecture.md
├── roadmap.md
└── features/
    └── <feature-name>/
        ├── prd.md
        ├── system-design.md
        └── slices/
            ├── 01-<slice-name>/
            │   ├── tdd.md
            │   └── implementation-plan.md
            └── 02-<slice-name>/
                └── tdd.md
```

Slice `02-<slice-name>` has no implementation plan yet because its technical design is not ready to build. Do not add `.md` to directory names; the directory supplies context, and stable filenames identify each document's role.

### Product level

`docs/product-vision.md` states the durable product direction. It applies across features and changes less often than feature requirements.

`docs/architecture.md` states the system-wide technical foundations every feature inherits: implementation language, frameworks, repository structure, tooling, and the technical concepts applied once across the system. It changes when a foundation decision changes, not when a feature ships.

`docs/roadmap.md` holds product ideas until they are ready for a document, the features in progress, and a log of finished features. See the [roadmap](#roadmap) contract.

### Feature level

Every full feature lives under `docs/features/<feature-name>/` and starts with `prd.md`, the Product Requirements Document. Use the small-feature shape unless the feature meets the [slice criteria](#when-a-feature-needs-slices); then use the large-feature shape. Create an implementation plan only when its technical design is `active` and ready to build. Material for a feature document that does not exist yet goes in the feature's [notes](#feature-notes), never in a placeholder document.

## Lightweight path for minor changes

For a minor fix or change, update the existing living document that owns the changed product fact or technical contract, if one exists, and verify the actual changed behavior. A `done` feature document is historical and must not be revised; later fixes or repeated work follow [Fixes after delivery](#fixes-after-delivery). Do not create a Product Requirements Document, technical design, system design, or implementation plan merely to satisfy this process.

Use the full-feature workflow instead when the change introduces a material requirement or non-goal, a new or changed cross-boundary interface, an unresolved product or architecture decision, a separately reviewable delivery, or work that needs ordered task decomposition. Record a concise decision in the owning document when the boundary is not obvious.

## Fixes after delivery

Record a problem found after a slice is `done` as a known issue in Beads when the repository has `.beads/`; otherwise record it in the roadmap's [Known issues](#roadmap) section. It does not interrupt current work unless the developer says so. The main session offers the developer a choice between a standalone fix and a new slice.

A standalone fix restores behavior the documents already specify and adds a regression test that would have caught the problem, written by a different worker from the fix. It goes through the same [code review cycle](code-review.md#review-cycle) and [developer validation](#11-validate-and-close-the-milestone) as a slice. Do not revise frozen documents or create a PRD, system design, TDD, or plan merely to satisfy this path.

When the documented behavior itself is wrong, use a new slice. A fix-only slice adds its own TDD and implementation plan; it does not by itself require a system design. For an existing multi-slice feature, update or reopen its system design under [document state and revision](#document-state-and-revision), preserving delivered-slice sections. Take changed documents through their review loops and [gates](#approvals).

## When a feature needs slices

Create slices when at least one of these conditions is true:

- The feature has two or more independently useful delivery milestones.
- One part must establish persisted or observable state before another part can begin.
- Different parts have materially different security, reliability, or operational risks.
- The complete technical design is too large to review as one coherent change.
- A later part can be tested from a fixture representing the earlier part's exit state.

Do not create slices merely because the code crosses directories, crates, components, or programming languages. If a proposed slice has no independently testable exit state, it is probably a task inside another slice rather than a slice.

## Document contracts

### Document state and revision

The first lines of every product document listed below are a YAML frontmatter block. This block is the **only** authority for the document's state and revision; [approvals](#approvals) live separately. Product documents use exactly these lowercase keys in order: `state`, then `revision` where required. Write one nonempty, unquoted flat `key: value` scalar per line between opening and closing `---`; no additional keys beyond the applicable contract, duplicates, arrays, nesting, or YAML aliases. The `## Status` section, where present, remains in its existing position and may describe reviews, changes, and parent contracts, but must not restate or contradict any frontmatter value. An old free-text status without this block is non-conforming, not an inferred state.

| Document | Allowed `state` values | `revision` |
| --- | --- | --- |
| `docs/product-vision.md` | `draft`, `active`, `superseded` | Required: `vision-r<N>` |
| `docs/architecture.md` | `draft`, `active`, `superseded` | Required: `arch-r<N>` |
| `docs/roadmap.md` | `draft`, `active`, `superseded` | Absent |
| `docs/features/<feature>/prd.md` | `draft`, `active`, `done`, `superseded` | Required: `prd-r<N>` |
| `docs/features/<feature>/system-design.md` | `draft`, `active`, `done`, `superseded` | Required: `sd-r<N>` |
| Feature or slice `tdd.md` | `draft`, `active`, `done`, `superseded` | Required: `tdd-r<N>` |
| Feature or slice `implementation-plan.md` | `draft`, `active`, `done`, `superseded` | Required: `plan-r<N>` |

`<N>` is a positive decimal integer with no leading zero; new revisioned documents start at `r1`. Passing the applicable [approval gate](#approvals) permits `state: draft` to become `state: active`; never infer developer approval from a review. A lifecycle-only state transition keeps the revision and document body. For a living document, a contract change increments its revision (if it has one) and returns it to `draft` where that state is allowed. Editorial changes may preserve revision and state, but still invalidate a content-bound approval. Every system-design body change requires a higher revision and a new approval. Do not invent historical revision IDs.

Product vision, architecture, and roadmap are living documents: edit their current rules as the product changes. Feature PRDs, technical designs, and implementation plans are living only until delivery, then `done` and historical rather than kept in sync with the current repository. A plan and its TDD become `done` only after developer validation and the post-validation update in [the full-feature workflow](#11-validate-and-close-the-milestone). Mark a PRD `done` when its feature finishes. A `done` PRD, TDD, or plan is **frozen**: do not edit it again, including metadata. Later problems follow [fixes after delivery](#fixes-after-delivery). `superseded` means an undelivered document was replaced and no longer governs.

A feature system design stays `active` while any slice is undelivered. Revise only rules for undelivered slices; sections describing delivered slices remain unchanged. Mark the system design `done` when every slice is done. A later new slice may reopen the system design with a higher revision and `state: draft`, then return it to `active` through its approval gate. The prohibition on editing delivered-slice sections is a drafting/review obligation, not a claim that the checker can infer which sections describe delivered work.

Use `python3 scripts/check-doc-status.py --check <path...>` to check files and `--json <path...>` to read metadata, including derived approval validity. Old prose-only statuses fail with diagnostics. Before integrating candidates, `python3 scripts/check-doc-status.py --frozen-diff --repo <root> --base <commit> --head <commit>` requires PRD/TDD/plan transitions to `done` to preserve the active document's body and revision; it rejects subsequent changes to those frozen documents and system-design body changes without a higher revision. Metadata-only completion transitions and commits that change only `docs/user-approvals.json` or `docs/agent-approvals.json` are allowed; acceptance does not change document metadata. The read-only extension tool `check_doc_status` exposes `mode: "check"` / `"json"` with `path`, and `mode: "frozen-diff"` with `repo`, `base`, and `head`.

### Approvals

`docs/user-approvals.json` holds developer approvals; its existence opts the repository into factory enforcement, and factory hooks are inert without it. Only the developer creates or edits this file, by hand. It is a JSON object mapping repository-relative forward-slash document paths to 64-lowercase-hex body hashes; `{}` is valid. `docs/agent-approvals.json` holds agent acceptances in a JSON object mapping paths to exactly `{"hash": "<64 lowercase hex>", "evidence": "<non-empty text>"}`. A missing agent file means no acceptances.

| Document type | Gate | Record location |
| --- | --- | --- |
| Product vision, PRD | Developer | Hash in `docs/user-approvals.json` |
| Architecture, system design | Developer | Hash in `docs/user-approvals.json` |
| Technical design, implementation plan | Agent | Hash and generated ledger evidence in `docs/agent-approvals.json` |
| Roadmap | None | No record allowed |

Document type comes from its path, as in `check-doc-status.py`'s `document_type`. Developer approval means accepting the content after reading it in full, or understanding and agreeing with the technical decisions well enough to explain and defend them, respectively. Developer-facing gate requests follow [Gate requests](communication-policy.md#gate-requests).

Hash the exact bytes after the line that closes frontmatter. For implementation plans only, remove complete lines matching `^- Assigned (?:worktree|branch):[^\r\n]*(?:\r?\n)?$` before hashing; task pickup may write these without invalidating acceptance. All other body changes automatically lapse approval, including editorial changes. Lifecycle-only frontmatter state changes do not. Approval is valid exactly when the appropriate file's entry hash matches the current body hash. Gated types require valid approval in `active` and `done`; `draft` and `superseded` do not.

Both files are validated strictly and fail closed: a non-object top level, a wrong-gate path, an invalid hash, or extra or missing agent entry fields is malformed, with a diagnostic naming the file and offending key. Ungated documents may not appear in either file. Entries contain only the hash, plus evidence for agent acceptances; there are no approval metadata fields.

Agents inspect approval state through `doc_approval` mode `status`, and accept or revoke only TDDs and implementation plans through modes `accept` (no evidence argument) and `revoke` (with a reason). Acceptance requires a review ledger closed on exactly the current body hash; otherwise it refuses with `review-not-closed`. Evidence in `docs/agent-approvals.json` is generated from the ledger. These operations write only the agent approval file; review agents remain read-only. Agents never edit either approval file directly and never revoke developer approvals. The developer runs `/playbook-hash <path>`, or `/playbook-hash` alone to list every developer-gated document's current entry, and pastes the approved entry into the user file by hand.

Tracked review ledgers live under the consumer's `.playbook/reviews/`: `docs/<rest>.md` maps to `.playbook/reviews/<rest>.json`, and feature coherence uses `.playbook/reviews/features/<feature>/coherence.json`. Only the Playbook writes them, through hooks and `review_ledger`; direct file or shell/eval writes are prohibited. The ledger owns rounds, findings, decisions, rejection reasons, and current review receipts. Developer-gated documents use the same ledger and include `review_ledger status` in their approval requests, without blocking the developer's own approval.

### Product vision

**File:** `docs/product-vision.md`

**Purpose:** State why the product exists and what durable direction constrains every feature.

Use this title and top-level section order:

1. `# Product vision: <product>`
2. `## Status`
3. `## Vision`
4. `## Target users and underlying problems`
5. `## Product principles`
6. `## Product-wide boundaries and non-goals`
7. `## Durable success signals`
8. `## Constraints every feature must preserve`
9. `## Open decisions`, only when consequential vision-level decisions remain open.

**Contains:**

- document state and revision in frontmatter, with optional review context under `## Status`;
- a concise statement of why the product exists and the future it should create;
- durable target users and their underlying problems;
- product principles that guide choices across features;
- product-wide boundaries and non-goals;
- durable, observable success signals without time-bound targets;
- constraints that every feature must preserve;
- consequential open decisions whose resolution would change durable product direction.

In `Target users and underlying problems`, name who the product serves before describing exclusions or problems. As an audience-specific application of [non-goals and boundaries](#non-goals-and-boundaries), include an excluded audience only when it is a plausible subgroup or edge of the stated target and the distinction changes product direction; do not enumerate unrelated people the product was never intended to serve. Put broader product exclusions under `Product-wide boundaries and non-goals`.

Keep underlying problems and product principles separate so downstream documents and their authors remain free to choose how to address the problems. Underlying problems state what goes wrong and why it matters, never a solution or how the product responds. Product principles state durable ideals or opinions that guide choices, never restate a problem, and include at most a brief reason.

The vision owns only product-wide facts intended to remain true when individual features, delivery sequence, interfaces, or implementation change. A feature Product Requirements Document (PRD) references applicable vision content instead of copying it, then owns its feature-specific users, problem, non-goals, requirements, acceptance intent, constraints, and product decisions. Evidence may follow the claim it supports; a separate evidence section is not required.

**Excludes:**

- feature-specific requirements, user stories, and acceptance criteria;
- ideas for future features and what comes next, which belong in the [roadmap](#roadmap);
- quantified or time-bound targets, releases, and milestones;
- implementation architecture;
- command, schema, interface, or module contracts;
- business-model, pricing, competitive-positioning, and go-to-market plans;
- task sequencing.

### System architecture

**File:** `docs/architecture.md`

**Purpose:** Fix the technical foundations every feature inherits, so no feature re-decides them.

**Contains:**

- status;
- externally imposed technical constraints that a feature must technically obey, such as a mandated language, runtime, platform, or organizational technical standard;
- the system boundary: the external systems this system depends on, what each of them owns rather than this system, and the integration mode;
- system-wide technology decisions: implementation language or languages, runtime, primary frameworks, and the core dependencies every feature builds on;
- the top-level decomposition approach and the repository structure it produces, naming each top-level directory's responsibility;
- boundaries — module, layer, and trust — and the dependency rule each one enforces, stated once;
- build, packaging, formatting, linting, and continuous-integration tooling, and the system's test-execution strategy;
- cross-cutting technical concepts applied once across the system, such as persistence approach, configuration, error and logging conventions, and observability;
- system-wide quality thresholds and the measurement regime that guards them, referenced to the configuration that owns the numbers;
- conventions adopted for the whole system, referenced to the standard, manifest, configuration, or lint rule that owns them rather than restated;
- a technology index with one row per system-wide choice: the choice's name, its status, its authority, and a link to the section that owns the rule; the index never restates a rule;
- proposed foundations awaiting the developer's approval, each marked as proposed with the option chosen and its tradeoff;
- current scope: facts every feature must obey today that are true of the present scope rather than foundations, each with the trigger that changes it, placed after the technology index and before open decisions;
- consequential open technical decisions whose resolution would change the system's foundations;

**Excludes:**

- product direction, users, problems, principles, product-wide boundaries, and success signals;
- requirement wording and product-level acceptance intent;
- feature-wide architecture, cross-slice invariants, slice dependency graphs, and requirement-to-slice mapping;
- slice-local interfaces, schemas, signatures, state transitions, and observable acceptance;
- task breakdown, work order, and per-task verification commands;
- rationale for a decision owned by another document;
- any component, technology, or structure that exists for exactly one feature;
- team composition, who reviews or implements, language fluency, hosting plan tiers, billing, vendor commercial terms, and operator identity; when the developer must know one, the revision report carries it.

A technical fact belongs here only when every feature must obey it. A choice that constrains more than one slice of a single feature belongs in that feature's system design; a choice contained in one slice belongs in that slice's technical design. A technology stays in the feature or slice document that introduced it until a second consumer appears or it constrains another feature's design; at that point promote the current rule here. A foundation survives the next feature; a fact that a named event will change — a host, a scale, an operator, a scope boundary — is current scope, not a foundation, and is recorded in the current-scope section with its trigger rather than as a decision.

This document states each current system-wide rule without a separate decision record. Preserve the reasoning beside a rule only when the reason is not obvious, and keep it as brief as possible. System-wide technical decisions are made here: establish what already exists, then research a missing or inadequate foundation and propose one for the developer's approval rather than leaving a blank. Mark a proposed foundation as proposed until the developer approves it, and never present an unapproved choice as established. Propose a change to an established foundation, with the evidence that motivates it, rather than rewriting it silently. Leave a foundation open only when research cannot settle it and the developer has not chosen.

**Altitude.** Each foundation is one rule a feature designer can obey, plus the file, configuration, or external page that owns its details. Record no configuration values, commands, SQL, ports, quotas, retention periods, or vendor defaults; cite the source that owns them. A fact belongs here only if a feature would have to re-decide it were the fact absent. Every rule appears exactly once, in the section that owns it; a section that needs it references that section. A proposal carries the one-sentence tradeoff the developer approves against; a settled rule carries a tradeoff only when the choice is not obvious. Confidence labels go only on the repository structure and conventions the document names, not on rules or prose. A rule's status lives in the technology index, not beside the rule; the document's own history, sources read, and approval record belong in the report that accompanies a revision, not in the document. Omit a content area with nothing system-wide to say. A rule is a sentence or a short paragraph; a table or list of values means the detail belongs in the file that owns it.

### Roadmap

**File:** `docs/roadmap.md`, created from the playbook's `templates/roadmap.md`. Every project has one, even while its sections are empty.

**Purpose:** Hold product ideas until they are ready for a document, show the features in progress, and log the features that are finished.

**Sections:**

- **Now:** features being worked on. Each names the feature, its start date, and a link to `docs/features/<feature-name>/` once that directory exists.
- **Next:** ideas likely to come next. Any level of detail.
- **Later:** ideas worth keeping. A single line is enough.
- **Done:** finished features, each with its name, start date, and finish date.
- **Known issues:** problems found after delivery that are waiting for a fix when the repository has no `.beads/` tracker.

**Rules:**

- An item moves toward Now by judgement: when there is a need for it and the capacity to work on it. Only work actually in progress sits in Now.
- Items in Next and Later are deliberately loose. They may hold partial ideas, problem statements, and early requirements.
- When a feature's documents are created, the ideas that belong in them move out of the roadmap and into those documents. Drafting agents read the matching Now item as source material but do not edit the roadmap; the developer or the orchestrator trims it. Once the feature's documents exist, its Now entry keeps only a short summary, its start date, and the link to its feature directory.
- A dropped idea is deleted. A deferred one moves back to Later.
- The roadmap is ungated. Recording known issues, trimming ideas, and moving entries do not require approval or reopen a gate.

**Excludes:**

- decisions and `[NEEDS YOUR CALL]` tags;
- implementation order and how a feature is split into slices;
- planned delivery dates; a real external deadline may be noted on the item it affects;
- content that already lives in a created document.

### Feature notes

**File:** `docs/features/<feature-name>/notes.md`, only while it holds material.

**Purpose:** Hold material gathered for a feature document that has not been drafted yet, so that the document's drafter receives it. Before the feature directory exists, the [roadmap](#roadmap) holds such material instead.

**Format:** One level-2 heading per target document, written as the target's path relative to the feature directory, optionally in backticks: `## system-design.md`, `## tdd.md`, or `## slices/01-<slice-name>/tdd.md`. Content under a heading is loose: findings, constraints, open questions, and links to evidence. Notes are not a product document: they have no frontmatter, state, revision, or approval, and status checks do not read them.

**Rules:**

- Never create a placeholder product document to hold material for later. A product document exists only once it is drafted, so factory status reports creating it as the next step and names the notes file when it holds a section for that document.
- The drafter of a target document reads its section as source material alongside the approved parent documents. A note never overrides an approved document; a conflict between them is a question for the caller.
- Drafting agents do not edit notes. Once the target document exists, the orchestrator deletes its section, and deletes the file when no section remains.
- A section whose target document already exists is stale.

**Excludes:**

- settled decisions; a decision is stated in its owning document when that document is drafted;
- task tracking and run state;
- material for documents that already exist; revise those documents instead.

### Feature Product Requirements Document

**File:** `docs/features/<feature-name>/prd.md`

**Purpose:** The Product Requirements Document (PRD) defines what one complete feature must accomplish and why it matters.

**Contains:**

- status;
- product summary;
- problem;
- explicit non-goals;
- user stories;
- individually identified requirements;
- product-level acceptance intent;
- product constraints and unresolved product decisions.

Keep the problem separate from the requirements: state what goes wrong and why it matters, never a solution or how the feature responds.

**Altitude.** A requirement states what the user gets and what is guaranteed, not how the product delivers it. Test each sentence: if the design chose a different mechanism that gave the same experience and the same guarantees, would this sentence have to change? If so, it is design detail and belongs in the architecture, system design, or technical design. Name a tool, command, file location, or screen only when it is itself the promise, such as an export format users must be able to open; otherwise give it as an example at most. Keep security, containment, reliability, and data-loss guarantees, and leave out how they are enforced. Product-level acceptance intent stays at the same altitude: a few scenarios per user-visible outcome, with step-level scenarios and edge flows left to the technical design's [behavioral acceptance](#behavioral-acceptance).

**Independence from downstream documents.** A design change reaches the PRD only when it changes behavior the user experiences. A PRD therefore never cites another document's revision, links into a system design, technical design, or plan, or tracks their progress: no spikes, verification status, or notes that the design must confirm something. When a requirement depends on something the design must prove, state the product need in the requirement; the design records how it is met and verified. A PRD's `## Status` narrows the general rule in [document state and revision](#document-state-and-revision): it describes only this PRD's scope and what remains open, not parent revisions, reviews, or a revision history.

**Excludes:**

- technical components;
- database or file schemas;
- function signatures;
- implementation order;
- design choices that fail the altitude test, including ones the user can see;
- references to downstream documents, their revisions, or their verification.

### Feature system design

**File:** `docs/features/<feature-name>/system-design.md`

**Purpose:** Explain how a large feature works as a whole and define contracts shared by more than one slice.

**Contains:**

- system context and external actors;
- major components and their responsibility boundaries;
- end-to-end control and data flow;
- feature-wide state and consistency model;
- trust and security boundaries shared by slices;
- feature-wide error, schema, event, and compatibility rules;
- feature-wide concurrency, locking, and recovery rules;
- automated-worker authority boundaries, only when the feature includes automated workers;
- slice dependency graph and persisted handoff states;
- mapping from requirement IDs to owning slices;
- feature-wide technical decisions that span more than one slice.

**Excludes:**

- exact slice-local database columns;
- complete command flag lists;
- slice-local payload schemas;
- prompt text;
- private algorithms;
- implementation tasks;
- system-wide technology, repository structure, and cross-cutting technical conventions.

A rule belongs here only when multiple slices must obey it or when it defines the boundary between slices. A rule that exists entirely inside one slice belongs in that slice's technical design.

**Slice order.** Give the build order under a `## Slice order` heading as a numbered list with one slice per item, first slice first. Begin each item with the slice's directory name in backticks, `NN-<slice-name>` as in the [large-feature shape](#large-feature), then a short description of what the slice delivers. Name no other slice in an item: factory status reads the current slice from this list, and slice dependencies belong in the dependency graph.

This document states each current feature-wide rule without a separate decision record. Preserve its reasoning beside the rule only when the reason is not obvious. A system-wide rule belongs in the [system architecture](#system-architecture) document instead.

**Altitude.** A shared rule is one sentence or a short paragraph naming the states, owner, and outcome at a boundary, plus the slice technical design that owns the mechanism inside it. A rule belongs here only if two or more slices would each have to re-decide it were it absent. Name the states a slice must persist or observe; do not describe how a slice reaches them. A table enumerates only slice handoffs, requirement ownership, or shared error classes; a table of external facts, per-item evidence, or values means the detail belongs in the owning slice's technical design, with only the invariant it produces kept here. A settled rule is stated without a decision tag; a tradeoff appears only when the choice is not obvious. Omit a content area with nothing cross-slice to say; an empty area is not a defect.

### Technical Design Document

**File:** `tdd.md`

**Purpose:** Define how one small feature or one large-feature slice will be implemented. “Technical Design Document (TDD)” is the repository meaning; it does not mean test-driven development here.

**Contains:**

- parent document and requirement references;
- explicit non-goals;
- entry state and exit state;
- rejected inputs and failure behavior;
- data-flow and control-flow traces;
- concrete interfaces and data schemas;
- state transitions and transaction boundaries;
- security and operational assumptions;
- explicit tradeoff decisions;
- observable acceptance in the notation selected under [behavioral acceptance](#behavioral-acceptance);
- technical contracts and verification criteria;
- handoff state for the next slice.

**Excludes:**

- copied product requirement text;
- copied feature-wide architecture;
- work breakdown and dependency order;
- speculative generalization for unapproved future features.

**Control-flow clarity.** Design control flow so an implementer can trace each consequential operation from its trigger to completion or failure, identifying what executes next, what determines that choice, and which component owns each decision and handoff. Prefer the simplest flow that satisfies the requirements; justify indirection, distributed coordination, or multiple execution paths when their debugging or maintenance cost is material. Explaining a tangled flow does not substitute for simplifying it.

Make the entry point, coordinating owner or ownership rule, major steps, branch conditions, side-effect ownership, and completion conditions explicit. Where asynchronous handoffs exist, identify what resumes execution and who owns pending work. Where applicable, define failure propagation and ownership of cancellation, retry, rollback, or cleanup. Do not introduce mechanisms merely to fill this checklist or require a centralized coordinator.

Keep traces at component, interface, and state-boundary level, not every function call. A short sequence is sufficient for straightforward work; use a diagram or state-transition table when it makes branching or asynchronous interaction clearer. No particular heading or diagram is required. Reference existing contracts and acceptance rather than duplicating their normative definitions.

### Implementation plan

**File:** `implementation-plan.md`

**Purpose:** Divide an active technical design into bounded, independently verifiable implementation tasks.

**Contains:**

- stable task identifiers and deliverable-oriented titles;
- direct prerequisite IDs, each with its required output or hard ordering constraint; these define the directed acyclic graph (DAG);
- exact file and symbol targets, distinguishing existing edits from approved planned creations;
- the bounded change and referenced TDD requirement, scenario, or technical contract;
- observable acceptance and a narrow verification command or concrete exercise with its expected result;
- verification prerequisites available within the task, the existing repository, or predecessor tasks;
- explicit ownership or ordered handoffs for shared files and contracts;
- integrated feature acceptance and required integration/final verification owned by the execution owner, outside task `Verify` fields;
- explicit decision gates only for already approved conditional choices.

**Excludes:**

- new architecture decisions;
- new product behavior;
- copied requirements or technical design sections;
- placeholders that appear complete but leave behavior unimplemented.

Use one task ID namespace per plan: headings are `### T<digits> — <title>`, with unique IDs and nonempty titles. Each task has exactly one unindented bullet for each mandatory label, in this order: `Depends on`, `Targets`, `Change`, `Done when`, `Verify`. Optional `Protects` and `Tests` bullets may each appear once: `Protects` immediately after `Targets`, and `Tests` between `Change` and `Done when`. Keep each mandatory field nonempty; `Targets`, `Change`, `Tests`, `Done when`, and `Verify` may continue on indented lines up to the next unindented label or task heading.

Write `- Depends on: none` or a single physical line of comma-and-space-separated **direct IDs only**, with no prose or transitive prerequisites. Immediately below that line, give one indented `- T<digits> — <reason>` sub-bullet per direct ID, in the same order; each reason names the required output or hard ordering constraint. Give no reason sub-bullets for `none`. Every dependency must reference an earlier task: no dangling IDs, self-edges, or cycles. List task blocks in topological order; a task is ready when its prerequisites finish, not when an arbitrary phase ends. This line is the authoritative DAG; diagrams and parallel-wave tables are optional derived views, not additional sources of truth.

Write `Targets` as `none` when the task changes no files, for example `- Targets: none` for a no-file evidence handoff. Otherwise list one or more items separated by `; ` or continued on separate indented lines. Each item is a file path (backtick-quoted, or unquoted with no whitespace), optionally followed by `::symbol`, then a space and exactly `(edit)` or `(create)`: for example, `` `src/cache.ts`::SessionCache (edit) ``. Use `(edit)` for an existing target and `(create)` for an approved planned creation. `none` must be the entire field; do not combine it with file targets. Parentheses contain only the action keyword, never descriptive prose: put details such as “new session cache and fixture beside `Scenario`” in `Change`, not `Targets`.

At pickup the execution owner adds `- Assigned worktree: <absolute path>` and `- Assigned branch: <branch name>` immediately after `Verify`, as a pair. Every task worktree goes under `<repo-root>/.worktrees/`; before any pickup the execution owner confirms Git ignores `.worktrees/` and, if not, stops and reports the missing ignore rule to its caller for resolution through the main session. The execution owner never edits `.gitignore` or `.git/info/exclude`, and never uses another root. Do not write assignment fields while drafting: an unstarted task has neither. Both remain after integration and safe cleanup as assignment history. The validator rejects a partial pair, duplicate path or branch across tasks, relative paths, and malformed branch names. Task status, attempts, verification, and cleanup stay in the separate run ledger. Static validation cannot infer whether a task is running; the execution owner reconciles the ledger and plan. Existing unassigned plans remain valid.
Put acceptance-test tasks derived from the active TDD's acceptance scenarios before their implementation dependents in the DAG, and assign them to a different worker from the implementation tasks. Every acceptance-test task must declare `- Protects: tests/test_feature.py; tests/test_other.py` immediately after `Targets`, listing **all** test files carrying its active TDD scenarios; no other task may declare `Protects`. The label is optional in the task-block grammar because that grammar cannot identify acceptance-test tasks: review this requirement semantically. `Protects` is a semicolon-and-space-separated list of distinct, plain repository-relative test file paths. Each slash-separated segment uses only ASCII letters, digits, `.`, `_`, or `-`, and cannot be `.` or `..`; quoting and backslashes are not allowed. Name target files as `` `path` (create) `` or `` `path`::symbol (edit) `` (unquoted paths also parse). Once that task integrates, no later task may target its protected files, and candidate changes to them are rejected except when validating the task that declares them. A wrong acceptance test returns to the caller for a TDD revision through its review loop and agent gate; the implementer does not change the test to make its code pass.

A file-changing task's `Verify` checks only its own targets: the tests and files it changes. For `Targets: none`, `Verify` checks only the task's stated non-file outcome and the evidence it is expected to produce. Never put whole-repository checks — the full test suite, whole-tree type checking, or whole-tree lint — in any task's `Verify`. Record those checks separately as execution-owner integration and final gates. The execution owner runs them personally once per integration/merge and is responsible for catching cross-task errors before merging.

For example:

```markdown
### T07 — Reading order and outline
- Depends on: T06
  - T06 — supplies blocks and segment rendering.
- Targets: `src/order.rs`::order (create); `src/lib.rs` (edit)
- Change: Implement TDD §6.6 reading order and §6.8 outline.
- Tests: Add ordering and outline regression cases.
- Done when: Every stored block is visited once in stable order.
- Verify: Run `cargo test order`; expect ordering and outline cases to pass.
```

The validator at `scripts/check-implementation-plans.py` checks task-block grammar, direct edges, assignment pair syntax/uniqueness, and protected-file targets with `--check <plan-path...>`; `--json <plan-path...>` emits parsed tasks. For candidates, `--protected-diff <plan-path> --repo <repository-root> --base <base-revision> --head <candidate-revision> [--task <task-id> --worktree-root <repo-root>/.worktrees]` checks protected paths and, for assigned tasks, the registered worktree under the fixed repository root, its recorded branch, clean candidate tip, and accepted-base ancestry. Supply both optional flags for assigned task candidates; omit them for out-of-plan candidates to enforce all `Protects` declarations. Old unassigned plans remain valid, including legacy protected-diff checks; new dispatches record assignments first. Git cannot prove where a commit was authored or prevent other writes. A Playbook checkout provides the script. It ignores fenced code and prose outside task blocks.

If decomposition reveals an unresolved design choice, return the precise question to the owning document instead of hiding it inside a task. Planning does not authorize changing the design.

### Code tests

Code tests provide executable proof for behavior and technical contracts. They reference requirement IDs, scenario names, or technical contract names; they do not become the only place where the contract is explained.

### Decisions

A settled decision is just the rule in the document that owns its scope; do not call it out as a decision or create a separate decision record. A system-wide technical rule belongs in the [system architecture](#system-architecture) document; a rule that spans more than one slice of a feature belongs in that feature's [system design](#feature-system-design); and a rule contained in one slice belongs in that slice's [technical design](#technical-design-document). A product-direction rule belongs in the [product vision](#product-vision), and a rule about one feature's promise belongs in its [Product Requirements Document](#feature-product-requirements-document).

When the reason for a settled rule is not obvious, preserve the reasoning beside it as briefly as possible; use more than one sentence when needed. An open decision is one that needs the developer's input or unfinished research. Put it in the owning document's open decisions and tag it `[NEEDS YOUR CALL]`. When a decision changes, revise the rule in place rather than leaving competing current readings.

Future product ideas that are not ready for a document live in the [roadmap](#roadmap) as ideas, not as decisions.

## Reference over repetition

Use this rule whenever information could appear in more than one document:

> Define a fact once in the document that owns it. Everywhere else, reference the owning file, heading, requirement ID, scenario, contract, or task.

### Reference rules

- A product vision owns durable product-wide users, problems, principles, boundaries, success signals, and constraints.
- A roadmap holds product ideas until they are ready for a document, the features in progress, and the log of finished features.
- Feature notes hold material for a feature's documents that are not drafted yet, until those documents exist.
- A system architecture document owns system-wide technical foundations — implementation language, frameworks, repository structure, tooling, and cross-cutting technical conventions — and the system-wide technical decisions that produced them.
- A Product Requirements Document owns requirement wording.
- A system design owns feature-wide architecture, shared invariants, and decisions that span more than one slice of its feature.
- A technical design owns slice-local interfaces, technical decisions, and their rationale.
- The technical design's [behavioral acceptance](#behavioral-acceptance) owns observable scenarios, whether expressed in Gherkin or a justified alternative.
- Technical contracts own internal preconditions, postconditions, and invariants.
- An implementation plan owns task dependencies and work order.
- Code tests own executable proof.

A short local summary is allowed when a reader cannot understand the current section without it. Label the summary as context, link to the authority, and do not introduce new normative wording.

An explicitly referenced, applicable parent constraint already governs the child document. Do not require a copied child rule or a new child requirement ID solely to repeat that constraint; use a reference for traceability and verification. Add a child-owned requirement only for a distinct feature-specific obligation, interpretation, or exception that the parent does not already define.

When an authoritative fact changes:

1. Update its owning document.
2. Check every reference to its identifier or heading.
3. Update dependent contracts only when the changed fact alters them.
4. Do not synchronize copied paragraphs because copied normative paragraphs should not exist.

## Requirement identifiers

Each feature defines one short identifier prefix and states its meaning once in that feature's Product Requirements Document.

The examples below use `EXPORT` for a document-export feature: a signed-in user requests a downloadable copy of a selected document.

Requirement identifiers use an opaque permanent sequence:

```text
EXPORT-001
EXPORT-002
EXPORT-003
```

Rules:

- Each individual requirement bullet receives one identifier.
- An identifier does not encode the requirement's story or category.
- Moving, reordering, or wording-preserving edits do not change the identifier.
- Retired identifiers are never reused.
- A genuinely new requirement receives the next unused number.
- Other documents reference the identifier rather than copying requirement text.

## Behavioral acceptance

For the full-feature workflow, Gherkin is the conscious default and normative home for behavior observable through a technical design's boundary. Choose an alternate notation only when it communicates that behavior more precisely, such as a state-transition table for a stateful protocol. Record why the alternate is clearer and keep all normative observable acceptance for that behavior in that single authoritative home; do not maintain an equivalent acceptance list beside it.

```gherkin
@EXPORT-001
Scenario: Export a selected document
  Given a signed-in user has selected one document
  When the user requests an export
  Then the system creates one downloadable export for that document
  And the export contains the document's current content
```

Use the clauses consistently:

- `Given` states persisted entry state or a user-visible precondition.
- `When` states one developer, user, or system action.
- `Then` states an observable result, state transition, artifact, or failure.

Do not use Gherkin for private implementation details such as a module name, database index, serializer library, or helper function.

## Technical contracts and verification

Use Design by Contract when an interface or state change has meaningful preconditions, postconditions, invariants, or partial-failure behavior. Use the obligation words defined by Request for Comments 2119 (RFC 2119) inside the contract.

```text
Contract: Atomic export creation

Preconditions
- The selected document MUST pass authorization and content validation.

Postconditions on success
- One export record and its durable output artifact MUST be committed.

Postconditions on failure
- No export record MAY reference a missing or partial output artifact.

Invariants
- A committed artifact reference MUST identify a durable body with the recorded hash.

Verification
- Inject a failure at each persistence boundary and assert the applicable postcondition.
```

Use a concise RFC 2119 statement without a full contract block when no useful precondition/postcondition relationship exists. A fixed file mode, hash format, or immutable identifier rule usually needs one normative statement and one verification criterion.

### RFC 2119 vocabulary

- `MUST` or `MUST NOT`: required for correctness, safety, or compatibility.
- `SHOULD` or `SHOULD NOT`: expected unless a documented exception justifies another choice.
- `MAY`: optional behavior with no implied requirement.

Do not capitalize ordinary prose for emphasis. Reserve these words for normative obligations.

## Recommended technical-design order

Use only the sections that apply, but preserve this reasoning order. Apply [the technical-writing standards](technical-writing-standards.md) when writing the sections; this guide assigns their place in the design rather than restating their writing rules.

1. **Status and parent contracts** — Name the owning documents and requirement IDs.
2. **Purpose, entry state, and exit state** — Bound the slice.
3. **Explicit non-goals** — Apply [non-goals and boundaries](#non-goals-and-boundaries).
4. **Rejection criteria and failure modes** — Define the edges before the happy path.
5. **Data-flow traces** — Show how concrete data moves and becomes durable.
6. **Concrete interfaces and data model** — Define signatures, commands, schemas, and guarantees.
7. **Tradeoff decisions** — Record benefits, accepted costs, and unresolved calls.
8. **Behavioral acceptance** — Define observable behavior in Gherkin by default, or record the justified alternate notation that is its sole authoritative home.
9. **Technical contracts and verification** — Define internal obligations with Design by Contract and RFC 2119.
10. **Handoff** — State the exact state available to the next slice.

## Full-feature workflow

The main session drives this sequence and is the only session that talks to the developer. Subagents needing a developer decision stop and report to their caller. Every draft goes through the [document review loop](document-review.md#review-loop), including its ledger, harness-selected full/change-check mode, and cycling stop, then its [gate](#approvals). Developer requests follow [Gate requests](communication-policy.md#gate-requests).

### 1. Maintain product direction

Create the product vision if it is missing. Otherwise update it only when durable product direction changes; feature work does not silently rewrite it. Complete its review loop and gate before proceeding.

### 2. Establish system architecture

Create `docs/architecture.md` after the vision and before the first PRD if it is missing. The project has one architecture. Later features update it only when they change a system-wide foundation; feature-wide and slice-local choices belong in their respective designs.

### 3. Define one feature

Start from the feature's roadmap item when one exists: move it to Now with its start date and use its ideas as source material. Create and obtain approval for `docs/features/<feature-name>/prd.md`. Assign permanent requirement IDs after the requirements are stable enough for technical design.

### 4. Decide whether to slice

Apply [the slice criteria](#when-a-feature-needs-slices). A single-slice feature has no system design; its TDD follows the PRD directly. For a multi-slice feature, the system design decides the slice count, names each slice, and orders independently testable handoffs.

### 5. Define feature-wide architecture when needed

For a multi-slice feature, create `system-design.md`, defining only shared architecture and contracts and mapping each requirement ID to an owning slice. When it is ready, run [document-set coherence review](document-review.md#when-coherence-review-runs) before its developer gate.

### 6. Write the technical design

Create one `tdd.md` for the single-slice feature or the next slice in the system design's order. Resolve choices contained within its implementation contract. Route product choices to the vision or PRD, system-wide choices to architecture, and feature-wide choices to the system design.

### 7. Define acceptance and verification

Use Gherkin as the default notation for observable acceptance, or justify and name the single authoritative alternate notation. Add technical contracts for internal invariants and identify verification for each contract.

### 8. Accept the design

Resolve interface confidence under [the technical-writing standards](technical-writing-standards.md#label-interface-confidence-in-ai-written-specifications), resolve every `[NEEDS YOUR CALL]` decision, and give every requirement an owner. Run [coherence review](document-review.md#when-coherence-review-runs) when the TDD is close to done and its readiness prerequisites hold. Coherence edits and documents changed by cascade, including parents, receive change checks and renewed gates; review affected downstream documents. Agents accept the TDD through [Approvals](#approvals) after its review loop and required checks.

### 9. Create the implementation plan

Create `implementation-plan.md` from the active TDD using the [implementation plan contract](#implementation-plan). Each task identifies its direct prerequisites and the criterion it implements. Agents accept the plan after its review loop and checks; implementation starts only with valid TDD and plan acceptance and approval of every developer-gated parent.

Once the feature's documents exist, trim its roadmap Now entry under the [roadmap contract](#roadmap).

### 10. Implement and review

Dispatch [Orchestrate an implementation plan](../skill-sources/orchestrate-implementation-plan.md) beneath the main session. It builds tasks in dependency order, verifies the integrated result, runs the [post-integration code review cycle](code-review.md#review-cycle), and returns evidence and deviations without marking documents `done`. The main session then owns developer validation and document completion.

When implementation stops for a large issue or repeated failure, the main session identifies the wrong document, takes it through its review loop and gate, and reviews documents below it that depend on the change. Replan only unfinished work, preserving completed work; resume from the ledger with accepted documentation and refreshed handoffs.

### 11. Validate and close the milestone

After code review, the main session gives the developer the delivery summary, corrections, remaining risks, and exact validation steps under [Gate requests](communication-policy.md#gate-requests). A slice is not done until the developer confirms it works.

If validation fails, the developer chooses an in-slice correction, a document correction with replanning of unfinished work, or a new slice. Small corrections go through workers without changing documented behavior; larger corrections use the stop-and-replan path above. Repeat code review and developer validation after the correction.

After successful validation, return all TDD deviations to the main session. Revise the still-active TDD to match the delivered result, repeat its document review loop and coherence review as applicable, and record agent acceptance again. Only then mark the plan and TDD `done` with metadata-only transitions. Mark the PRD `done` after the last slice and the system design `done` when all its slices finish. Preserve frozen documents; move the finished feature from Now to Done with its finish date. Start the next slice's TDD after the preceding slice is validated; after the final slice, return to choosing the next feature with the developer.

## Implementation execution

The orchestration skill selects these procedures as phase-bound references. Read the applicable phase before acting; startup authorization and scheduling remain in the skill.

### 2. Own a safe integration branch

Inspect the current branch and commit, local changes, registered worktrees, and any in-progress Git operation before mutation. Record the starting state; never stash, discard, commit, or overwrite the developer's existing changes, force-switch a checked-out branch, or reuse another run's worktree without established ownership.

Use the supplied integration branch, creating it if it does not exist. If none is supplied, create a unique branch using repository naming conventions, or `impl/<plan-name>-<unique-suffix>` when none exist; start a new branch at the supplied base, otherwise the current committed `HEAD`, and report the chosen base SHA.

An existing integration branch retains its history; a supplied base is not permission to reset it. Resolve a remote-only branch to its intended remote ref instead of creating an unrelated local branch; if that identity is ambiguous, stop and report it to the caller.

Use a clean integration checkout dedicated to this run. If the branch is already checked out, use that checkout only when it is clean and available to this run; otherwise stop for ownership resolution, while unrelated local changes may remain untouched in a different checkout.

Do not silently omit local changes the implementation needs: stop and report the missing base prerequisites to the caller so the main session can obtain them before dispatch. Only you advance the integration branch; never push, merge to the default/release branch, or rewrite published history without separate authorization.

### 4. Create each worktree and hand off bounded work

Before pickup, require `<repo-root>/.worktrees/` to be ignored by Git (`git check-ignore <repo-root>/.worktrees/`). If not ignored, stop before creating any task worktree and report the missing ignore rule to the caller for resolution through the main session; never edit `.gitignore` or `.git/info/exclude` yourself, or use another location. At pickup choose a unique branch and absolute path `<repo-root>/.worktrees/<name>`; use `<repo-root>/.worktrees` as `worktreeRoot` at the candidate gate. Never overwrite existing branches or paths. Add `Assigned worktree` and `Assigned branch` after `Verify`, check the plan, and commit only this metadata when tracked. Stop and report if unable to persist it. From the resulting accepted SHA create the task worktree (`git worktree add -b <branch> <path> <sha>`). If creation fails, preserve the assignment for reconciliation; do not dispatch.

Verify registered path, branch, and base SHA before dispatch. Require work only in that worktree/branch: absolute paths for file tools, explicit worktree selection for shell/Git, never bare relative paths that may resolve against the parent's directory. Assign acceptance tests to a worker distinct from implementation; that worker edits every protected test and demonstrates the specified failure. Implementation workers cannot edit protected tests; a wrong oracle requires design review.

Give each worker a self-contained packet; do not assume it inherits this conversation:

```text
Task: stable plan ID, bounded outcome, and explicit non-goals
Workspace: absolute assigned worktree path, task branch, dispatch base SHA; use only that worktree
Authority: plan/TDD/system-design revisions and relevant sections; applicable repo instructions
Prerequisites: integrated task outputs and commits the worker can consume
Ownership: allowed files/symbols/contracts; protected tests and excluded work
Implementation: required behavior, existing patterns, acceptance, and verification commands
Environment: setup, isolated resources, and any access constraints
Escalation: report design conflicts or scope expansion immediately; do not choose a new design
Return: task ID, base and final commit SHAs, changed files, acceptance evidence,
        exact checks/results and skips, deviations/risks, and worktree/process state
```

Require the worker to inspect its targets, implement the complete bounded outcome, and keep all intended changes in commits on its task branch before returning. The worker may run assigned narrow checks when the harness permits; reserve project-wide build/lint/test suites for your integration/final gate, and obey any harness restriction on concurrent validation.

When a task adds or changes tests, the packet requires the worker to read the [test quality core standard](test-quality.md#core-standard) before writing them and gives that standard's location; the worker does not otherwise load it.

Workers must not modify the integration checkout, merge their work into it, push, delete worktrees, expand their assignment, or dispatch untracked workers. Permit a worker to merge a pinned integration commit into its own task branch only when you explicitly assign synchronization; have it stop task processes and relinquish writes when returning, including on failure, with uncommitted or incomplete work explicitly reported rather than labeled done.

### 5. Validate, integrate, then remove the worktree

Treat a returned report as a claim, not acceptance. Confirm the worker and its processes have stopped, inspect the actual commits and diff against the assigned base, and check scope, contracts, tests, documentation, and unexplained changes; reject an uncommitted, incomplete, or out-of-scope candidate and delegate the correction without editing it yourself.

Serialize integration and freeze the candidate while validating it. If the integration branch advanced since dispatch, incorporate its current accepted tip into the task branch before acceptance: you may perform a mechanical Git merge, but abort conflicts and assign their resolution to a subagent in that task worktree, then review the new candidate and rerun affected checks.
Before integrating **any** candidate, run `check_doc_status` frozen-diff and `check_implementation_plan` protected-diff against the accepted tip and candidate commit. Pass assigned task and worktreeRoot only to protected-diff for assigned tasks; omit both for out-of-plan candidates. Stop if either tool is unavailable or fails; repeat after merge or repair.

Call `check_doc_status` with `mode: "frozen-diff"`, `repo`, `base`, `head`; call `check_implementation_plan` with `mode: "protected-diff"`, `plan`, `repo`, `base`, `head`, plus `task` and `worktreeRoot` for assigned tasks. The first guards done documents and system-design revision increments; the second guards protected tests, worktree identity, clean tip, and ancestry. Personally check delivered system-design slice sections: the tool cannot infer ownership. Git cannot prove where a commit originated or prevent outside writes.

Require the current accepted integration tip to be an ancestor of the candidate; validation of an older isolated result does not prove the combined result. Personally inspect the resulting diff and run the task's acceptance checks plus relevant cross-task checks against that exact candidate, exercising the actual changed surface when applicable; worker logs and reviewer opinions supplement but never replace your own validation.
Workers run only their task's scoped `Verify`. Run every command used for task `Verify`, integration checks, post-integration smoke checks, final verification, or integrated acceptance through `run_check` with command, cwd, and timeout. Use foreground commands only. Personally run the project's whole-repository checks once per integration/merge, catching cross-task errors before merging. Every required command must return `passed`; do not merge, release dependents, or declare completion before its applicable checks pass. Expected-red commands must exit zero only for the specified failure. Preserve each `logPath` as evidence. `unavailable` means not verified, not a code failure: stop and report the missing command to the caller; never skip it or proceed past the gate. The runner uses pipefail and keeps full output outside the repository. Observing UI and other non-command surfaces is a separate, additional obligation, not a substitute for these command gates.
For an acceptance-test task, the red check succeeds **only** when each protected approved TDD scenario fails because its specified behavior is missing, with no unrelated failure; a premature pass or unexpected failure rejects the candidate. For its implementation dependent, verify the applicable protected scenarios pass without editing their tests. A check "fails" when it misses the task-specific expected result, not merely because its command returns a nonzero status.
If a check misses its expected result, keep the task unaccepted and delegate diagnosis or repair in its worktree. Distinguish a verified pre-existing failure or missing environment from a regression, but do not weaken acceptance, silently skip a required check, or call incomplete validation a pass; report a blocking prerequisite when it cannot be resolved within authorized scope.

After acceptance, confirm both candidate and integration SHAs are unchanged and the integration checkout is clean, then advance it to the exact validated candidate, for example `git merge --ff-only <validated-sha>`. If either SHA changed, re-evaluate and revalidate instead of forcing the merge; preserve repository-mandated history conventions only if they still validate the exact candidate before advancing the branch.

Verify the integration branch reached the accepted commit and run the relevant post-integration smoke commands through `run_check` under the command gate above before releasing dependents; also observe applicable non-command surfaces. A post-integration failure blocks further dispatch and integration until a subagent repair is accepted; retain the failed-task evidence and worktree rather than deleting them or hiding the failure with a destructive reset.

Only after the task's work is merged into the integration branch (or main, if that is the integration branch) and post-integration checks succeed, save evidence outside its worktree. Confirm no worker/process remains and no uncommitted, untracked, or valuable ignored work would be lost, then `git worktree remove <task-path>` and `git branch -d <task-branch>` (never `-D`). Record both cleanup results in the ledger. Never remove an unmerged worktree or force-delete its branch; preserve and report dirty, failed, or unmerged worktrees, and never delete the integration branch or developer's checkout.

### 6. Handle bounded issues; halt for significant design changes

A small issue is a local implementation correction or plan clarification that preserves documented behavior, interfaces, invariants, and acceptance. Delegate it to a worker with explicit scope, keep evidence under the affected task, and have a worker update the owning living documentation or plan when needed under [reference rules](#reference-rules). Do not turn incidental cleanup into new product work. Record every TDD departure, repair attempt, and result in the ledger. After three failed repairs for one task, use the stop-and-report procedure below rather than retrying indefinitely.

A significant issue changes a material TDD or system-design decision, product behavior, a shared interface/invariant, compatibility, security, or data ownership; also stop for a complex or far-reaching issue spanning multiple tasks. A wrong acceptance-test oracle needs a TDD revision through its review loop and agent gate, not a fix by an implementation worker. Changing a produced interface or `Done when` outcome relied upon by dependent tasks requires replanning even if that output has not yet been produced. Examples include replacing persistence strategy, changing a shared API, or discovering a false transaction assumption; file count alone does not determine severity, and uncertainty about material impact is a reason to stop.

On a significant issue or repeated repair failure:

1. Stop new dispatch, acceptance, and merges for the entire run, including independent tasks. Tell every active worker to stop and preserve work; cancel or terminate through the harness if needed.
2. Confirm workers and task processes are stopped. Record any inability to stop as a safety blocker, reject late returns from automatic acceptance, and preserve worktrees, commits, ledger, and evidence without cleanup or destructive rollback.
3. Report to the caller what happened, the evidence, conflicting document sections, the document believed wrong, affected tasks, completed and unfinished work, viable resolutions, tradeoffs, and a recommendation. Then end the implementation run; do not ask the developer directly or wait within this subagent for a decision.

The main session follows [the correction and replanning path](#10-implement-and-review). A resumed implementation run reads the preserved ledger, keeps completed work, validates accepted revised documentation through both candidate gates, reruns the plan static check, and rechecks affected previously accepted work. Reassign unfinished tasks from the updated integration tip with refreshed handoffs; repair or replace stale candidates through workers rather than merging old-design returns unchanged.

### 7. Verify the complete branch and deliver it

After all planned outcomes are integrated, run the repository's required final verification and integrated feature acceptance on the final branch tip. Before executing their commands, read and apply the [command verification gate](#5-validate-integrate-then-remove-the-worktree), using `run_check`; observing the actual CLI, UI, service, or other changed surface remains an additional obligation. If documents declare invariants, dispatch `review-code-invariants-agent` on the final tip against the run's base; findings follow step 6. Delegate every discovered fix and repeat affected acceptance and final checks after integration; no task count, green worker report, or successful merge substitutes for working end-to-end behavior.

After integrated acceptance and final verification, run the [post-integration review cycle](code-review.md#review-cycle). Once that cycle concludes, return the delivered branch, exact evidence, corrections, risks, preserved ledger, all TDD deviations, and concrete developer validation steps to the caller. The main session owns [developer validation and completion](#11-validate-and-close-the-milestone). Do not mark any document `done` in the implementation run. Delegate other authorized delivery material, clean up only safe worktrees, and report blockers.
