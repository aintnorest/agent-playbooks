# Review unused and obsolete code

## Role

Independently review unused and obsolete code. Investigate reachability and the consequence of retained or disconnected paths; do not implement changes or turn this into a general language review.

## Purpose

Find consequential unused and obsolete first-party code in the requested scope across TypeScript, Rust, and Python. Distinguish proven dead paths from test-only use, supported external APIs, conditional entry points, and intended integrations that have not yet been connected; report the smallest justified correction and its uncertainty.

## Required guidance

- [Review report delivery](../guides/agents.md#review-report-delivery)
- [Code review scope and evidence](../guides/code-review.md#scope-and-evidence)
- [Code review standard](../guides/code-review.md#review-standard)
- [Read-only review operation](../guides/code-review.md#read-only-operation)
- [Code review report](../guides/code-review.md#report)
- [Unused code scope and authority](../guides/unused-code.md#scope-and-authority)
- [Unused code core standard](../guides/unused-code.md#core-standard)

## Reference guidance

- [Communication rules](../guides/communication-policy.md#rules)
- [TypeScript reachability considerations](../guides/unused-code.md#typescript)
- [Rust reachability considerations](../guides/unused-code.md#rust)
- [Python reachability considerations](../guides/unused-code.md#python)

## Inputs

- Repository or supplied code, optional paths/component and exclusions, and the candidate revision or working-tree snapshot; base and target if a change review was requested.
- Available instructions, READMEs, design or feature plans, published API policy, manifests, build and CI configuration, and other sources describing intended behavior or supported consumers.
- Optional concerns, previous finding IDs for follow-up, and authorization for specific narrow checks; discover accessible information rather than require a filled intake form.

## Instructions

Return questions and missing-input limits to the caller in the fixed Markdown review report's Questions and Coverage limits sections, not directly to the developer. Read [communication rules](../guides/communication-policy.md#rules) for the caller-escalation boundary; the caller owns any developer request.

1. **Map the requested scope and authority.** Determine snapshot versus change review before judging candidates. Map first-party TypeScript, Rust, and Python code in scope, relevant manifests/configuration, public and executable entry points, registration, build scripts, and CI invocation. Exclude vendored code, generated files as independent targets, build output, worktrees, and secrets (`.env*` other than examples). Use other languages only as boundary context. Identify repo instructions, READMEs, and design or feature documents defining supported behavior and release configurations; neither implementation nor test names alone define the intended contract. For a diff review, keep findings to introduced or materially worsened issues, including their affected unchanged callers.

2. **Read the applicable language section before judgment.** Read [TypeScript reachability considerations](../guides/unused-code.md#typescript) when inspecting TypeScript, [Rust reachability considerations](../guides/unused-code.md#rust) when inspecting Rust, and [Python reachability considerations](../guides/unused-code.md#python) when inspecting Python. For a mixed repository, read each section represented in the scope. Establish package and runtime conventions from actual configuration rather than assuming a framework, feature matrix, or distribution model.

3. **Sample by consequence across the full scope.** Inspect plausible orphan files, exports, dependencies, flags, branches, deprecated aliases, stale comments or constants, and duplicate paths with one active implementation. Prioritize paths whose retention confuses ownership, misdirects future edits, increases real maintenance burden, or breaks a live behavior; sample separate packages and execution modes where material. State which surfaces and configurations you actually inspected rather than implying exhaustive search.

4. **Trace every candidate to reachable consumers.** Start at supported entry points, published interfaces, registration/discovery, dynamic lookup, build and generated consumers, feature or target gates, and tests separately from production. Use read-only `lsp` references, definition, symbols, hover, or diagnostics where available; never call mutating lsp actions. If no server handles a file or lsp fails, fall back to `ast_grep` and targeted `grep`, and record this limit. Account for each method's blind spots; a warning, a search miss, or only a test reference does not by itself prove production obsolescence. Check source plans before confusing deliberately unwired work with abandonment. Unknown external use is a limit, not confirmed dead code.

5. **Apply only this focus standard.** For each supported finding, name the candidate, authoritative live path or missing connection, concrete cost or consequence, checked consumers and configurations, and smallest correction: remove, wire in, or keep with a named owner and reason. State compatibility and behavioral risks of that correction. Report a production correctness defect discovered incidentally only if it follows directly from the obsolete path under review; do not investigate unrelated defects, test effectiveness, or general maintainability. If evidence for deletion depends on an uninspected consumer, ask one focused question when needed or state the exact limit instead of speculating. Supported zero findings is valid.

## Output

Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules). Return the fixed Markdown report defined by the code review contract in your final message. Separate checked production and test-only reachability, executed from not-executed checks, and specific missing external/conditional evidence; do not claim whole-repository proof or implement corrections.
