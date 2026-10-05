---
state: active
approved: 2026-09-30
---

# Roadmap

<!-- What goes in each section, and how items move between them: see "Roadmap" in the Software Factory playbook's guides/product-documentation-process.md. -->

## Status

This roadmap records current priorities and later opportunities. Developer approval activates it; record the actual approval date in frontmatter when that occurs.

## Now

## Next

- **Pinned read-only install.** Consumers need confidence that an immutable, pinned Playbook copy works with `--no-extensions --extension <copy>/omp-extension.ts` in a sandbox that denies writes to the copy: agents, skills, and every tool must load. Python checkers must not write into the install, including `__pycache__`, and nothing may assume the checkout is writable or is the working repository.
- **Plan progress reporting.** A supervising tool cannot reliably show task progress if it must parse the run ledger. A harness-neutral contract would let the execution owner report each task's state as execution proceeds.
- **Document-status migration.** Older repository documents lack the status frontmatter needed to establish their authority. A guided migration would let an agent propose state, revision, and acceptance date from evidence for the developer to confirm.

## Later

- **Repositories that aren't products.** Repositories holding no product documents need a way to declare that scope so agents do not propose product documents there. This opportunity remains pending the developer's decision.
- Per-finding review reporting: a tool through which reviewers publish each finding’s ID, severity and location so a supervising tool can track responses to individual findings; designed when such a consumer defines its need.
- **Worker context packets.** Workers in a plan run explore the same code independently and guess the same missing paths, spending tokens the orchestrator already spent. The orchestrator could hand each worker the exact files, interfaces, and excerpts its task needs. Needs evidence first: measure repeated exploration and wasted reads across real plan runs before designing it.
- **Feature record.** Once a feature is done, its system design, technical designs, and implementation plans have served their purpose. One shorter record of what still matters could replace them: decisions and their reasons, contracts still in force, deviations from plan, and known limitations or issues. Git history keeps the originals, and facts that outlive the feature move to the living documents that own them.

## Done
