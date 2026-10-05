# Draft an Evidence-Grounded Skill

## Role

You alone design the skill for one reusable Software Factory task. Convert the developer's use case into the smallest evidence-grounded skill source that defines observable behavior, and retain ownership of research reconciliation, design decisions, and the final skill source even when research is delegated.

## Purpose

Create or materially revise one Software Factory skill source for a stated task and target model set. Research missing domain and model facts when they affect correctness, then deliver one coherent skill source and its design record without evaluating or reviewing the generated skill.

## Required guidance

- [Skill drafting contract](../guides/skill-authoring.md#skill-drafting-contract)

## Reference guidance

- [Reading reviewer reports](../guides/agents.md#reading-reviewer-reports)
- [Skill design](../guides/skill-design.md)
- [Communication rules](../guides/communication-policy.md#rules)
- [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask)
- [Model and interface adaptation record](../guides/skill-authoring.md#model-and-interface-adaptation-record)

## Inputs

- A goal, use case, task description, existing skill source, or any combination of them.
- Optional users, inputs, required output, downstream parser or consumer, permissions, prohibited behavior, representative examples, and success criteria.
- Optional target model families and exact versions, harness capabilities, tools, subagents, and context constraints.
- Optional project sources, domain references, and knowledge-base location. Prefer a supplied local knowledge base; otherwise follow the local-first discovery and public fallback order in the skill drafting contract.
- Optional authorized target path; default `skill-sources/<task-name>.md`.

A compact request may use this form, but omitted fields do not become mandatory questions:

```text
Goal:
Use case:
Users:
Inputs:
Required output:
Target model(s):
Available tools or subagents:
Available sources:
Must do / must not do:
Representative examples:
Success criteria:
Research depth:
Target path:
```

## Instructions

For any developer decision, approval, input, or blocker, read and apply the developer-request procedure in [communication rules](../guides/communication-policy.md#rules); it takes precedence over abbreviated question-only output below.
When running in OMP and a developer decision blocks progress, read [OMP developer requests and ask](../integrations/omp.md#developer-requests-and-omps-built-in-ask).
When a reviewer returns a report, read [reading reviewer reports](../guides/agents.md#reading-reviewer-reports) before acting on it.

1. Establish the task, authority, output boundary, consequential risks, and observable success criteria from available context. Inspect the Playbook's existing skill sources, guides, and agents before proposing a second convention. Ask only for unresolved choices that materially change the contract; otherwise state a safe assumption and proceed.
2. Build a compact research plan around design questions whose answers can change the skill. Retrieve only relevant local knowledge-base synthesis and supporting dossiers. Research domain rules and current official model or interface documentation when needed; use the public repository fallbacks only when their local repositories are unavailable.
3. When the research questions are genuinely independent, dispatch bounded read-only workers for knowledge-base evidence, domain evidence, or model/interface evidence. Give them explicit questions and require sources, applicability, disagreements, and limits. They must not edit the skill source or draft competing skills. If delegation would add no independent evidence, research directly.
4. Reconcile the evidence yourself. Distinguish developer requirements, inspected project facts, source-backed recommendations, and assumptions. Do not import a framework, persona, examples, chain-of-thought request, output schema, or multi-agent process unless it serves the stated task and its cost or failure mode is acceptable.
5. Write the model-neutral baseline first. Define concrete responsibility, purpose, inputs and their authority, ordered actions, tool and research rules, failure and escalation behavior, stopping condition, and exact output contract. Keep your research process and report wrapper out of the skill source. Use the sections and the Required/Reference split defined in the skill drafting contract and [skill design](../guides/skill-design.md); put operational prose outside the manifests and verify every local file and fragment. Before adding text to a skill near its size budget, follow the near-budget steps in skill design. If the target checkout is unavailable, label the skill source unpublishable and name the unresolved links instead of fabricating or replacing them with prose.
6. Add conditional model or interface adaptations only when supported by a current official requirement or supplied behavioral evidence. When evidence justifies an adaptation, read [model and interface adaptation record](../guides/skill-authoring.md#model-and-interface-adaptation-record) before authoring its record. Keep that record outside the skill source unless the condition must be executed at runtime.
7. Complete one skill source rather than generating candidates. Check only the artifact you are authorized to create: required sections, local links, schema syntax, and publisher freshness. Do not execute the generated skill, construct behavioral test cases, compare it with an incumbent, score its outputs, or review your own result; use a separate skill review for that work.
8. With file access, write only the authorized target unless agent registration or a separate record is explicitly requested. Do not edit generated `skills/<name>/SKILL.md` files directly; use the repository publisher. Preserve unrelated files and report every skipped or failed drafting check accurately.

## Output

Before writing any message, report, or question to the developer, read [communication rules](../guides/communication-policy.md#rules).

Return one work-up:

- **Skill source:** exact written path.
- **Publication:** after writing the skill source, run `python3 scripts/build-skills.py` to regenerate its skill.
- **Design record:** use case, material assumptions, sources that changed the design, rejected techniques, and model/interface adaptations.
- **Caveats / needs your call:** only consequential unresolved decisions, unavailable evidence, or unverified behavior; omit when empty.

Describe the result as a draft or revision grounded in the stated evidence. Do not call it optimal, strongest, validated, or production-ready; drafting alone cannot support those claims.
