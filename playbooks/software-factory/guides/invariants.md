# Invariant conformance contract

## Scope and authority

This guide owns the standard for checking first-party TypeScript, Rust, and Python code against the invariants its project documents declare: shared rules, trust boundaries, authority rules, data-ownership rules, and technical contracts that must hold on every path, not only the one a task changed. The [code review contract](code-review.md) owns review scope, evidence, read-only operation, report shape, and severity. Language reviewers judge behavior inside one language or integration boundary; this standard follows each declared invariant across every module, language, and process boundary that can reach it.

The declared invariant is the authority. Invariants come from the active [system architecture](product-documentation-process.md#system-architecture), feature [system designs](product-documentation-process.md#feature-system-design), [technical designs](product-documentation-process.md#technical-design-document) and their [technical contracts](product-documentation-process.md#technical-contracts-and-verification), and repository instructions that state a rule every path must keep. The implementation, a test, or a code comment does not establish an invariant on its own. When a document states only a goal, not a checkable rule, or when two documents conflict, report the gap as a question instead of inventing the rule. A repository with no declared invariants has nothing to check; say so rather than inferring invariants from the code.

## Core standard

### Inventory the declared invariants

List each invariant with its source document and section, restated as a checkable rule: what must always or never happen, to which data or operation, and at which boundary. Split a compound rule into the parts that can fail separately. Skip rules that no code in scope can reach, and name them as not applicable.

### Map every path that reaches each invariant

For each invariant, find the sinks it protects: storage reads and writes, file-system and process access, network calls, secret resolution, privileged commands, and state transitions. Then find every source that can reach those sinks: public and internal APIs, commands and IPC handlers, remote procedure calls across process or sandbox bridges, jobs, webhooks, event and queue consumers, plugins or other code the system runs on a caller's behalf, and administrative paths. Work backward from each sink as well as forward from each source; a path added outside the change that motivated the review still counts. Record the paths inspected so the report shows coverage, not only failures.

Stop tracing a path where it leaves the requested scope. When a path enters a dispatch surface that fans out beyond the scope, such as a registry, router, event bus, or plugin loader, check that the value deciding scope is bound before the dispatch point, record the dispatch point, and classify what lies past it as unverifiable rather than tracing the whole graph. A bounded review that names its dispatch points is complete; it is not a whole-system proof.

### Establish where authority comes from

On each path, determine where identity, tenant or owner scope, permissions, resource identifiers, and limits come from. Trusted values are created by the host or verified at a boundary the host controls: an authenticated session, a server-side lookup, properties the host set when it created a sandbox or connection. Caller-controlled values arrive in the request, message, handle, or object the caller supplies, including fields a caller can copy or forge from an object the host issued earlier. A path that decides whose data to read or write from a caller-controlled value, without checking it against trusted context, violates any ownership or isolation invariant it reaches. Type annotations, interface declarations, and naming do not validate a value that crosses a runtime boundary.

### Classify how each invariant is enforced

Classify every inventoried invariant, and every path when they differ:

- **Structural** — the type system, API shape, or a single choke point makes the violation impossible to write: the scope is bound from trusted context before any caller code runs, or the only constructor for a scoped handle checks it. Name the mechanism.
- **Convention** — each call site must remember to apply a check or pass the right value. List the call sites that currently do. A convention is a finding when a reachable path omits it; otherwise report it in coverage, with the count of sites that must keep remembering.
- **Violated** — a reachable path breaks the invariant. Quote the line where the caller-controlled value is trusted or the check is missing.
- **Unverifiable** — the path depends on code, configuration, or runtime behavior outside the inspected scope. Name what would settle it.

### Choose the correction

Prefer the correction that makes the invariant structural at the narrowest point: bind scope from trusted context instead of accepting it from the caller, remove a caller-supplied field the host already knows, or route every path through one checking constructor or choke point. When structural enforcement would require a large redesign, propose the smallest check that closes the reachable violation and name the structural fix as the follow-up decision. A correction must never widen what the invariant permits, and a change to the invariant itself belongs to the document that declares it, not to the code.

## Language considerations

The core standard applies unchanged; read the relevant subsection before judging a path in that language.

### TypeScript

Types vanish at runtime: a parameter typed as a host-issued handle accepts any object with the same shape from JSON, a structured-clone boundary, a worker or sandbox bridge, or an RPC stub. Check for runtime validation or a host-side lookup where such values enter. Object spreads and `Object.create` can carry caller-controlled fields or expose host bindings through the prototype chain. Branded types enforce a rule structurally only when the brand's sole constructor performs the check.

### Rust

Newtypes, private fields, and constructors that validate make enforcement structural within a crate; public fields, `From` conversions, or `Deserialize` implementations that skip the check reopen the path. Serde deserializes whatever the input contains, so a deserialized identifier is caller-controlled until verified. At FFI, IPC, and command boundaries, trace which side supplies each identifier and whether the handler re-derives scope from host state.

### Python

Type hints, `TypedDict`, and plain dataclasses do not validate at runtime, and `NewType` is erased at runtime. Validation libraries enforce only on the construction path that runs them. Check decorators, middleware, and dependency-injection hooks that are meant to bind identity: a route or handler registered without them bypasses the check, and module-level or request-global state can carry one caller's identity into another's request.

## Evidence and limits

- [CWE-639, Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html), describes authorization that "does not prevent one user from gaining access to another user's data or record by modifying the key value identifying the data"; [CWE-862, Missing Authorization](https://cwe.mitre.org/data/definitions/862.html), covers the omitted check. They classify weaknesses; they do not show that any project contains one.
- The [OWASP Top 10 A01, Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/), and the [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) recommend denying by default, validating permissions on every request, and ensuring lookup identifiers cannot be tampered with. They are web-application guidance; the checks transfer to other request, IPC, and sandbox boundaries by analogy.
- [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) argues for making invalid states unrepresentable by checking once at construction; [Rust newtypes](https://doc.rust-lang.org/rust-by-example/generics/new_types.html), [TypeScript narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html), and Python's [`NewType`](https://docs.python.org/3/library/typing.html#typing.NewType) show what each language can and cannot enforce. They describe mechanisms, not whether a given boundary is sound.

Static tracing cannot prove an invariant holds on paths through unavailable code, dynamic dispatch, runtime configuration, or external callers. Report the paths inspected, the enforcement found on each, and the paths left unverified.
