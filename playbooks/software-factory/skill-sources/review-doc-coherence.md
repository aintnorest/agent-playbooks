# Review document-set coherence

## Role

Independently review a document set and its relationships without editing it. Assess whether the documents compose into one coherent contract without replacing their individual owners or specialist reviews.

## Purpose

Review whether the supplied documents stay within their roles and levels of detail, avoid competing authority and contradictions, preserve obligations through refinement and handoffs, and give downstream readers and agents an unambiguous path from product intent to implementation.

## Required guidance

- [Review report delivery](../guides/agents.md#review-report-delivery)
- [Independent review context](../guides/document-review.md#independent-review-context)
- [Evidence and authority](../guides/document-review.md#evidence-and-authority)
- [Findings](../guides/document-review.md#findings)
- [Governing principles](../guides/product-documentation-process.md#governing-principles)
- [Documentation hierarchy](../guides/product-documentation-process.md#documentation-hierarchy)
- [Reference over repetition](../guides/product-documentation-process.md#reference-over-repetition)

## Reference guidance

- [Document state and revision](../guides/product-documentation-process.md#document-state-and-revision)
- [Approvals](../guides/product-documentation-process.md#approvals)
- [Product vision contract](../guides/product-documentation-process.md#product-vision)
- [System architecture contract](../guides/product-documentation-process.md#system-architecture)
- [Roadmap contract](../guides/product-documentation-process.md#roadmap)
- [Feature Product Requirements Document contract](../guides/product-documentation-process.md#feature-product-requirements-document)
- [Feature system design contract](../guides/product-documentation-process.md#feature-system-design)
- [Technical Design Document contract](../guides/product-documentation-process.md#technical-design-document)
- [Implementation plan contract](../guides/product-documentation-process.md#implementation-plan)
- [Feature notes](../guides/product-documentation-process.md#feature-notes)
- [When a feature needs slices](../guides/product-documentation-process.md#when-a-feature-needs-slices)
- [Lightweight path for minor changes](../guides/product-documentation-process.md#lightweight-path-for-minor-changes)
- [Decisions](../guides/product-documentation-process.md#decisions)
- [Behavioral acceptance](../guides/product-documentation-process.md#behavioral-acceptance)
- [Technical contracts and verification](../guides/product-documentation-process.md#technical-contracts-and-verification)
- [Technical-writing standards](../guides/technical-writing-standards.md)
- [Communication rules](../guides/communication-policy.md#rules)

## Inputs

- The requested document set or authorized project scope, with paths, exact revisions or unambiguous candidate bodies, and any focused change or downstream task.
- Project goals, governing sources, accepted decisions, and explicit scoped exceptions; raw Markdown when links, comments, examples, or diagrams affect meaning.
- Optional related feature or slice documents and repository evidence needed to resolve a concrete relationship.
- A blind full-review packet, or a harness change-check packet containing the edited documents' diff and accepted fixes (including recurring ones) to verify; never rejected findings, dispositions, verdicts, or totals.

## Instructions

Full reviews stay blind and apply the whole-set procedure below. For a change check, scope that procedure to the harness diff and accepted fixes: check whether those fixes hold and whether the diff introduces a Blocker/Major or breaks dependent documents. Do not report issues in unchanged text unless the change makes them wrong. Never use rejected findings, dispositions, verdicts, totals, author cues, or desired outcomes; disclose extra context.

Return questions and missing-input limits to the caller in the fixed Markdown review report's Questions and Coverage limits sections, not directly to the developer. Read [communication rules](../guides/communication-policy.md#rules) for the caller-escalation boundary; the caller owns any developer request.

Before checking status, read [document state and revision](../guides/product-documentation-process.md#document-state-and-revision) and [approvals](../guides/product-documentation-process.md#approvals). Run `check_doc_status` on every accessible eligible document in the authorized set, including roadmap and implementation plans; report metadata and approval errors alongside substantive cross-document findings. Approval comes from `docs/user-approvals.json` and `docs/agent-approvals.json`, exposed as `approval: {gate, valid}`, not frontmatter. For inaccessible/chat-only members or an unavailable tool, identify each unperformed status check as a coverage limit. `## Status` is prose only.
Check lifecycle relationships and approval validity against the linked rules, including governing-design prerequisites and delivered-slice ownership.

1. **Establish the set and review basis.** Inventory the authorized documents, their roles, revisions, statuses, and links. For a whole-set review, inspect every document in scope; for a focused change, follow affected parents, siblings, and dependents within the authorized scope. Do not substitute a sample of documents for a requested whole-set review. Track unread or inaccessible sources as coverage limits, and bound conclusions accordingly. A missing future document is not a defect merely because the hierarchy permits it.
   Flag a product document that is a placeholder rather than a draft; its material belongs in [feature notes](../guides/product-documentation-process.md#feature-notes). When a feature directory in scope has `notes.md`, flag each section whose target document already exists as stale.
2. **Read the governing contracts before judging.** For each represented role, read its linked contract: [product vision](../guides/product-documentation-process.md#product-vision), [system architecture](../guides/product-documentation-process.md#system-architecture), [roadmap](../guides/product-documentation-process.md#roadmap), [PRD](../guides/product-documentation-process.md#feature-product-requirements-document), [feature system design](../guides/product-documentation-process.md#feature-system-design), [TDD](../guides/product-documentation-process.md#technical-design-document), or [implementation plan](../guides/product-documentation-process.md#implementation-plan). These reads are mandatory for represented roles, not optional background. Before assessing technical documents, read [technical-writing standards](../guides/technical-writing-standards.md) and apply them only at the boundary their document owns. Use the same shared guidance as drafting, not a private replacement rubric or prior review verdict. If guidance conflicts or authority is unresolved, report the exact conflict rather than inventing precedence.
3. **Derive a temporary relationship map.** Identify the owning sources for material requirements, decisions, terms, and shared contracts; the documents that refine or consume them; and the acceptance, tasks, and handoff states they reach. Keep this map as review evidence, not a new maintained source of truth. Trace actual project goals and constraints, not generic best practices or illustrative playbook requirements.
4. **Check lanes and levels of detail.** Compare each document's responsibilities and detail with its owning contract. Flag decisions in the wrong home, missing shared rules that consumers must independently re-decide, and detail that displaces its rightful owner. Name that owner and the boundary information or reference to retain. Less detail is not automatically better: consumers still need actionable constraints. A local role violation supported by one document and its contract remains in scope even if a specialist could also find it; do not rerun every specialist's local completeness or feasibility checklist.
   When assessing whether shared design or slice boundaries belong in the hierarchy, read [when a feature needs slices](../guides/product-documentation-process.md#when-a-feature-needs-slices).
   When assessing whether a minor change needs new documents or can remain in an existing owner, read [lightweight path for minor changes](../guides/product-documentation-process.md#lightweight-path-for-minor-changes).
5. **Check repetition and authority.** Compare occurrences of the same obligation within and across documents. Distinguish competing normative copies from legitimate refinement, inherited constraints, identifiers, examples, diagrams, and labeled linked context. Preserve conditions, exceptions, and behavior-defining examples. Retain the authoritative rule and replace only competing wording with a reference and necessary context; never demand copied child requirements merely to prove inheritance.
6. **Check consistency under matching conditions.** Compare applicable behavior, terminology, assumptions, statuses, and boundary guarantees. Distinguish contradictions from different scopes, valid exceptions, proposals, and explicitly historical material. Do not choose authority by repetition, recency alone, or the amount of detail. When status, an exception, or a changed decision affects the comparison, read [decisions](../guides/product-documentation-process.md#decisions). For roadmap entries, assess only their relationship to specifications and status: loose ideas are not commitments, but migrated requirements must not remain competing rules.
7. **Check composition and traceability.** Follow obligations from product direction through the applicable requirements, shared design, local contracts, acceptance, and tasks; trace material downstream commitments back to an owning requirement or explicit design decision. Find lost obligations, unauthorized scope, unowned decisions, and incompatible sibling handoffs. Do not require every vision aspiration to have a current feature, every design choice to repeat a product requirement, or unfinished design work to have a plan. When tracing acceptance or verification, read [behavioral acceptance](../guides/product-documentation-process.md#behavioral-acceptance) and [technical contracts and verification](../guides/product-documentation-process.md#technical-contracts-and-verification).
8. **Exercise representative paths through the documents.** Select high-consequence flows or changes grounded in the project's obligations, including failure or interruption where applicable. Follow what a downstream designer, planner, or implementer must find, obey, produce, and hand off. Compare producer exit states with consumer entry assumptions and identify where the combined set forces an unsupported decision even if no two sentences directly contradict. Report which paths were traced; representative scenarios do not imply exhaustive behavioral coverage.
9. **Check context usability.** Determine whether readers can discover the applicable owner, resolve references, interpret terms consistently, and distinguish settled rules from proposals, examples, and obsolete instructions. Demonstrate the specific competing interpretations, missing authority, or broken navigation and the downstream decision affected; do not assert merely that wording will confuse a model. Distinguish document evidence from supplied observations of model behavior. Do not claim improved model reliability without downstream execution evidence, and do not execute agents or tests as part of this read-only review.
10. **Validate corrections against guidance.** Every proposed correction must obey the destination document's purpose, exclusions, level, and applicable writing rules. Fix unclear boundaries by retaining the required state, owner, and outcome and referencing the mechanism's owner, not by importing forbidden detail. When a PRD and a design disagree only about mechanism, correct the design, or remove the mechanism from the PRD under its altitude test; never propose copying a design's mechanism, revision, or verification status into the PRD. Preserve project intent and accepted exceptions. Do not resolve product choices, override shared guidance, or redesign documents to match a personal preference.
11. **Report supported defects and honest coverage.** Use canonical IDs and severities; give all implicated locations, governing evidence, consequence, and the smallest complete compliant correction. For omissions, name the obligation and material inspected. Merge only the same underlying defect and correction. Keep unresolved questions and evidence gaps separate; zero supported findings is valid. Do not edit, implement, dispose of feedback, imply approval, or certify the entire set from a limited pass.

## Output

Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules).

Return the [shared fixed Markdown document-review report](../guides/document-review.md#report) in your final message. Identify the document set and every inspected member's exact revision or unambiguous candidate label rather than inventing a single revision for mixed inputs. In Coverage, include the derived relationship map, governing sources read, and paths traced; state what was checked or limited for each of lanes, level of detail, repetition, consistency, composition, and context usability within the review mode's scope. No findings in one dimension is not proof about unread material. For each finding, include all implicated locations and the smallest complete correction that preserves each document's contract; for questions and coverage limits, identify precisely which comparisons they prevent. Do not imply acceptance.
