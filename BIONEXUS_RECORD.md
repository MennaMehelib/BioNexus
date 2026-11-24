# BioNexus V1 — Working Record (decisions, issues, changes, validation)

Maintained by the lead architect. Every entry cites its source. Status words: Decided / Open / Proposed-gated / Done.

## 1. Accepted decisions

| ID | Decision | Source | Date |
|---|---|---|---|
| AD-01 | Consolidated plan and rule cards are the approved working baseline for V1 | Owner message 2026-11-21 02:12 | 2026-11-21 |
| AD-02 | Plan section 8 decisions accepted as written (DR-01..DR-09 decided by architect; DR-10 spec amendments, DR-11 register v1.0 approved in principle by the baseline approval) | Same message ("I agree with the proposed direction and decisions") | 2026-11-21 |
| AD-03 | GATED and CONDITIONAL rules stay proposed and disabled until their validation passes | Same message | 2026-11-21 |
| AD-04 | `PREPROCESSING_DECISION_MAP.md` exists; not relied on, including for Nemotron tasks | Owner clarification | 2026-11-21 |
| AD-05 | Changes only from a documented finding, test result or verified requirement | Owner message | 2026-11-21 |

Note on AD-02: the owner approved "the plan" and "the proposed direction and decisions". I read this as OD-1 and OD-2 answered. The spec text itself (`AGENT_INSTRUCTIONS.md`) is not edited yet; OD-1 amendments are recorded as approved wording and will be applied to the spec only when the owner explicitly confirms the file edit. This remains tracked as I-03.

## 2. Open issues

| ID | Issue | Blocks | Owner/next step |
|---|---|---|---|
| I-01 | Accession in both the Stage 1 plan and the locked U list (OD-3) | M5 | Owner |
| I-02 | Supervisor review of T-* and B-* (OD-4) | M4 freeze | Owner |
| I-03 | Apply OD-1 wording to `AGENT_INSTRUCTIONS.md`; the approved wording has not yet been applied to the file because explicit authorization for that file edit is still required | M1 spec parity only | Obtain explicit owner authorization before editing the file |
| I-04 | Authorize Skills Pack and test-wording revision (OD-5) | M2 | Owner |
| I-05 | Nemotron N2 and N1 have not yet been run (briefs ready: `NEMOTRON_N2_PASTE.md`, `NEMOTRON_N1_PASTE.md`) | M1 exit | Owner pastes; architect reviews |
| I-06 | Set B definition: pre-registered criteria not yet written | M5 | Architect, before any candidate is opened |
| I-07 | A3 read layout conflict (C-12 in master knowledge) | none for M1 | Note only |
| I-09 | Status: Open. Specification gap, not shown to be a conflict: the exact disposition of identical duplicate sample columns in derived outputs, and the stage at which it is handled, are not sufficiently specified. The sources use different wording that may or may not describe the same behavior: "record and keep one with note" (`BIONEXUS_V1_RULE_CARDS.md` L24, M-04); "R (flagged, original kept)" (`BIONEXUS_V1_SCIENTIFIC_TECHNICAL_DESIGN_V4.md` §4.1, L113); "Identical dup collapsed" with output "Duplicate record" (`BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md` L57); "identical duplicates recorded with a note" (`ANTIGRAVITY_M1_PROMPTS.md` T1.7, L121). `BIONEXUS_V1_CONSOLIDATED_PLAN.md` L152 says only "Exact duplicate samples and genes detected" and L338 says M1 has "No transformation, no gene mapping, no compatibility state, no batch." `AGENT_INSTRUCTIONS.md` §20: "Do not silently delete duplicates." Not stated: whether derived outputs keep all identical copies or one, and in which stage. Raw inputs stay unchanged either way (`BIONEXUS_V1_CONSOLIDATED_PLAN.md` L349, AC2: "Originals byte-identical before and after every run"). | Owner to set | Owner clarification |
| I-10 | Status: Open. Specification gap: handling of duplicate gene rows. `BIONEXUS_V1_RULE_CARDS.md` L24 (M-04) names sample IDs/columns only. `BIONEXUS_V1_SCIENTIFIC_TECHNICAL_DESIGN_V4.md` §4.1, L113 covers "Exact duplicate rows or samples". `BIONEXUS_V1_CONSOLIDATED_PLAN.md` L109 (P-13, output "Derived matrix") says "Exact duplicates collapsed with record; many-to-one aggregation by space (N-03)", and L164 lists N-03 as "ACCEPT-GATED (revised)"; L338 says M1 has "No transformation". `BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md` L57 says "Exact duplicate samples/genes". Not stated: whether and when exact duplicate gene rows are removed from a derived matrix, and whether that step belongs to M1 or to the later gated preprocessing stage. | Owner to set | Owner clarification |

## 3. Resolved issues

| ID | Resolution | Evidence | Date |
|---|---|---|---|
| I-08 | Resolved. The roadmap, workflow chart and Antigravity prompts were delivered, and the owner repo handoff took place. M1 implementation subsequently started; the earlier status "awaiting owner repo handoff / M1 start" is no longer current. | Delivered M0 artifacts; owner-provided repository at `D:\BioNexus`; subsequent M1 implementation activity | 2026-11-24 |
| I-11 | Resolved for T1.7. The duplicate comparison policy is implemented against parsed cell values rather than source-file byte identity. The accepted implementation defines the comparison behavior in `src/bionexus/duplicates.py`; source-file integrity remains a separate concern under AC2. | T1.7 duplicate implementation, commit `41d1ca3`; owner-approved I-11 correction and focused tests | 2026-11-24 |
| I-12 | Resolved and implemented under M-01. Metadata duplicate detection is handled by the dedicated `find_metadata_duplicates(metadata, id_column, scope="matrix")` helper, not by extending M-04 `find_duplicates()`. All metadata rows are retained. Repeated metadata IDs produce NEED_FACT records whether the corresponding rows are identical or conflicting; evidence distinguishes the two cases and identifies differing fields and values. The ID-column validation and blank-ID findings are reported separately under `M-01.metadata_id_column`. | Owner-approved I-12 decisions; implementation commit `45dedd8`; 107 focused metadata tests passed locally | 2026-11-24 |

## 4. Changes

| Date | File | Change | Reason |
|---|---|---|---|
| 2026-11-21 | BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md, ANTIGRAVITY_M1_PROMPTS.md, BIONEXUS_V1_WORKFLOW.png, NEMOTRON_N1_PASTE.md, NEMOTRON_N2_PASTE.md | New files per owner request; no existing file modified | Owner message 2026-11-21 04:21 |
| 2026-11-21 | BIONEXUS_V1_CONSOLIDATED_PLAN.md | Source-check statement corrected; status line set to approved baseline | Owner correction, approval |
| 2026-11-22 | src/bionexus/fileio.py, tests/unit/test_fileio.py | T1.3b (commit 2417c68, branch fix/t1-3b-t1-5b): a delimiter candidate that fails on quoting while another candidate is plausible only by reading a quote as literal text now gives not_assessable instead of a silent guess (D-T1.3-1); added `first_column_as_index` (first column as row labels; exact strings, duplicates preserved, input not mutated). +11 tests | Resolves D-T1.3-1. Adds the `first_column_as_index` helper; its integration into the parse-to-orientation data flow remains for T1.8. Owner authorization 2026-11-22 |
| 2026-11-22 | src/bionexus/representation.py, tests/unit/test_representation.py | T1.5b (commit 9e64cad, branch fix/t1-3b-t1-5b): cells (strings and Python ints) whose exact expansion exceeds 4000 digits are not_assessable (resource-safety bound, not a scientific threshold), closing a hang and a serialization failure on extreme exponents or huge integers (D-T1.5-1); R-05 annotation coverage is now reported on the non-numeric and no-values early-return paths (D-T1.5-2). +32 tests | Resolves D-T1.5-1 and D-T1.5-2. Owner authorization 2026-11-22 |
| 2026-11-24 | src/bionexus/duplicates.py, tests/unit/test_duplicates.py | T1.7 duplicate detection implementation and tests committed as `41d1ca3` | T1.7 duplicate detection implementation |
| 2026-11-24 | src/bionexus/metadata.py, tests/unit/test_metadata.py | T1.7 metadata checks (M-01, M-02, M-03), including the F1 positional-matching collision correction, committed as `033feba` | Implement approved metadata checks and prevent positional matching when normalized IDs collide |
| 2026-11-24 | src/bionexus/metadata.py, tests/unit/test_metadata.py | I-12 metadata duplicate detection committed separately as `45dedd8`; adds `find_metadata_duplicates()` and its evidence/tests without changing `find_duplicates()` or `match_samples()` | Implement the approved M-01 metadata duplicate-row behavior |

## 5. Validation results

Historical baseline: no tests or experiments had been recorded at the time of the previous record update.

| Date | Scope | Result |
|---|---|---|
| 2026-11-22 | T1.3b (2417c68) | 11 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | T1.5b (9e64cad) | 32 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | Full test suite on Windows (owner-reported) | 286 passed after both patches (focused fileio and representation tests: 135 passed) |
| 2026-11-22 | Post-commit remote verification of fix/t1-3b-t1-5b | All checks passed: two commits on top of 51d1bed (M1 T1.6), each with only its two intended files, content identical to the delivered patches, `git diff --check` clean |
| 2026-11-24 | T1.7 duplicate detection | Focused tests passed after I-11 correction (owner-confirmed); `git apply --reverse --check` confirmed the correction was applied |
| 2026-11-24 | T1.7 metadata checks and F1 correction (`033feba`) | Owner-reported local result: 70 tests passed in `tests/unit/test_metadata.py` |
| 2026-11-24 | T1.7 I-12 metadata duplicate detection (`45dedd8`) | Owner-reported local result: 107 tests passed in `tests/unit/test_metadata.py`; `git diff --check` clean |
| 2026-11-24 | T1.8 implementation report (not independently verified) | Antigravity reported 65 integration tests, 566 full-suite tests and AC8 PASS. These are agent-reported results only; independent review and local verification remain pending. |

## 6. Milestone state

M0: roadmap, workflow chart and prompts delivered; owner repo handoff completed. M1 implementation is underway. N1/N2 must finish by M1 exit, not before M1 start.

2026-11-22: T1.3b (2417c68) and T1.5b (9e64cad) were committed and pushed to `fix/t1-3b-t1-5b`, then merged into `implementation/m1-intake` through PR #1.

2026-11-24: T1.7 duplicate detection implementation was committed as `41d1ca3`. The metadata checks and F1 correction were committed separately as `033feba`; I-12 metadata duplicate detection was committed separately as `45dedd8`. The local branch `implementation/m1-intake` is two commits ahead of `origin/implementation/m1-intake` as of this record update; `033feba` and `45dedd8` have not yet been pushed. I-08, I-11 and I-12 are resolved. I-09 and I-10 remain open specification issues.

T1.8: implementation artifacts are present in the working tree, including `src/bionexus/cli.py`, `scripts/coverage_report.py` and `tests/integration/`. They have not yet been accepted or committed. The Antigravity implementation report is not a substitute for independent verification. T1.8 acceptance remains pending.

Pending T1.8 review items raised during the read-only review:
- Verify output-directory containment against all input-containing directories, including ancestor/descendant overlap and resolved paths.
- Verify that provenance and derived outputs cannot retain stale results from a previous run.
- Strengthen the G-01 NEED_FACT integration test to assert the required independent checks and their records.
- Correct the G-04 unreadable-input test so it actually tests an unreadable file rather than a missing file.
- Verify AC5 value preservation for G-01 BLOCKED and G-03 NEED_FACT paths.
- Verify dependency handling when metadata parsing fails.
- Verify behavior when initial S0 hashing fails and no valid expected hash is available.
- Verify that the single-column metadata fallback preserves the required parse/change provenance.
- Verify that reused output directories cannot expose stale `oriented_matrix.tsv`, `sample_matches.json` or `representation_evidence.json` outputs.

These are review findings requiring verification and disposition; they are not recorded as resolved defects or approved specification changes. No T1.8 acceptance should be inferred until the relevant code, tests, and outputs have been independently reviewed.
