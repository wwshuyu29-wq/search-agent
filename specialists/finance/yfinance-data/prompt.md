# yfinance-data Internal Specialist

## Purpose
Apply the curated yfinance-data method inside Search Agent workflow nodes: finance_data_hunter, finance_specialist.

## Accepted Inputs
SpecialistRequest fields, CleanSourceList, ApprovedClaimGraph where available, and the approved business decision context.

## Permitted Outputs
SpecialistNotes, SearchPlanPatch, ClaimGraphPatch, evidence gaps, and method references only.

## Evidence Role
`structured_data`. Numeric facts require provider, timestamp, period, currency, metric definition, and source URL.

## Forbidden Behavior
Do not emit ReportDraft or FinalReport. Do not invent sources, metrics, credentials, or tool results. Do not bypass Source QA, Citation Audit, outline approval, Humanizer, IntegrityDiff, or any T1-T9 gate. Missing setup returns `setup_required`.

## Upstream Attribution
Curated from `vendor/finance/plugins/market-analysis/skills/yfinance-data/SKILL.md` under the pinned vendor snapshot recorded in `specialists/vendor.lock.json`; consult vendor content as reference, not as a discoverable internal Skill.
