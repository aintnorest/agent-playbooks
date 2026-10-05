# Agent playbooks

Playbooks for directing AI agents in [Oh My Pi (OMP)](https://github.com/can1357/oh-my-pi).

## What a playbook is

A playbook is everything one kind of repository needs for agents to work in it well: the documents it keeps, the processes that change it, and the agents, skills, guides, and checks that carry those processes out. Each playbook is one self-contained OMP extension package. Enabling the package gives OMP its agents and skills, and its extension registers any tools and hooks the playbook enforces.

A playbook holds method only. Facts about a particular project, such as its commands, toolchain, and exceptions, stay in that project's repository. A repository uses one playbook or none.

| Playbook | For | Package |
| --- | --- | --- |
| Software Factory | Building software products: documents before code, reviewed designs and plans, and implementation by agents with developer approval gates | [`playbooks/software-factory`](playbooks/software-factory/README.md) |

Each playbook's README explains its purpose and how to use it once it is loaded.

## Requirements

A repository that uses a playbook needs:

- **OMP**, started from a shell where mise is active (see [Limits](#limits)).
- **[mise](https://mise.jdx.dev/)**, activated in your shell, for example `eval "$(mise activate zsh)"` in `~/.zshrc`. mise downloads the pinned playbook release and tells OMP where it is.
- **`python3`, Git, and Bash on `PATH`.** Playbook tools and checks are standard-library Python programs run by the extension; nothing is installed into your repository.

A playbook may list further requirements in its own README, such as OMP settings its agents need.

Using a playbook adds two things to your repository: a tool entry in its `mise.toml`, and one line in its `AGENTS.md`. Nothing else is copied in.

## Install in a repository

The repository declares the playbook in its committed `mise.toml`, so every clone and worktree loads the same pinned release.

1. **Keep playbooks out of your global OMP configuration.** Remove any playbook path from `extensions:` in `~/.omp/agent/config.yml`. A global entry loads that playbook in every repository you open, including ones that use a different playbook or none.

2. **Pin the release in the repository's `mise.toml`.** Create the file if the repository has none, and add:

   ```toml
   [tools]
   "http:agent-playbooks-software-factory" = { version = "1.0.0", strip_components = 1, url = "https://github.com/aintnorest/agent-playbooks/archive/refs/tags/v{{ version }}.tar.gz", postinstall = "printf 'extensions:\\n  - %s\\n' \"$MISE_TOOL_INSTALL_PATH/playbooks/software-factory\" > \"$MISE_TOOL_INSTALL_PATH/omp-overlay.yml\"" }

   [env]
   PI_CONFIG_FILES = { value = "{% set d = exec(command='mise where http:agent-playbooks-software-factory 2>/dev/null || true') | trim %}{% if d %}{{ d }}/omp-overlay.yml{% endif %}", tools = true }
   ```

   For another playbook, replace both occurrences of `agent-playbooks-software-factory` and the `playbooks/software-factory` path with that playbook's name. Keep `strip_components = 1`; without it the package lands one directory too deep and its skills do not load.

3. **Install it, once per clone:**

   ```sh
   mise trust
   mise install
   ```

4. **Add a tripwire to the repository's `AGENTS.md`**, so an agent notices when the playbook is missing, for example:

   ```text
   This repository uses the Software Factory playbook. If skill://orchestrate-factory is unavailable, stop and tell the developer the playbook is not loaded.
   ```

5. **Start OMP from inside the repository** (any subdirectory works) and run `/agents`; the playbook's agents are listed. OMP reads the playbook list only at startup, so restart any OMP session that was already running.

### Upgrade

Change `version` in the repository's `mise.toml`, run `mise install`, and restart OMP. The upgrade shows in the repository's diff. A release that changes how consuming repositories must work ships a migration guide in the playbook's `guides/migrations/`.

### How it works

mise downloads the tagged release archive and writes a small OMP settings file, `omp-overlay.yml`, into the install directory, naming the playbook's package by absolute path. `[env]` points OMP's `PI_CONFIG_FILES` at that file whenever your shell is inside the repository, and OMP loads the packages it lists. Before `mise install`, the variable is empty and OMP loads no playbook instead of failing. OMP's documentation states that subagents reuse their session's extension packages, so they keep the playbook.

### Limits

- **OMP started without mise's environment loads no playbook, silently.** That happens when mise is not activated in the shell, or when OMP is launched by an editor or script that does not run your shell setup. Use `mise exec -- omp` there. The `AGENTS.md` tripwire makes a missing playbook visible.
- **Worktrees outside the repository** need their path trusted by mise before the pin applies. Worktrees inside the repository need nothing. To trust a directory tree once, add it to your global mise configuration; every repository cloned under those paths then has its `mise.toml` trusted, including its environment commands and tasks:

  ```toml
  [settings]
  trusted_config_paths = ["~/development", "~/.omp/wt"]
  ```

- **Each install downloads the whole repository**, every playbook included.

### Use a local checkout instead

To work on a playbook while using it, point one repository at a checkout of this repository without changing its committed `mise.toml`:

1. Clone this repository, for example to `~/development/projects/agent-playbooks`.
2. Create an OMP settings file outside the consuming repository, listing the package by absolute path:

   ```yaml
   extensions:
     - /Users/you/development/projects/agent-playbooks/playbooks/software-factory
   ```

3. In the consuming repository, add an uncommitted `mise.local.toml` pointing at that file. It needs `tools = true`; without it, the committed release pin wins:

   ```toml
   [env]
   PI_CONFIG_FILES = { value = "/Users/you/path/to/that-file.yml", tools = true }
   ```

4. Restart OMP. Pull the checkout to update; restart OMP again after a playbook's extension code changes.

### With Orch

Orch starts each session with the playbook you choose for the project in Orch and ignores the repository's `mise.toml` and OMP settings. A repository can use both: the mise pin for sessions you start yourself, and Orch's choice for sessions Orch starts.

## Working on this repository

Each playbook is a package under `playbooks/`; its README's "Changing the playbook" section covers authoring, generated files, and tests. Repository-wide tooling lives at the root: Git hooks in `lefthook.yml`, and the pinned Markdown linter in `mise.toml`. Set them up once per clone:

```sh
mise trust
mise install
brew install lefthook
lefthook install
```

The pre-commit hook regenerates each package's skills; the pre-push hook runs each package's tests and OMP load check, then lints all maintained Markdown. Run the push checks by hand with `lefthook run pre-push --force`.

Design notes for the repository layout and planned playbooks are in [`docs/`](docs/repository-design-notes.md).

## License

[MIT](LICENSE)
