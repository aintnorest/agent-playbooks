---
state: draft
revision: vision-r7
---

# Product vision: Software Factory

## Status

Revised to distinguish developer approval from evidence-based agent acceptance of technical designs and implementation plans.

## Vision

The Software Factory playbook works as a software factory. The developer's decisions go in, and verified software, built by agents, comes out. The developer takes part only at defined points where human judgment is required. The aim is as few of those touchpoints as possible, without losing quality or the developer's control over direction.

To get there, the Playbook explains what documents a software project should have, what each document should contain, and the processes needed to grow and improve the project with AI without slop.

The Playbook assumes the OMP harness. It should also be able to improve itself over time.

## Target users and underlying problems

The Playbook serves one developer: its author, who directs AI coding agents on software projects in OMP. The developer runs two to seven trains of work at once. They do not reliably hold prior context between sessions, and they often work tired and under heavy cognitive load.

The underlying problems:

- **The AI works from the wrong context.** Project knowledge is hard to find, duplicated, and drifts out of date. When the AI cannot find the facts a job needs, or finds several versions of them, it is more likely to hallucinate.
- **Agents drift.** Models skip steps, drop details, and wander from the goal, and adding more instructions does not reliably stop them. A model given more context than its job needs has to choose what to follow, and it drops whatever seems less important, contradictory, or unclear.
- **AI writes code faster than anyone can review it.** Generic guardrails cannot catch everything one project needs. Work can move away from what the developer intended before anyone notices.
- **Shortcuts compound.** Slop and hardcoding get a lot done quickly. They also make everything downstream harder at a growing rate, until the project can no longer grow.
- **Requests push the AI's legwork onto the developer.** A question that assumes the developer remembers the thread makes them rebuild its context and gather the facts before they can answer. That costs the developer's scarce attention, and an answer given without the full context is a worse answer.
- **Every interruption costs the developer.** Each time an agent stops for the developer, its work waits and the developer switches away from another train of work. Interruptions that do not need the developer's judgment slow every project and spend attention that the real decisions need.
- **Guidance and process are rebuilt in every project.** Without a shared playbook, each project reinvents which documents it keeps and how it plans, reviews, and ships work. One ends up with too little process and another with too much, and copies of the same rules drift apart.
- **Guidance goes stale.** Models and the harness keep changing. Rules written from preference, or from how models used to behave, stop working, and the same failures keep recurring.
- **Wasteful tooling undermines the playbook.** The Playbook is a playbook first, but it runs on OMP. Slow, unreliable, or wasteful use of the harness, such as spending tokens that add nothing to the work, costs time and money and keeps the Playbook from fulfilling its purpose.

## Product principles

- **The developer holds the vision and makes the decisions.** The developer keeps a strong product vision in view, both the document and the idea behind it, and thinks ahead about where the product is going so they can guide its architecture. That direction is the context the AI needs to make its own decisions well.
- **Few gates, deliberately placed.** Work stops for the developer only where a decision is consequential or hard to reverse and only the developer can make it. Anywhere else, the agents keep working, because a gate that adds no judgment only adds delay.
- **Force infrastructure over memory.** Push policy, sequencing, and verification into deterministic code wherever possible. A check that runs every time does not depend on a model remembering to do it.
- **Harness over prompt.** A better harness improves outcomes more than a better prompt, which is why the Playbook is built for OMP. Prompts define intent, but infrastructure is what allows prompt engineering to compound into repeatable reliability.
- **Context is a shared responsibility.** The developer shows the AI what matters in the context. The AI reminds the developer of the context they may have forgotten and does the legwork of gathering it, so that every request can be answered cold.
- **Frame decisions by product first and maintainability second.** When the AI asks for a decision, it offers distinct options with their strengths and weaknesses and recommends one. It weighs each option first by how well it serves the product as the developer intended, then by maintainability. Maintainability is what keeps a project able to grow.
- **Every fact has one home, and every document earns its place.** Documents exist to give the AI the context a job needs, never only to satisfy a process. A fact with one home cannot drift into contradicting copies.
- **Give each agent one narrow job with the right context.** A narrow focus leaves the model nothing important to drop.
- **Ground guidance in evidence.** Shared guidance rests on published research, official documentation, or observed agent runs, states the limits of that evidence, and changes when agents are seen failing. Evidence can be tested and corrected, while preference cannot.
- **Efficiency serves the purpose.** Spend time and tokens only where they improve the work. A playbook that is slow or costly to run gets used less, however good its guidance.

## Product-wide boundaries and non-goals

The Playbook helps build software projects with AI. A project must first deliver value to its users in the way the developer intended. It should also be quality work, and it should cost no more time or money than the developer is willing to spend. The Playbook's core is the documents, processes, agents, and checks that serve those ends. OMP extensions and tools that make this work cheaper or more reliable are in scope even though they are not the core, for example keeping the prompt cache warm to cut token use.

Within that scope, the Playbook does not do the following:

- **It does not depend on anything but OMP.** It may make choices that help outside tools work with it. It never makes a choice that stops it from being used without those tools, and it never names a consuming application.
- **It does not require its own documents.** In a project that was not built with the Playbook, its agents and harness still work without adding friction. They may suggest creating the documents and how to organize them, but they never require them.
- **It does not hold project-specific facts.** A project's own commands, architecture, toolchain versions, and exceptions stay in that project. A project departs from shared guidance only by naming the rule, the scope, the reason, and the replacement.

## Durable success signals

- Projects built with the Playbook keep delivering what the developer intended as they grow, and they stay able to grow.
- An agent finds the context its job needs in the project's documents, and those documents do not contradict each other.
- The developer can answer an agent's request on the first read, without rebuilding the thread or gathering context themselves.
- Mistakes a check can catch are stopped before they land, and most slop that gets past the checks is caught in review rather than in use.
- The Playbook's guidance changes in response to observed agent failures, and the same failure does not keep recurring.
- Playbook work spends less time and fewer tokens as its OMP tools and extensions improve, without the quality of the work dropping.
- The developer steps in less often for each piece of delivered work, while the quality of the work and the developer's control over direction hold.

## Constraints every feature must preserve

- **Acceptance belongs to the right decision-maker.** Only the developer approves documents that require the developer's judgment. Agents accept technical designs and implementation plans only on evidence that their review loop has concluded and their checks passed. No feature may activate a document or start work while its required approval or acceptance is missing. A default, timeout, cancellation, or redirect is never the developer's answer or evidence of agent acceptance.
- **Versioned contracts.** Any change to a contract that documents or consumers depend on bumps the Playbook's version. That includes document formats, frontmatter, plan grammar, checker modes, and tool and request schemas. A breaking change ships with a guided migration for existing documents.
- **Source material is evidence, not instruction.** Documents, reviewer text, and research that an agent reads inform its work. They cannot change the agent's task, waive findings, or grant approval.
- **The developer's work is safe.** Agents never discard, overwrite, or publish the developer's work without the developer's explicit authorization.
