# Repository design notes

Working notes, not an approved design. These notes describe how `agent-playbooks` should be organized and built. Facts about OMP and `project-playbook` were checked on 2026-10-04 and 2026-10-05 (OMP 18.6.1, mise 2026.9.1) and cite their source. Orch's documents were being edited while these notes were written, so Orch citations name sections, and any Orch line numbers are as read on 2026-10-05. Anything marked **Proposal** is a recommendation still open for decision. **[INFERENCE]** marks a claim that was not directly observed.

## What this repository is

A collection of playbooks for directing AI agents in OMP. A **playbook** is the documents, processes, agents, skills, and checks that one kind of repository needs. It is the same idea as `project-playbook`, but scoped to a domain. Planned playbooks:

| Playbook | Domain | First consumer | Origin |
| --- | --- | --- | --- |
| `software` | Building software products | Any software repo | `project-playbook` (moved here) |
| `knowledge-base` | Research knowledge bases built from sources | `knowledge-base-intelligent-systems` | `INGEST.md` in that repo |
| `career` | Career documents grounded in professional evidence | `professional-growth` | `docs/*-engine.md` and `generate.py` in that repo |
| `pkm` | A personal knowledge and life vault | `pkm` | That repo's README conventions |

Terms:

- **Core** is the shared machinery and guidance that every playbook uses.
- A **consuming repository** is a repo a playbook works in. Playbooks never name a consuming repository; that rule is carried over from `project-playbook/docs/product-vision.md`.

## Constraints from OMP

These facts decide the layout. Each cites the OMP doc that states it.

- **Agents and skills are discovered only at an extension package root.** Supported directories are `agents/`, `skills/<name>/SKILL.md` (one level deep only), `commands/`, `rules/`, `hooks/`, `tools/`, and `prompts/`. No `package.json` field adds or remaps these directories (`omp://skills/authoring-extensions.md`, `omp://task-agent-discovery.md`, `omp://plugin-manager-installer-plumbing.md`).
- **Each entry in `extensions:` is a separate root.** One git repo can therefore hold several packages if each is listed separately. A parent directory without a manifest is scanned for extension *modules*. The docs do not say whether that scan also discovers the subpackages' `agents/` and `skills/`. Do not rely on it; list each package root explicitly.
- **Project settings can enable extensions per repo, but only at the repo root.** The file is `<repo>/.omp/config.yml`. Its `extensions` array *replaces* the global array instead of adding to it (`omp://settings.md`), so a project list must name every package it wants. OMP reads `.omp/` only in the directory it was started from. It does not look in parent directories, so starting OMP from a subdirectory ignores the repo's file (`omp://settings.md`, "Native project settings are intentionally scoped to the process working directory").
- **Config overlays rank above project settings.** Overlays are YAML files named in `PI_CONFIG_FILES` or passed with `--config`. They take precedence over project and global settings, and their arrays also replace (`omp://settings.md`, settings precedence).
- **Duplicate agent names fail silently.** Agent discovery keeps the first definition with a given exact name: project, then user, then extension roots in list order, then bundled agents. Any later definition with the same name is skipped without a warning (`omp://task-agent-discovery.md`).
- **Duplicate skill names are namespaced.** A later skill is renamed `<package>/<name>`, and OMP logs a warning (`omp://skills.md`).
- **Hooks apply to every session in the process.** OMP rebinds each extension factory into every subagent session. `ctx.cwd` is read fresh on every call (`omp://extensions.md`). A hook must therefore decide for itself whether it applies to the current repository.

## Layout

**Proposal.** Core and each playbook are separate OMP packages, all in one git repo. See [Orch compatibility](#orch-compatibility): Orch loads exactly one package per playbook, which favours shipping core *inside* each playbook package rather than beside it.

```text
agent-playbooks/
  README.md              install, layout, contributor workflow
  VERSION                one release number for the repo (see Versioning)
  package.json           dev dependencies for tests only; not an OMP package
  lefthook.yml  mise.toml  mise.lock  .rumdl.toml  bunfig.toml
  docs/                  this repo's own vision, architecture, notes
  core/                  OMP package root: always enabled
    package.json         omp.extensions: ["./extension.ts"]
    extension.ts         run_check, request_developer, collect_agent_runs
    agents/  skills/     draft-skill, review-skill, review-friction (skills/ generated)
    skill-sources/  guides/  scripts/  tests/
  playbooks/
    software/            OMP package root
      package.json  extension.ts  agents/  skills/  skill-sources/
      guides/  scripts/  templates/  tests/  docs/  migrations/
    knowledge-base/      same shape; only the parts it needs
    career/
    pkm/
```

Each `extensions:` entry names one package root, for example `.../agent-playbooks/core` or `.../agent-playbooks/playbooks/software`. Each consuming repo selects its playbook package through mise; see [Enabling playbooks](#enabling-playbooks).

### Why separate packages, not one

- OMP has exactly one `agents/` and one `skills/` directory per package root. Separate packages are the only way to enable one playbook without the others.
- Each package keeps its own `extension.ts`. Software-factory hooks and tools never load where they are not wanted, and a broken playbook extension cannot keep the others from loading.

### Why one repo, not several

- **No copies of core.** In separate repos, core would be copied into each one or versioned across repos. `build-skills.py` is 1,141 lines, and copies of rules drifting apart is the exact problem `project-playbook` exists to prevent.
- **Routing can be tested across packages.** Every session runs core plus at least one playbook. Only a single repo can test that requests route to the right one, for example "review this skill" reaching core's `review-skill-agent` rather than a playbook reviewer.
- **The software playbook already depends on KB content.** Its `draft-skill` and `review-skill` skills consult the KB as evidence (`project-playbook/guides/skill-authoring.md:30,36,146,181`).

## Dependency rules

- **Core does not depend on any playbook.** Playbooks may link to core guides and call core tools.
- **Playbooks do not depend on each other.** When two playbooks need the same rule or program, it moves into core. Never copy it.
- **Promote to core when a second playbook needs something, not before.** Code that only one playbook uses stays in that playbook, even if it looks general.
- **Meta work is core.** Building, routing, reviewing, and improving agents and skills belongs to core; doing domain work belongs to a playbook.
- **Project-specific facts stay in the consuming repo.** This applies to every playbook. Examples are the KB's taxonomy, the career repo's evidence files, and a software project's toolchain.

## Agent and skill naming

**Proposal.**

- **Prefix every new playbook's agents and skills with the playbook name**: `kb-`, `career-`, `pkm-`. This prevents the silent first-wins collisions described under OMP constraints.
- **Core meta agents stay unprefixed**: `draft-skill-agent`, `review-skill-agent`, `review-friction-agent`.
- **Software agents keep their current names.** `collect_agent_runs` finds past runs by agent name, so renaming would cut each agent off from its transcript history. Renaming also changes every dispatch you type.
- **Name uniqueness is checked across all packages by the build**, not per package.

## Build

`project-playbook/scripts/build-skills.py` assumes a single root, and that assumption breaks in this layout:

| Assumption today | Where | Effect here |
| --- | --- | --- |
| Root = the script's directory plus two levels up | `repository_root()`, l.100-101 | With the script in `core/scripts/`, links from a playbook into `core/guides/` would count as escaping the root |
| One non-recursive `skill-sources/` | `SOURCES_DIR`, l.16 | Only one package can be built |
| One `skills/` output directory with a global stale scan | `inspect_outputs`, l.1020 onward | Per-package builds would delete each other's output |
| Reference file name = guide stem | l.354-358 | `core/guides/x.md` and `playbooks/kb/guides/x.md` collide within one skill |
| One `agents/`, `checks.json`, `routing-cases.json` | l.758-805 | Agent checks see only one package |
| `review-doc-*` sibling routing rule | about l.873-948 | Software naming hard-coded in core |
| Near-budget hint path `guides/skill-design.md` | l.1086 | The path moves |
| `GENERATED_MARKER` names the script path and is copied in `collect-agent-runs.py:21` | l.15 | Two copies of the marker to keep in sync |

**Proposal.** One build at `core/scripts/build-skills.py`.

- **Root.** The root is the repository root. Links may resolve anywhere inside it, so playbook sources can link to core guides.
- **Packages.** It finds packages from a fixed list: `core` plus `playbooks/*` directories that contain a `package.json`. For each package it reads `<pkg>/skill-sources`, writes `<pkg>/skills`, and scans for stale files only inside that package.
- **Reference file names.** These carry enough of the path to be unique, for example `core--communication-policy--rules.md`.
- **Cross-package checks.** Skill and agent names must be unique across packages. Routing cases are checked as one pool across packages.
- **Per-package checks.** Package-specific routing rules, such as the `review-doc-*` sibling rule, move into that package's `agents/checks.json`.
- **Generated marker.** The marker text moves to one module that both the build and `collect-agent-runs.py` import.

## Core contents

These parts of `project-playbook` are domain-agnostic and move to core (based on a read of that repo on 2026-10-04):

- **Scripts:**
  - `build-skills.py`
  - `collect-agent-runs.py`, which needs to read every package's `agents/` instead of `PLAYBOOK_ROOT/agents`
  - `run-check.py`
  - `request-developer.py`
  - `check-omp-load.py`, which needs to load several extension files instead of scraping one
  - `git_environment.py`
- **Guides:**
  - fully generic: `agents.md`, `skill-design.md`, `skill-authoring.md`, `friction.md`
  - generic parts of mixed guides:
    - `communication-policy.md`: everything except product-fit rule 2 and "Gate requests"
    - `document-review.md`: independent review context, review loop, evidence and authority, findings
  - `developer-request.schema.json`
- **Skills and agents:** `draft-skill`, `review-skill`, `review-friction`. Their routing cases currently use software examples and need examples from several domains.
- **Tests:** the build, collector, `run_check`, `request_developer`, optional-arguments, and OMP-load tests.

Generalization needed when moving:

- `request_developer` has a required grounding field named `productBasis`. Every decision, approval, input, or blocked request an agent sends you must carry either `productBasis` or `productBasisUnavailableReason` (`guides/developer-request.schema.json:16-28,55-58`).
  - `productBasis` is a list of `{source, reference, relevance}` citations into your product documents (the product vision and the governing PRD), showing which goals or requirements each option serves or harms.
  - `productBasisUnavailableReason` explains why no such document exists.
  - It is the checkable form of the communication policy's rule "Ground product fit first, maintainability second" (`guides/communication-policy.md:36`): agents may not recommend a choice on convenience when your stated intent says otherwise.
  - Other playbooks need the same rule, but their grounding is the repo's own statement of purpose. For a KB, that is its README's admission rule and scope; career and PKM repos have none written yet. The field name and the rule's wording are software-specific; the mechanism is not.
- Almost every software skill links to `guides/communication-policy.md#rules` and `integrations/omp.md#developer-requests-and-omps-built-in-ask`. Both targets move to core, and every link must follow.

## Hooks and opt-in

- **Enabling a package decides where it loads; a marker decides whether its gates run.** [Enabling playbooks](#enabling-playbooks) keeps a playbook out of repos of other kinds. Within a repo where it is enabled, an extension still checks the session repo for its own marker file before its hooks act. The software factory's existing check is `docs/user-approvals.json` (`project-playbook/omp-extension.ts:295`); it lets a software repo use the agents without the approval gates.
- **Tools are not gated by the marker.** This matches current behavior.
- **Hooks are added only where a deterministic gate pays for itself.** That is the playbook's existing rule: force infrastructure over memory. A playbook may have no hooks at all.

## Enabling playbooks

**Requirement (developer, 2026-10-04):** a playbook loads only in repos of its kind. Today `project-playbook` is the single global `extensions:` entry in `~/.omp/agent/config.yml`, so its software agents and hooks load in every repo, including this KB.

**Shared shape for every option:** each repo of a given kind gets a complete list from somewhere that outranks the global config. A complete list is needed because each layer's array replaces the one below it. Core ships inside each playbook package (see [Orch compatibility](#orch-compatibility)), so the global list is empty and each repo's list is its one playbook.

**Self-gating inside the extension cannot meet the requirement alone.** The software hooks already do nothing without `docs/user-approvals.json`. However, OMP discovers `agents/` and `skills/` from the package root no matter what the extension code does, so the agents would still appear everywhere.

| Option | How | Strengths | Weaknesses |
| --- | --- | --- | --- |
| A. Project config | Each repo has `<repo>/.omp/config.yml` with `extensions: [<core>, <playbook>]` | OMP-native; no dependency on the shell | Only works when OMP starts at the repo root (verified below). Every repo holds its own copy of the list, so adding or splitting a package means editing every repo. The machine-specific paths need to be committed or ignored per repo. |
| B. Overlay via mise | The playbook owns one overlay file, e.g. `playbooks/software/omp.yml`, holding the complete list. Each repo's `mise.toml` sets `PI_CONFIG_FILES` to that file's path in `[env]` | Works from any subdirectory (verified below). The list has one home, owned by the playbook. Your `~/.zshrc` already runs `mise activate zsh`. Six repos under `~/development/projects` already have a `mise.toml` (`Orch`, `beads-workbench`, `greenskinlabs-verbatim`, `project-playbook`, `pursuit`, `thought-partners`), and the software playbook already ships `templates/mise.toml` | Works only when OMP is started from a shell with mise active. A missing or invalid overlay file is a hard startup error, not a fallback (`omp://settings.md`). It outranks the repo's own `.omp/config.yml` `extensions`. Repos without a `mise.toml`, such as `gsl`, need one. |
| C. OMP profiles | `omp --profile software` with its own config | One switch per launch | A profile also isolates auth, sessions, and caches (`omp://settings.md`). That splits session history, which `collect_agent_runs` reads from one sessions directory by default. You have to remember the flag. |
| D. Wrapper or alias | e.g. `omp --config <overlay>` per repo kind | No repo changes | Depends on remembering which command to use where, which goes against "force infrastructure over memory" |
| E. Repo declares, launcher resolves | Each repo commits a one-line file naming its playbook (e.g. `.agent-playbook` containing `software`). An `omp` launcher on `PATH` finds the nearest such file and runs the real `omp --no-extensions --extension <package>` | No mise or other tool needed. Works from subdirectories. The repo holds a portable name, not machine paths. Loads exactly what Orch would. | **Rejected 2026-10-05.** Personal tooling other users must adopt. `--no-extensions` drops OMP's bundled `/review`, `/green`, and `/annotate`. Details in [Option E in detail](#option-e-in-detail). |
| F. Pinned release via mise (**chosen 2026-10-05**) | Each repo's committed `mise.toml` pins a release of this repo as a mise tool. mise downloads the tagged archive, a postinstall step writes an overlay naming the playbook's package, and `[env]` points `PI_CONFIG_FILES` at it | A committed, versioned declaration that travels with every clone and worktree. Works from subdirectories and outside worktrees. Needs no local checkout of this repo, no launcher, and no `PATH` change. Each version installs to its own directory. Keeps OMP's bundled commands. Orch ignores it. | Needs mise activated, or `mise exec -- omp`. Each clone runs `mise trust && mise install`. OMP started without mise's environment loads no playbook. Details in [Chosen: pinned release via mise](#chosen-pinned-release-via-mise). |
| G. Marketplace, project scope | This repo ships `.omp-plugin/marketplace.json`; each clone runs `omp plugin install --scope project <name>@agent-playbooks` | OMP-native; no mise | Nothing committed: the install record holds an absolute path and timestamps, so every clone and outside worktree installs separately. Details in [Installing with the plugin manager](#installing-with-the-plugin-manager). |

**Verified 2026-10-04 in a throwaway temp directory,** using `omp config get extensions`. Your real config was not changed.

- Started at a repo root with `.omp/config.yml`, OMP used the project list.
- Started in a subdirectory of that repo, OMP fell back to the global list.
- With `PI_CONFIG_FILES` set, OMP used the overlay list from both the root and the subdirectory, and the overlay outranked the project file.

This confirms only the effective setting. It does not confirm agent discovery from those paths, which needs a real load check.

### Chosen: pinned release via mise

**Decided 2026-10-05 (developer).** Playbooks must work per repo with and without Orch, take few setup steps, and not require the developer's other tools. mise is an acceptable requirement for the easy path.

**How it works.**

- A release is a git tag of this repo. GitHub serves each tag as a tarball (`archive/refs/tags/v<version>.tar.gz`).
- A consuming repo's committed `mise.toml` declares one mise tool per playbook it uses. The tool name names the playbook, so each playbook gets its own install directory even when two repos pin the same release.
- mise's `http` backend downloads the tarball. A `postinstall` command writes `omp-overlay.yml` into the install directory, listing the playbook's package by absolute path. The path must be absolute: OMP resolves `extensions:` entries against its working directory, not the overlay's location (verified: an overlay entry of `.` loaded nothing).
- `[env]` sets `PI_CONFIG_FILES` to that overlay. The guard gives an empty value until the tool is installed, and OMP treats an empty value as unset.
- The global `extensions:` list is empty, so a repo with no declaration loads no playbook.

```toml
# <consuming repo>/mise.toml
[tools]
"http:agent-playbooks-software" = { version = "1.0.0", strip_components = 1, url = "https://github.com/aintnorest/agent-playbooks/archive/refs/tags/v{{ version }}.tar.gz", postinstall = "printf 'extensions:\\n  - %s\\n' \"$MISE_TOOL_INSTALL_PATH/playbooks/software\" > \"$MISE_TOOL_INSTALL_PATH/omp-overlay.yml\"" }

[env]
PI_CONFIG_FILES = { value = "{% set d = exec(command='mise where http:agent-playbooks-software 2>/dev/null || true') | trim %}{% if d %}{{ d }}/omp-overlay.yml{% endif %}", tools = true }
```

Each piece of this snippet was tested on 2026-10-05. The assembled snippet for this repo's layout has not been run, because this repo has no release yet.

**Verified 2026-10-05** in temp directories with separate mise state, a temp `HOME`, the real OMP binary, and a dummy model; no model turns. The package was a tarball of the current `project-playbook` checkout served over local HTTP. mise refuses `file://` URLs, and `project-playbook`'s only published tag, `v0.1.0`, predates its OMP package.

| Where OMP started | Playbook skills and `/playbook-hash` | Bundled `/review` |
| --- | --- | --- |
| Repo root | loaded | kept |
| Subfolder two levels down | loaded | kept |
| Plain `git worktree` outside the repo, path trusted by mise | loaded | kept |
| Folder outside the repo | not loaded | kept |
| Repo root with `--no-extensions`, as Orch launches | not loaded | dropped by the flag |

Also verified:

- `project-playbook`'s GitHub tarball for `v0.1.0` downloads without credentials and installs; `mise where` returns the install directory.
- With a test tarball holding one top-level directory and no `strip_components`, the package root sat one level down: the extension loaded but its skills did not. `strip_components = 1` fixed it. Keep it explicit.
- Before `mise install`, an unguarded `exec()` template makes mise print `not installed` errors on every directory change. The guarded template above returns an empty value with exit 0, and the installed path afterwards.

**User steps.**

- Once per machine: install mise and activate it in the shell (`mise activate zsh`).
- Once per clone: `mise trust && mise install`. The software playbook already asks software repos for these steps (`project-playbook/templates/mise.toml`, `project-playbook/README.md:42-46`).
- Without mise: download a release and point `PI_CONFIG_FILES` or `extensions:` at `playbooks/<name>` by hand.
- Upgrading: change `version` in `mise.toml`, run `mise install`, and restart OMP. The change shows in the repo's diff.

**Costs.**

- OMP must start with mise's environment: an activated shell, `mise exec -- omp`, or an editor with mise support. Otherwise it silently loads no playbook. The `AGENTS.md` tripwire under [Worktrees and subagents](#worktrees-and-subagents) makes that visible.
- The snippet is clever-looking. Ship it in each playbook's `templates/mise.toml` so users paste it rather than write it.
- `exec()` runs `mise where` whenever mise re-evaluates the environment. **[INFERENCE]** The cost is small; not measured.
- Each install downloads the whole repo, every playbook included.

#### Worktrees and subagents

- **Subagents keep the playbook.** A subagent is a child session in the parent OMP process, with a copy of the parent's settings, sharing the workspace, skills, and context files (`omp://tools/task.md:114,151,195`). Agent lookup reuses the session's extension roots, overlays included (`omp://task-agent-discovery.md:208-211`). A subagent working in a worktree therefore keeps the playbook loaded when the session started. **[INFERENCE]** From the docs; not run, because it needs a model turn.
- **The software playbook's worktrees are inside the repo.** It gives implementation to subagents in worktrees (`project-playbook/skill-sources/orchestrate-implementation-plan.md:5`) under `<repo>/.worktrees` (`project-playbook/scripts/check-implementation-plans.py:304-313`). A fresh process there also finds the repo's `mise.toml`, because mise reads parent directories.
- **The remaining gap** is a new OMP process started in a worktree outside the repo, such as under `~/.omp/wt`. Because `mise.toml` is committed, it loads once mise trusts the path (verified above). Trust the trees once in the global mise config:

  ```toml
  [settings]
  trusted_config_paths = ["~/development", "~/.omp/wt"]
  ```

  Cost: any repo cloned under those paths has its `mise.toml` trusted automatically, including its env commands and tasks.
- **Tripwire.** Each consuming repo's `AGENTS.md` says, for example: "This repository uses the software playbook. If `skill://orchestrate-factory` is unavailable, stop and tell the developer the playbook is not loaded." `AGENTS.md` loads in every checkout and worktree, with or without mise, and in Orch. It is an instruction, not enforcement.

#### Editing a playbook while using it

- In a repo where you want your live checkout instead of the pinned release, put a `PI_CONFIG_FILES` override in an uncommitted `mise.local.toml`, pointing at an overlay that lists `<checkout>/playbooks/<name>` by absolute path. **Verified 2026-10-05** in a temp consumer repo against a local tarball of commit `433c5da`: the override must also set `tools = true` (`PI_CONFIG_FILES = { value = "<overlay>", tools = true }`). A plain string value loses to the committed `tools = true` value. With `tools = true` it wins, and OMP loaded the checkout's package. The steps live in the root README.
- Restart OMP after changing an `extension.ts`; `/reload-plugins` does not reload extension factories (`project-playbook/integrations/omp.md:122`).

**Can start before the migration.** The same snippet can pin today's `project-playbook` once it has a release that includes `package.json`: tool `http:project-playbook`, URL `.../project-playbook/archive/refs/tags/v{{ version }}.tar.gz`, overlay entry `$MISE_TOOL_INSTALL_PATH`. Then empty the global `extensions:` list.

### Option B in detail

**Status (2026-10-05):** superseded for selection by [option F](#chosen-pinned-release-via-mise), which reuses the mechanics verified here. B's form, an overlay pointing into a local checkout of this repo, remains the author's override; see [Editing a playbook while using it](#editing-a-playbook-while-using-it).

**How it works.** A shell started with `mise activate zsh` (already in `~/.zshrc`) re-applies `[env]` from every `mise.toml` between `/` and the current directory each time you change directories, and drops those variables when you leave. OMP reads `PI_CONFIG_FILES` once, at startup. So whichever repo you are in when you run `omp` decides which playbooks load for the whole session, subagents included.

The pieces:

```yaml
# agent-playbooks/playbooks/software/omp.yml: the playbook owns its list
extensions:
  - ~/development/projects/agent-playbooks/core
  - ~/development/projects/agent-playbooks/playbooks/software
```

```toml
# <software repo>/mise.toml: the repo only points at the list
[env]
PI_CONFIG_FILES = "{% set p = env.HOME ~ '/development/projects/agent-playbooks/playbooks/software/omp.yml' %}{% if p is file %}{{ p }}{% endif %}"
```

```yaml
# ~/.omp/agent/config.yml: what every other repo gets
extensions:
  - ~/development/projects/agent-playbooks/core
```

**Verified 2026-10-04 in temp directories,** using `mise exec` and `omp config get extensions`. Your real config and mise trust list were not changed.

- The variable reaches a directory two levels below the repo's `mise.toml` and is unset outside the repo.
- `{{env.HOME}}` expands. A `~` inside `PI_CONFIG_FILES` is expanded by OMP.
- A missing overlay file is a hard failure: `error: Config overlay not found: <path>`, exit 1. The `is file` guard above turns that case into an empty variable.
- OMP treats an empty `PI_CONFIG_FILES` as unset and falls back to the global list. With the guard, a clone on another machine, a collaborator's checkout, or a moved `agent-playbooks` degrades to core only instead of breaking OMP startup.
- With two overlays in `PI_CONFIG_FILES` (`a.yml:b.yml`), the last file's `extensions` wins outright. Overlays do not combine. A repo that needs two playbooks needs one overlay listing both.

**From the docs, not tested:**

- Relative paths inside `extensions` resolve against OMP's working directory, not the overlay file's location (`omp://extension-loading.md`, path resolution). The overlay must therefore use `~` or absolute paths.
- Changing the list takes effect only when OMP restarts.
- Moving a running session to another repo keeps the playbooks it started with.

**Where it does not apply.** OMP started outside a mise-activated shell, for example from a script, launchd, or an editor integration that does not run your zsh, gets no overlay. It loads core only; that is a quiet downgrade, not an error. `mise exec -- omp` restores the overlay in those cases.

**Per-repo cost.**

- One `[env]` line in `mise.toml`. Repos without a `mise.toml` (for example `gsl` and `knowledge-base-intelligent-systems`) need a file containing only that section.
- Committing the line is safe because of the guard; otherwise it belongs in an uncommitted `mise.local.toml`.
- Mise's `paranoid` setting is `false` on this machine, so trust is by path. A repo that already runs mise needs no new `mise trust` for an edited file.

**Extra benefit: software-only settings move into the overlay.** The `review-code-*` agents need `task.enableLsp` and `astGrep.enabled`, which are currently set globally (`project-playbook/integrations/omp.md`). They could live in `playbooks/software/omp.yml` and apply only in software repos.

**Independent of the migration.** B works with today's single `project-playbook` package: the overlay lists `project-playbook`, and the global list becomes empty. So the "loads everywhere" problem can be fixed before `agent-playbooks` exists in code.

### Option E in detail

**Status (2026-10-05):** rejected; see the end of this section.

**Developer constraints, 2026-10-04:** don't force mise on every repo (it is used on new projects, not all). Orch is not built yet, so changing Orch is acceptable as long as Orch still works.

**The gap.** OMP has no native "nearest project config" lookup: `.omp/config.yml` is read only from the start directory. Some launcher has to supply the choice. This option keeps the launcher generic and puts only a name in the repo.

**Pieces:**

- **Declaration.** A committed file at the repo root holding the playbook's package name, for example `.agent-playbook` containing `software`. It contains no paths, so it is safe in public repos and on other machines, where nothing reads it. It sits outside `.omp/`, so it neither triggers OMP's project settings load nor falls under Orch's `.omp/` restrictions.
- **Launcher.** A small executable `omp` script shipped in this repo (e.g. `bin/omp`) and placed ahead of the real `omp` on `PATH`. It:
  - walks up from the current directory to the nearest `.agent-playbook`, or the git root
  - maps the name to `agent-playbooks/playbooks/<name>`
  - runs `exec <real omp> --no-extensions --extension <that package> "$@"`
  - with no declaration, runs `exec <real omp> --no-extensions "$@"`, which loads no playbook
  - with a declared name that has no package on this machine, fails with a message naming the file and the missing package
  - Being an executable rather than a shell function, it also works from scripts and from editors that inherit `PATH`.
- **Global config.** `extensions:` becomes empty, so OMP launched without the launcher also loads no playbook.
- **Orch.** It can use the same file to default a project's playbook choice, then pass `--extension` itself as it already plans to. One declaration then drives both hand-started and Orch-started sessions.

**Verified 2026-10-04.** `omp --no-extensions [--extension <path>]` combined with `config get`, `plugin list`, and `--version` ran without errors. So a launcher that always adds the flags does not break those subcommands.

**Verified 2026-10-05.** `--no-extensions --extension <package>` exposes the package's skills and its `/playbook-hash` command. RPC `get_available_commands` in a temp directory returned 48 commands with `--no-extensions` alone and 76 with the package. `update --help`, `completions zsh`, `wt list`, `agents --help`, `acp --help`, and `stats --help` also ran with the flags, exit 0.

**Compared with B.**

- E needs no per-repo tool, and the repo states intent ("this is a software repo") rather than a machine path.
- E also ignores a repo's `.omp/extensions` and installed plugins, as Orch does.
- B needs no `PATH` change, but every repo needs a `mise.toml`.
- Both miss launches that bypass the shell environment: B misses non-mise shells, and E misses absolute-path launches.

**Rejected 2026-10-05,** in favour of [option F](#chosen-pinned-release-via-mise):

- **Personal tooling.** Other users would have to install a launcher ahead of the real `omp` on `PATH`.
- **`--no-extensions` drops OMP's bundled commands.** RPC `get_available_commands` in a temp directory returned 79 commands with the default global config and 76 with `--no-extensions --extension <package>`. The missing three are `/review`, `/green`, and `/annotate`. OMP's docs do not mention this. Orch sessions lose them too, since Orch launches the same way.
- **It conflicts with `--trusted-extension`,** which "cannot be combined with `--extension`, `-e`" (`omp://skills/authoring-extensions.md`).
- **`HOME` overrides.** `project-playbook/scripts/check-omp-load.py` runs `omp` from `PATH` with `HOME` set to a temp directory, so a launcher must not use `$HOME` to find the real binary or the packages.
- **The repo picks code to run.** The name in `.agent-playbook` would need strict validation (`^[a-z0-9-]+$`) so a cloned repo cannot point the launcher at its own code through `../`.
- **Orch cannot read the file.** See [Orch compatibility](#orch-compatibility).

### Installing with the plugin manager

OMP has three ways to load an extension package: a path in the `extensions:` setting, which is what `project-playbook` uses (`integrations/omp.md`); a per-launch `--extension` path, which Orch uses; and the plugin manager. Source: `omp://plugin-manager-installer-plumbing.md`.

- **How it installs.** `omp plugin install <npm spec | github:user/repo#ref | local path>` runs `bun install` into `~/.omp/plugins/` and records enabled state and features in `omp-plugins.lock.json`. Dependencies are installed too. A local path becomes a symlink (`omp plugin link`). `omp plugin upgrade` moves npm packages to the latest version and re-resolves git refs.
- **Scope.** npm, git, and link installs are user-scoped, so an installed plugin loads in every repo. The only per-project control is `<repo>/.omp/plugin-overrides.json`, which can disable a plugin or change its features in that repo. Meeting "loads only in software repos" this way means a disable file in every *non*-software repo.
- **Features do not gate agents or skills.** A package can declare features, selected at install as `pkg[a,b]`. However, features select only manifest entries such as extension modules and tools. `agents/` and `skills/` are always scanned at the plugin root, so a single root package with one feature per playbook cannot hide another playbook's agents.
- **Dependencies do not contribute agents or skills.** Discovery scans only each plugin's own root, the same limit as path-loaded packages. A playbook could depend on a published core package for code, but core's agents and skills would still have to be copied into the playbook.
- **Monorepo subpackages and git installs.** A git spec installs the repository's root package. Installing `playbooks/software/` alone from git would need npm publishing per package. **[INFERENCE]** This assumes bun's git dependencies cannot select a subdirectory; not checked.
- **Orch ignores installed plugins.** Under `--no-extensions`, installed packages are excluded (`omp://extension-loading.md`).
- **Marketplace installs have a project scope.** A marketplace is a repo with `.omp-plugin/marketplace.json`, or Claude Code's `.claude-plugin/marketplace.json`, listing plugins. A plugin's `source` can be a subdirectory (`"./playbooks/software"`), a GitHub repo, or a `git-subdir` with `path` and `sha` (`omp://marketplace.md`). `omp plugin install --scope project <name>@<marketplace>` records the install in `<repo>/.omp/plugins/`.
- **Verified 2026-10-05** with a temp `HOME` and a local-directory marketplace: the playbook loaded from the repo root and a subfolder, not elsewhere, and `/review` stayed. Under `--no-extensions` its skills still loaded but its extension did not.
- **Why not chosen.** From a reviewer run on 2026-10-05, in temp directories:
  - Nothing is committed. `installed_plugins.json` holds an absolute `installPath` into `~/.omp/plugins/cache/` plus timestamps, so it is gitignored and each clone installs separately. A plain git worktree outside the repo loaded no playbook. `omp wt` worktrees (an APFS clone that copies `.omp/plugins`) and in-repo `.worktrees/` (ancestor lookup) did.
  - All installs of one version share one cache directory. `install --force` in one project changed another project's copy.
  - Upgrades are found only through the catalog's `version`. Bumping `package.json` alone reported "All marketplace plugins are up to date".
  - Local-directory marketplaces copy uncommitted and gitignored files.
  - OMP asks no trust question before loading project plugins (`omp://extensions.md:289`).
  - Marketplace registration is per OMP profile.

So the plugin manager can load per repo through marketplace project installs, but each clone must install separately, and nothing in the repo records the choice. Option F records it in a committed file.

## Orch compatibility

Orch (`~/development/projects/Orch`) is your app for supervising OMP sessions. Its architecture is read-only input here; these notes do not change it. It consumes playbooks through a documented interface, and that interface constrains this repo's layout. Its vision names knowledge-base and professional-growth playbooks as expected consumers (`Orch/docs/product-vision.md:14`, `Orch/docs/architecture.md:106`).

**How Orch loads a playbook** (`Orch/docs/architecture.md:106-120`):

- **Launch.** Every session starts with `omp --no-extensions` and then exactly two `--extension` packages: Orch's bridge, and that session's playbook (or none).
  - `--no-extensions` ignores every `extensions:` setting (global, project, or overlay) and every installed package. Explicitly named packages still bring their `agents/` and `skills/` (`omp://extension-loading.md`, `omp://cli-reference.md`).
  - Orch's sessions are therefore unaffected by options A, B, and F. Those options matter only for OMP started by hand. For F this was verified on 2026-10-05: with the overlay set, `--no-extensions` loaded no playbook.
- **Repo settings.** A repo's own `.omp/` settings, extensions, and hooks are denied in Orch sessions; only instruction files load.
- **Identity and version.**
  - "A playbook supplies its identity and version, an OMP extension package containing its agents, skills, and guides." Identity is the package's `name` (`project-playbook` today). A renamed package looks like a different playbook.
  - Each project picks one playbook or none.
  - Orch pins each playbook separately as its own git submodule under `vendor/playbooks/`. A version is an immutable copy of one commit, and "each playbook takes up versions independently."
- **Separate profile and sign-in.** Orch runs OMP under its own profile, with a per-session `--session-dir`.

**What this means for agent-playbooks:**

- **One playbook must be one self-contained package.** Orch passes one playbook package, so a separate `core` package would never load in Orch sessions.
  - **Proposal:** core stays one source tree here. The build copies core's generated skills, agents, and guide references into each playbook package, the same way skills are already generated from guides.
  - Each playbook's `extension.ts` imports core's tool registrations.
  - The result: one package per playbook works for Orch, for option F (the overlay lists one package), and for a hand-typed `--extension`.
  - **Cost:** generated copies in each package. A session that loads two playbooks at once would register core's tools twice. OMP's docs do not state the rule for duplicate tool names across extensions, but Orch's one-playbook-per-project rule avoids the case.
- **Package names are permanent identities.** Choose them once, for example `software`, `knowledge-base`, `career`, `pkm`, or with a prefix. Keeping `project-playbook` as the software package's name preserves Orch's recorded identity. Orch's playbook interface is still marked `[PROPOSED]`, so a rename now costs only Orch doc edits.
- **Orch pins commits; this repo has one history.** Orch can pin different commits of this repo per playbook, because two submodules may point at the same repository. However, any commit here, even one touching only `knowledge-base`, is a new commit for every pin. To keep "each playbook takes up versions independently," Orch would compare the playbook's own content between commits rather than the commit itself. That is an Orch-side change.
  - Each playbook's `extension.ts` imports core by relative path (see [How core reaches each playbook package](#how-core-reaches-each-playbook-package)), so that content is the playbook's directory plus `core/`. An identity that hashed only `playbooks/<name>` would miss core changes. The alternative is for the build to copy core's code into each package as well, so the package directory alone is the identity.
  - Orch must copy only committed content, never a working tree or an OMP plugin cache.
- **Orch's docs say "a playbook is a separate repository"** (`Orch/docs/architecture.md` rule 8, `Orch/docs/features/session-supervision/prd.md` glossary). That wording assumes one repo per playbook; it would need to say "a separate OMP extension package." The one-way dependency rule (no playbook references Orch) is unaffected.
- **Orch transcripts live elsewhere.** Orch sessions keep transcripts under Orch's profile and per-session directories, not `~/.omp/agent/sessions`. `collect_agent_runs` already takes a sessions directory, but reviewing friction across Orch sessions needs it to accept many per-session directories.
- **Formats Orch reads are consumer contracts.** Orch reads the software playbook's document-status frontmatter, plan task graph, developer-approval request and record, and hash command (`Orch/docs/architecture.md:106-108`). Moving the software playbook must keep them byte-compatible, or ship a migration Orch can follow.
- **Orch must not read the consuming repo to pick a playbook.** Orch may read only four named `.git` entries directly; everything else goes through git in its sandbox (`Orch/docs/features/session-supervision/slices/01-projects-and-sign-in/tdd.md:619,2115`). So Orch does not default a project's playbook from `mise.toml`, `.agent-playbook`, or `.omp/plugins/`; the developer picks it in Orch (SUP-001).
- **Orch should launch sessions with a cleared environment.** Under `--no-extensions`, a `PI_CONFIG_FILES` inherited from the developer's shell loads no extensions (verified above), but an overlay can carry other settings. Slice 01 already clears the environment for account calls (`env_clear()`, same `tdd.md:814`). **[INFERENCE]** Slice 02's session launch was not checked.
- **Project plugins survive `--no-extensions`.** A project-scope plugin's skills still loaded under that flag (verified 2026-10-05). In Orch, the sandbox's denial of every code-running file under a reachable `.omp/` (architecture, OMP integration) is what keeps them out. A reviewer run on 2026-10-05 denied `.omp/plugins` and the plugin cache with `sandbox-exec`: nothing leaked, and an explicit `--extension` still loaded. The architecture should name `.omp/plugins/` and add a regression case.
- **Orch document edits for the monorepo.** From a reviewer run on 2026-10-05; none changes how sessions behave:
  - Vision, architecture (status, system boundaries, layout, rule 8), and the session-supervision PRD's playbook definition: "separate repository" becomes "self-contained, separately versioned package".
  - Playbook interface: identity stays the `package.json` `name`, with matching folder name. A version is the source commit plus the content identity above. Choose one vendoring layout: one submodule of this repo, or one per playbook pointing at the same repo.
  - Session sandbox and OMP integration: name `.omp/plugins/` in the denial.
  - Session-supervision system design and slice 01's playbook catalog: stored playbook versions use that identity, and catalog entries point at `vendor/.../playbooks/<name>`, not the repo root.
  - Approved Orch documents that change need the developer's re-approval in `Orch/docs/user-approvals.json`.

**Matching Orch's launch outside Orch.** Not pursued. Adding `--no-extensions --extension <package>` to hand-started sessions drops OMP's bundled `/review`, `/green`, and `/annotate` (see [Option E in detail](#option-e-in-detail)). Option F loads the same package without that flag.

### How core reaches each playbook package

The repo is a monorepo of packages: `core/` plus one package per playbook. OMP treats an extension package as a directory with a `package.json` whose own `agents/` and `skills/` sit at its root. OMP does not pull `agents/` or `skills/` from a package's dependencies; no such mechanism is documented. So making core a dependency shares its code but not its agents and skills. Each kind of content needs its own route:

| Content | Route | Why |
| --- | --- | --- |
| Tool and hook code | Each playbook's `extension.ts` imports core by relative path (`../../core/...`) | Works in a checkout and in Orch's copy of a whole commit, with no install step. A package-manager workspace dependency (`"@agent-playbooks/core": "workspace:*"`) would need `bun install` wherever the package runs, including Orch's pinned copies, against the no-build-step rule (`project-playbook/docs/architecture.md`, technology decisions). |
| Agents and skills | The build writes core's generated agents and skills into each playbook package's `agents/` and `skills/` | Skills are already generated output, so this adds no new mechanism. Works with any copy or pin method. |
| Alternative for agents and skills | Symlinks from each package to `core/` | Untested: whether OMP discovery follows symlinked skill or agent directories is not documented. The current build also refuses symlinks under `skills/`. |

**Per-package versions.** A monorepo can give each package its own version, either in its `package.json` or its own `VERSION` file, tagged as `<package>@<version>`, as JavaScript monorepos commonly do. That matches Orch's "each playbook takes up versions independently" for people reading the tags. Orch itself pins commits, so it would still compare the playbook's directory between commits to tell whether that playbook changed. This replaces the single-`VERSION` proposal under [Versioning](#versioning) if adopted.

## Product documents

- **Repo-level `docs/product-vision.md`.** It holds the parts of the current vision that apply to any repo an agent works in:
  - the target user and the generic problems
  - all product principles, with "product" generalized to the repo's purpose
  - the OMP-only boundary
  - "does not require its own documents" and "holds no project-specific facts"
  - the source-is-evidence and developer-work-safety constraints
- **Per-playbook vision** at `playbooks/<name>/docs/product-vision.md`. It holds the domain-specific vision. For software this is the software-factory framing, the code-review problems, and design and plan acceptance.
- **The `project-playbook` roadmap item "Repositories that aren't products"** (`docs/roadmap.md`, Later) is resolved by this repository's existence. It closes when the software playbook stops proposing product documents in non-software repos.

## Versioning

`project-playbook` keeps one `VERSION` with tags `v<version>`. Migrations live at `guides/migrations/<from>-to-<to>.md` (`docs/architecture.md:86-87`). Nothing reads `VERSION` programmatically.

**Proposal.**

- Keep one `VERSION` for the whole repo. A contract change in any package bumps it, following SemVer as it does today.
- Migrations live in the package that changed: `playbooks/<name>/migrations/<from>-to-<to>.md`, or `core/migrations/`.
- Per-playbook versions are possible later. They are not worth the overhead while one developer owns every package and installs from one checkout.
- **Consuming repos pin a release in `mise.toml`** (see [Chosen: pinned release via mise](#chosen-pinned-release-via-mise)). With one `VERSION`, a release that changes only one playbook still offers every consumer a new version; release notes or per-package migrations say whether it matters to them. Per-playbook tags such as `software-v1.2.0` would avoid that, at the cost of per-package versions.

## Tooling and gates

- **One lefthook, one mise and rumdl pin, one Bun lockfile at the root.** These carry over from `project-playbook`.
- **Pre-commit** runs the build for every package, stages each `skills/` and `agents/` directory, and then runs the check.
- **Pre-push** runs:
  - Python tests found per package
  - `bun test`
  - the OMP load check over every package extension
  - check-only Markdown lint over every maintained Markdown path, excluding generated `skills/`
- **Python stays standard-library only and TypeScript stays build-free.** Both rules carry over from `project-playbook/docs/architecture.md`.

## Moving `project-playbook` in

**Decided (2026-10-04): fresh copy, no imported git history.** `project-playbook` stays available for history lookups.

**Proposal.** Order of work:

1. Create the root tooling and an empty core package. Move the build and generalize it as described in [Build](#build). Copy core guides, scripts, skills, and tests.
2. Copy the software playbook into `playbooks/software/`. Fix links and `mise` lint paths. Keep generated output byte-identical except for reference file names and provenance paths.
3. Tag the first release. Add the [mise snippet](#chosen-pinned-release-via-mise) and the `AGENTS.md` tripwire to each consuming repo, and empty the global `extensions:` list. Restart OMP; changing `extensions:` needs a restart, and `/reload-plugins` is not enough. Run the OMP load check.
4. Archive `project-playbook` on GitHub with a README pointer here.
5. Start `playbooks/knowledge-base` (see `knowledge-base-playbook-notes.md`).

## Decision status

Decided:

- **Git history:** fresh copy; see [Moving `project-playbook` in](#moving-project-playbook-in).
- **PKM:** a separate playbook from the knowledge base one, if built.
- **Repository name:** `agent-playbooks`, public, owned by `aintnorest`.
- **Enabling playbooks per repo:** pinned release via mise ([option F](#chosen-pinned-release-via-mise)), 2026-10-05.
- **Software playbook identity:** the package is named `software-factory` (its `package.json` `name`, which Orch persists as the playbook's identity), in `playbooks/software-factory/`, 2026-10-05. This replaces `project-playbook` and the `playbooks/software/` path used elsewhere in these notes.
- **Move order:** `software-factory` was copied in as one self-contained package from `project-playbook` commit `e89d8f8`, before any core extraction, 2026-10-05. Core is extracted when a second playbook needs it. This replaces steps 1 and 2 of [Moving `project-playbook` in](#moving-project-playbook-in); repository tooling (`lefthook.yml`, `mise.toml`, `mise.lock`, `.rumdl.toml`, `LICENSE`) lives at the repository root.
- **Grounding field:** `productBasis` and `productBasisUnavailableReason` are renamed `intentBasis` and `intentBasisUnavailableReason`, 2026-10-05. Because `software-factory` is a new package, its first release stays `1.0.0` and the developer-request record stays version `1`; no migration guide covers the move from `project-playbook`.

Open:

1. **`project-playbook`'s Beads issues.** You will review them before deciding what moves. Its `.beads/` holds open evidence issues about software agent runs (slice-02 to slice-04) and roadmap follow-ups.
