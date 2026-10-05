# Unused and obsolete code contract

## Scope and authority

This guide owns the standard for identifying unused and obsolete first-party code in TypeScript, Rust, and Python projects. It covers declarations, exports, modules and files, dependencies, configuration and feature flags, branches, superseded implementations, and contradictory comments or constants. The [code review contract](code-review.md) owns review scope, evidence, read-only permissions, reporting, and severity; do not treat every possible cleanup as a finding.

Repository instructions, published API promises, build and release configuration, and feature plans establish which consumers and configurations are supported. An implementation's existence, a test invoking it, a deprecation label, or a tool warning does not establish that it belongs in production. Conversely, no references inside a checkout does not establish that external clients cannot use a public API. Resolve an apparently abandoned path against plans and feature documents: planned but not yet wired work may need integration rather than deletion. If ownership or intent remains unknown, ask a focused question or report the limit instead of asserting it is dead.

## Core standard

### Locate candidates by consequence

Look for unused declarations and exports, orphan modules and files, unneeded dependencies or configuration, unused flags, unreachable branches, deprecated aliases with no consumers, and implementations replaced by another live path. Distinguish a live implementation from a duplicate reached only by tests, a production helper called only by tests, and a path that remains available for supported compatibility. Trace stale comments and constants against live code before calling them obsolete; explain which decision or maintenance work their contradiction misleads. A dependency named in a manifest may still be consumed by a build script, a plugin, or an external tool rather than by an import.

Prefer candidates whose retention has a present cost or risk: a stale route that shadows a supported one, obsolete logic mistaken for the authoritative implementation, redundant maintenance of divergent paths, or a stale flag that obscures supported behavior. Mere file age, naming, unused-symbol diagnostics, similarity, or a speculative simplification is not evidence of a consequential finding.

### Prove reachability against supported uses

Work from documented entry points and packaging to each candidate: callers and re-exports; route or plugin registration and framework discovery; dynamic imports and dispatch; string-keyed names; generated consumers; build scripts and CI commands; supported runtime modes, targets, and feature gates; and public/published API and known external consumers. Check tests separately from production entry points so test-only use does not turn a production path into a live feature. An unused branch in one configuration may serve another supported configuration. A missing local call to a public symbol is a coverage limit until its external contract and consumers are understood.

Use `lsp` read-only references, definitions, symbols, hover, or diagnostics when available; references give the strongest local symbol evidence. If the server has no project for a file or fails, use structural `ast_grep`, then targeted `grep` for names and paths, and record the limit. `lsp` can miss re-exports, generated or unindexed code, macro expansion, external packages, and dynamic or string-keyed use; `ast_grep` matches syntax but may not resolve identities or runtime registration; `grep` finds text, including false positives in comments or tests, but cannot establish bindings, inspect unavailable external consumers, or read files inaccessible as text. Follow each lead to the actual registered or callable path rather than equating either a hit or a miss with reachability.

### Choose the least risky correction

For a proven obsolete path, propose removal together with its associated configuration, registration, and tests only where their purpose is obsolete; consider backwards compatibility and migration of real consumers. For an intended but disconnected path, propose wiring it through the supported entry point, not deleting or testing the isolated implementation as if it were live. If compatibility or a delayed feature requires retention, identify the owner and reason for keeping it and the condition under which it can be retired. Wiring unused code into production may change behavior; removing it may break dynamic or external users; documenting retention must not disguise a live defect. If the obsolete path itself causes incorrect production behavior, report that connected correctness defect on its live path, not an independent speculative cleanup.

## Language considerations

The core standard applies unchanged; read the relevant subsection before judging a candidate in that language. These are reachability leads, not proof of use or disuse.

### TypeScript

Check package `exports` and published declarations against supported consumers, plus re-export chains, dynamic imports, framework file discovery, templates, generated consumers, and side-effect imports. Establish build/runtime entry points and configurations before deleting a module or export. Compiler and linter unused-symbol checks cannot establish whole-module or public-API reachability; TypeScript's `noUnusedLocals` specifically reports unused *local variables*. Trace emitted or bundled artifacts to the source that owns a candidate rather than treating generated output as its own maintenance target.

### Rust

Check workspace consumers, public crate API and downstream callers, `cfg` feature and target gates, macro expansion or registration, build scripts, tests, and foreign entry points where applicable. A private item with no supported references differs from a public item whose downstream callers are unavailable. `dead_code` and related diagnostics support investigation but do not analyze every external or conditional use; verify the relevant configurations and macro/build connections before proposing removal.

### Python

Inspect package exports (`__all__`, `__init__.py`), installed console/plugin entry points, and imports made by scripts, framework route discovery, and plugin or registry decorators. Follow `importlib`, `getattr`, and string-keyed dispatch to their configured names; direct import searches cannot find every dynamic consumer. Pytest can resolve fixtures by name from `conftest.py` without a direct import, and fixtures may be reached transitively or automatically. Distinguish test-only use from production API use while checking published import paths and unavailable downstream packages before retiring an alias.

## Evidence and limits

- The [TypeScript `noUnusedLocals` reference](https://www.typescriptlang.org/tsconfig/noUnusedLocals.html) describes diagnostics for unused local variables, not complete package-API or dynamic reachability. [Node's package entry point documentation](https://nodejs.org/api/packages.html#package-entry-points) describes exports for Node consumers, not every bundler or framework.
- The [rustc `dead_code` lint](https://doc.rust-lang.org/rustc/lints/listing/warn-by-default.html#dead-code) identifies items in its compilation context; it cannot establish every downstream or alternate-configuration consumer.
- The [Python entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/) defines discoverable object references but does not show which application loads a particular plugin. Python's [`importlib.import_module`](https://docs.python.org/3/library/importlib.html#importlib.import_module) permits imports from runtime names; it does not establish which names this project supplies. [Pytest fixture availability](https://docs.pytest.org/en/stable/reference/fixtures.html#fixture-availability) explains name-based fixture access and `conftest.py` discovery, not whether a fixture is collected by this project's configured runs.

No static search proves a symbol unused for every unseen consumer. Report confirmed reachability and the exact configurations and consumer classes not inspected.
