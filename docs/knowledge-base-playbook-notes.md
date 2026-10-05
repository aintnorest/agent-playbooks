# Knowledge-base playbook notes

These are working notes, not an approved design. They cover how a `knowledge-base` playbook would work, based on the first consuming repository, `knowledge-base-intelligent-systems`. Repository facts and counts were measured read-only on 2026-10-04. **Proposal** marks a recommendation. **[INFERENCE]** marks a claim that was not directly observed.

## What the knowledge base is today

**Two-layer zettelkasten.**

- `dossiers/` holds one study note per source.
- `vault/` holds atomic, reusable ideas. Each idea page must be understandable on its own and cite dossiers as evidence.
- `archive/` holds the raw sources and never changes; `inbox/` is the drop zone.
- `index.md` is the table of contents.
- `log.md` is the authoritative source registry and append-only history.
- `archive/index.md` is the manifest of archived files.
- `TAXONOMY.md` is the controlled tag vocabulary.
- Every page carries OKF metadata.

**Scale.** 432 dossiers, 262 vault pages, 430 `**Ingest**` entries with unique source keys, 58 controlled tags, and 110 commits.

**Admission rule** (`README.md`, "What belongs here"). The knowledge base keeps ideas, mechanisms, tradeoffs, results, and first-hand experience. It keeps the *model* a product exposes, never its manual. The rule was added on 2026-09-28, after an audit found operational detail in 26 dossiers and vendor specifics in 13 vault pages. Every problem came from docs, blogs, or vendor posts; the papers were clean.

**Procedure.** `INGEST.md` covers one source per run:

- source-key precedence: `doi:`/`ssrn:`, then `arxiv:`, then `url:`, then `sha256:`
- an eligibility check against `log.md`
- a ten-step procedure
- a verification checklist

**How the work actually runs.** Most volume arrives in batches, not single ingests:

- 11 batches of 3 to 101 sources
- the batches of 99 and 101 used 13 to 14 workers each
- coordination pattern: thematic workers *propose* vault creations and updates, a coordinator merges the proposals (52 proposed creations became 20 notes), and writers own disjoint files; back-links are added centrally (`log.md:837-838`, `log.md:962`, `log.md:996`, `log.md:1024`)
- parallel branches without that pattern produced duplicate vault pages that later had to be merged (`log.md:595-597`, `log.md:695`)

**Other work types** recorded in Beads:

- research answers that ingest nothing: mining 1,036 OMP transcripts for friction classes, and verdicts on orchestrator-isolation approaches
- research that feeds an ingest batch, where the developer approves the source list
- repair of verified errors
- taxonomy promotions
- a repository-wide audit run as parallel batches with JSON verdicts (`local:/dossier-audit.md`)

## What the playbook owns and what stays in the knowledge base

The playbook serves more than one knowledge base, so it holds method only. Each knowledge base keeps its own facts.

There is already a second consumer, `knowledge-base-gaming`. It has the same layout and its own `INGEST.md`, `TAXONOMY.md`, and `RESEARCH.md`, with 34 dossiers and 186 vault pages. Its `INGEST.md` has diverged from this KB's copy: `diff` shows 37 differing lines. The gaming copy lacks the tagging section, the operational-content ineligibility rule, the model-not-manual dossier rule, the product-independent vault rules, and the matching verification check. In the other direction, only this KB's copy lacks the pointer to `RESEARCH.md`. A shared playbook exists to prevent this kind of drift.

| Playbook (`playbooks/knowledge-base/`) | Consuming knowledge base |
| --- | --- |
| The two-layer model: dossier and vault roles, the vault-cites-dossier rule | Its subject scope ("intelligent systems") |
| Source-key precedence and eligibility | `TAXONOMY.md`: tags, facets, watchlist, alias map |
| The model-not-manual admission rule | Departures from the playbook's conventions, each stating the rule, scope, reason, and replacement |
| Ingest, batch, review, audit, research, and taxonomy procedures | Its registry, index, manifest, and pages |
| The registry, index, and manifest *formats*, plus the checker | The OKF profile it uses, if that differs from the default |
| Default directory layout and metadata fields | |

**Proposal.**

- **Default layout.** The default is the current layout: `inbox/`, `archive/`, `dossiers/`, `vault/`, `index.md`, `log.md`, `archive/index.md`, `TAXONOMY.md`.
- **Departures.** A knowledge base that differs states each departure in its README, following the existing "departs only by naming the rule" principle.
- **`INGEST.md` cleanup.** The method in `INGEST.md` moves into the playbook. The knowledge base keeps only its own facts and a pointer to the playbook.

## Agents and skills

All names use the `kb-` prefix, as the repository architecture requires for new playbooks. Each entry gives the job, the evidence that the job recurs, and the boundary that separates it from the other agents.

| Agent | Job | Evidence it recurs | Boundary |
| --- | --- | --- | --- |
| `kb-ingest-agent` | Ingest exactly one source: eligibility, archive, dossier, 0–4 vault updates, index, registry, manifest, verification | `INGEST.md`; 110 single-ingest log sections | Never repairs earlier inconsistencies; it reports them |
| `kb-review-dossier-agent` (read-only) | Check one dossier against its source: faithful, complete on material findings, model not manual, numbers match the source | The omitted whole-rubric-judge finding in `anthropic-multi-agent-research` (Beads `kb-ml-ccq`); operational detail in 26 dossiers (2026-09-28 audit) | Reviews one dossier; edits nothing |
| `kb-review-vault-agent` (read-only) | Check one vault page: claims no wider than their cited evidence, numbers match the dossiers, product-independent body, one idea per page, no near-duplicate | A principle stated beyond its evidence (`multi-agent-orchestration`), a +18.0 vs +19.0 transcription error (`progressive-skill-disclosure`) (both `kb-ml-ccq`); vendor specifics in 13 vault bodies | Reviews one page; edits nothing |
| `kb-curate-taxonomy-agent` | Apply `TAXONOMY.md` governance: re-evaluate every 25–30 sources, promote watchlist tags at about 5 carriers, demote tags whose clusters never formed, retag, keep the alias map | 11 Taxonomy and 8 Taxonomy-gap log entries; 4 promotions; 26 watchlist candidates, several at the promotion bar | Changes tags and `TAXONOMY.md` only |
| `kb-research-agent` | Answer a question from the knowledge base first, then from verified external sources. Return verdicts with evidence strength and a candidate source list | Beads `kb-ml-u5m`, `kb-ml-arx`; downstream lookups from the software playbook's `draft-skill`/`review-skill` | Ingests nothing; candidate sources go to the developer for batch approval |
| `kb-audit-agent` (read-only) | Check a set of pages against one rule and return per-page JSON verdicts | The 2026-09-28 audit: 6 batches of about 43 dossiers, verdicts clean/update/delete | Finds problems; repairs are a separate step |

The main-session skill is **`kb-orchestrate-batch`**, with no agent, like `orchestrate-factory`. It runs a batch:

1. Select the sources and get developer approval of the list. This is the single gate.
2. Dispatch thematic ingest workers that write dossiers and *propose* vault changes.
3. Merge the proposals into one vault plan. Prefer updates over creations; drop near-duplicates.
4. Dispatch vault writers that own disjoint files.
5. Add back-links centrally.
6. Run the reviewers on a sample, plus on any page they flag.
7. Run the checker in diff mode.
8. Write one dated log section.

This turns the coordination pattern now kept only in log prose into a procedure. It also prevents the duplicate pages that parallel branches produced.

Repairs (fixing verified errors, applying audit verdicts) need no agent of their own at first. The orchestrating session dispatches a general worker using the reviewer's findings, which is how `kb-ml-ccq` was handled.

## Deterministic checker

**Proposal.** `playbooks/knowledge-base/scripts/check-kb.py` is standard-library Python, exposed as a `check_kb` tool. Its pattern copies `check_doc_status`: a domain program plus a thin tool wrapper.

It has two modes, because `INGEST.md` forbids repairing pre-existing inconsistencies during an ingest:

- **`check`** reports every violation in the repository. Use it for audits and maintenance.
- **`diff --base --head`** fails only on violations a commit range *introduces* or *touches*. It also rejects any modification or deletion under `archive/` other than appends to `archive/index.md`, and any non-append edit to `log.md`. It is the gate for ingest and batch work.

Checks, with what `check` mode would report against the knowledge base today:

| Check | Today |
| --- | --- |
| Metadata block exists and parses as YAML | 1 failure: `dossiers/openai-symphony-service-specification.md` (unquoted colon in `description`) |
| Required fields by type. Dossier: `type`, `title`, `description`, `source`, `tags`, `timestamp`; `resource` when known. Vault: `type`, `title`, `description`, `tags`, `timestamp` | 3 dossiers lack `source` (2 were reclassified from vault, 1 is local research) |
| Tags exist in the taxonomy, 3–6 per page, at most one genre tag, no reserved tags | 0 unknown tags, 0 count or genre violations; `quantization` is reserved but used once |
| Every bundle-relative link resolves; no `[[wikilinks]]` | 2 broken links (both in `log.md`, after the vault-to-dossier move); 50 wikilinks in 11 vault pages |
| Every dossier and vault page appears exactly once in `index.md` | Clean |
| Every dossier has an Ingest entry or a recorded exception; every Ingest entry has a dossier or a recorded removal | 3 dossiers without entries; 1 deliberate removal (`github-copilot-review-effort-levels`) |
| Source keys in `log.md` are unique and well-formed | Clean (430 unique; 4 line formats coexist) |
| Archive files match manifest rows | 17 unlisted entries (6 HTML captures, 10 `_files` directories, `.DS_Store`) |
| Every vault page has a Sources section linking at least one dossier | 7 failures: pages whose evidence is your own GSL work (see open decisions) |
| `inbox/` holds no source after a successful ingest | Clean |

Hooks: probably only one at first. It would block edits and deletes under `archive/` except appends to `archive/index.md`, mirroring the approval-file guard in the software playbook. As the repository architecture requires, the hook stays inactive unless the session repository carries the playbook's marker file. Everything else is enforced by the checker's diff mode, run by the ingest and batch procedures.

## Developer touchpoints

The few-gates principle carries over. Proposed gates:

- **Approval of a batch's source list.** This already happens; `kb-ml-o62` was a "user-approved batch".
- **Deleting a dossier or vault page.** Deletion is destructive, and the registry keeps the key anyway.
- **Policy changes:** admission rules, and taxonomy facets as opposed to individual tags.

Taxonomy promotions and demotions inside the stated governance thresholds need no gate. The curator records each decision with its reason, like the `llm-code-testing` memory in Beads.

## Relationship to other playbooks

- **Core.** Skills are authored with `draft-skill` and improved through `review-friction` and `review-skill`. The playbook calls `run_check` for verification and `request_developer` for the gates.
- **Software playbook.** Its `skill-authoring.md` defines how to look up knowledge-base evidence (lookup order, advisory-only use, search `index.md`/`vault/`/tags, never load the whole corpus). That read contract should be owned once, by this playbook or core, and linked from software. Its fallback URL `https://github.com/aintnorest/knowledge-base` does not match the KB's actual remote `aintnorest/knowledge-base-intelligent-systems`; fix it when the contract moves.
- **First-hand findings from your own projects.** Seven pages in this KB's `vault/` directory record what you learned building GSL (`aintnorest/gsl`, your Rust workflow engine), for example `gate-forced-parroting` and `two-layer-schema-governance`. They cite GSL decision records such as `docs/resume-prompt-decisions.md` V3b instead of dossiers, and they are absent from `log.md`. `professional-growth` is not involved: it only cites GSL as an accomplishment. The KB playbook needs a defined path for first-hand findings from any project; see open decision 1.

## Open decisions

1. **First-hand evidence.** The vault rule requires a dossier source, but the seven GSL pages record your own experiments.
   - *Option A:* the first-hand finding becomes a source document in `inbox/` and is ingested normally. It gets a dossier, a registry key, and an archive copy, and vault pages cite its dossier like any other. `knowledge-base-gaming/RESEARCH.md` already defines this path for original research ("Research does not write directly to `dossiers/` or `vault/`. It produces a research document in `inbox/`"). Every rule and check stays uniform.
   - *Option B:* allow vault pages with a `## Evidence (first-hand)` section instead of Sources. Less ceremony, but the checker needs a second rule and the registry stays incomplete.
   - *Recommendation:* A. It is the procedure your other KB already uses, and the admission rule already counts first-hand experience as in scope. `RESEARCH.md`'s method would become a playbook procedure shared by both KBs.
2. **Normalize the registry.** `log.md` has 4 Ingest line formats and 3 date inversions.
   - *Option A:* leave history alone. The checker accepts all historical formats and enforces only the current format on new lines.
   - *Option B:* run one normalization pass, logged as a repair.
   - *Recommendation:* A. The log is append-only, and rewriting history breaks that promise for no reader-visible gain.
3. **Archive captures.** Six HTML captures and their asset folders are not listed in the manifest. Should the manifest list every archived file, or only primary sources? *Recommendation:* list every primary file and treat `_files` folders as part of their HTML capture. That makes the check exact without adding 10 rows.
4. **PKM: decided 2026-10-04.** PKM gets its own playbook if built. Its layers are life facets and a journal, not source-backed synthesis. Anything both playbooks prove to need, such as inbox handling or metadata checks, moves to core.

## Clean-up noticed in the knowledge base

These are repository facts, not playbook design. Fix them when the playbook first runs there:

- `README.md` shows the layout under a `knowledge/` root with 12 vault files. The real root is the repository, with 262 vault pages.
- A literal directory `local:` holds `dossier-audit.md`. It is committed, apparently an unresolved `local://` write. Move or delete it.
- 10 dossiers lack `## Vault Ideas Extracted`, and 4 vault pages have no inbound link.
