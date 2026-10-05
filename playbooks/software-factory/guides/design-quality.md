# Design and maintainability contract

## Scope and authority

This guide owns the design and maintainability standard for first-party TypeScript, Rust, and Python code. Apply it to the requested code, its actual callers and entry points, and the configuration and connected boundaries needed to understand a design decision. The [code review contract](code-review.md) owns review scope, evidence, read-only operation, report shape, and severity; this guide does not turn an incidental production bug, weak test, or unused item into an independent design finding. Intended behavior and accepted tradeoffs come from the project's requirements, contracts, instructions, and consumers, not a preferred pattern or the existing implementation alone.

A maintainability finding does not require a runtime failure. It does require a concrete *present* burden in changing, understanding, testing, or owning the inspected operation and a smaller correction whose benefits exceed its migration or coupling cost. Preserve equally sound alternatives; do not prescribe a rewrite, framework, abstraction, generic type, immutability, or validation by default. For design-time traces, refer to the [technical-design control-flow clarity rule](product-documentation-process.md#technical-design-document); this guide judges the inspected code and its actual paths rather than restating that document contract.

## Core standard

### Control-flow complexity

Trace each consequential operation from a supported entry point through the main path and materially different alternate and failure paths. Identify who decides each branch, what invokes or resumes the next step, who owns side effects, and where completion or failure returns. Ask whether the flow is **more complicated than the problem requires**. Look for unnecessary layers or indirection; implicit callbacks, registration, or event chains that hide the decision maker; one decision scattered across modules; hidden ordering obligations or temporal coupling; and several flags that together imply an unexpressed state machine. Show a specific trace where the reader or caller must reconstruct control across handoffs, or where a change requires synchronized edits. Do not mistake justified asynchronous or distributed coordination for excess complexity; compare a simpler path with the actual requirements and failure contract.

### Data-flow complexity

Trace the same operation's authoritative value from creation to consumers, conversions, mutation, storage, and failure handling. Ask whether the **data flow is more complicated than the problem requires**. Identify repeated or lossy conversions of one representation, ambiguous ownership transfer, shared mutable state whose writers or readers cannot be located, derived state stored in several places without a reliable update owner, and boundaries that make callers duplicate domain knowledge to interpret or reconstruct data. Establish the actual round trip or multiple writers and its consequence before proposing one representation, an adapter, or a new owner. An intentional snapshot, transfer, serialization format, or conversion at a real boundary may reduce coupling; do not eliminate it on aesthetic grounds.

### Cohesion, boundaries, and caller costs

Find the authoritative owner of each policy and the callers affected when it changes. Unrelated responsibilities forced to change together, duplicated authoritative decisions, or an API that repeatedly makes callers copy a condition, assertion, conversion, or workaround indicate change amplification. Conversely, a missing boundary may cause unrelated clients to depend directly on a volatile implementation detail. Inspect concrete callers and the actual variation before deciding whether to split responsibilities or introduce an interface.

Look for missed reuse: code that reimplements a helper already in the codebase, a standard-library or runtime primitive, or a guarantee the framework or a downstream layer already provides. Name the existing facility and propose it only when it is behavior-equivalent for the inputs actually in play; locale, sorting, serialization, and error behavior often differ from a hand-written version.

Judge abstractions by the invariant they express and the coupling they remove. Leaked representation, broad mutable exposure, unclear error or resource ownership, and speculative generality can impose more knowledge on callers than the abstraction saves. A narrow adapter or direct call may be clearer; a stable boundary can be worth its indirection when it centralizes a real policy. Misleading names, units, signatures, or failure contracts are findings only when they cause a concrete misinterpretation, repeated correction, or change hazard. Evaluate whether callers can use an API without learning undocumented state, ordering, or domain rules.

### Prove the maintenance consequence

For each candidate, identify the affected operation and observed sites: a policy requiring synchronized edits, a caller recreating a domain rule, an error path requiring a trace through several owners, or storage that must stay consistent in multiple places. Explain why the smallest proposed correction reduces that burden and what it costs, including compatibility or migration risk. Similar-looking code, a long function, a high complexity score, the presence of a keyword, or preference for a pattern alone does not establish harm. Check current guarantees and accepted tradeoffs first; do not replace straightforward local behavior with mechanisms the operation does not need. Performance allegations need an observed avoidable cost or an applicable workload rather than hypothetical scale.

Before proposing a shared abstraction for duplicated code, check whether the duplicate can instead be eliminated by deriving it from an existing source of truth or relying on a verified guarantee. A correction must never remove or thin validation at a trust boundary, error handling that prevents data loss, a security check, or an accessibility affordance, even when a finding frames it as redundant. Do not propose inlining a helper that names a concept or merging unrelated logic, and establish an abstraction's original purpose, for example from history or documentation, before calling it unnecessary. If the proposed code would be longer or harder to follow than the current code, do not report it.

## Language considerations

The core standard applies unchanged. Read the subsection for each target language present; these are prompts to inspect actual callers, not language-wide style rules.

### TypeScript

Check whether types model real relationships and states and whether public signatures hide unstable representation. Follow callers whose repeated assertions, guards, conversions, or duplicated domain decisions reveal a boundary cost. A guard's claim about a runtime value is a correctness question; assess a design concern only when the guard's API makes callers repeatedly compensate for a weak contract. Report generic, overload, or conditional-type complexity only with demonstrated comprehension or caller cost. Preserve useful inference and equally sound `type`/`interface`, function/class, and modeling choices. `any`, assertions, local mutation, and complex types are not findings by presence; inspect the invariant or adapter containing them. Do not demand redundant validation, copies, annotations, or a schema library where existing guarantees suffice.

### Rust

Assess module and API ownership through actual callers: leaked representation, unrelated responsibilities coupled to one edit, overbroad mutable access, duplicated policy, or an abstraction obscuring its invariant. Examine borrowing, consuming, sharing, returning, and retaining data against actual storage and escape needs; show when lifetime coupling, restrictive bounds, forced caller copies, or resource retention impose a present cost. A clone can deliberately detach a snapshot, release a lock, or transfer work. Straightforward ownership need not become intricate borrowing; do not require builders, newtypes, traits, generics, derives, or layers merely because they are available. Distinguish design cost from a reachable ownership or resource-lifetime correctness defect.

### Python

Follow actual call sites and initialization paths through duck-typed protocols, dict-shaped data versus named records, and module-level mutable state. Determine whether the chosen shape expresses a real invariant or makes callers repeatedly remember keys, units, and optional states; neither a dictionary nor a typed record is automatically preferable. Inspect decorators, metaclasses, registries, and dynamic lookup for hidden dispatch or ownership, and circular imports for ordering constraints; do not demand explicit dispatch or a protocol if existing usage is clearer. Separate a documented shared state owner from writers spread across modules, and ground any proposed change in specific consumers rather than a demand for static typing.

## Evidence and limits

- The [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-assertions) documents assertion and inference mechanics; those mechanics do not establish that any particular assertion is a maintenance defect. The [Rust ownership chapter](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) explains ownership and moves; it does not decide whether an inspected clone or lifetime bound is justified.
- Python's [typing documentation](https://docs.python.org/3/library/typing.html#typing.Protocol) describes structural protocols and notes that annotations are not enforced at runtime; its existence does not make a protocol necessary. The [language reference](https://docs.python.org/3/reference/compound_stmts.html#function-definitions) describes function decorators; it does not establish that a project's decorated flow is hard to follow.
- These sources establish language mechanisms, not the cost or acceptability of a repository's design. That judgment depends on inspected paths, callers, supported configurations, and project authority; absent callers or undisclosed external consumers are coverage limits, not proof of a defect.
