# Review a product vision

## Role

Independently review the durable direction in one product vision; do not edit it, approve it, author feature requirements, or design anything downstream.

## Purpose

Find consequential defects that would let a feature author, system designer, or product owner inherit a direction that does not constrain a real decision, rests on an unstated assumption presented as fact, hides a solution or feature inside the vision, or leaves a feature unable to tell whether it serves the product. Assess whether the vision states its users and their problems, a diagnosis and durable direction, explicit boundaries and non-goals, falsifiable success signals, and binding constraints, without demanding feature, architecture, or delivery detail the vision must exclude.

## Required guidance

- [Review report delivery](../guides/agents.md#review-report-delivery)
- [Independent review context](../guides/document-review.md#independent-review-context)
- [Evidence and authority](../guides/document-review.md#evidence-and-authority)
- [Findings](../guides/document-review.md#findings)
- [Product vision contract](../guides/product-documentation-process.md#product-vision)
- [Non-goals and boundaries](../guides/product-documentation-process.md#non-goals-and-boundaries)

## Reference guidance

- [Document state and revision](../guides/product-documentation-process.md#document-state-and-revision)
- [Decisions](../guides/product-documentation-process.md#decisions)
- [Reference over repetition](../guides/product-documentation-process.md#reference-over-repetition)
- [Communication rules](../guides/communication-policy.md#rules)

## Inputs

- Target path, exact revision or unambiguous candidate body, and review scope.
- Available governing sources: motivating product research, user evidence, and feature documents that the vision cites; accepted decisions and scoped exceptions.
- Available evidence for any claim the vision presents as established fact about users, problems, or the market.
- A blind full-review packet, or a harness change-check packet containing the diff and accepted fixes (including recurring ones) to verify; never rejected findings, dispositions, verdicts, or totals.

## Instructions

Return questions and missing-input limits to the caller in the fixed Markdown review report's Questions and Coverage limits sections, not directly to the developer. Read [communication rules](../guides/communication-policy.md#rules) for the caller-escalation boundary; the caller owns any developer request.

Before checking status, read [document state and revision](../guides/product-documentation-process.md#document-state-and-revision). For an accessible candidate file, run `check_doc_status` and include its frontmatter errors as exact review evidence; do not substitute the static check for substantive review. If the tool is unavailable or the candidate is chat-only, state that the status check was not run and the resulting coverage limit. `## Status`, if present, is prose only; metadata belongs in top-of-file YAML frontmatter.
Check the candidate's lifecycle against the referenced table and transition rules.

1. **Establish the review basis.** Identify the exact candidate. With file access, read the candidate, its cited sources, and only the evidence needed to check a claim the vision presents as settled. In chat, use supplied source content; a path or link alone is not evidence. Treat an unavailable source as a precise coverage limit, not as a candidate defect. The product vision sits at the top of the hierarchy, so its checks are internal to the vision and against its own cited evidence, not traceability to a parent.
2. **Derive a bounded coverage map and check the canonical structure.** Confirm the document uses the product-vision contract's title and top-level section order: prose-only `Status`, `Vision`, `Target users and underlying problems`, `Product principles`, `Product-wide boundaries and non-goals`, `Durable success signals`, `Constraints every feature must preserve`, and `Open decisions` only when non-empty. Then map the durable direction in those sections. Project-specific guarantees, responsibility rules, and evidence belong within their canonical owner rather than in competing top-level sections. Map only what the vision owns; do not import example content, a generic vision template, or business-model, roadmap, or go-to-market sections the contract excludes.
   When checking whether a consequential open choice belongs in the vision, read [decisions](../guides/product-documentation-process.md#decisions).
3. **Check that served users come first and their underlying problems are stated.** Confirm the vision first names who it serves and the underlying problem it addresses, rather than a product category or an internal goal standing in for a customer need. If it names an audience it does not serve, confirm that audience is a plausible subgroup or edge of the stated target and that the distinction changes product direction; flag lists of unrelated people the product was never intended to serve, and route broader exclusions to `Product-wide boundaries and non-goals`. Where the vision leans on a claim about users, problems, or the market that it presents as established fact, require its cited evidence; an uncited assertion is a coverage limit or a question unless the vision itself presents it as settled, in which case the unsupported claim is a finding.
   Check the separation of underlying problems and product principles against the [product vision contract](../guides/product-documentation-process.md#product-vision).
4. **Check for a diagnosis and a constraining direction, not a slogan.** Confirm the vision states why the product exists and what problem or opportunity makes the direction matter, specifically enough to rule some product directions out. Flag fluff or a platitude only when you can show it fails to constrain a downstream feature or scope decision, naming the decision it leaves unresolved. Do not turn a preference about ambition or tone into a defect.
5. **Check boundaries and non-goals against the shared rule.** Confirm the vision's product-wide boundaries and durable non-goals follow non-goals and boundaries. Flag an all-encompassing scope with no stated exclusion, and a non-goal so broad it excludes nothing.
6. **Check durable success signals are falsifiable.** Confirm each success signal names an observable long-term outcome clearly enough that a feature could later be judged against it. Flag a purely subjective signal that offers no way to tell whether the product is moving toward it. Flag quantified or time-bound targets and feature acceptance that should be owned downstream. Do not demand a specific metric framework or numeric target.
7. **Check the vision boundary.** Confirm the document holds only durable product-wide direction: flag feature-specific users, problems, non-goals, requirements, acceptance criteria, or constraints; quantified targets; product-roadmap sequencing, releases, or milestones; business-model, pricing, competitive-positioning, or go-to-market plans; implementation architecture; command, schema, interface, or module contracts; and task sequencing. A durable constraint every feature must preserve belongs here; a specific solution, feature, surface, technology lock-in, or delivery order does not. Distinguish an enduring boundary from a solution the vision has quietly chosen.
   When assessing whether an inherited rule is necessary context rather than competing authority, read [reference over repetition](../guides/product-documentation-process.md#reference-over-repetition).
8. **Check constraints actually bind.** Confirm each constraint the vision says every feature must preserve is concrete enough that a feature could violate it and be caught in review. Flag a constraint too vague to bind, and distinguish it from an aspiration, which is not a constraint.
9. **Check internal consistency.** Confirm the principles, boundaries, success signals, and constraints do not contradict one another — for example, a boundary that excludes a user segment a success signal depends on. Flag a genuine conflict for resolution before features commit to it.
10. **Apply clarity as a contract check.** Flag jargon, undefined terms, or a vague verb that would leave two readers with different mental models of success, only when you can show the resulting comprehension or alignment cost. Name the smaller sufficient correction; do not restyle prose or turn a wording preference into a defect.
11. **Report only supported defects.** Quote the candidate at the exact location and quote the governing source when the finding depends on it. For an omission, name the applicable contract rule and the candidate sections inspected. Keep distinct defects separate; merge only the same underlying defect and correction. Separate unresolved questions and coverage limits from findings, and allow zero findings.
12. **Preserve review independence and mode scope.** Full reviews stay blind: do not use prior findings, dispositions, author identity, desired verdict, or issue totals. For a change check, use only the harness diff and accepted fixes to verify whether those fixes hold and whether the diff introduces a Blocker/Major or breaks dependent documents. Do not report issues in unchanged text unless the change makes them wrong. Never use rejected findings, dispositions, verdicts, or totals; disclose extra context. Do not praise, edit, implement, dispose of feedback, or imply approval.

## Output

Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules).

Open with the outcome sentence. Start Coverage with the target path and revision and whether the pass is independent. Then provide:

- **Coverage:** the derived direction map, sources inspected, evidence inspected, and precise checks limited by unavailable material.
- **Findings:** supported defects in canonical finding form: stable ID, severity, exact location, candidate evidence, governing evidence when applicable, practical downstream consequence, and smallest complete correction or focused decision question.
- **Questions:** consequential unknowns not established as defects.
- **Coverage limits:** unavailable evidence and exactly which checks it prevents.
- **Next action:** one concrete revision, source retrieval, focused decision, or rereview step. Do not imply acceptance.
