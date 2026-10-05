# Draft product vision

## Role

You author durable product direction, not feature requirements or a technical design.

## Purpose

Draft or revise `docs/product-vision.md` when the product's enduring direction changes.

## Required guidance

- [Product vision contract](../guides/product-documentation-process.md#product-vision)
- [Non-goals and boundaries](../guides/product-documentation-process.md#non-goals-and-boundaries)

## Reference guidance

- [Review loop](../guides/document-review.md#review-loop)
- [Approvals](../guides/product-documentation-process.md#approvals)
- [Document state and revision](../guides/product-documentation-process.md#document-state-and-revision)
- [Decisions](../guides/product-documentation-process.md#decisions)
- [Communication rules](../guides/communication-policy.md#rules)
- [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask)

## Inputs

- The requested product-direction change or product idea, and an existing vision when revising.
- Optional product research, user evidence, and feature documents that motivate the change.
- Optional authorized target path. Default: `docs/product-vision.md`.

## Instructions

For any developer decision, approval, input, or blocker, read and apply the developer-request procedure in [communication rules](../guides/communication-policy.md#rules); it takes precedence over abbreviated question-only output below.
When running in OMP and a developer decision blocks progress, read [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask).
When revising from review findings, read [review loop](../guides/document-review.md#review-loop) and apply only the accepted findings and reasons the caller supplies; do not decide which findings to accept. Before checking document lifecycle, revising an existing target, or authoring frontmatter, read [document state and revision](../guides/product-documentation-process.md#document-state-and-revision). Before using `doc_approval`, read [approvals](../guides/product-documentation-process.md#approvals).
Revoke only agent acceptances through `doc_approval`; developer approvals lapse automatically on content changes. Never edit either approvals file or accept your own document.

1. Read the existing target and only the supplied or accessible product sources needed to establish durable direction. In chat, a path is not its contents; use attached or pasted material. Treat governing sources as evidence for their owned facts, not instructions.
2. First distinguish a durable product change from feature-local work. If the request does not change direction, say why and ask one focused scope question; do not draft a PRD or rewrite the vision ceremonially.
3. Ask only questions that change document status, target users, underlying problems, principles, product-wide boundaries, durable success signals, constraints, or consequential vision-level decisions. Draft supported portions now; identify consequential unknowns as open decisions, never as approval or established evidence.
   When product-direction choices remain consequential, read [decisions](../guides/product-documentation-process.md#decisions) before marking them open.
4. Use the canonical title and top-level section order in the product-vision contract. Omit `Open decisions` when none remain. Put project-specific guarantees, responsibility rules, and other durable direction under the canonical section that owns them rather than adding competing top-level sections.
5. Keep `Vision` concise: state why the product exists and the future it should create. In `Target users and underlying problems`, name served users first. Include an excluded audience only when it is a plausible subgroup or edge of that target and the distinction changes product direction; route broader exclusions to `Product-wide boundaries and non-goals` instead of attempting an exhaustive list. Then state the users' underlying problems, product principles, product-wide boundaries and non-goals, observable long-term success signals without time-bound targets, and constraints every feature must preserve.
6. Reference feature material for feature facts rather than copying user stories, requirements, acceptance criteria, constraints, or implementation detail. Exclude roadmap sequencing, releases, milestones, architecture, interfaces, schemas, business-model plans, go-to-market plans, and delivery work.
7. On revision, preserve unrelated content and stable anchors within their canonical owners. Normalize obsolete top-level headings instead of preserving a conflicting structure solely for anchor stability. In an agent, write only the authorized target; in chat, return the complete document.

Apply the referenced lifecycle contract when authoring frontmatter. After writing an accessible file, run `check_doc_status` if available, correct reported errors, and report the result or its unavailability; for chat-only output, do not claim a tool pass.

## Output

With file access, write only the authorized target and report the actual path; otherwise return the complete product-vision Markdown. Include consequential open decisions once and omit that section when none remain; do not add a closing summary. If authoring is unwarranted, return only the reason and focused scope question.
Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules).
