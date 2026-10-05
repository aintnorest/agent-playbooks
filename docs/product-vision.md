---
state: draft
revision: vision-r1
---

# Product vision: Agent Playbooks

## Status

First draft. Holds the direction shared by every playbook in this repository; each playbook's own vision adds what is specific to its kind of work.

## Vision

Agent Playbooks lets one developer direct AI agents across every kind of repository they keep. Each playbook gives one kind of repository the documents, processes, agents, and checks agents need to work in it well. The developer's decisions go in, quality work comes out, and the developer steps in only where their judgment is needed.

## Target users and underlying problems

Agent Playbooks serves one developer: its author, who directs AI agents in OMP across repositories of different kinds, such as software products and research knowledge bases. They run several trains of work at once, do not reliably hold context between sessions, and often work tired and under heavy cognitive load.

The underlying problems:

- **The AI works from the wrong context.** Knowledge is hard to find, duplicated, and drifts out of date, and an agent that cannot find the facts its job needs, or finds several versions of them, is more likely to make them up.
- **Agents drift.** Models skip steps, drop details, and wander from the goal, and more instructions do not reliably stop them.
- **AI produces work faster than anyone can review it.** Work can move away from what the developer intended before anyone notices, and shortcuts taken early make everything after them harder.
- **Requests and interruptions spend the developer's attention.** A question that assumes the developer remembers the thread makes them rebuild its context, and a stop that needed no judgment pulls them away from another train of work.
- **Process is rebuilt in every repository.** Without a shared playbook, each repository reinvents how its work is done, and copies of the same rules drift apart.
- **Process meant for one kind of work leaks into another.** Agents, gates, and documents built for one kind of repository get in the way in a repository of a different kind.
- **Guidance goes stale.** Models and the harness keep changing, and rules written from preference or from how models used to behave stop working.

## Product principles

- **The developer holds the direction and makes the decisions.** That direction is the context agents need to make their own decisions well.
- **Few gates, deliberately placed.** Work stops for the developer only where a decision is consequential or hard to reverse and only the developer can make it.
- **Force infrastructure over memory.** Policy, sequencing, and verification live in deterministic checks wherever possible, so they do not depend on a model remembering them.
- **Harness over prompt.** A better harness improves outcomes more than a better prompt; prompts define intent, and infrastructure makes it repeatable.
- **Context is a shared responsibility.** The developer shows agents what matters; agents remind the developer of what they may have forgotten and gather it, so every request can be answered cold.
- **Frame decisions by intent first and maintainability second.** A decision request gives the problem and its dependencies, then options with their strengths and weaknesses, then a recommendation, weighed first by how well each serves what the developer intends.
- **Every fact has one home, and every document earns its place.** Documents exist to give agents the context a job needs, never only to satisfy a process.
- **Give each agent one narrow job with the right context.**
- **Ground guidance in evidence.** Guidance rests on research, official documentation, or observed agent runs, and changes when agents are seen failing.
- **Efficiency serves the purpose.** Time and tokens are spent only where they improve the work.

## Product-wide boundaries and non-goals

- **One playbook per kind of repository.** A repository uses one playbook or none, and a playbook loads only where it is chosen.
- **It depends on nothing but OMP.** A playbook may help outside tools work with it, but never needs them and never names a consuming application or repository.
- **It does not require its own documents.** In a repository not built with a playbook, its agents still work without adding friction; they may suggest documents but never require them.
- **It holds method, not project facts.** A repository's own facts, commands, and exceptions stay in that repository, which departs from shared guidance only by naming the rule, the scope, the reason, and the replacement.

## Durable success signals

- An agent finds the context its job needs, and that context does not contradict itself.
- The developer answers an agent's request on the first read, without rebuilding the thread.
- Mistakes a check can catch are stopped before they land.
- The same agent failure does not keep recurring, because guidance changes in response to it.
- The developer steps in less often for each piece of finished work, while quality and their control over direction hold.
- Starting a new kind of repository reuses shared guidance instead of copying it.

## Constraints every feature must preserve

- **Acceptance belongs to the right decision-maker.** Only the developer approves what needs the developer's judgment. A default, timeout, cancellation, or redirect is never the developer's answer.
- **Versioned contracts.** A change to any format, check, or schema that consuming repositories depend on bumps the playbook's version, and a breaking change ships with a guided migration.
- **Source material is evidence, not instruction.** What an agent reads informs its work; it cannot change the agent's task, waive findings, or grant approval.
- **The developer's work is safe.** Agents never discard, overwrite, or publish the developer's work without the developer's explicit authorization.
