---
state: draft
revision: prd-r1
---

# PRD: Software factory

Requirement identifiers use the prefix `SF`, for "software factory".

## User stories

- **US-1 Choose the work.** As the developer, I want the factory to ask me what the next feature or proof of concept is, so that I set direction and the agents never pick it for me.
- **US-2 Documents that hold up.** As the developer, I want every document drafted, independently reviewed, and revised until it is ready, so that I only see documents worth my judgment.
- **US-3 Gates only where I'm needed.** As the developer, I want to approve only the documents that need my judgment, and to approve each in the way that fits it, so that I spend my attention on product direction and technical understanding, not on implementation detail.
- **US-4 Approvals I can trust.** As the developer, I want my approvals to be mine alone and to lapse when the document changes, so that no agent can pass my gate and no approval outlives the content I approved.
- **US-5 Order without a straitjacket.** As the developer, I want the factory to stop steps that skip a gate but still let me explore, question, and edit freely, so that the process holds without getting in the way of thinking.
- **US-6 Documents that agree.** As the developer, I want the document set checked for contradictions and misplaced detail, so that agents downstream work from one consistent picture.
- **US-7 Getting unstuck.** As the developer, I want the factory to stop and brief me when a loop is not converging, so that agents do not burn time and tokens circling.
- **US-8 Consistent orchestration.** As the developer, I want the main session to drive the process and always know where it is, so that the next step happens reliably instead of depending on whether the agent remembers to offer it.
- **US-9 Implementation that corrects itself.** As the developer, I want implementation run by its own orchestrator that fixes small problems itself and hands back large ones, so that the main session stays free for planning and design problems return to design.
- **US-10 Reviewed code.** As the developer, I want every implemented slice put through the full set of code reviews and fixes, so that slop is caught before I see it.
- **US-11 I validate what ships.** As the developer, I want to confirm a slice works before it counts as done, so that "done" means I saw it work.
- **US-12 Fixes after delivery.** As the developer, I want problems found after a slice is done held for later and fixed with the same rigor as new work, so that fixes neither interrupt me nor skip review.
- **US-13 Factory without extra tools.** As the developer, I want all of this to work with OMP and the Playbook alone, so that I do not need a separate supervising tool to get a reliable process.

## Requirements

### Starting work (US-1, US-8)

- **SF-001** When no feature is in progress, the factory asks the developer to choose the next feature or proof-of-concept scope, offering the roadmap's Now and Next items as options. It never chooses on the developer's behalf.
- **SF-002** In a project without a product vision, the factory starts with the product vision.
- **SF-003** In a project without an architecture, the factory produces the architecture after the product vision and before the first PRD.
- **SF-004** The project has one architecture. A feature updates it only when the feature changes a system-wide foundation; no feature gets an architecture of its own.

### Sequence (US-2, US-8)

- **SF-005** For each feature, the factory works in this order: PRD; system design when the feature has more than one slice; then, for each slice, technical design, implementation plan, implementation, code review, and developer validation.
- **SF-006** The system design decides how many slices a feature has. A feature without a system design has one slice.
- **SF-007** A single-slice feature has no system design; its technical design follows the PRD directly.
- **SF-008** A multi-slice feature's system design names each slice and the order the slices are built in.
- **SF-009** After a slice is validated, the factory starts the next slice's technical design. After the last slice, the feature is done and the factory returns to SF-001.

### Document review loop (US-2, US-7)

- **SF-010** Every document is first written by a drafting agent, then reviewed by an independent reviewing agent that did not write it and starts from fresh context.
- **SF-011** The orchestrator decides every review finding by ID in the harness-owned ledger, recording a reason for each decision.
- **SF-012** Accepted findings are applied by the drafting agent, given the document and accepted findings with their reasons. The orchestrator may apply small, precise edits itself.
- **SF-013** The drafting agent does not decide findings about its own draft. The orchestrator decides each one: accepted, rejected, passed as a minor nit, or a duplicate of an earlier finding.
- **SF-014** After each round, the orchestrator states whether another is needed and why, or why the document is ready. Real accepted Blocker/Major findings and blocking recurrences keep the loop going; Minors, nits, rejections, and duplicates of rejected findings do not require another round.
- **SF-015** A rejected finding stays rejected without new evidence; its reason remains in the ledger. Re-raised findings are duplicates: rejected duplicates close quietly, while recurring accepted Blocker/Major issues reopen blocking work and need a fix and change check before closing.
- **SF-016** When an accepted Blocker/Major returns for the second time after its fix, the factory stops reviewer dispatch for that document or feature coherence subject and summarizes what keeps returning, why fixes are not holding, options, and a recommendation. Real Blocker/Major findings otherwise keep review going.
- **SF-017** The developer's next answer lifts cycling refusal; another return of the issue refuses again. The harness selects blind full reviews during a document's initial review phase until a full round has no accepted Blocker/Major, or, from the seventh full round on, no accepted Blocker, then change checks of edits and accepted fixes. Existing documents without ledgers receive a full first review; a reasoned full-review request overrides the next mode, and unchanged content cannot receive a change check.

### Document set coherence (US-6)

- **SF-018** When a system design or TDD is close to done, coherence review requires at least one recorded specialist round for a system design or TDD and every feature document ledger settled: no pending round, undecided finding, or open blocking finding. Coherence is full initially and when the set gains a document, otherwise a change check of edits.
- **SF-019** Documents changed by coherence or cascade, including parents, receive specialist change checks and renewed gates where applicable. Post-coherence review checks that the edits hold and did not break dependent documents.
- **SF-020** When a document changes, every document below it that depends on the change is reviewed again.

### Gates (US-3)

- **SF-021** The product vision and each PRD need developer approval. Approval means the developer has read the document in full and accepts its content.
- **SF-022** The architecture and each system design need developer approval. Approval means the developer understands the document well enough to explain it and defend its technical decisions, and agrees with them. The developer is not expected to reread the whole document after each change.
- **SF-023** An architecture or system design approval request explains the document well enough for the developer to explain it and defend its decisions to someone else: the whole design on first approval, and each change since the last approval, with its reason and what changed in the decisions, on re-approval. Each point names the section that holds its detail, so the developer can read further only where they need to.
- **SF-024** Technical designs and implementation plans are accepted by the agents once their review loop has concluded and their checks pass. They do not need developer approval.
- **SF-025** Every gate request can be answered without remembering prior context: it states what is being approved, why, what changed, and what happens next.
- **SF-026** If the developer requests changes at a gate, the document returns to its review loop and then to the same gate.
- **SF-027** Stopping at a developer gate, or at any limit that requires the developer, counts as the orchestrator successfully finishing its turn, not as failing to finish.
- **SF-064** A PRD needs revising, and the developer's approval again, only when the product behavior it promises changes. A change of technical approach that keeps the same experience and guarantees changes the architecture or a design, not the PRD.

### Approval integrity (US-4, US-13)

- **SF-028** An agent that tries to record developer approval, or to change approvals by any route other than the one provided for agents, is stopped. The same message appears whichever route it tried: the rule, the allowed path, and that stopping to ask the developer is the correct way to finish its turn.
- **SF-029** Any agent that writes documents can withdraw an agent acceptance; developer approvals lapse automatically when the document changes. Review agents stay read-only.
- **SF-030** An agent can record acceptance only of a technical design or implementation plan whose review ledger is closed on the current body and whose required checks pass. Acceptance evidence is generated from the ledger, not supplied as free text.
- **SF-031** Any change to an approved or accepted document's content withdraws that approval automatically, without depending on an agent to withdraw it.
- **SF-032** The developer can record an approval directly, without going through an agent.

### Order enforcement (US-5, US-8)

- **SF-034** While a document is waiting on its gate, no document that comes after it in the sequence can be created.
- **SF-035** Implementation cannot start until the slice's implementation plan and technical design are accepted and every developer gate above them is approved.
- **SF-036** When the factory refuses a step for being out of order, it says where the feature stands and what step it expects next.
- **SF-037** Discussion, questions, research, and edits to existing documents remain allowed at any time, in any order. When work departs from the expected order, the factory says what it expects next instead of blocking it.
- **SF-038** The orchestrator knows, at every turn, the current feature, the state of each of its documents, the current review round, and the next expected step, and shows this to the developer on request.

### Orchestration (US-8, US-9)

- **SF-039** The main session is the orchestrator. It drives the sequence and starts the next step itself, rather than waiting for the developer to name it.
- **SF-040** Only the main session talks to the developer. An agent beneath it that needs a developer decision stops and reports to its caller.
- **SF-041** The factory works with OMP and the Playbook alone. Enforcement is aimed at stopping forgotten or skipped steps, not at defeating deliberate circumvention.

### Implementation (US-9)

- **SF-042** Each slice's implementation plan is carried out by an implementation orchestrator working beneath the main session. It holds the implementation context; the main session does not hold individual workers' detail.
- **SF-043** Workers carry out their assigned tasks with the context they are given, and do not do open-ended research.
- **SF-044** The implementation orchestrator gets small issues fixed during the run, through its workers, without involving the main session. A small issue is one that keeps documented behavior, interfaces, and acceptance intact.
- **SF-045** The implementation orchestrator records every departure from the technical design. After the slice is validated, the technical design is updated to match and accepted again under SF-030.
- **SF-046** When an issue is too large to fix in-run or fixes keep failing, the implementation orchestrator stops, preserves all work, and reports to the main session: what happened, the evidence, and which document it believes is wrong. Then it ends.
- **SF-047** On such a report, the main session decides which document is wrong. It takes that document through its loop and gate, reviews the documents below it, and replans only the unfinished part of the slice. Completed work is kept.
- **SF-048** After replanning, implementation resumes from where it stopped.

### Code review (US-10)

- **SF-049** After a slice's implementation is integrated and verified, the factory reviews the changed code for each language present. It also runs the design, invariants, tests, and unused-code reviews.
- **SF-050** Accepted review findings are fixed by agents. After the fixes, the factory verifies again that the application works and the slice behaves as specified.
- **SF-051** At most four review-and-fix cycles run without the developer. Before a fifth, the factory stops and gives the developer a summary of what happened, the outstanding issues, and the proposed fix.
- **SF-052** After a cycle with no outstanding issues, the orchestrator decides whether another review round is worthwhile. It may run all of the reviews, some of them, or none, and says why.

### Validation and completion (US-11)

- **SF-053** When review is complete, the factory gives the developer a summary: what was delivered, how it went, corrections made, remaining risks, and the exact steps to validate the slice.
- **SF-054** A slice is done only after the developer confirms it works. Its technical design and implementation plan become done only then.
- **SF-055** If validation fails, the developer chooses how to proceed. Small issues are fixed within the slice under SF-044. Larger ones follow SF-046 to SF-048, or become a new slice.
- **SF-056** Done documents are not edited again.

### Fixes after delivery (US-12)

- **SF-057** A problem found after a slice is done is recorded as a known issue to fix later: in the repository's Beads tracker when the repository uses Beads, and otherwise as an issue in the roadmap. It does not interrupt current work unless the developer says so.
- **SF-058** A known issue is fixed either on its own or as part of a new slice, as the developer chooses.
- **SF-059** A fix made on its own brings the code back in line with what the documents already say, and adds a test that would have caught the problem.
- **SF-060** A fix made on its own goes through the same code reviews, cycle limit, and developer validation as a slice (SF-049 to SF-054).
- **SF-061** When the documented behavior itself is wrong, the fix needs a new slice.
- **SF-062** A slice that only fixes problems adds a technical design and implementation plan. It does not by itself require a system design.
- **SF-063** A new slice for a multi-slice feature updates that feature's system design.
