---
state: draft
revision: arch-r1
---

# System architecture: Agent Playbooks

## Status

This document records the repository-wide foundations of `agent-playbooks`: how playbook packages are laid out, released, and loaded, both in OMP sessions the developer starts by hand and in sessions Orch starts. Each package's internal architecture is owned by that package's own `docs/architecture.md`.

## Imposed constraints

- **OMP discovers capabilities only at a package root.** OMP finds `agents/` and `skills/` only directly under an extension package's root; a package's dependencies contribute none. Each settings layer's `extensions:` list replaces the one below it, and when two packages define an agent with the same name, OMP silently keeps the first.
- **A playbook loads only in repositories of its kind**, works per repository with and without Orch, and needs few setup steps.
- **Orch's playbook interface.** Orch consumes a playbook as one OMP extension package, identified by its `package.json` `name`. It pins each playbook separately as an immutable copy of one committed revision, loads it explicitly into each session, and reads only the formats the playbook documents. No playbook may reference Orch.

## System boundary

- **OMP.** Owns extension and capability discovery, settings layering, sessions, subagents, and transcripts. Every playbook integrates as one extension package.
- **mise.** Owns downloading, installing, and pinning a release for hand-started sessions, and exporting the environment that points OMP at it. Reached only through the consuming repository's committed `mise.toml`.
- **GitHub** (`aintnorest/agent-playbooks`) [EXISTS]. Owns the public release archives that mise downloads by tag.
- **Orch.** Owns which playbook each project and session uses, launching and sandboxing the sessions it starts, its own pinned copies of playbook revisions, relaying network `git` and `gh` operations, and writing a developer approval on the developer's action in Orch. It depends on playbooks one way, through documented formats.
- **Consuming repositories.** Own their project facts, documents, and approval records. They declare a playbook with a committed pin and carry one `AGENTS.md` tripwire line that tells an agent to stop when the playbook's entry skill is missing; nothing else is copied in.
- **`python3`, Git, and Bash on `PATH`.** Own execution of every playbook program; packages reach them only as child processes.

## Technology decisions

- OMP is the only harness every playbook targets.
- Every package runs from a plain copy of a committed revision with no install or build step, because Orch's pinned copies and mise's release archives are used as they are. Deterministic logic is standard-library Python run as command-line programs; extension code is TypeScript that OMP loads directly, using only Node built-ins and OMP's extension API at runtime; generated content is committed.
- Human-authored content is Markdown; machine-readable contracts are JSON, and JSON Schema where a shape is validated.

## Parts and repository structure

One Git repository holds every playbook, each as its own self-contained OMP extension package, so one checkout tests and releases them together while each loads alone. Paths verified by listing the repository root and `playbooks/`, and remote tags with `git ls-remote`:

- `playbooks/<name>/` — one OMP extension package per playbook. Its `package.json` `name` is the playbook's permanent identity and matches the directory name; renaming it makes Orch see a different playbook.
  - `playbooks/software-factory/` [EXISTS] — the Software Factory playbook.
- `core/` [PROPOSED] — shared machinery and guidance, created only when a second playbook needs something the first already has.
- `docs/` [EXISTS] — this repository's own product vision, architecture, and working notes; nothing here is loaded at runtime.
- Root files shared by every package: `README.md` [EXISTS] (consumer install, upgrade, local-checkout, and Orch notes, plus contributor workflow), `lefthook.yml` [EXISTS], `mise.toml` [EXISTS] and `mise.lock` [EXISTS] (maintainer tool pins and tasks), `.rumdl.toml` [EXISTS], `LICENSE` [EXISTS], and `.beads/` [EXISTS] (maintainer issue tracking, never loaded by consumers).

## Boundaries and dependency rules

- **A playbook is one self-contained package.** Everything a playbook needs at runtime — agents, skills, guide references, extension code, and programs — is inside its package directory, because Orch and the mise overlay each load exactly one package per session.
- **Playbooks do not depend on each other.** When two playbooks need the same rule or program, it moves into core; it is never copied by hand.
- **Packages never name Orch.** Orch-specific glue lives in Orch. What a package must tolerate under supervision is stated generically under Supervised sessions; what Orch needs from this repository is recorded only at repository level, in this document and the root README.
- **Packages hold method only.** Facts about a consuming project stay in that project, and no package names a consuming repository.
- **Loading decides where a package runs; a marker decides whether its gates act.** OMP rebinds every extension into every session in the process, so each hook checks the session repository for its playbook's own marker file before acting; tools are not gated. Software Factory's marker is the consumer's `docs/user-approvals.json`.
- **Agent and skill names are unique across all packages.** New playbooks prefix theirs with the playbook name; Software Factory keeps its unprefixed names because its run history is found by agent name.

## Loading

A consuming repository declares one playbook or none. Both paths load the same package directory from a committed revision, and neither reads the other's declaration.

- **Hand-started sessions: pinned release through mise.** The repository's committed `mise.toml` pins a release of this repository as a mise tool named for the playbook. mise installs the tagged archive, writes an OMP settings overlay naming the package by absolute path, and exports that overlay to OMP while the shell is inside the repository, including subdirectories and in-repository worktrees. The developer's global `extensions:` list stays empty, so a repository with no declaration loads no playbook. The root README holds the snippet and setup steps. Tradeoff: OMP started without mise's environment loads no playbook, silently; the `AGENTS.md` tripwire makes that visible.
- **Playbook authors** point one consuming repository at a live checkout through an uncommitted `mise.local.toml` override, never by editing the committed pin.
- **Package OMP settings travel with the package.** OMP settings a playbook's agents need live in the package's `omp-settings.yml`, never in the developer's global configuration, and the install step appends them to the overlay, so they apply only in repositories using that playbook. Overlay settings merge with the global configuration key by key; only arrays such as `extensions:` replace it.
- **Orch-started sessions.** Orch launches every session with OMP's extension discovery off and passes the session's selected playbook package explicitly from its own pinned copy, so the repository's `mise.toml`, overlays, `.omp/` settings, and installed plugins have no effect, including a package's `omp-settings.yml`. The developer chooses the playbook in Orch; Orch never infers it from the repository. The tripwire still works, because Orch loads the root `AGENTS.md`.
- **Hand-started sessions do not imitate Orch's launch.** Turning extension discovery off also drops OMP's bundled `/review`, `/green`, and `/annotate` commands; the mise overlay loads the same package without that cost.

## Supervised sessions

Every package works unchanged whether a session is hand-started or run by a supervising environment such as Orch. Packages state these rules without naming any supervisor:

- **Worktree location.** A session may start in a worktree outside the main checkout and may be able to write only that worktree and the repository's Git metadata; the main checkout and other worktrees may be read-only. A package finds the main repository through Git's common directory, never through relative paths or by assuming its worktree sits inside the main checkout.
- **Worktrees a package creates** go under OMP's `OMP_WORKTREE_DIR` when it is set, otherwise under `<main root>/.worktrees/`, which must be Git-ignored. Worktrees are never nested, and a package removes only worktrees it created.
- **Plain `git` and `gh`.** Packages use ordinary commands; a supervisor may relay network operations, and credentials and secrets may be unreadable inside the session.
- **Enforcement lives in extension hooks, never Git hooks**, because a supervisor may not run repository hooks.
- **Developer approvals may arrive from outside the session.** A supervisor may write a package's documented developer-approval record on the developer's action; the package treats that write as the developer's.

## Core

Core is created only when a second playbook needs something the first already has; until then, code used by one playbook stays in that playbook even if it looks general. Core never depends on any playbook. Meta work — building, routing, reviewing, and improving agents and skills — is core; domain work belongs to a playbook.

The build copies everything a playbook uses from core — generated agents, skills, and guide references, and core's code — into that playbook's package, and its check fails on stale copies. A package never imports from outside its own directory, so the package directory alone is the playbook's version, which is what Orch compares between pinned commits. Tradeoff: every package commits generated duplicates, and one core change shows up as a diff in each package that uses it; importing core by relative path would make every core change look like a new version of every playbook, and a published dependency would need an install step.

## Releases and versioning

- **A release is a Git tag of this repository.** mise and Orch both consume committed revisions only, never a working tree or plugin cache.
- **Each playbook is tagged separately, as `<name>-v<version>`**, so a consumer is offered only its own playbook's releases and each version number keeps its meaning; the cost is a different install-snippet URL per playbook. Software Factory's existing tags are bare `v<version>`; see Current scope.
- **Each package's `VERSION` owns its release number**, following Semantic Versioning: a change that makes a previously valid consumer input or reader invalid bumps the major number, an additive contract change bumps the minor number, and anything else bumps the patch number. Only a major release ships a guided migration, in the package's `guides/migrations/`; minor and patch upgrades need at most the current install snippet from the root README.
- **Formats Orch reads are consumer contracts.** For Software Factory these are its document-status frontmatter, implementation-plan task graph, developer-request call arguments, developer-approval record, and read-only hash command. Each stays owned where the package defines it, and breaking one follows the versioning rule above.

## Build, checks, and gates

- Root `lefthook.yml` runs each package's checks: pre-commit regenerates and checks every package's generated content; pre-push runs every package's tests and real-OMP load check, then lints all maintained Markdown. A new package adds its commands there. Hooks are local and skippable; there is no hosted continuous integration.
- Markdown is checked by rumdl, pinned in the root `mise.toml` and `mise.lock` and configured by the root `.rumdl.toml`; generated skills are excluded and checked through their sources.

## Conventions

- This document contains no links, because it is loaded as context for decisions about any part of the repository; it states facts inline instead.
- Each package's agents, skills, guides, and prose follow that package's own architecture.

## Technology index

| Choice | Status | Authority | Rule |
| --- | --- | --- | --- |
| OMP as the only harness | Decided | Developer, 2026-09-29 | Technology decisions |
| No install or build step for any package | Proposed | Agent proposal, 2026-10-05 | Technology decisions |
| One repository, one package per playbook | Decided | Developer, repository at `433c5da` | Parts and repository structure |
| Package name as permanent playbook identity | Decided | Developer, 2026-10-05 | Parts and repository structure |
| Self-contained playbook packages | Decided | Developer, 2026-10-05 | Boundaries and dependency rules |
| No dependencies between playbooks | Proposed | Agent proposal, 2026-10-04 | Boundaries and dependency rules |
| Packages never name Orch | Decided | Developer, 2026-09-30 (Orch playbook boundary) | Boundaries and dependency rules |
| Method only, no project facts | Decided | Developer, repository at `433c5da` | Boundaries and dependency rules |
| Marker-gated hooks | Proposed | Agent proposal, 2026-10-04 | Boundaries and dependency rules |
| Cross-package name uniqueness and prefixes | Proposed | Agent proposal, 2026-10-04 | Boundaries and dependency rules |
| Pinned release through mise for hand-started sessions | Decided | Developer, 2026-10-05 | Loading |
| Local-checkout override | Decided | Developer, repository at `8306025` | Loading |
| Orch loads its own pinned copy explicitly | Decided | Developer, 2026-09-30 (Orch playbook interface) | Loading |
| No imitation of Orch's launch by hand | Decided | Developer, 2026-10-05 | Loading |
| Package OMP settings in the install overlay | Decided | Developer, 2026-10-05 | Loading |
| Worktrees outside the main checkout, under `OMP_WORKTREE_DIR` when set | Decided | Developer, 2026-10-04 (Orch session) | Supervised sessions |
| Plain `git` and `gh`, relayed by the supervisor | Decided | Developer, 2026-10-04 (Orch session) | Supervised sessions |
| Extension hooks, not Git hooks | Proposed | Orch session recommendation, 2026-10-04 | Supervised sessions |
| Core extracted on second need | Decided | Developer, 2026-10-05 | Core |
| Core content and code generated into each package | Decided | Developer, 2026-10-05 | Core |
| Releases are repository tags of committed revisions | Decided | Developer, 2026-09-29 | Releases and versioning |
| Per-playbook release tags | Decided | Developer, 2026-10-05 | Releases and versioning |
| Orch-read formats are consumer contracts | Proposed | Agent proposal, 2026-10-05 | Releases and versioning |
| Root hooks and Markdown check, no hosted CI | Decided | Developer, 2026-09-30 | Build, checks, and gates |
| No links in this document | Decided | Developer, 2026-10-05 | Conventions |

## Current scope

- **One playbook, no core.** `playbooks/software-factory/` is the only package. Changes when a second playbook is started; the knowledge-base playbook is next.
- **Software Factory releases use bare `v<version>` tags.** It moves to `software-factory-v<version>` at its first release after a second playbook ships a release; consumers pick up the new tag URL from the root README's install snippet when they upgrade.
- **Software Factory does not yet meet the supervised-session rules.** It still requires every task worktree under `<repo-root>/.worktrees/`, its plan checker rejects any other location, and it has no extension guard against pushing to or merging into the default branch. Plan execution therefore fails in an Orch session that does not hold the main checkout. Changes when Software Factory ships a release with these rules, which must happen before Orch runs implementation.
- **Orch is not built, and parts of its documents predate this repository.** They still describe a playbook as a separate repository and name `project-playbook` as Software Factory's identity. Changes when Orch's playbook interface is revised to say "self-contained, separately versioned package" and `software-factory`.
- **Friction review reads one OMP sessions directory.** Orch keeps each session's transcripts in its own per-session storage. Changes when friction review must cover Orch-started sessions.
- **Orch sessions do not get a package's `omp-settings.yml`.** Software Factory's review agents need its two settings in Orch's OMP profile too. Changes when Orch's playbook interface reads the file or sets them in its profile.
