# Internal Specialists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert selected marketing and finance capabilities into internal Search Agent specialists and install only one top-level Codex Skill.

**Architecture:** A validated catalog resolves curated prompt resources and executable adapters. The workflow routes specialist requests through typed request/result contracts; specialist output can only enter `SpecialistNotes`, `SearchPlanPatch`, or `ClaimGraphPatch`, and remains subject to Source QA and Citation Audit. Full upstream snapshots remain under `vendor/` for controlled synchronization.

**Tech Stack:** Python 3.11, JSON manifests, unittest, Bash installer, existing workflow artifact contracts.

## Global Constraints

- Preserve all existing T1-T9 human and evidence gates.
- Do not expose internal specialist resources as top-level Codex Skills.
- Marketing method resources cannot support factual claims.
- Finance numeric output must include provider, timestamp, period, currency, metric definition, and source URL.
- Missing tools or credentials return `setup_required`; never fabricate results.
- Preserve existing workflow node IDs and public helper signatures during migration.
- Keep complete upstream snapshots and provenance under `vendor/`.

---

### Task 1: Curated Specialist Catalog And Registry

**Files:**
- Create: `specialists/catalog.json`
- Create: `specialists/vendor.lock.json`
- Create: `lib/specialist_registry.py`
- Create: `tests/test_specialist_registry.py`

**Interfaces:**
- Produces: `SpecialistRegistry(root: Path)`, `list_specialists(domain=None)`, `get_specialist(specialist_id)`, `resolve_prompt(specialist_id)`.
- Catalog entries contain `id`, `domain`, `nodes`, `trigger_terms`, `evidence_role`, `adapter`, `prompt_path`, `dependencies`, and `upstream_path`.

- [ ] Write failing tests asserting exactly eight marketing and eight finance core entries, unique IDs, existing upstream paths, allowed evidence roles, and rejection of malformed catalogs.
- [ ] Run `python3 -m unittest tests.test_specialist_registry -v`; expect import or assertion failures.
- [ ] Add the two manifests and registry validation implementation.
- [ ] Re-run the focused test; expect all tests to pass.
- [ ] Commit with `feat: add internal specialist registry`.

### Task 2: Curated Internal Prompt Resources

**Files:**
- Create: `specialists/marketing/<id>/prompt.md` for the eight approved marketing specialists.
- Create: `specialists/finance/<id>/prompt.md` for the eight approved finance specialists.
- Modify: `tests/test_specialist_registry.py`

**Interfaces:**
- Consumes: catalog `prompt_path` and `upstream_path`.
- Produces: internal prompt resources without YAML Skill frontmatter, each declaring purpose, accepted inputs, permitted outputs, evidence role, and forbidden behavior.

- [ ] Add failing tests requiring all prompt files, no `name:`/`description:` Skill frontmatter, and mandatory contract headings.
- [ ] Run the focused test and confirm missing-resource failures.
- [ ] Add concise curated prompt resources derived from the pinned upstream methods while preserving attribution in `vendor.lock.json`.
- [ ] Run the focused test and confirm success.
- [ ] Commit with `feat: curate marketing and finance specialists`.

### Task 3: Typed Router And Executor

**Files:**
- Create: `lib/specialist_router.py`
- Create: `lib/specialist_executor.py`
- Create: `tests/test_specialist_executor.py`

**Interfaces:**
- Produces: `route_specialists(query, node_id, domain=None, limit=3)`.
- Produces: `execute_specialist(request, adapters=None) -> SpecialistResult`.
- Request fields: `specialist_id`, `topic`, `decision`, `frameworks`, `clean_sources`, `approved_claims`, `node_id`.
- Result fields: `specialist_id`, `status`, `notes`, `claim_graph_patch`, `evidence_gaps`, `search_plan_patch`, `method_references`.

- [ ] Write failing tests for deterministic mixed-domain routing, request validation, allowed statuses, missing dependency `setup_required`, and rejection of direct report output.
- [ ] Run `python3 -m unittest tests.test_specialist_executor -v`; confirm RED.
- [ ] Implement router scoring from catalog triggers and executor schema/evidence-role enforcement.
- [ ] Re-run focused tests; confirm GREEN.
- [ ] Commit with `feat: execute internal specialists through contracts`.

### Task 4: Workflow Integration And Compatibility

**Files:**
- Modify: `lib/workflow_contracts.py`
- Modify: `lib/source_hunter_executor.py`
- Modify: `tests/test_workflow_contracts.py`
- Modify: `tests/test_source_hunter_executor.py`
- Modify: `tests/test_specialist_executor.py`

**Interfaces:**
- Consumes: registry/router/executor from Tasks 1-3.
- Produces: existing `SpecialistNotes`, `SearchPlanPatch`, `ClaimGraphPatch`, and method-source rows without changing artifact names.

- [ ] Add failing tests proving marketing and finance nodes use the internal catalog, mixed requests route to both domains, marketing methods remain `method_reference`, and specialist claims still require Citation Audit.
- [ ] Run the three focused test modules and confirm expected failures.
- [ ] Delegate legacy adapter selection to the internal router and replace direct vendor-path routing with registry resource resolution.
- [ ] Keep existing yfinance and optional provider adapters behind the executor registry.
- [ ] Run focused tests and confirm success.
- [ ] Commit with `feat: integrate specialists into research workflow`.

### Task 5: Single-Skill Installer And Doctor

**Files:**
- Modify: `install.sh`
- Modify: `uninstall.sh`
- Modify: `scripts/search_agent_doctor.py`
- Create: `tests/test_single_skill_install.py`
- Modify: `tests/test_tooling_preflight.py`

**Interfaces:**
- Installer creates only `$TARGET_DIR/search-agent`.
- Doctor validates internal catalog/resources and reports external top-level copies as optional stale installations.

- [ ] Write a failing temporary-directory installer test asserting no `$TARGET_DIR/marketing` or `$TARGET_DIR/finance`, all internal resources present, and existing unrelated directories untouched.
- [ ] Add failing doctor tests for catalog readiness and stale-copy warnings.
- [ ] Run focused tests and confirm RED.
- [ ] Remove top-level marketing/finance deployment from installer and update verification/output text; make uninstall remove only Search Agent-owned files.
- [ ] Update doctor checks.
- [ ] Run focused tests and an installer smoke test in a temporary target directory.
- [ ] Commit with `feat: install search agent as one codex skill`.

### Task 6: Documentation, Full Verification, And Release

**Files:**
- Modify: `README.md`
- Modify: `USAGE.md`
- Modify: `SKILL.md`
- Modify: `references/external-skills.md`
- Modify: `references/agent-nodes.md`
- Modify: `references/codex-execution.md`
- Modify: `tests/test_workflow_docs.py`

**Interfaces:**
- Documentation describes one top-level Skill, internal specialists, manual Git update behavior, controlled vendor synchronization, and optional external dependencies.

- [ ] Add failing documentation assertions for single-Skill installation and internal specialist terminology.
- [ ] Run `python3 -m unittest tests.test_workflow_docs -v`; confirm RED.
- [ ] Update user and technical documentation while preserving all 31 frameworks and T1-T9 gates.
- [ ] Run documentation tests.
- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run `python3 -m compileall -q lib tests bin scripts` and `git diff --check`.
- [ ] Run an independent code review and fix all Critical/P0/P1 findings.
- [ ] Commit with `docs: document internal specialist workflow` and push `main` to `origin` after final verification.
