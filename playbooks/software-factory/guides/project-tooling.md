# Project tooling contract

## Scope and authority

Each project owns its tool versions, environment variables, and runnable checks in a root `mise.toml`. This is the single source of truth for the toolchain and commands used by humans, agents, and continuous integration (CI). Copy and adapt the [mise template](../templates/mise.toml) in each project; the playbook does not prescribe that project's version numbers, directories, or package scripts.

## Project configuration

- Pin the minimum supported mise release with `min_version`. Set `[settings] lockfile = true` and `[tool_config] locked = true`; commit the resulting `mise.lock` alongside `mise.toml`. Update the lockfile after changing tools or Rust components, for example with `mise install rust` after a component change.
- Put pinned project tool versions and their options in `[tools]`. Put project-owned environment variables in `[env]`; use `{{config_root}}` for paths relative to the checkout that supplies the configuration.
- Put runnable project commands in `[tasks]`, including `versions`, `format`, `lint`, `typecheck`, `test`, `audit`, and `verify`. Make `verify` compose every non-interactive check, including any project-specific build or validation task. Use task dependencies for prerequisites, such as installing locked dependencies before frontend checks. Keep interactive commands outside `verify`.
- Define task commands against the actual project layout and package scripts. Humans, agents, and CI should all use `mise run <task>` rather than maintain separate command lists. Use `mise run verify` for the full check. Without an activated mise shell, use `mise exec -- <cmd>` to run an individual command with the project's pinned toolchain.

## Gotchas

### Trust configuration outside CI

An untrusted `mise.toml` fails with `mise ERROR Config files in … are not trusted`. Mise auto-trusts configs when `CI` is set, so `mise trust --show` under `CI=true` can misleadingly report "trusted" even if a normal process has never trusted the file. Language servers launched by OMP through mise shims (such as `rust-analyzer` and `typescript-language-server`) can then exit immediately; OMP may show only `LSP server exited unexpectedly (code 0)` because the shared LSP mux does not surface stderr.

From the project root, run `mise trust` without `CI` in the environment, for example `env -i HOME="$HOME" PATH=/usr/bin:/bin mise trust` (use the absolute path to `mise` if it is outside that `PATH`). Repeat after every edit to `mise.toml`: trust is tied to its content. Check trust from a CI-free environment too, not only from a CI-enabled terminal.

### Include Rust language-server components

With `rust = { profile = "minimal", components = [...] }`, explicitly include both `rust-src` and `rust-analyzer` in `components`; otherwise rust-analyzer cannot use that toolchain. Run `mise install rust` after changing the component list and commit the updated `mise.lock`.

### Resolve paths per worktree

`{{config_root}}` in `[env]` resolves to the root of the current worktree, not the main checkout. An environment variable supplied before `mise exec` is overridden by the same variable in `[env]`; to override it for one command, set it inside the execution boundary: `mise exec -- env VAR=… cmd`.
