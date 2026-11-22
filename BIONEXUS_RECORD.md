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

Note on AD-02: the owner approved "the plan" and "the proposed direction and decisions". I read this as OD-1 and OD-2 answered. The spec text itself (`AGENT_INSTRUCTIONS.md`) is not edited yet; OD-1 amendments are recorded as approved wording and will be applied to the spec only when the owner confirms the edit to the file. This is logged as I-03.

## 2. Open issues
| ID | Issue | Blocks | Owner/next step |
|---|---|---|---|
| I-01 | Accession in both the Stage 1 plan and the locked U list (OD-3) | M5 | Owner |
| I-02 | Supervisor review of T-* and B-* (OD-4) | M4 freeze | Owner |
| I-03 | Apply OD-1 wording to `AGENT_INSTRUCTIONS.md` (file edit not yet authorized explicitly) | M1 spec parity only | Ask owner once, at M1 start |
| I-04 | Authorize Skills Pack and test-wording revision (OD-5) | M2 | Owner |
| I-08 | Roadmap, workflow chart and Antigravity prompts delivered; awaiting owner repo handoff (M0 items 5, 6) | M1 start | Owner |
| I-05 | Nemotron N2 and N1 not yet run (briefs ready: NEMOTRON_N2_PASTE.md, NEMOTRON_N1_PASTE.md) | M0 exit | Owner pastes; architect reviews |
| I-06 | Set B definition: pre-registered criteria not yet written | M5 | Architect, before any candidate is opened |
| I-07 | A3 read layout conflict (C-12 in master knowledge) | none for M1 | Note only |

## 3. Changes
| Date | File | Change | Reason |
|---|---|---|---|
| 2026-11-21 | BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md, ANTIGRAVITY_M1_PROMPTS.md, BIONEXUS_V1_WORKFLOW.png, NEMOTRON_N1_PASTE.md, NEMOTRON_N2_PASTE.md | New files per owner request; no existing file modified | Owner message 2026-11-21 04:21 |
| 2026-11-21 | BIONEXUS_V1_CONSOLIDATED_PLAN.md | Source-check statement corrected; status line set to approved baseline | Owner correction, approval |
| 2026-11-22 | src/bionexus/fileio.py, tests/unit/test_fileio.py | T1.3b (commit 2417c68, branch fix/t1-3b-t1-5b): a delimiter candidate that fails on quoting while another candidate is plausible only by reading a quote as literal text now gives not_assessable instead of a silent guess (D-T1.3-1); added `first_column_as_index` (first column as row labels; exact strings, duplicates preserved, input not mutated). +11 tests | Resolves D-T1.3-1. Adds the `first_column_as_index` helper; its integration into the parse-to-orientation data flow remains for T1.8. Owner authorization 2026-11-22 |
| 2026-11-22 | src/bionexus/representation.py, tests/unit/test_representation.py | T1.5b (commit 9e64cad, branch fix/t1-3b-t1-5b): cells (strings and Python ints) whose exact expansion exceeds 4000 digits are not_assessable (resource-safety bound, not a scientific threshold), closing a hang and a serialization failure on extreme exponents or huge integers (D-T1.5-1); R-05 annotation coverage is now reported on the non-numeric and no-values early-return paths (D-T1.5-2). +32 tests | Resolves D-T1.5-1 and D-T1.5-2. Owner authorization 2026-11-22 |

## 4. Validation results
Historical baseline: no tests or experiments had been recorded at the time of the previous record update.

| Date | Scope | Result |
|---|---|---|
| 2026-11-22 | T1.3b (2417c68) | 11 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | T1.5b (9e64cad) | 32 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | Full test suite on Windows (owner-reported) | 286 passed after both patches (focused fileio and representation tests: 135 passed) |
| 2026-11-22 | Post-commit remote verification of fix/t1-3b-t1-5b | All checks passed: two commits on top of 51d1bed (M1 T1.6), each with only its two intended files, content identical to the delivered patches, `git diff --check` clean |

## 5. Milestone state
M0: roadmap and prompts done; waiting on owner items 5 and 6 (repo + data path + deny-list). M1 can start once those are given. N1/N2 must finish by M1 exit, not before M1 start.

2026-11-22: T1.3b (2417c68) and T1.5b (9e64cad) are committed and pushed to `fix/t1-3b-t1-5b`. The branch is not merged into `implementation/m1-intake`; T1.8 depends on both.
