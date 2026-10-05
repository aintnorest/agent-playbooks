---
state: draft
revision: vision-r8
---

# Product vision: Software Factory

## Status

Revised to keep only what is specific to building software. Direction shared by every playbook — the target developer, the general problems, the principles, the boundaries, the general success signals, and the shared constraints — lives in the repository's product vision at `docs/product-vision.md`, and applies here without being repeated.

## Vision

The Software Factory playbook works as a software factory. The developer's decisions go in, and verified software, built by agents, comes out. The developer takes part only at defined points where human judgment is required. The aim is as few of those touchpoints as possible, without losing quality or the developer's control over direction.

To get there, the Playbook explains what documents a software project should have, what each document should contain, and the processes needed to grow and improve the project with AI without slop. It should also be able to improve itself over time.

## Target users and underlying problems

The Playbook serves the repository vision's developer when they direct AI coding agents on software projects.

The underlying problems specific to software:

- **AI writes code faster than anyone can review it.** Generic guardrails cannot catch everything one project needs, so code can move away from what the developer intended before anyone notices.
- **Shortcuts compound.** Slop and hardcoding get a lot done quickly. They also make everything downstream harder at a growing rate, until the project can no longer grow.
- **Wasteful tooling undermines the playbook.** The Playbook is a playbook first, but it runs on OMP. Slow, unreliable, or wasteful use of the harness, such as spending tokens that add nothing to the work, costs time and money and keeps the Playbook from fulfilling its purpose.

## Product principles

The repository vision's principles apply unchanged. In software, intent is the product the developer intends, so decisions are weighed by product fit first and maintainability second; maintainability is what keeps a project able to grow.

## Product-wide boundaries and non-goals

The Playbook helps build software projects with AI. A project must first deliver value to its users in the way the developer intended. It should also be quality work, and it should cost no more time or money than the developer is willing to spend. The Playbook's core is the documents, processes, agents, and checks that serve those ends. OMP extensions and tools that make this work cheaper or more reliable are in scope even though they are not the core, for example keeping the prompt cache warm to cut token use.

## Durable success signals

- Projects built with the Playbook keep delivering what the developer intended as they grow, and they stay able to grow.
- Most slop that gets past the checks is caught in review rather than in use.
- Playbook work spends less time and fewer tokens as its OMP tools and extensions improve, without the quality of the work dropping.

## Constraints every feature must preserve

- **Agent acceptance rests on evidence.** Agents accept technical designs and implementation plans only on evidence that their review loop has concluded and their checks passed. No feature may activate a document or start work while its required developer approval or agent acceptance is missing, and a default, timeout, cancellation, or redirect is never evidence of agent acceptance.
- **The versioned contracts include** document formats, frontmatter, plan grammar, checker modes, and tool and request schemas.
