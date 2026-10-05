---
state: draft
revision: arch-r1
---

# System architecture: Agent Playbooks

## Status

This document records the repository-wide foundations of `agent-playbooks`: how playbook packages are laid out, released, and loaded. Every playbook works on its own in OMP sessions the developer starts; a supervising environment, such as Orch, is an optional enhancement that loads the same packages. Each package's internal architecture is owned by that package's own `docs/architecture.md`.

## Imposed constraints

- **OMP discovers capabilities only at a package root.** OMP finds `agents/` and `skills/` only directly under an extension package's root; a package's dependencies contribute none. Each settings layer's `extensions:` list replaces the one below it, and when two packages define an agent with the same name, OMP silently keeps the first.
- **A playbook loads only in repositories of its kind**, works per repository with or without a supervising environment, and needs few setup steps.

## System boundary

- **OMP.** Owns extension and capability discovery, settings layering, sessions, subagents, and transcripts. Every playbook integrates as one extension package.
- **mise.** Owns downloading, installing, and pinning a release for hand-started sessions, and exporting the environment that points OMP at it. Reached only through the consuming repository's committed `mise.toml`.
- **GitHub** (`aintnorest/agent-playbooks`) [EXISTS]. Owns the public release archives that mise downloads by tag.
- **Supervising environments (optional), such as Orch.** Own which playbook each session uses, launching and confining the sessions they start, their own pinned copies of playbook releases, and any relaying of network `git` and `gh` operations. They depend on playbooks one way, through documented formats; no playbook needs one.
- **Consuming repositories.** Own their project facts, documents, and approval records. They declare a playbook with a committed pin and carry one `AGENTS.md` tripwire line that tells an agent to stop when the playbook's entry skill is missing; nothing else is copied in.
- **`python3`, Git, and Bash on `PATH`.** Own execution of every playbook program; packages reach them only as child processes.

## Technology decisions

- OMP is the only harness every playbook targets.
- Every package runs from a plain copy of a committed revision with no install or build step, because release archives and supervisors' pinned copies are used as they are. Deterministic logic is standard-library Python run as command-line programs; extension code is TypeScript that OMP loads directly, using only Node built-ins and OMP's extension API at runtime; generated content is committed.
- Human-authored content is Markdown; machine-readable contracts are JSON, and JSON Schema where a shape is validated.

## Parts and repository structure

One Git repository holds every playbook, each as its own self-contained OMP extension package, so one checkout tests and releases them together while each loads alone. Paths verified by listing the repository root and `playbooks/`, and remote tags with `git ls-remote`:

- `playbooks/<name>/` — one OMP extension package per playbook. Its `package.json` `name` is the playbook's permanent identity and matches the directory name; a renamed package is a different playbook to anything that records the name.
  - `playbooks/software-factory/` [EXISTS] — the Software Factory playbook.
- `core/` [PROPOSED] — shared machinery and guidance, created only when a second playbook needs something the first already has.
- `docs/` [EXISTS] — this repository's own product vision, architecture, and working notes; nothing here is loaded at runtime.
- Root files shared by every package: `README.md` [EXISTS] (consumer install, upgrade, and local-checkout steps, plus contributor workflow), `lefthook.yml` [EXISTS], `mise.toml` [EXISTS] and `mise.lock` [EXISTS] (maintainer tool pins and tasks), `.rumdl.toml` [EXISTS], `LICENSE` [EXISTS], and `.beads/` [EXISTS] (maintainer issue tracking, never loaded by consumers).

## Boundaries and dependency rules

- **A playbook is one self-contained package.** Everything a playbook needs at runtime — agents, skills, guide references, extension code, and programs — is inside its package directory, because every loader loads exactly one package per session.
- **Playbooks do not depend on each other.** When two playbooks need the same rule or program, it moves into core; it is never copied by hand.
- **Packages never name a supervising environment.** Supervisor-specific glue lives in the supervisor; packages meet the generic rules under Supervised sessions instead.
- **Packages hold method only.** Facts about a consuming project stay in that project, and no package names a consuming repository.
- **Loading decides where a package runs; a marker decides whether its gates act.** OMP rebinds every extension into every session in the process, so each hook checks the session repository for its playbook's own marker file before acting; tools are not gated. Software Factory's marker is the consumer's `docs/user-approvals.json`.
- **Agent and skill names are unique across all packages.** New playbooks prefix theirs with the playbook name; Software Factory keeps its unprefixed names because its run history is found by agent name.

## Loading

A consuming repository declares one playbook or none. Every path loads the same package directory from a committed revision.

- **Hand-started sessions: pinned release through mise.** The repository's committed `mise.toml` pins a release of this repository as a mise tool named for the playbook. mise installs the tagged archive, writes an OMP settings overlay naming the package by absolute path, and exports that overlay to OMP while the shell is inside the repository, including subdirectories and in-repository worktrees. The developer's global `extensions:` list stays empty, so a repository with no declaration loads no playbook. The root README holds the snippet and setup steps. Tradeoff: OMP started without mise's environment loads no playbook, silently; the `AGENTS.md` tripwire makes that visible.
- **Playbook authors** point one consuming repository at a live checkout through an uncommitted `mise.local.toml` override, never by editing the committed pin.
- **Package OMP settings travel with the package.** OMP settings a playbook's agents need live in the package's `omp-settings.yml`, never in the developer's global configuration and never `extensions`. The install step appends them to the overlay, so they apply only in repositories using that playbook; overlay settings merge with the global configuration key by key, and only arrays such as `extensions:` replace it.
- **Sessions a supervising environment starts** load the package explicitly from the supervisor's own pinned copy, so the repository's mise pin and overlay do not apply; the supervisor chooses the playbook and applies `omp-settings.yml` itself. The tripwire still works wherever the root `AGENTS.md` loads.
- **Hand-started sessions never turn off OMP's extension discovery** to load a package explicitly, because that also drops OMP's bundled `/review`, `/green`, and `/annotate` commands; the mise overlay loads the same package without that cost.

## Supervised sessions

Every package works unchanged whether a session is hand-started or run by a supervising environment. Packages state these rules without naming any supervisor:

- **Worktree location.** A session may start in a worktree outside the main checkout and may be able to write only that worktree and the repository's Git metadata; the main checkout and other worktrees may be read-only. A package finds the main repository through Git's common directory, never through relative paths or by assuming its worktree sits inside the main checkout.
- **Worktrees a package creates** go under OMP's `OMP_WORKTREE_DIR` when it is set, otherwise under `<main root>/.worktrees/`, which must be Git-ignored. Worktrees are never nested, and a package removes only worktrees it created.
- **Plain `git` and `gh`.** Packages use ordinary commands; a supervisor may relay network operations, and credentials and secrets may be unreadable inside the session.
- **Enforcement lives in extension hooks, never Git hooks**, because a supervisor may not run repository hooks.
- **Developer approvals may arrive from outside the session.** A supervisor may write a package's documented developer-approval record on the developer's action; the package treats that write as the developer's.

## Core

Core is created only when a second playbook needs something the first already has; until then, code used by one playbook stays in that playbook even if it looks general. Core never depends on any playbook. Meta work — building, routing, reviewing, and improving agents and skills — is core; domain work belongs to a playbook.

The build copies everything a playbook uses from core — generated agents, skills, and guide references, and core's code — into that playbook's package, and its check fails on stale copies. A package never imports from outside its own directory, so the package directory alone is the playbook's version, and a supervisor can tell whether a playbook changed by comparing that directory between commits. Tradeoff: every package commits generated duplicates, and one core change shows up as a diff in each package that uses it; importing core by relative path would make every core change look like a new version of every playbook, and a published dependency would need an install step.

## Releases and versioning

- **A release is a Git tag of this repository.** Every loader consumes committed revisions only, never a working tree or plugin cache.
- **Each playbook is tagged separately, as `<name>-v<version>`**, so a consumer is offered only its own playbook's releases and each version number keeps its meaning; the cost is a different install-snippet URL per playbook. Software Factory's existing tags are bare `v<version>`; see Current scope.
- **Each package's `VERSION` owns its release number**, following Semantic Versioning: a change that makes a previously valid consumer input or reader invalid bumps the major number, an additive contract change bumps the minor number, and anything else bumps the patch number. Only a major release ships a guided migration, in the package's `guides/migrations/`; minor and patch upgrades need at most the current install snippet from the root README.
- **Documented formats are consumer contracts, whoever reads them.** Agents and supervising environments may read the same formats; for Software Factory these include its document-status frontmatter, implementation-plan task graph, developer-request call arguments, developer-approval record, and read-only hash command. Each stays owned where the package defines it, and breaking one follows the versioning rule above.

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
| Packages never name a supervising environment | Decided | Developer, 2026-09-30 | Boundaries and dependency rules |
| Method only, no project facts | Decided | Developer, repository at `433c5da` | Boundaries and dependency rules |
| Marker-gated hooks | Proposed | Agent proposal, 2026-10-04 | Boundaries and dependency rules |
| Cross-package name uniqueness and prefixes | Proposed | Agent proposal, 2026-10-04 | Boundaries and dependency rules |
| Pinned release through mise for hand-started sessions | Decided | Developer, 2026-10-05 | Loading |
| Local-checkout override | Decided | Developer, repository at `8306025` | Loading |
| Supervised sessions load the package explicitly | Decided | Developer, 2026-09-30 | Loading |
| Hand-started sessions keep extension discovery on | Decided | Developer, 2026-10-05 | Loading |
| Package OMP settings in the install overlay | Decided | Developer, 2026-10-05 | Loading |
| Worktrees outside the main checkout, under `OMP_WORKTREE_DIR` when set | Decided | Developer, 2026-10-04 | Supervised sessions |
| Plain `git` and `gh`, relayed by a supervisor | Decided | Developer, 2026-10-04 | Supervised sessions |
| Extension hooks, not Git hooks | Proposed | Agent proposal, 2026-10-04 | Supervised sessions |
| Core extracted on second need | Decided | Developer, 2026-10-05 | Core |
| Core content and code generated into each package | Decided | Developer, 2026-10-05 | Core |
| Releases are repository tags of committed revisions | Decided | Developer, 2026-09-29 | Releases and versioning |
| Per-playbook release tags | Decided | Developer, 2026-10-05 | Releases and versioning |
| Documented formats are consumer contracts | Proposed | Agent proposal, 2026-10-05 | Releases and versioning |
| Root hooks and Markdown check, no hosted CI | Decided | Developer, 2026-09-30 | Build, checks, and gates |
| No links in this document | Decided | Developer, 2026-10-05 | Conventions |

## Current scope

- **One playbook, no core.** `playbooks/software-factory/` is the only package. Changes when a second playbook is started; the knowledge-base playbook is next.
- **Software Factory releases use bare `v<version>` tags.** It moves to `software-factory-v<version>` at its first release after a second playbook ships a release; consumers pick up the new tag URL from the root README's install snippet when they upgrade.
- **Software Factory does not yet meet the supervised-session rules.** It still requires every task worktree under `<repo-root>/.worktrees/`, its plan checker rejects any other location, and it has no extension guard against pushing to or merging into the default branch, so plan execution fails in a supervised session that does not hold the main checkout. Hand-started sessions are unaffected. Changes when Software Factory ships a release with these rules.
- **Friction review reads one OMP sessions directory.** A supervising environment may keep each session's transcripts elsewhere. Changes when friction review must cover supervised sessions.
