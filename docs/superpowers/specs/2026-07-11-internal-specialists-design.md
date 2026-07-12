# Internal Specialists Design

## Goal

Install and expose only `search-agent` as a top-level Codex Skill while embedding a curated set of marketing and finance capabilities as controlled workflow specialists.

## Architecture

The full upstream repositories remain under `vendor/` as pinned source snapshots. Curated internal resources live under `specialists/` and are registered through a manifest. `SpecialistRouter` selects capabilities; `SpecialistExecutor` validates requests, invokes deterministic adapters, and returns typed artifacts. Internal specialists never bypass Source QA, Citation Audit, outline approval, or final integrity gates.

## Curated Scope

Marketing core:

- customer-research
- competitor-profiling
- product-marketing
- marketing-ideas
- marketing-plan
- pricing
- analytics
- ab-testing

Finance core:

- yfinance-data
- funda-data
- earnings-preview
- earnings-recap
- estimate-analysis
- company-valuation
- startup-analysis
- stock-liquidity

Other upstream capabilities remain discoverable in `vendor/` but are conditional and are not installed as top-level Codex Skills.

## Files And Responsibilities

- `specialists/catalog.json`: curated capability metadata, workflow nodes, artifact roles, adapter IDs, dependencies, and upstream provenance.
- `specialists/marketing/*/prompt.md`: curated internal method instructions without top-level Skill frontmatter.
- `specialists/finance/*/prompt.md`: curated internal finance method instructions without top-level Skill frontmatter.
- `specialists/vendor.lock.json`: upstream repositories, pinned revisions, licenses, and synchronization metadata.
- `lib/specialist_registry.py`: loads and validates the catalog and resolves internal resources.
- `lib/specialist_router.py`: deterministic node/domain routing using catalog triggers.
- `lib/specialist_executor.py`: validates requests and results, invokes registered adapters, and enforces evidence roles.
- `lib/specialist_adapters/`: focused executable adapters for local methods and structured finance data.
- `install.sh`: installs only `~/.codex/skills/search-agent`; it does not create top-level `marketing` or `finance` directories.

## Contracts

`SpecialistRequest` contains:

- `specialist_id`
- `topic`
- `decision`
- `frameworks`
- `clean_sources`
- `approved_claims`
- `node_id`

`SpecialistResult` contains:

- `specialist_id`
- `status`
- `notes`
- `claim_graph_patch`
- `evidence_gaps`
- `search_plan_patch`
- `method_references`

Allowed statuses are `completed`, `partial`, `setup_required`, and `blocked`.

## Evidence Rules

- Marketing methods have `method_reference` role and cannot support factual claims by themselves.
- Structured finance data must retain provider, timestamp, period, currency, metric definition, and source URL.
- New specialist claims flow through `ClaimGraphPatch` and Citation Audit.
- Specialists cannot produce `ReportDraft`, `FinalReport`, or bypass human gates.
- Missing credentials or tools produce `setup_required`, never fabricated evidence.

## Routing And Execution

Step 0 uses internal methods to refine `AuditCard` and framework selection. Step 1 uses executable data adapters and method-guided search patches. Step 2 runs marketing and finance specialists against `CleanSourceList`, returning `SpecialistNotes` and `ClaimGraphPatch`. Step 3 consumes only Citation-Audited claims.

The existing adapter matrix remains temporarily compatible but delegates selection to the internal catalog. Existing public helper functions retain their signatures during migration.

## Installation And Updates

`install.sh` copies the complete repository, including curated specialists and vendor snapshots, into `~/.codex/skills/search-agent`. It no longer installs separate top-level marketing and finance Skill trees.

Updating remains explicit:

```bash
git pull origin main
bash install.sh
```

A later `update.sh` may automate these commands, but automatic background updates are outside this implementation.

## Upstream Synchronization

Updating an upstream repository follows this controlled sequence:

1. Refresh the corresponding vendor snapshot.
2. Update `specialists/vendor.lock.json`.
3. Compare changes affecting curated capabilities.
4. Manually update curated prompts or adapters.
5. Run catalog, adapter, workflow, installation, and full regression tests.
6. Publish only after review.

Upstream content never overwrites curated adapters automatically.

## Compatibility

- Existing `vendor/marketing` and `vendor/finance` paths remain available during migration.
- Existing workflow node IDs and artifact names remain stable.
- Existing users with old top-level marketing/finance installations are not modified or deleted by the new installer.
- The doctor reports stale optional top-level copies but does not depend on them.

## Verification

Acceptance requires:

- Fresh installation creates only `~/.codex/skills/search-agent`.
- All 16 curated specialists resolve from the internal catalog.
- Marketing methods cannot become market evidence.
- Finance outputs retain numeric provenance fields.
- Missing dependencies return `setup_required`.
- Mixed marketing and finance requests can route to both specialists and merge only through `ClaimGraphPatch`.
- The complete test suite, compile checks, installer smoke test, and code review pass.
