---
state: draft
revision: arch-r9
---

# System architecture: Software Factory

## Status

This document records how the Playbook is built to deliver its guidance: the rules anyone adding a guide, skill, agent, checker, or tool must follow. The guidance itself, including the documents-first process, lives in `guides/`; product direction lives in the [product vision](product-vision.md).

## Imposed constraints

The product-wide boundaries and constraints every feature must preserve, in the [repository's product vision](../../../docs/product-vision.md) and [this playbook's](product-vision.md), bind every choice here; this document gives versioned contracts and the developer's safety their technical form without restating them. The Playbook ships no runtime for consuming projects and runs only on the developer's machine, inside OMP or a shell.

## System boundary

- **OMP.** Owns discovery of agent and skill capability directories, extension loading, the extension API and the schema builder that tools are declared with, agent dispatch and models, sessions and provider calls, and interactive questions. The Playbook integrates as an extension package declared in `package.json` [EXISTS]; installation, update, and OMP runtime facts live in `integrations/omp.md` [EXISTS].
- **`python3` on `PATH`.** Owns execution of every checker, renderer, gate runner, and the build; the Playbook reaches it only as a child process.
- **Git.** Owns history, revisions, branches, worktrees, and release tags; checkers read it only through the `git` command. How a consumer obtains and pins a checkout is owned by [install](../integrations/omp.md#install).
- **Consuming project repositories.** Each owns its own documents, commands, toolchain, and exceptions; the Playbook reads them through agents and checker arguments, and writes approval records only through the exception below.

## Technology decisions

- OMP is the only harness the Playbook targets. Guides, skill sources, scripts, and generated output may state OMP facts directly; no layer is kept harness-neutral for portability.
- All deterministic logic — checkers, the developer-request renderer, the gate runner, and the skill build — is Python 3 using only the standard library, run as command-line programs with no install step. The gate runner requires Bash on `PATH` for pipeline failure propagation.
- Extension code is TypeScript that OMP loads directly, with no build step. At runtime it uses only Node built-ins and what OMP's extension API supplies; tool schemas use the API's `pi.zod`, a Zod-compatible subset that lacks some Zod methods (`README.md` [EXISTS] records the known gaps). The only package dependency is the development dependency `@oh-my-pi/omptype`, declared in `package.json` and locked in `bun.lock` [EXISTS], which the tests use to exercise OMP's real schema builder at the verified OMP release.
- Human-authored content — guides, skill sources, agents, templates, and documents — is Markdown; machine-readable contracts are JSON, and JSON Schema where a shape is validated.

## Parts and repository structure

The Playbook is the package at `playbooks/software-factory/` in the `agent-playbooks` repository; paths in this document are relative to the package unless they name the repository root. The package separates authored rules, authored task procedures, generated per-task artifacts, deterministic programs, and extension code, so each rule and each check has exactly one home. Package layout (every `[EXISTS]` path in this document was verified by listing the package root, the repository root, and the named directories):

- `guides/` [EXISTS] — shared rules, each stated once, plus machine-readable contracts such as `guides/developer-request.schema.json` [EXISTS].
- `guides/migrations/` [EXISTS] — guided migrations for major releases.
- `skill-sources/` [EXISTS] — one authored task procedure per skill, selecting guide sections by link.
- `skills/` [EXISTS] — generated per-task skills (`SKILL.md` plus `references/`); committed so consumers never build.
- `agents/` [EXISTS] — one OMP agent per skill, plus `agents/routing-cases.json` [EXISTS] and build-check exceptions in `agents/checks.json` [EXISTS].
- `scripts/` [EXISTS] — the build and the checker command-line programs.
- `extensions/` [PROPOSED] — way-of-working OMP extensions, one module each; created with the first such extension.
- `tests/` [EXISTS] — executable proof for `scripts/` and all extension code.
- `templates/` [EXISTS] — starting files consumers copy by hand into their own projects.
- `integrations/` [EXISTS] — installation, update, and OMP runtime facts a consumer acts on.
- `research/` [EXISTS] — evidence notes that inform guidance and never govern it.
- `docs/` [EXISTS] — the Playbook's own product documents.
- Package root files: `omp-extension.ts` [EXISTS] (contract tools, contract hooks, and developer commands), `omp-settings.yml` [EXISTS] (OMP settings the agents need), `package.json` [EXISTS] and `bun.lock` [EXISTS] (extension manifest and locked development dependency), `VERSION` [EXISTS], `README.md` [EXISTS].
- Repository root files shared by every package: `lefthook.yml` [EXISTS] (Git hooks), `mise.toml` [EXISTS] and `mise.lock` [EXISTS] (maintainer tool pins and tasks), `.rumdl.toml` [EXISTS] (Markdown check configuration), `LICENSE` [EXISTS], and the maintainer's issue-tracker state in `.beads/` [EXISTS], which Git ignores and consumers never load.

## Content flow

- **One home per rule.** A rule lives in one guide section. A skill source links to the sections its task needs, and `scripts/build-skills.py` [EXISTS] inlines guidance every run needs into `SKILL.md` and ships conditional guidance as references ([skill construction](../guides/skill-design.md#scope-and-disclosure)). No skill source, agent, or integration note restates a guide rule.
- **Generated output.** Only the build writes `skills/`; authors edit `guides/`, `skill-sources/`, and `agents/`. The build refuses to overwrite a file without its generated marker, and its check fails on stale output.
- **Loading.** OMP loads everything through the extension package: it discovers `agents/` and `skills/` as capability directories, each agent autoloads its generated skill, and the extension modules named in `package.json` register tools ([integrations/omp.md](../integrations/omp.md)). Templates are the only content a consumer copies.

## Boundaries and dependency rules

- **Contract tools.** A tool that enforces or renders a Playbook contract is registered in `omp-extension.ts`. Domain validation and rendering live in a `scripts/` program; the tool owns only transport: declaring its arguments, rejecting argument combinations a mode does not accept, running the program as a bounded child process, and checking the result envelope — exit status, unexpected output, and JSON shape — before returning it. The program's command-line mode is the fallback when the tool is not loaded, not a portability promise.
- **Contract hooks.** Hooks that enforce Playbook contracts live in `omp-extension.ts`, next to contract tools, and act through OMP's extension API. They protect approval and ledger writing boundaries and enforce document order, implementation gates, and per-document review-round gates using the contract programs. They are inert in consumer repositories without `docs/user-approvals.json`. Enforcement prevents forgotten or skipped steps; it is not a sandbox against deliberate circumvention.
- **Way-of-working extensions.** An OMP extension that supports the way of working without enforcing a Playbook contract — for example, a prompt-cache keep-alive, should one ever be built — is its own module under `extensions/`, declared in the extension list in `package.json`, and acts only through OMP's extension API. Contract tools never depend on such a module, so each one can be removed alone.
- **Trust boundary.** Contract tools and checkers only read files and Git state named by their arguments, never use the network, and never contact the developer. Explicit write exceptions are `run_check`'s external full-output logs and execution of project-owned commands, `doc_approval`'s agent acceptance records in the named consumer repository, and Playbook hooks and `review_ledger`'s tracked review ledgers under that repository's `.playbook/reviews/`. Only the developer edits `docs/user-approvals.json`, by hand; no tool or script mode writes it. `/playbook-hash` is read-only. Contract hooks refuse direct agent writes to approval files and review ledgers.
- **Tracked persistence, no service.** Durable governing facts are files under Git in this repository or the consuming project. Per-document and feature-coherence review ledgers under the consumer's `.playbook/reviews/` persist rounds, findings, decisions, and body-hash receipts and are written only by the Playbook. Gate-runner evidence logs live in the system temp directory; the Playbook runs no persistent service.

## Consumer contracts and versioning

A consumer contract is any format, grammar, mode, output, or schema that consuming projects' documents, agents, or callers depend on. Each has one owner; change it there. Each entry also names who reads it today, and any reader that is planned but not yet reading. A field, section, or mode with no reader does not belong in a contract; when a reader goes away, apply the [removal rule](../README.md#changing-the-playbook) to whatever served only that reader.

- Document formats and frontmatter: [document contracts](../guides/product-documentation-process.md#document-contracts), checked by `scripts/check-doc-status.py` [EXISTS]. Read by the draft and review-doc agents through `check_doc_status`, and by the `orchestrate-factory` skill and implementation and fix orchestrators. Consumer product-document frontmatter carries lifecycle state and revision; approval comes from the separate approvals contract. Playbook guides are internal guidance outside that scheme and retain their existing frontmatter contract.
- Developer approval records: `docs/user-approvals.json` in each opted-in consumer repository, a path-to-body-hash object maintained only by the developer. Its existence is the factory opt-in. The [approvals contract](../guides/product-documentation-process.md#approvals) owns gate types and content-bound validity; `scripts/doc_approvals.py` [EXISTS] owns shared strict JSON parsing and hashing. Read by `check_doc_status`, approval and status programs, and contract hooks; factory, drafting, implementation, and fix workflows read state through the tools.
- Agent acceptance records: `docs/agent-approvals.json` in the consumer repository, a path-to-`{hash, evidence}` object written only through `doc_approval`; a missing file means no acceptances. The same approvals contract and shared module own validation and validity, and the same programs and workflows read it.
- Agent approval operations: `scripts/doc-approval.py` [EXISTS] owns command-line modes and JSON results; `doc_approval` in `omp-extension.ts` owns tool arguments and transport for `status`, `accept`, and `revoke`. The [approvals contract](../guides/product-documentation-process.md#approvals) owns when to revoke or accept agent-gated documents. Called by the `orchestrate-factory` skill, document-writing drafters, and implementation and fix orchestrators; validity is also read by `check_doc_status` through the shared module. Review agents remain read-only.
- Factory status: `scripts/factory-status.py` [EXISTS] owns document-derived feature, slice, gate, ambiguity, and next-step output; `factory_status` in `omp-extension.ts` owns tool arguments and transport. Read by the `orchestrate-factory` skill and contract hooks; drafters and implementation and fix orchestrators use it when they need the expected document step. Approval validity uses the same shared module as `check_doc_status`. Execution phase remains with the main-session skill; review rounds come from `review_ledger status`, not the factory-status program.
- Review ledgers: `scripts/review-ledger.py` [EXISTS] owns parsing, mode selection, baseline diffs, recurrence, and transitions under the consumer's `.playbook/reviews/`; `review_ledger` in `omp-extension.ts` owns transport for `status`, `decide`, `void`, `close`, and `request-full`. Hooks record and gate only main-session `review-doc-*` dispatches and append change-check packets, not subagent reviewer dispatches. The factory caller reads complete reports and records decisions through the tool. `doc_approval` requires a closed current-body receipt and generates acceptance evidence from it.
- Contract-hook decisions and refusal results: `omp-extension.ts` owns hook registration, opt-in detection, reviewer-dispatch transport, developer-answer notifications that lift cycling refusal, and shared refusal text. Domain rules and ledger transitions belong to the contract programs. Governing rules live in [approvals](../guides/product-documentation-process.md#approvals), [full-feature workflow](../guides/product-documentation-process.md#full-feature-workflow), [implementation execution](../guides/product-documentation-process.md#implementation-execution), and [document review](../guides/document-review.md#review-loop).
- Developer hash command: `/playbook-hash <path>` in `omp-extension.ts` invokes the read-only `--hash` mode of `scripts/doc-approval.py` [EXISTS], which returns the path, body hash, and paste-ready entry line for any existing file inside the consumer repository; without a path, it returns those entries with approval state for every developer-gated, non-superseded document. The developer reads the notification and records accepted developer-gated content by hand in the user file. The [gate requests](../guides/communication-policy.md#gate-requests) and [approvals](../guides/product-documentation-process.md#approvals) sections own approval meanings and recording rules.
- Implementation-plan grammar: [implementation plan](../guides/product-documentation-process.md#implementation-plan), checked by `scripts/check-implementation-plans.py` [EXISTS]. Read by the plan drafter, plan reviewer, and orchestrator through `check_implementation_plan`. Planned: a supervising tool reporting task progress ([roadmap](roadmap.md), plan progress reporting).
- Checker command-line modes and JSON output: each program in `scripts/`, described in the guide section it checks. Read by the contract tools in `omp-extension.ts`, which check the exit status and JSON shape; no skill calls a JSON mode directly.
- Tool arguments: the tool declarations in `omp-extension.ts`. Read by the agents that list each tool in their frontmatter `tools`.
- Developer requests: `guides/developer-request.schema.json`, rendered by `scripts/request-developer.py` [EXISTS]. Called by the seven draft agents and the orchestrator; the rendered Markdown is read by the developer. Planned: an observer that reads the call arguments rather than the Markdown ([OMP integration](../integrations/omp.md)).
- Task verification: `scripts/run-check.py` owns execution, Bash pipefail, timeouts, external logs, and passed/failed/timed-out/unavailable results; `run_check` declares arguments. Missing commands (exit 127) are unavailable, not verified and not a task-code failure. Read by the orchestrator, which gates task, integration, and final checks on its results.
- Markdown review reports: the [document](../guides/document-review.md#report), [code](../guides/code-review.md#report), [skill](../guides/skill-authoring.md#report-without-editing), and [friction](../guides/friction.md#report) report contracts, delivered as [review report delivery](../guides/agents.md#review-report-delivery) specifies. Read by the agent that dispatched the reviewer, as [reading reviewer reports](../guides/agents.md#reading-reviewer-reports) specifies; friction reports are also read by `review-skill` when supplied as evidence. No program parses them.
- Friction lines: the [Friction line](../guides/communication-policy.md#friction-line) rule. Read by `scripts/collect-agent-runs.py` [EXISTS] through `collect_agent_runs`, and by `review-friction`.
- Package OMP settings: `omp-settings.yml` [EXISTS], a YAML mapping of OMP settings the agents need and never `extensions`. Read by the install snippet in the repository README, which appends it to the generated overlay so the settings apply only where the playbook is installed; [integrations/omp.md](../integrations/omp.md#verify) names why each setting is needed.

Rules shared by every contract:

- **Program output.** A checker is deterministic for the same files and revisions. It reports diagnostics on standard error with a nonzero exit, and writes standard output only in its machine-readable modes; tools treat any other output as a failure.
- **Optional arguments.** A null or empty optional tool argument means absent, except where a mode requires a supplied argument to be non-empty; each such exception is declared with the tool in `omp-extension.ts`.
- **Releases.** `VERSION` owns the release number, and each release is the Git tag `v<version>`; the `package.json` version is not a release identifier. Numbers follow [Semantic Versioning](https://semver.org/): a change that makes a previously valid document, plan, tool call, or report consumer invalid, or changes the meaning of existing output, bumps the major number; an additive contract change bumps the minor number; a release with no contract change bumps the patch number.
- **Migrations.** Each major release ships its guided migration for consumer repositories as `guides/migrations/<from>-to-<to>.md`, named by the two release numbers. Minor and patch releases have none, because everything that was valid stays valid; a changed install snippet is picked up from the repository README when upgrading. The first is `guides/migrations/0.1.0-to-1.0.0.md` [EXISTS].

## Build, checks, and gates

- `scripts/build-skills.py` is the only build; its check mode gates generated-output freshness, the agent contract, and routing cases ([build check](../guides/agents.md#build-check)), and holds every generated skill within the size limit it owns.
- Checker tests are black-box command-line contract tests under `unittest` that run each program as a subprocess against temporary files and temporary Git repositories. Extension tests run under Bun's test runner against OMP's real schema builder and the real programs. The README owns the commands.
- Maintained Markdown passes rumdl, pinned in the repository root's `mise.toml` and `mise.lock`, configured by the root `.rumdl.toml`, and run by the `lint-markdown` task in the root `mise.toml` over the whole repository; generated skills are excluded.
- The repository root's `lefthook.yml` defines local hooks: pre-commit regenerates, stages, and checks this package's generated output; pre-push runs this package's Python tests, Bun tests, and real installed-OMP sandbox load check with no model turn, plus the Markdown check. They run only in a clone where installed ([changing the playbook](../README.md#changing-the-playbook)) and can be skipped, so they are not a guaranteed gate. There is no hosted continuous integration.

## Conventions

- Agent frontmatter, body, description, and routing cases: [agents and skills](../guides/agents.md), checked by the build.
- Skill sources and generated skills: [skill construction](../guides/skill-design.md) and [skill authoring](../guides/skill-authoring.md).
- Prose: [technical-writing standards](../guides/technical-writing-standards.md).

## Technology index

| Choice | Status | Authority | Rule |
| --- | --- | --- | --- |
| OMP as the only harness | Decided | Developer, 2026-09-29 | [Technology decisions](#technology-decisions) |
| Python standard-library programs | Decided | Developer, repository at `96ae784` | [Technology decisions](#technology-decisions) |
| Extension runtime uses only OMP's API | Decided | Developer, 2026-09-30 | [Technology decisions](#technology-decisions) |
| Markdown and JSON formats | Decided | Developer, repository at `96ae784` | [Technology decisions](#technology-decisions) |
| Repository layout | Decided | Developer, repository at `96ae784` | [Parts and repository structure](#parts-and-repository-structure) |
| One home per rule | Decided | Developer, repository at `96ae784` | [Content flow](#content-flow) |
| Generated skills | Decided | Developer, commit `f10819d` | [Content flow](#content-flow) |
| Extension loading | Decided | Developer, repository at `96ae784` | [Content flow](#content-flow) |
| Contract tools wrap programs | Decided | Developer, 2026-09-30 | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Way-of-working extensions | Decided | Developer, 2026-09-29 | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Read-only runtime and pinned copy | Decided | Developer, repository at `96ae784` | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Project-command gate runner and external log exception | Decided | Developer, 2026-09-30 | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Consumer agent-acceptance-write exception | Decided | Developer, 2026-10-02 | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Contract hooks beside contract tools | Proposed | Developer, pending approval | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Tracked per-document review ledgers | Decided | Developer, 2026-10-05 | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Separate content-bound developer approvals and agent acceptances | Decided | Developer, 2026-10-02 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Agent approval tool and shared approval module | Decided | Developer, 2026-10-02 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Document-derived factory status | Proposed | Developer, pending approval | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Read-only developer hash command | Decided | Developer, 2026-10-02 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| No persistence or service | Decided | Developer, repository at `96ae784` | [Boundaries and dependency rules](#boundaries-and-dependency-rules) |
| Consumer contract owners | Decided | Developer, 2026-09-30 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Program output contract | Decided | Developer, repository at `96ae784` | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Optional tool arguments | Decided | Developer, 2026-09-30 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Release identity and Semantic Versioning | Decided | Developer, 2026-09-29 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Migration guides for major releases only | Decided | Developer, 2026-10-05 | [Consumer contracts and versioning](#consumer-contracts-and-versioning) |
| Build check | Decided | Developer, repository at `96ae784` | [Build, checks, and gates](#build-checks-and-gates) |
| Contract test strategy | Decided | Developer, 2026-09-30 | [Build, checks, and gates](#build-checks-and-gates) |
| Markdown check with rumdl | Decided | Developer, 2026-09-29 | [Build, checks, and gates](#build-checks-and-gates) |
| Local hooks, no hosted CI | Decided | Developer, 2026-09-30 | [Build, checks, and gates](#build-checks-and-gates) |
