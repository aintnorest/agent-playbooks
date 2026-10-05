# Test quality contract

## Scope and authority

This guide defines what makes automated tests credible evidence. It applies to writing, improving, and reviewing tests in TypeScript, Rust, and Python projects, whether a person or an agent wrote them. Tasks that consume it own their procedure, permissions, and report; the [code review contract](code-review.md) owns code-review scope, authorization, severity, and findings.

Project documents own intended behavior: requirement wording, behavioral acceptance, and technical contracts keep their homes under the [reference rules](product-documentation-process.md#reference-rules). Tests supply executable proof and do not become a second home for the contract. Repository instructions and configuration own frameworks, commands, and thresholds. This guide requires no framework, test-first sequence, test-layer ratio, coverage or mutation threshold, or new document.

A test is credible evidence when it checks independently justified behavior, at a boundary able to expose the relevant defect, with assertions that distinguish correct from incorrect outcomes, and its evidence states its limits. Green status, test count, coverage, and another reviewer's agreement do not establish these properties by themselves.

## Core standard

### Establish expected behavior first

Before changing behavior or interpreting a verification result, identify:

```text
Authority:   requirement ID, scenario, contract, issue, or stated assumption
Stimulus:    input or action and the relevant starting state
Expected:    observable result, effects, and outcomes that must not happen
Sensitivity: a plausible defect the check must reject
```

Reference existing acceptance where it exists; otherwise record the expectation in the task or the test itself rather than creating a parallel acceptance list. When no authority defines a consequential outcome, ask its owner or label the expectation as an assumption.

Distinguish conformance from characterization. A conformance test checks behavior against its authority. A characterization test deliberately pins existing behavior, for example before a refactor or while the contract is unknown; name it as such and do not claim it proves correctness. A bug's observed output is evidence of the failure, never the oracle for its fix.

Once set, an expectation changes only through its owner. When a check fails, determine whether the implementation, the test, or the expectation is wrong. Updating expected values or snapshots to observed output, deleting or skipping cases, widening tolerances, catching broader errors, marking expected failures, adding retries, or changing exclusions is an acceptance change when it alters what the check protects: justify it against the authority, and revise the owning document when intended behavior changed. A later green run does not authorize the change. A new test failing on current code may reveal a defect: diagnose it against the authority before changing its assertion, and never keep only the generated tests passing on current code unless they are labeled characterization tests.

### Derive assertions independently

The expected value must come from somewhere other than the code under test: the contract, a hand-derived literal, an independently validated fixture, a domain law, or a reference implementation whose assumptions and failure modes differ. Reading the implementation to understand its structure is acceptable; copying its calculation, calling its helpers to compute the expectation, or recording its current output as truth is circular. A model that has seen the implementation tends to reproduce or accept its defects in expected values, even without copying, so another model's agreement after reading it is not an oracle. Have a model derive expected values from the authority, interfaces, and starting state, preferably in a fresh context without the implementation body or its author's reasoning; this separation, not test-first order, matters.

Assert the specific outcome that matters: the value, variant, state, emitted effect, or rejection. Existence, truthiness, success-only results, "does not throw", and type checks suffice only when they are the whole contract. An error test identifies the failure and fails when the operation succeeds. After a failure, check the state that must survive or be rolled back, not only that an error occurred.

Snapshots and golden files are acceptable when their content was reviewed as the expected output and they are narrow enough that a diff is meaningful; an unreviewed snapshot records current behavior. Assert calls, arguments, or order when the interaction is the contract, such as a protocol exchange, a published event, or a command to an external system, not merely because a test double exposes it. Avoid assertions on private structure, incidental ordering, exact wording, or constant values unless they are contractual; assert the behavior that depends on them instead.

### Choose cases and boundaries by risk

Select cases that distinguish plausible faults: representative valid and invalid classes; values on each side of inclusive and exclusive boundaries; empty, missing, duplicate, and maximal inputs; ordering, precision, overflow, encoding, and time zones where relevant; authorization; and state transitions after both success and failure. A small table of discriminating cases with explicit expected values protects more than many happy-path variants.

Test at the boundary where the defect can occur and be observed. Small tests localize computations; integration tests expose persistence, serialization, runtime, framework, and component interactions; contract tests check compatibility between separately changed producers and consumers; end-to-end tests demonstrate a few essential journeys. Choose by the defect being guarded, not by a layer quota, and do not repeat one check across layers without a separate risk.

Test your contract with a framework or library, such as the route you register, the query you emit, or the payload you produce, not the dependency's own documented mechanics. Constructors, getters, constants, and trivial forwarding earn a direct test only when they validate, normalize, default, derive, or cause effects not observed elsewhere.

### Keep dependency behavior faithful

A test double replaces a dependency's behavior, so it must preserve the semantics the test relies on: side effects, error shapes, ordering, partial results, and the data consumed downstream. Keep real the code whose behavior the test checks; replace slow, nondeterministic, external, or costly operations below it. Asserting on a double's configured return value or presence checks the test's setup, not the component.

A replaced boundary establishes the consumer's assumptions, not the provider's behavior. For each consequential boundary replaced in narrow tests, such as serialization, a database, IPC, a network API, or the operating system, some check should exercise the real counterpart or a verified contract at the level the project affords; otherwise report the gap.

When double setup outgrows the behavior under test, or tests break under refactors that preserve behavior, prefer a fake with real semantics or an integration test.

### Make results deterministic and diagnosable

Control everything the outcome depends on: clock, randomness, locale and time zone, environment variables, filesystem, network, shared global or module state, execution order, and scheduling. Create and clean up resources at the narrowest scope that achieves isolation. A test must pass alone, with the rest of the suite, in any supported order, and in parallel where the runner parallelizes.

Await or join all asynchronous and concurrent work an assertion depends on, propagate failures from spawned work into the test result, and wait on an observable condition rather than a fixed sleep. A timeout bounds a hang; it does not synchronize. Ordinary runs rarely exercise rare interleavings, so claim concurrency safety only for what was actually explored.

A flaky test signals a defect in the test or the code. Reruns, retries, and quarantine may contain noise during diagnosis; they are not a fix and must not turn a failure into a pass. When generated input finds a failure, retain the minimized case as an explicit example or regression test, because seeds and local failure stores may not replay after generator or tool changes.

Make failures identify the case and the difference between expected and actual, listing the accepted alternatives when several outcomes pass, through named parameterized cases and meaningful messages.

### Demonstrate failure sensitivity

For each important check, name the plausible defect it rejects, such as a wrong boundary operator, a missing branch, a dropped side effect, an unobserved rejection, a default or empty return, or missing validation. If no such defect can be named, the test either protects nothing that matters or its purpose needs restating.

Use the strongest evidence available:

1. **Observed red/green.** The test fails against the defective or missing behavior for its intended reason, an assertion on the expected behavior, and passes after the change. A compile error, import failure, missing fixture, or not-yet-existing symbol does not demonstrate behavioral sensitivity.
2. **Authorized fault injection.** A targeted defect, introduced manually or by a mutation tool in a disposable workspace, makes the check fail; the fault is then discarded and never committed.
3. **Reasoned counterfactual.** An explanation of why the assertion would fail under the defect. It is useful for design and review, and is reported as reasoning, not execution.

Characterization tests and new tests for already-correct code cannot fail first against intended behavior; use fault injection or reasoning for them.

### Keep tests maintainable

Tests are maintained code. Keep each test's case, action, and expected outcome readable where it is written: move incidental setup into helpers or fixtures, but keep expected values visible rather than re-derived by builders or loops. A test protects one behavior, possibly through several assertions, and its name states that behavior and its condition. Smell flags such as Assertion Roulette prompt review, not splitting such a test.

Replace or remove tests that duplicate stronger ones, pin incidental implementation, or claim protection they do not provide; a test that must change under a behavior-preserving refactor is coupled to the implementation. Add a test only when it protects a behavior or boundary that no existing check protects at comparable cost.

### Report evidence and limits

Report what was exercised: the candidate revision, the command or harness, the relevant configuration, features, or platform, and the result. Include skipped, ignored, excluded, or flaky tests relevant to the claim; which sensitivity evidence (observed, injected, or reasoned) supports each important claim; and remaining gaps, such as unexercised boundaries, doubles never checked against their real counterparts, and assumptions awaiting an owner. Do not describe planned, partial, or unauthorized verification as a pass, or generalize from a subset.

Independent review helps only when the reviewer derives expectations from the authority rather than from the author's tests, names, or green report. Held-out tests reduce tailoring to visible examples but do not establish that the specification is right.

## Stronger techniques

Use these when example cases leave a consequential input or state space unchecked and the project can afford the cost. Each technique still needs an independent oracle.

- **Property-based testing** asserts invariants that hold for generated inputs, such as round trips, preserved elements and multiplicities, idempotence, or ordering laws. The property must be true of the domain, not merely of the implementation; comparing sets after sorting, for example, misses lost duplicates. Generators must reach boundary regions. Sampling does not prove a property, so keep critical cases as explicit examples. A property an agent infers is a proposal until reviewed against intent, because its violation may be intended behavior. Report a confirmed violation as the property with its shrunk counterexample, which gives a repairing agent more to act on than an input/output mismatch.
- **Metamorphic testing** relates outputs across justified input transformations when an exact expected output is unavailable, for example that adding a record excluded by a filter does not change the filtered result.
- **Differential testing** compares against another implementation, a reference system, or a previous version. Agreement is evidence only to the extent the implementations fail independently; comparison with a previous version is characterization.
- **Model-based or stateful testing** generates action sequences and compares the system to a model that is simpler than, and independent from, the implementation.
- **Fuzzing** targets parsers, decoders, and other untrusted-input boundaries. Its usual oracle is a crash, hang, sanitizer report, or invariant violation; add semantic assertions where correctness matters beyond robustness.
- **Fault injection** fails dependencies at persistence, network, or process boundaries to verify partial-failure contracts: rollback, cleanup, retry, and the reported error. It verifies the partial-failure postconditions of [technical contracts](product-documentation-process.md#technical-contracts-and-verification).
- **Concurrency exploration** systematically schedules the interleavings a model checker or controlled scheduler can observe; conclusions cover only the modeled operations.

## Coverage, mutation, and CRAP

Metrics locate risk; none establishes that an expectation is correct. Do not make a metric the target of the work it measures, set or change a threshold without the project owner, or compare numbers produced by different tools or configurations.

### Coverage

Line, statement, and branch coverage report what executed. Uncovered consequential code is a gap to investigate; covered code may still be unchecked. Branch coverage exposes untaken decisions that line coverage hides. Every exclusion from measurement needs a reason. A test that adds no coverage can still reject a fault the suite misses; judge it by that fault.

Coverage of a model-generated suite says little about whether it detects a defect present in the code it was generated from, because its expectations may encode that defect. Report whether the generator saw code assumed correct or code that may contain the defect.

### Mutation testing

Mutation testing injects small faults and records whether tests detect them. It is most useful on selected consequential code the tests already execute, targeted to changed code; whole-codebase runs are costly and noisy. Triage each undetected mutant before acting:

- **No coverage:** a missing test for reachable behavior, or unreachable code to remove.
- **Survived with coverage:** a weak assertion or a missing case.
- **Equivalent:** no observable difference exists. Record it rather than writing a contrived test, and consider whether simpler code removes it.
- **Outside the contract:** the mutation changes only unspecified behavior, such as diagnostic logging.

Strengthen tests against the behavior a mutant revealed, not against the mutation operator. Report the tool, scope, and score denominator with the counts of survived, uncovered, timed-out, errored, and ignored mutants: tools differ, and Stryker, for example, counts timeouts as detected and excludes compile errors, runtime errors, and ignored mutants from its score. Inspect timeouts, which can signal detection or only slowness. A complete score is not a goal.

A model can aim mutation at one concern, such as an authorization rule or a boundary: it proposes a few plausible faults there, then writes tests that pass on the original and fail on each fault. Such tests protect current behavior, so their expected values still need independent review.

A reviewer without execution authority reasons about mutations and may recommend them; it does not edit code or run mutation tools.

### CRAP

The Change Risk Anti-Patterns (CRAP) score of a function with cyclomatic complexity $C$ and test coverage fraction $cov$ is:

$$
\mathrm{CRAP} = C^2 (1 - cov)^3 + C
$$

It ranks functions where complexity combines with weak coverage. At full coverage it reduces to $C$ regardless of assertion quality. Use it to prioritize review, testing, or simplification, and record the complexity tool and coverage kind: the original metric used basis-path coverage, and line- or branch-based implementations are not equivalent measurements. Its original threshold of 30 is a heuristic, not an acceptance gate. Lower the score by simplifying code or testing its behavior, never by adding tests that execute without checking.

## Language considerations

The shared standard applies unchanged; these sections list recurring hazards, not complete manuals. Use the project's configured runner and tools. Named tools are established examples, not required dependencies; confirm version-sensitive behavior against the installed version's documentation.

### TypeScript

- Static types do not validate runtime data. Test parsing and validation at network, storage, IPC, and JavaScript boundaries with realistic payloads, including the missing, null, extra, and mistyped fields the contract rejects. Type-level tests check the compiler's view and execute no runtime behavior.
- Await or return every promise an assertion depends on, and await rejection assertions; a floating promise or unawaited rejection assertion can pass regardless of the result. Where a callback containing assertions might never run, assert that it ran.
- Advance fake timers and flush pending promise work as the runner requires, then restore real timers. Restore mocks, spies, module mocks, and global stubs between tests; hoisted module mocks can affect other cases in the file.
- Query rendered UI by the role, label, or text a user perceives, drive it through user-level interactions, and assert rendered results rather than component internals or mock test IDs. Simulated DOM environments are not browsers; use browser tests where layout, navigation, or real event behavior matters.
- Examples: Vitest, Jest, or `node:test` runners; fast-check for property testing with shrinking and replayable seeds; StrykerJS for mutation testing; Playwright for browser tests; Pact for consumer/provider contracts.

### Rust

- Compilation and the borrow checker exclude classes of memory-safety and data-race faults, not domain faults. Assert values and specific error variants with their relevant data, not only `is_ok()` or `is_err()`.
- `#[should_panic]` passes on any panic unless `expected` constrains the message. Test a panic only when the panic is contractual; otherwise assert on returned results.
- Join spawned threads and await spawned tasks, checking their results: a panic in a spawned task is returned through its handle and does not fail the test unless observed. Async tests need a runtime such as `#[tokio::test]`, whose default single-threaded runtime cannot exhibit some multi-threaded interleavings; use the runtime's paused or mocked time for timer behavior where available.
- Test the supported feature and target configurations whose behavior differs, and keep `cfg(test)` code from altering the behavior under test. Integration tests under `tests/` see only the public API; doc tests keep examples compiling and correct but do not replace edge-case tests.
- Run Miri on tested paths through `unsafe` code where it is supported; it detects undefined behavior only on the paths executed.
- Examples: the built-in test harness or cargo-nextest; proptest or quickcheck for property testing, with committed regression files and important cases promoted to explicit tests; cargo-mutants for mutation testing; Loom for exploring interleavings of operations that use its types; cargo-fuzz for fuzzing.

### Python

- Without static enforcement, tests are the main runtime check of data shapes. Assert exact values and types where the contract requires them; type checkers complement tests but execute nothing.
- Unspecified mocks accept any attribute and call. Use `autospec`, `create_autospec`, or `spec_set` to keep a double's interface faithful, and patch a name where it is looked up, not where it is defined.
- Target the specific exception type, match the message only when it is contractual, and keep the raising block to the single call that should raise.
- Fixture scope determines sharing: module- or session-scoped fixtures and module-level state can leak between tests. Use the runner's facilities, such as `monkeypatch` and `tmp_path`, for environment and filesystem changes, and ensure teardown runs.
- Coroutine tests need an async-capable runner or plugin; without one, the coroutine body does not run as a test. Treat never-awaited-coroutine warnings as failures where the project allows.
- Compare floating-point results with a tolerance justified by the domain, such as `pytest.approx` or `math.isclose`.
- Examples: pytest or unittest; Hypothesis for property and stateful testing, keeping important failures as explicit `@example` cases; mutmut for mutation testing; coverage.py with branch measurement.

## Evidence and limits

- [Konstantinou et al.](https://arxiv.org/html/2410.21136) found that model-generated test oracles for 24 Java repositories tended to capture implemented rather than intended behavior, and a mutated implementation lowered a model's recognition of correct assertions from 40.77% to 31.94%. [Konstantinou, Tambon, and Papadakis](https://arxiv.org/abs/2607.05139) found that tests generated in a fresh context from the task alone detected about 25% of faults, against about 14% when generated in the same conversation after faulty code, at similar coverage. [Zhao, Zhou, and Cohen](https://doi.org/10.1145/3832204) found that replacing a buggy method body with an inferred specification cut bug-validating tests from 3.84% to 2.69%, adding the specification beside the body barely helped (3.80%), and inferred specifications kept the bug in 15–21% of cases. These support the independent-oracle and fresh-context rules; they study benchmark functions in Java and Python rather than current agents in these three languages, and they compare contexts, not test-first with test-last ordering.
- [Mathews and Nagappan](https://arxiv.org/abs/2412.14137) found that a generator keeping only tests that pass on current code retained bug-validating suites for 171 of 287 faulty student programs. It supports the rule against filtering generated tests to passing ones; its subjects are introductory Python exercises.
- [Ouédraogo et al.](https://doi.org/10.1145/3838597) found test-smell detectors disagreeing sharply on model-generated tests, for example flagging Assertion Roulette in 37.51% or 68.59% of the same GPT-3.5 suites. They measure smell prevalence, not fault detection or maintenance cost.
- [Ray and Goyal](https://arxiv.org/abs/2607.14167) found that listing admissible alternatives after a rejection raised repair from 14/50 to 36/50 and from 8/50 to 29/50, while location and observed value alone added little; the tasks were short TextWorld action plans, not repository code.
- [Foster et al.](https://doi.org/10.1145/3696630.3728544) report that Meta's mutation-guided generator produced 571 fault-killing tests, 277 adding no line coverage, and engineers accepted 140 of 191 in review sessions. Its tests characterize current behavior, and it did not measure defects prevented.
- [Zhao, Zhou, and Cohen's replication](https://doi.org/10.1145/3832093) found coverage and mutation scores ranked 13 model settings well by real-bug detection when tests came from fixed code (r ≈ 0.86), predicted little within one model's suites, and lost coverage's signal when tests came from buggy code, where mutation was not measured. It studies Java methods.
- [Maaz et al.](https://arxiv.org/abs/2510.09907) judged 28 of 50 sampled agent property-based bug reports valid and 16 worth reporting, and one report submitted to maintainers described intended behavior. [He et al.](https://arxiv.org/abs/2506.18315) raised pass@1 from 32.0% to 36.2% by presenting the same failure as a property violation rather than an input/output mismatch. Both study Python libraries or benchmark problems.
- [Petrovic et al.](https://research.google/pubs/practical-mutation-testing-at-scale-a-view-from-google/) report that incremental mutation of changed code with mutant filtering made mutation testing actionable at Google's scale; their setting is not every project's. Stryker documents [mutant states and score denominators](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/) and [equivalent mutants](https://stryker-mutator.io/docs/mutation-testing-elements/equivalent-mutants/); other tools classify outcomes differently.
- [Savoia](https://www.artima.com/weblogs/viewpost.jsp?thread=215899) introduced CRAP as an experimental metric, acknowledging that high coverage can coexist with poor tests; its threshold was a starting point rather than an empirical result.
- Fowler's [practical test pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) and [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html) inform boundary selection and interaction assertions; they are practitioner guidance, not measured results. Pact's [workflow](https://docs.pact.io/getting_started/how_pact_works) documents that consumer contracts require separate provider verification.
- Hypothesis recommends explicit [`@example` cases over its failure database](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html) for correctness, and proptest documents that [persisted failures](https://proptest-rs.github.io/proptest/proptest/failure-persistence.html) depend on the generator. pytest's [flaky-test guidance](https://docs.pytest.org/en/stable/explanation/flaky.html) and coverage.py's [branch measurement](https://coverage.readthedocs.io/en/latest/branch.html) support the determinism and coverage rules.
- A published agent skill for [writing good tests](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/writing-good-tests.md) informed the practice of naming the break a test catches; its stricter absolutes about mocks and test-first ordering were not adopted.

No guide makes tests correct. Intended behavior remains with its owning documents and the developer; this guide governs how tests provide evidence for it.
