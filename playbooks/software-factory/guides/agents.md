# Agents and skills

An agent and its skill have separate jobs. Keep their instructions distinct so they cannot compete or drift.

## Agent contract

Agent frontmatter holds routing and runtime configuration: the name, description, model, tools, `read-summarize: false` (so `read` returns verbatim file content rather than structural summaries; every playbook agent cites exact text), optional `spawns`, and `autoloadSkills`. Review report delivery follows [Review report delivery](#review-report-delivery).

The body contains only these elements, in this order:

1. One sentence that defines the agent's scope.
2. The standard pointer to the skill.
3. Boundaries that the tool list cannot enforce, such as write scope, authority, and trust.
4. The standard completion pointer.
5. The standard fallback for an unreadable skill.

Do not restate restrictions already enforced by the tool list. An agent may repeat a statement from its skill only when that statement is true in every branch of the skill.

### Description contract

Write the agent frontmatter `description` as one double-quoted physical line of at most 400 characters. Use third person: say what the agent produces, then `Use when` in the developer's phrasing and `Not for` with its nearest sibling task or agents; a family reference such as “the other review-doc-* agents” is acceptable. Follow the skill source's Purpose, rather than describing only a first draft. Add `Read-only.` for a read-only agent. Do not use `MUST`, `ALWAYS`, `NEVER`, or `CRITICAL` as whole words in the description; soft routing language avoids over-triggering. Do not use OMP's standalone magic keywords (`orchestrate`, `ultrathink`, `workflowz`, `jevify`) as bare words in a description or routing case; they change the calling session's behavior for that turn.

For example: `"Reviews one feature PRD's requirements, acceptance intent, and scope against the playbook contract. Use when a developer asks to review or check a PRD before technical design. Not for drafting (draft-prd-agent) or reviewing other document types (the other review-doc-* agents). Read-only."`

### Routing cases

Keep developer-phrased routing examples in `agents/routing-cases.json`, keyed by agent name. Each entry has `positive` request strings and `negative` objects whose `expected` value names another agent or is `null` when no playbook agent should handle the request. For example:

```json
{
  "review-doc-prd-agent": {
    "positive": [
      "Review the PRD in docs/features/export/prd.md",
      "Check whether the export feature's requirements doc is ready for technical design",
      "Independent review of our PRD before we start the TDD"
    ],
    "negative": [
      {"request": "Review the product vision doc", "expected": "review-doc-product-vision-agent"},
      {"request": "Write a PRD for document export", "expected": "draft-prd-agent"},
      {"request": "Fix the failing export test", "expected": null}
    ]
  }
}
```

Each agent needs at least three positives and two negatives. A negative must not expect its own agent; all non-null expectations name an existing agent. No request contains an agent name, and positive requests are unique across agents. Use the guides' `EXPORT` example when an illustrative feature is needed.

Each `review-doc-*` agent needs a negative routed to another `review-doc-*` document type and, where one exists, its matching `draft-*` agent; `review-doc-coherence` instead uses any draft agent. Each `draft-*` agent needs a negative for its reviewer. Each `review-code-*` agent needs negatives distinguishing its scope from at least one language or integration reviewer and at least one focused reviewer; a focused reviewer also distinguishes its standard from another focused standard. `orchestrate-*` needs `draft-implementation-plan-agent`, and draft-skill and review-skill need each other. Treat a description change as a routing behavior change and update its cases with the source.

## Skill contract

The skill owns everything else: the procedure, every conditional instruction, the output contract, and the definition of done. Conditional decisions belong only in the skill, including when to research, delegate, write, or stop early.

### Developer communication and escalation

Before any top-level developer-facing message or escalation, read and apply the [communication rules](communication-policy.md#rules), including their developer-request procedure. Drafting and orchestration skills use that shared procedure rather than local question templates. A caller receiving a review report owns escalation: in the factory workflow, this is the main-session orchestrator, not the drafter or reviewer. Resolve repository-answerable questions before validating and rendering any remaining developer request under the shared policy. Document-review decisions follow [Review loop](document-review.md#review-loop). Review agents return questions in their report; they never contact the developer directly.

## Reading reviewer reports

This rule governs callers receiving a review, not their own final-answer format. Reviewers return Markdown; read its Findings section by stable finding ID, and its Questions and Coverage limits sections before deciding a response. The preview caps at 5,000 characters; `agent://<id>` holds the full report. If truncated, retrieve it with `read` before acting on findings, counts, questions, or coverage. Omit reviewer `outputSchema` and dispatch from a schema-free caller session to avoid inherited validation.

For document reviews, the harness records reports into the review ledger automatically; the caller must still read the full report before deciding any finding. The caller's triage through `review_ledger decide` and the drafter's application of accepted findings follow [Review loop](document-review.md#review-loop).

## Review report delivery

Open the report with one sentence stating its outcome: how many supported findings it has, the most severe one with its ID, and what it blocks; for zero findings, say so and name the most important coverage limit. Then return the complete Markdown sections from the owning [document](document-review.md#report), [code](code-review.md#report), [skill](skill-authoring.md#report-without-editing), or [friction](friction.md#report) contract as final text, without JSON or fences. Schema-free OMP accepts prose. If runtime requires terminal `yield`, write the report, then call `yield` with `type: "result"` and no `data` to capture it. Omit agent `output` and invocation `outputSchema`; the caller session must lack a schema, since OMP inherits it.

## Build check

`scripts/build-skills.py --check` validates the agent-to-skill relationship, matching names, the standard body lines, obsolete completion wording, reviewer tool restrictions, `verbatim-read`, `description-contract`, and `routing-cases`; it also rejects an `output` frontmatter key in any Playbook agent. The exact standard sentences and check rule names are defined in `scripts/build-skills.py`; do not copy their wording into this guide.

All rules apply by default. To make an exception, add the affected skill to `skillsWithoutAgents` or add the rule under the affected agent in `exemptions` in `agents/checks.json`. Every exception must have a non-empty reason. The check rejects exceptions that name an unknown skill, agent, or rule.
